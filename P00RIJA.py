#!/usr/bin/env python3
import os
import sys
import time
import stat
import re
import socket
import struct
import threading
import json
import hashlib
import hmac
import uuid
import secrets
import ssl
import base64
import select
import signal
import gc
import resource
import ctypes
import subprocess
import tempfile
import zipfile
import tarfile
import gzip
import io
import shutil
import pty
from queue import Queue, Empty, Full
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --------- Constants & Configuration ----------
CONFIG_DIR = os.environ.get("P00RIJA_CONFIG_DIR", "/opt/p00rija")
CONFIG_PATH = os.environ.get("P00RIJA_CONFIG_PATH", f"{CONFIG_DIR}/p00rija_config.json")
DB_PATH = os.environ.get("P00RIJA_DB_PATH", f"{CONFIG_DIR}/p00rija_db.json")
PANEL_SECRET_PATH = os.environ.get("P00RIJA_PANEL_SECRET_PATH", f"{CONFIG_DIR}/panel_secret")
SSH_VAULT_PATH = os.environ.get("P00RIJA_SSH_VAULT_PATH", f"{CONFIG_DIR}/ssh_credentials.enc")
ENGINES_DIR = os.environ.get("P00RIJA_ENGINES_DIR", "/usr/local/bin")
SOCKBUF = 8 * 1024 * 1024
BUF_COPY = 256 * 1024
def env_float(name, default, minimum):
    try:
        return max(minimum, float(os.environ.get(name, str(default))))
    except Exception:
        return default

POOL_WAIT = env_float("P00RIJA_POOL_WAIT", 5.0, 0.5)
SYNC_INTERVAL = env_float("P00RIJA_SYNC_INTERVAL", 3.0, 1.0)
DIAL_TIMEOUT = env_float("P00RIJA_DIAL_TIMEOUT", 5.0, 1.0)
APP_VERSION = "1.3.3"
APP_BUILD = "ui-tunnel-node-monitor-polish-20260607"
APP_LICENSE = "GPL-3.0"
APP_AUTHOR_GITHUB = "https://github.com/Poorija"
APP_AUTHOR_EMAIL = "mohammadmahdi.farhadianfard@gmail.com"
NODE_ENROLLMENT_API_KEY = os.environ.get("P00RIJA_NODE_API_KEY", "")
PANEL_TLS_FORCED = True
try:
    MAX_REVERSE_WORKERS_PER_LINK = max(1, int(os.environ.get("P00RIJA_MAX_REVERSE_WORKERS_PER_LINK", "4")))
except Exception:
    MAX_REVERSE_WORKERS_PER_LINK = 4
try:
    MAX_POOL_SIZE_PER_LINK = max(1, int(os.environ.get("P00RIJA_MAX_POOL_SIZE_PER_LINK", "64")))
except Exception:
    MAX_POOL_SIZE_PER_LINK = 64
node_ping_lock = threading.Lock()
node_ping_inflight = set()
ssh_sessions = {}
ssh_sessions_lock = threading.Lock()
APP_LOGO_SVG = """<svg id="Layer_1" xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 256 256">
  <defs>
    <style>
      .st0, .st1 {
        stroke: #3a86ff;
      }

      .st0, .st1, .st2, .st3, .st4 {
        stroke-linecap: round;
        stroke-linejoin: round;
      }

      .st0, .st4 {
        fill: #fff;
        stroke-width: 4px;
      }

      .st1, .st2 {
        stroke-width: 16px;
      }

      .st1, .st2, .st3 {
        fill: none;
      }

      .st2, .st4 {
        stroke: #00ebff;
      }

      .st3 {
        stroke: #7000ff;
        stroke-dasharray: 4 6;
        stroke-width: 3px;
      }

      .st5 {
        fill: #0b132b;
      }
    </style>
  </defs>
  <rect class="st5" width="256" height="256" rx="40.96" ry="40.96"/>
  <path class="st2" d="M51.2,102.4h153.6M204.8,102.4l-25.6-25.6M204.8,102.4l-25.6,25.6"/>
  <path class="st1" d="M204.8,153.6H51.2M51.2,153.6l25.6-25.6M51.2,153.6l25.6,25.6"/>
  <line class="st3" x1="128" y1="39.21" x2="128" y2="216.79"/>
  <circle class="st0" cx="128" cy="102.4" r="12.8"/>
  <circle class="st4" cx="128" cy="153.6" r="12.8"/>
</svg>"""

# Global runtime variables
active_sessions = {}  # token -> login_time
active_sessions_lock = threading.Lock()
active_bridges = {}   # session_id -> BridgeSession
active_bridges_lock = threading.Lock()
temp_echo_servers = {}
temp_echo_servers_lock = threading.Lock()

# --------- System Metrics Collector (Linux Only) ----------
class NetSpeedometer:
    def __init__(self):
        self.last_rx = 0
        self.last_tx = 0
        self.last_time = time.time()
        self.last_rx, self.last_tx = self.get_bytes()

    def get_bytes(self):
        rx, tx = 0, 0
        try:
            with open("/proc/net/dev", "r") as f:
                lines = f.readlines()
            for line in lines[2:]:
                parts = line.split()
                if len(parts) >= 10:
                    if "lo" in parts[0] or "docker" in parts[0] or "veth" in parts[0]:
                        continue
                    rx += int(parts[1])
                    tx += int(parts[9])
        except Exception:
            pass
        return rx, tx

    def sample(self):
        now = time.time()
        rx, tx = self.get_bytes()
        dt = now - self.last_time
        if dt <= 0:
            return 0, 0
        rx_speed = (rx - self.last_rx) / dt
        tx_speed = (tx - self.last_tx) / dt
        if rx_speed < 0: rx_speed = 0
        if tx_speed < 0: tx_speed = 0
        self.last_rx = rx
        self.last_tx = tx
        self.last_time = now
        return rx_speed, tx_speed

def get_cpu_percent():
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        parts = [int(x) for x in line.split()[1:5]]
        total = sum(parts)
        idle = parts[3]
        return total, idle
    except Exception:
        return 0, 0

def get_host_info():
    info = {
        "cpu_cores": os.cpu_count() or 1,
        "load_avg": [],
        "uptime_seconds": 0,
        "ram_total_gb": 0,
        "ram_free_gb": 0,
        "swap_total_gb": 0,
        "swap_free_gb": 0,
        "disk_total_gb": 0,
        "disk_free_gb": 0,
        "panel_pid": os.getpid(),
        "panel_rss_mb": 0,
        "docker": {
            "available": False,
            "containers_running": 0,
            "containers_total": 0,
            "images": 0,
            "version": ""
        }
    }
    try:
        info["load_avg"] = [round(x, 2) for x in os.getloadavg()]
    except Exception:
        pass
    try:
        with open("/proc/uptime", "r") as f:
            info["uptime_seconds"] = int(float(f.read().split()[0]))
    except Exception:
        pass
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("MemTotal:"):
                    info["ram_total_gb"] = round(int(line.split()[1]) / (1024 * 1024), 2)
                elif line.startswith("MemAvailable:"):
                    info["ram_free_gb"] = round(int(line.split()[1]) / (1024 * 1024), 2)
                elif line.startswith("SwapTotal:"):
                    info["swap_total_gb"] = round(int(line.split()[1]) / (1024 * 1024), 2)
                elif line.startswith("SwapFree:"):
                    info["swap_free_gb"] = round(int(line.split()[1]) / (1024 * 1024), 2)
    except:
        pass
    try:
        st = os.statvfs("/")
        info["disk_total_gb"] = round((st.f_blocks * st.f_frsize) / (1024**3), 2)
        info["disk_free_gb"] = round((st.f_bavail * st.f_frsize) / (1024**3), 2)
    except:
        pass
    try:
        info["panel_rss_mb"] = round(get_own_rss_kb() / 1024, 1)
    except Exception:
        pass
    try:
        if os.path.exists("/var/run/docker.sock") or subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True, timeout=2).returncode == 0:
            info["docker"]["available"] = True
            ver = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True, timeout=2)
            if ver.returncode == 0:
                info["docker"]["version"] = ver.stdout.strip()
            ps = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=2)
            if ps.returncode == 0:
                info["docker"]["containers_running"] = len([x for x in ps.stdout.splitlines() if x.strip()])
            psa = subprocess.run(["docker", "ps", "-aq"], capture_output=True, text=True, timeout=2)
            if psa.returncode == 0:
                info["docker"]["containers_total"] = len([x for x in psa.stdout.splitlines() if x.strip()])
            imgs = subprocess.run(["docker", "images", "-q"], capture_output=True, text=True, timeout=2)
            if imgs.returncode == 0:
                info["docker"]["images"] = len(set(x.strip() for x in imgs.stdout.splitlines() if x.strip()))
    except Exception:
        pass
    return info

def get_ram_percent():
    try:
        mem = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mem[parts[0].rstrip(":")] = int(parts[1])
        total = mem.get("MemTotal", 0)
        free = mem.get("MemFree", 0)
        buffers = mem.get("Buffers", 0)
        cached = mem.get("Cached", 0)
        used = total - free - buffers - cached
        return (used / total) * 100 if total > 0 else 0
    except Exception:
        return 0.0

def default_tunnel_profiles():
    return {
        "easy": {
            "name": "Easy",
            "engine": "builtin",
            "tunnel_mode": "websocket",
            "transport": "websocket",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 80,
            "obfs_host": "speedtest.net",
            "obfs_path": "/assets/ws",
            "padding_min": 0,
            "padding_max": 32,
            "jitter_ms": 0,
            "keepalive_interval": 25
        },
        "hard": {
            "name": "Hard",
            "engine": "gost",
            "tunnel_mode": "http_obfs",
            "transport": "ws",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 140,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/cdn-cgi/trace",
            "padding_min": 16,
            "padding_max": 128,
            "jitter_ms": 20,
            "keepalive_interval": 18
        },
        "resilient": {
            "name": "Resilient",
            "engine": "backhaul",
            "tunnel_mode": "websocket",
            "transport": "wsmux",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 220,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/updates/connect",
            "padding_min": 32,
            "padding_max": 256,
            "jitter_ms": 40,
            "keepalive_interval": 12
        },
        "gost_grpc": {
            "name": "GOST gRPC",
            "engine": "gost",
            "tunnel_mode": "grpc",
            "transport": "grpc",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 120,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/grpc",
            "padding_min": 8,
            "padding_max": 96,
            "jitter_ms": 10,
            "keepalive_interval": 20
        },
        "frp_tcp_udp": {
            "name": "FRP TCP/UDP",
            "engine": "frp",
            "tunnel_mode": "tcp_udp",
            "transport": "tcp",
            "network": "tcp_udp",
            "tls_enabled": False,
            "pool_size": 80,
            "obfs_host": "localhost",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 0,
            "jitter_ms": 0,
            "keepalive_interval": 30
        },
        "rathole_ws": {
            "name": "Rathole WebSocket",
            "engine": "rathole",
            "tunnel_mode": "websocket",
            "transport": "ws",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 100,
            "obfs_host": "cdn.jsdelivr.net",
            "obfs_path": "/assets",
            "padding_min": 16,
            "padding_max": 160,
            "jitter_ms": 25,
            "keepalive_interval": 18
        },
        "chisel_reverse": {
            "name": "Chisel Reverse",
            "engine": "chisel",
            "tunnel_mode": "websocket",
            "transport": "ws",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 90,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/connect",
            "padding_min": 0,
            "padding_max": 80,
            "jitter_ms": 15,
            "keepalive_interval": 25
        },
        "xray_vless_reality": {
            "name": "Xray VLESS Reality",
            "engine": "xray",
            "tunnel_mode": "vless_reality",
            "transport": "tcp",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 60,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/",
            "xray_protocol": "vless",
            "xray_security": "reality",
            "xray_flow": "xtls-rprx-vision",
            "padding_min": 0,
            "padding_max": 64,
            "jitter_ms": 5,
            "keepalive_interval": 30
        },
        "rathole_tcp": {
            "name": "Rathole TCP",
            "engine": "rathole",
            "tunnel_mode": "tcp",
            "transport": "tcp",
            "network": "tcp",
            "tls_enabled": False,
            "pool_size": 100,
            "obfs_host": "localhost",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 0,
            "jitter_ms": 0,
            "keepalive_interval": 25
        },
        "rathole_wss": {
            "name": "Rathole WSS",
            "engine": "rathole",
            "tunnel_mode": "websocket",
            "transport": "wss",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 120,
            "obfs_host": "cdn.jsdelivr.net",
            "obfs_path": "/npm/package",
            "padding_min": 8,
            "padding_max": 128,
            "jitter_ms": 15,
            "keepalive_interval": 18
        },
        "backhaul_tcpmux": {
            "name": "Backhaul TCPMux",
            "engine": "backhaul",
            "tunnel_mode": "tcpmux",
            "transport": "tcpmux",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 180,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/connect",
            "padding_min": 16,
            "padding_max": 192,
            "jitter_ms": 25,
            "keepalive_interval": 12,
            "mux_session": 8,
            "mux_version": 2,
            "mux_framesize": 32768
        },
        "backhaul_udp": {
            "name": "Backhaul UDP",
            "engine": "backhaul",
            "tunnel_mode": "udp",
            "transport": "udp",
            "network": "udp",
            "tls_enabled": False,
            "pool_size": 100,
            "obfs_host": "localhost",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 32,
            "jitter_ms": 10,
            "keepalive_interval": 15,
            "accept_udp": True
        },
        "gost_ws_grpc": {
            "name": "GOST WS/gRPC",
            "engine": "gost",
            "tunnel_mode": "grpc",
            "transport": "grpc",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 140,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/grpc",
            "padding_min": 8,
            "padding_max": 160,
            "jitter_ms": 20,
            "keepalive_interval": 18
        },
        "frp_kcp": {
            "name": "FRP KCP",
            "engine": "frp",
            "tunnel_mode": "kcp",
            "transport": "kcp",
            "network": "udp",
            "tls_enabled": False,
            "pool_size": 80,
            "obfs_host": "localhost",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 64,
            "jitter_ms": 10,
            "keepalive_interval": 25
        },
        "chisel_reverse_tls": {
            "name": "Chisel Reverse TLS",
            "engine": "chisel",
            "tunnel_mode": "websocket",
            "transport": "wss",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 90,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/api/connect",
            "padding_min": 0,
            "padding_max": 96,
            "jitter_ms": 12,
            "keepalive_interval": 25
        },
        "muxquantum_httpsmux": {
            "name": "Mux/Quantum HTTPSMux",
            "engine": "muxquantum",
            "tunnel_mode": "httpsmux",
            "transport": "httpsmux",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 4,
            "obfs_host": "www.google.com",
            "obfs_path": "/search",
            "padding_min": 16,
            "padding_max": 256,
            "jitter_ms": 10,
            "keepalive_interval": 8
        },
        "muxquantum_quantummux": {
            "name": "Mux/Quantum QuantumMux",
            "engine": "muxquantum",
            "tunnel_mode": "quantummux",
            "transport": "quantummux",
            "network": "tcp",
            "tls_enabled": False,
            "pool_size": 4,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 0,
            "jitter_ms": 0,
            "keepalive_interval": 15
        },
        "muxquantum_tunmux": {
            "name": "Mux/Quantum TunMux (TCP)",
            "engine": "muxquantum",
            "tunnel_mode": "tunmux",
            "transport": "tunmux",
            "network": "tcp",
            "tls_enabled": False,
            "pool_size": 2,
            "obfs_host": "",
            "obfs_path": "",
            "padding_min": 0,
            "padding_max": 0,
            "jitter_ms": 0,
            "keepalive_interval": 15
        },
        "hysteria2_quic": {
            "name": "Hysteria 2 QUIC",
            "engine": "hysteria2",
            "tunnel_mode": "quic",
            "transport": "quic",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 60,
            "obfs_host": "www.apple.com",
            "obfs_path": "/",
            "padding_min": 8,
            "padding_max": 96,
            "jitter_ms": 8,
            "keepalive_interval": 20
        },
        "hysteria2_http3_masquerade": {
            "name": "Hysteria2 HTTP/3 Masquerade",
            "engine": "hysteria2",
            "tunnel_mode": "http3_masquerade",
            "transport": "h3",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 80,
            "obfs_host": "www.bing.com",
            "obfs_path": "/",
            "padding_min": 8,
            "padding_max": 128,
            "jitter_ms": 12,
            "keepalive_interval": 18
        },
        "singbox_reality_vision": {
            "name": "sing-box VLESS REALITY Vision",
            "engine": "singbox",
            "tunnel_mode": "vless_reality",
            "transport": "tcp",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 70,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/",
            "xray_protocol": "vless",
            "xray_security": "reality",
            "xray_flow": "xtls-rprx-vision",
            "padding_min": 0,
            "padding_max": 80,
            "jitter_ms": 6,
            "keepalive_interval": 25
        },
        "singbox_shadowtls_ws": {
            "name": "sing-box ShadowTLS + WebSocket",
            "engine": "singbox",
            "tunnel_mode": "shadowtls_ws",
            "transport": "shadowtls",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 100,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/cdn-cgi/trace",
            "padding_min": 16,
            "padding_max": 160,
            "jitter_ms": 15,
            "keepalive_interval": 20
        },
        "tuic_quic_web": {
            "name": "TUIC QUIC Web-like",
            "engine": "tuic",
            "tunnel_mode": "tuic_quic",
            "transport": "tuic",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 70,
            "obfs_host": "www.apple.com",
            "obfs_path": "/",
            "padding_min": 8,
            "padding_max": 128,
            "jitter_ms": 10,
            "keepalive_interval": 16
        },
        "naiveproxy_https": {
            "name": "NaiveProxy HTTPS Camouflage",
            "engine": "naiveproxy",
            "tunnel_mode": "naive_https",
            "transport": "naive",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 80,
            "obfs_host": "www.google.com",
            "obfs_path": "/generate_204",
            "padding_min": 0,
            "padding_max": 96,
            "jitter_ms": 8,
            "keepalive_interval": 25
        },
        "shadowtls_v3_web": {
            "name": "ShadowTLS v3 Web Handshake",
            "engine": "shadowtls",
            "tunnel_mode": "shadowtls",
            "transport": "shadowtls",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 90,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/",
            "padding_min": 8,
            "padding_max": 128,
            "jitter_ms": 12,
            "keepalive_interval": 20
        },
        "brook_wss_web": {
            "name": "Brook WSS Web",
            "engine": "brook",
            "tunnel_mode": "websocket",
            "transport": "wss",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 90,
            "obfs_host": "cdn.jsdelivr.net",
            "obfs_path": "/npm/package",
            "padding_min": 12,
            "padding_max": 144,
            "jitter_ms": 14,
            "keepalive_interval": 18
        },
        "mieru_http2_tls": {
            "name": "Mieru HTTP/2 TLS",
            "engine": "mieru",
            "tunnel_mode": "http2_tls",
            "transport": "h2",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 100,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/",
            "padding_min": 16,
            "padding_max": 160,
            "jitter_ms": 15,
            "keepalive_interval": 20
        },
        "singbox_anytls": {
            "name": "sing-box AnyTLS",
            "engine": "singbox",
            "tunnel_mode": "anytls",
            "transport": "anytls",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 90,
            "obfs_host": "www.apple.com",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 128,
            "jitter_ms": 10,
            "keepalive_interval": 20
        },
        "ultra_stealth_naive_chrome_h2": {
            "name": "Ultra Stealth Naive Chrome HTTP/2",
            "engine": "naiveproxy",
            "tunnel_mode": "naive_h2",
            "transport": "h2",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 96,
            "obfs_host": "www.google.com",
            "obfs_path": "/generate_204",
            "padding_min": 0,
            "padding_max": 64,
            "jitter_ms": 6,
            "keepalive_interval": 25,
            "tls_fingerprint": "chrome",
            "stealth_profile": "browser_https"
        },
        "ultra_stealth_hysteria2_gecko": {
            "name": "Ultra Stealth Hysteria2 Gecko HTTP/3",
            "engine": "hysteria2",
            "tunnel_mode": "hysteria2_gecko",
            "transport": "h3",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 80,
            "obfs_host": "www.bing.com",
            "obfs_path": "/",
            "padding_min": 16,
            "padding_max": 192,
            "jitter_ms": 18,
            "keepalive_interval": 18,
            "obfs_layer": "gecko",
            "stealth_profile": "http3_masquerade"
        },
        "ultra_stealth_hysteria2_salamander": {
            "name": "Ultra Stealth Hysteria2 Salamander",
            "engine": "hysteria2",
            "tunnel_mode": "hysteria2_salamander",
            "transport": "quic",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 76,
            "obfs_host": "www.apple.com",
            "obfs_path": "/",
            "padding_min": 12,
            "padding_max": 160,
            "jitter_ms": 14,
            "keepalive_interval": 18,
            "obfs_layer": "salamander",
            "stealth_profile": "quic_obfs"
        },
        "ultra_stealth_reality_grpc": {
            "name": "Ultra Stealth REALITY gRPC",
            "engine": "singbox",
            "tunnel_mode": "reality_grpc",
            "transport": "grpc",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 72,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/grpc",
            "xray_protocol": "vless",
            "xray_security": "reality",
            "xray_flow": "xtls-rprx-vision",
            "padding_min": 0,
            "padding_max": 80,
            "jitter_ms": 8,
            "keepalive_interval": 24,
            "stealth_profile": "reality_grpc"
        },
        "ultra_stealth_reality_h2": {
            "name": "Ultra Stealth REALITY HTTP/2",
            "engine": "singbox",
            "tunnel_mode": "reality_h2",
            "transport": "h2",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 72,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/",
            "xray_protocol": "vless",
            "xray_security": "reality",
            "xray_flow": "xtls-rprx-vision",
            "padding_min": 0,
            "padding_max": 80,
            "jitter_ms": 8,
            "keepalive_interval": 24,
            "stealth_profile": "reality_h2"
        },
        "ultra_stealth_shadowtls_h2": {
            "name": "Ultra Stealth ShadowTLS HTTP/2",
            "engine": "shadowtls",
            "tunnel_mode": "shadowtls_h2",
            "transport": "shadowtls",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 96,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/cdn-cgi/trace",
            "padding_min": 12,
            "padding_max": 128,
            "jitter_ms": 12,
            "keepalive_interval": 20,
            "stealth_profile": "shadowtls_h2"
        },
        "ultra_stealth_anytls_h2": {
            "name": "Ultra Stealth AnyTLS HTTP/2",
            "engine": "singbox",
            "tunnel_mode": "anytls_h2",
            "transport": "anytls",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 96,
            "obfs_host": "www.apple.com",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 128,
            "jitter_ms": 10,
            "keepalive_interval": 20,
            "stealth_profile": "anytls_h2"
        },
        "ultra_stealth_tuic_quic_migration": {
            "name": "Ultra Stealth TUIC QUIC Migration",
            "engine": "tuic",
            "tunnel_mode": "tuic_quic",
            "transport": "tuic",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 78,
            "obfs_host": "www.apple.com",
            "obfs_path": "/",
            "padding_min": 12,
            "padding_max": 160,
            "jitter_ms": 12,
            "keepalive_interval": 16,
            "stealth_profile": "quic_migration"
        },
        "muxquantum_wss_web": {
            "name": "Mux/Quantum WSS Web",
            "engine": "muxquantum",
            "tunnel_mode": "mux_wss",
            "transport": "mux_wss",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 4,
            "obfs_host": "cdn.jsdelivr.net",
            "obfs_path": "/npm/package",
            "padding_min": 24,
            "padding_max": 224,
            "jitter_ms": 16,
            "keepalive_interval": 10,
            "cover_protocol": "websocket_tls"
        },
        "muxquantum_h2_tls": {
            "name": "Mux/Quantum HTTP/2 TLS",
            "engine": "muxquantum",
            "tunnel_mode": "mux_h2",
            "transport": "mux_h2",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 4,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/",
            "padding_min": 16,
            "padding_max": 192,
            "jitter_ms": 14,
            "keepalive_interval": 10,
            "cover_protocol": "http2_tls"
        },
        "muxquantum_h3_quic": {
            "name": "Mux/Quantum HTTP/3 QUIC",
            "engine": "muxquantum",
            "tunnel_mode": "mux_h3",
            "transport": "mux_h3",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 4,
            "obfs_host": "www.bing.com",
            "obfs_path": "/",
            "padding_min": 16,
            "padding_max": 224,
            "jitter_ms": 18,
            "keepalive_interval": 9,
            "cover_protocol": "http3_quic"
        },
        "muxquantum_reality_vision": {
            "name": "Mux/Quantum REALITY Vision",
            "engine": "muxquantum",
            "tunnel_mode": "mux_reality",
            "transport": "mux_reality",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 3,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 96,
            "jitter_ms": 8,
            "keepalive_interval": 12,
            "cover_protocol": "reality_vision"
        },
        "muxquantum_shadowtls": {
            "name": "Mux/Quantum ShadowTLS",
            "engine": "muxquantum",
            "tunnel_mode": "mux_shadowtls",
            "transport": "mux_shadowtls",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 3,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/cdn-cgi/trace",
            "padding_min": 12,
            "padding_max": 160,
            "jitter_ms": 12,
            "keepalive_interval": 12,
            "cover_protocol": "shadowtls"
        },
        "muxquantum_anytls": {
            "name": "Mux/Quantum AnyTLS",
            "engine": "muxquantum",
            "tunnel_mode": "mux_anytls",
            "transport": "mux_anytls",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 3,
            "obfs_host": "www.apple.com",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 128,
            "jitter_ms": 10,
            "keepalive_interval": 12,
            "cover_protocol": "anytls"
        },
        "muxquantum_naive_https": {
            "name": "Mux/Quantum Naive HTTPS",
            "engine": "muxquantum",
            "tunnel_mode": "mux_naive",
            "transport": "mux_naive",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 3,
            "obfs_host": "www.google.com",
            "obfs_path": "/generate_204",
            "padding_min": 0,
            "padding_max": 96,
            "jitter_ms": 8,
            "keepalive_interval": 12,
            "cover_protocol": "naive_https"
        },
        "muxquantum_grpc_tls": {
            "name": "Mux/Quantum gRPC TLS",
            "engine": "muxquantum",
            "tunnel_mode": "mux_grpc",
            "transport": "mux_grpc",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 4,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/grpc",
            "padding_min": 8,
            "padding_max": 160,
            "jitter_ms": 14,
            "keepalive_interval": 10,
            "cover_protocol": "grpc_tls"
        },
        "muxquantum_quic_udp": {
            "name": "Mux/Quantum QUIC UDP",
            "engine": "muxquantum",
            "tunnel_mode": "mux_quic",
            "transport": "mux_quic",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 4,
            "obfs_host": "www.apple.com",
            "obfs_path": "/",
            "padding_min": 12,
            "padding_max": 160,
            "jitter_ms": 14,
            "keepalive_interval": 9,
            "cover_protocol": "quic"
        },
        "singbox_ech_h2_experimental": {
            "name": "sing-box ECH HTTP/2 Experimental",
            "engine": "singbox",
            "tunnel_mode": "ech_h2",
            "transport": "ech",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 72,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/",
            "padding_min": 0,
            "padding_max": 96,
            "jitter_ms": 8,
            "keepalive_interval": 24,
            "experimental": True,
            "stealth_profile": "ech_h2"
        }
    }

def ensure_tunnel_profiles():
    profiles = db.data["settings"].setdefault("tunnel_profiles", {})
    defaults = default_tunnel_profiles()
    changed = False
    for profile_id, profile in defaults.items():
        if profile_id not in profiles:
            profiles[profile_id] = profile
            changed = True
    return profiles, changed

def normalize_role(role):
    if role in ("iran", "internal"):
        return "internal"
    if role in ("eu", "foreign", "external"):
        return "external"
    return role

def role_matches(node_role, desired):
    return normalize_role(node_role) == normalize_role(desired)

def node_public_from_private(private_key):
    return hashlib.sha256(str(private_key).encode()).hexdigest()

def make_node_keypair():
    private_key = secrets.token_urlsafe(32)
    return private_key, node_public_from_private(private_key)

def normalize_node_token(token):
    token = str(token or "").strip()
    if token and not token.startswith("tok_") and re.fullmatch(r"[0-9a-fA-F]{16}", token):
        return f"tok_{token.lower()}"
    return token

def valid_node_signature(node, path, payload_text, signature):
    private_key = node.get("private_key", "")
    if not private_key:
        return True
    expected = hmac.new(private_key.encode(), f"{path}\n{payload_text or ''}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")

def hysteria2_config_for_link(link, role):
    psk = link.get("xray_uuid") or str(uuid.uuid4())
    listen_port = int(link.get("bridge_port", 7000))
    sni = link.get("tls_sni", "speedtest.net")
    
    if normalize_role(role) == "external":
        return {
            "listen": f":{listen_port}",
            "tls": {
                "cert": f"{CONFIG_DIR}/certs/cert.pem",
                "key": f"{CONFIG_DIR}/certs/key.pem"
            },
            "auth": {
                "type": "password",
                "password": psk
            },
            "bandwidth": {
                "up": "1000 mbps",
                "down": "1000 mbps"
            }
        }
    
    tcp_fw = []
    for p in link.get("ports", []):
        tcp_fw.append({
            "listen": f"0.0.0.0:{p.get('user_port', p.get('target_port'))}",
            "target": f"127.0.0.1:{p.get('target_port', 443)}"
        })
        
    other_ip = link.get("external_ip", link.get("iran_ip", "127.0.0.1"))
    if ":" in other_ip:
        other_ip = f"[{other_ip}]"
        
    return {
        "server": f"{other_ip}:{listen_port}",
        "auth": psk,
        "tls": {
            "sni": sni,
            "insecure": True
        },
        "bandwidth": {
            "up": "1000 mbps",
            "down": "1000 mbps"
        },
        "tcpForwarding": tcp_fw
    }

def muxquantum_config_for_link(lid, link, role, other_ip):
    psk = str(lid)
    transport = link.get("transport", link.get("tunnel_mode", "httpsmux"))
    bridge_port = int(link.get("bridge_port", 7000))
    cover_by_transport = {
        "httpsmux": "https",
        "mux_wss": "websocket_tls",
        "mux_h2": "http2_tls",
        "mux_h3": "http3_quic",
        "mux_quic": "quic",
        "mux_shadowtls": "shadowtls",
        "mux_reality": "reality_vision",
        "mux_anytls": "anytls",
        "mux_naive": "naive_https",
        "mux_grpc": "grpc_tls",
        "mux_kcp": "kcp_udp"
    }
    cover_protocol = link.get("cover_protocol") or cover_by_transport.get(transport, transport)
    cover = {
        "protocol": cover_protocol,
        "sni": link.get("tls_sni") or link.get("obfs_host", "www.cloudflare.com"),
        "host": link.get("obfs_host", "www.cloudflare.com"),
        "path": link.get("obfs_path", "/"),
        "fingerprint": link.get("tls_fingerprint", "chrome"),
        "alpn": "h3" if transport in ("mux_h3", "mux_quic") else ("h2" if transport in ("mux_h2", "mux_grpc", "mux_naive") else "http/1.1")
    }
    
    ports = link.get("ports", [])
    maps = []
    for p in ports:
        maps.append({
            "type": "tcp",
            "bind": f"0.0.0.0:{p.get('bridge_port', p.get('target_port'))}",
            "target": f"127.0.0.1:{p.get('target_port')}"
        })
    if not maps:
        maps.append({"type": "tcp", "bind": f"0.0.0.0:{bridge_port+1}", "target": "127.0.0.1:443"})

    obfs = {
        "enabled": True if link.get("padding_max", 0) > 0 else False,
        "min_padding": link.get("padding_min", 0),
        "max_padding": link.get("padding_max", 0),
        "burst_chance": 0.15
    }

    if normalize_role(role) == "external":
        return {
            "mode": "server",
            "psk": psk,
            "listeners": [{
                "addr": f"0.0.0.0:{bridge_port}",
                "transport": transport,
                "network": link.get("network", "tcp"),
                "maps": maps,
                "cover": cover
            }],
            "tls": {
                "enabled": bool(link.get("tls_enabled", False)),
                "sni": cover["sni"],
                "fingerprint": cover["fingerprint"]
            },
            "obfuscation": obfs
        }
    return {
        "mode": "client",
        "psk": psk,
        "paths": [{
            "transport": transport,
            "addr": f"{other_ip}:{bridge_port}",
            "network": link.get("network", "tcp"),
            "cover": cover,
            "connection_pool": link.get("pool_size", 2),
            "retry_interval": 3
        }],
        "tls": {
            "enabled": bool(link.get("tls_enabled", False)),
            "sni": cover["sni"],
            "fingerprint": cover["fingerprint"],
            "insecure": bool(link.get("tls_insecure", False))
        },
        "obfuscation": obfs
    }

def xray_config_for_link(link, role):
    protocol = link.get("xray_protocol", "vless")
    security = link.get("xray_security", "reality")
    listen_port = int(link.get("bridge_port", 7000))
    target_port = int((link.get("ports") or [{"target_port": 443}])[0].get("target_port", 443))
    
    server_names = [s.strip() for s in link.get("xray_sni", "www.microsoft.com").split(",") if s.strip()]
    if not server_names:
        server_names = ["www.microsoft.com"]
    
    private_key = link.get("xray_private_key", "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM=")
    public_key = link.get("xray_public_key", "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM=")
    short_id = link.get("xray_shortid", "0123456789abcdef")
    flow = link.get("xray_flow", "xtls-rprx-vision")
    uuid_val = link.get("xray_uuid") or str(uuid.uuid4())

    if normalize_role(role) == "external":
        return {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "tag": "p00rija-xray-in",
                "port": listen_port,
                "protocol": protocol,
                "settings": {
                    "clients": [{"id": uuid_val, "flow": flow}],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": security,
                    "realitySettings": {
                        "show": False,
                        "dest": "1.1.1.1:443",
                        "xver": 0,
                        "serverNames": server_names,
                        "privateKey": private_key,
                        "shortIds": [short_id]
                    }
                }
            }],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}]
        }
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{"tag": "p00rija-socks-in", "port": target_port, "listen": "127.0.0.1", "protocol": "socks"}],
        "outbounds": [{
            "tag": "p00rija-xray-out",
            "protocol": protocol,
            "settings": {
                "vnext": [{
                    "address": link.get("external_ip", link.get("iran_ip", "127.0.0.1")), 
                    "port": listen_port, 
                    "users": [{"id": uuid_val, "flow": flow, "encryption": "none"}]
                }]
            },
            "streamSettings": {
                "network": "tcp", 
                "security": security,
                "realitySettings": {
                    "show": False,
                    "fingerprint": "chrome",
                    "serverName": server_names[0],
                    "publicKey": public_key,
                    "shortId": short_id,
                    "spiderX": ""
                }
            }
        }]
    }

def make_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

def verify_totp(secret, code, window=1):
    code = str(code or "").strip().replace(" ", "")
    if not secret or len(code) != 6 or not code.isdigit():
        return False
    try:
        padded = secret + "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(padded, casefold=True)
    except Exception:
        return False
    counter = int(time.time() // 30)
    for offset in range(-window, window + 1):
        msg = struct.pack(">Q", counter + offset)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        pos = digest[-1] & 0x0F
        token = (struct.unpack(">I", digest[pos:pos + 4])[0] & 0x7FFFFFFF) % 1000000
        if hmac.compare_digest(f"{token:06d}", code):
            return True
    return False

def is_ip_address(value):
    try:
        socket.inet_pton(socket.AF_INET, value)
        return True
    except Exception:
        try:
            socket.inet_pton(socket.AF_INET6, value)
            return True
        except Exception:
            return False

def normalize_cert_host(host):
    host = str(host or "").strip()
    if "://" in host:
        parsed = urlparse(host)
        host = parsed.hostname or host
    if host.startswith("[") and "]" in host:
        host = host[1:host.index("]")]
    if ":" in host and not is_ip_address(host):
        host = host.split(":", 1)[0]
    if not host or len(host) > 253 or any(ch in host for ch in "\\/'\"`$;|&<> \t\r\n"):
        return "localhost"
    return host

def unique_cert_hosts(primary_host=None):
    hosts = []
    for item in (
        primary_host,
        "localhost",
        "127.0.0.1",
        "::1",
        socket.gethostname(),
        socket.getfqdn(),
    ):
        host = normalize_cert_host(item)
        if host and host not in hosts:
            hosts.append(host)
    return hosts

def generate_local_panel_certificate(host="localhost", cert_path=None, key_path=None):
    cert_dir = f"{CONFIG_DIR}/certs"
    os.makedirs(cert_dir, exist_ok=True)
    cert_path = cert_path or f"{cert_dir}/cert.pem"
    key_path = key_path or f"{cert_dir}/key.pem"
    cfg_path = f"{cert_dir}/local-cert-openssl.cnf"
    hosts = unique_cert_hosts(host)
    san_parts = [f"{'IP' if is_ip_address(item) else 'DNS'}:{item}" for item in hosts]
    common_name = hosts[0] if hosts else "localhost"
    with open(cfg_path, "w") as f:
        f.write(
            "[req]\n"
            "distinguished_name=req_distinguished_name\n"
            "x509_extensions=v3_req\n"
            "prompt=no\n"
            "[req_distinguished_name]\n"
            f"CN={common_name}\n"
            "[v3_req]\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth\n"
            f"subjectAltName={','.join(san_parts)}\n"
        )
    res = subprocess.run([
        "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
        "-days", "825", "-keyout", key_path, "-out", cert_path,
        "-config", cfg_path
    ], capture_output=True, text=True, timeout=30)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "OpenSSL failed")
    os.chmod(key_path, 0o600)
    os.chmod(cert_path, 0o644)
    return cert_path, key_path

def certificate_is_self_signed(cert_path):
    try:
        res = subprocess.run(
            ["openssl", "x509", "-noout", "-subject", "-issuer", "-in", cert_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode != 0:
            return False
        subject = ""
        issuer = ""
        for line in res.stdout.splitlines():
            if line.startswith("subject="):
                subject = line.split("=", 1)[1].strip()
            elif line.startswith("issuer="):
                issuer = line.split("=", 1)[1].strip()
        return bool(subject and issuer and subject == issuer)
    except Exception:
        return False

# --------- Database Manager ----------
class P00RIJADB:
    def __init__(self, filepath=DB_PATH):
        self.filepath = filepath
        self.lock = threading.Lock()
        self.data = {
            "admin": {
                "username": "admin",
                "password_hash": hashlib.sha256(b"admin").hexdigest()
            },
            "settings": {
                "port": 8080,
                "test_interval": 30,
                "max_idle_seconds": 300,
                "panel_tls": True,
                "cert_path": f"{CONFIG_DIR}/certs/cert.pem",
                "key_path": f"{CONFIG_DIR}/certs/key.pem",
                "two_factor_enabled": False,
                "two_factor_secret": "",
                "biometric_enabled": False,
                "node_api_key": NODE_ENROLLMENT_API_KEY,
                "tunnel_profiles": default_tunnel_profiles()
            },
            "nodes": {},
            "links": {},
            "node_commands": {},
            "logs": []
        }
        self.load()

    def load(self):
        with self.lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r") as f:
                        loaded = json.load(f)
                        for k in self.data:
                            if k in loaded:
                                # Ensure settings handles nested keys safely
                                if k == "settings":
                                    self.data[k].update(loaded[k])
                                else:
                                    self.data[k] = loaded[k]
                except Exception as e:
                    print(f"Error loading DB: {e}")

    def save(self):
        with self.lock:
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                tmp_path = f"{self.filepath}.tmp"
                with open(tmp_path, "w") as f:
                    json.dump(self.data, f, indent=4)
                os.chmod(tmp_path, 0o600)
                os.replace(tmp_path, self.filepath)
            except Exception as e:
                print(f"Error saving DB: {e}")

    def log(self, source, level, message):
        print(f"[{source.upper()}] [{level.upper()}] {message}", flush=True)
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "level": level,
            "message": message
        }
        with self.lock:
            self.data.setdefault("logs", []).append(entry)
            if len(self.data["logs"]) > 1000:
                self.data["logs"] = self.data["logs"][-1000:]
        self.save()

db = P00RIJADB()

def ensure_panel_https_config(config=None):
    settings = db.data.setdefault("settings", {})
    host = (
        settings.get("panel_host")
        or (config or {}).get("panel_host")
        or (config or {}).get("host")
        or "localhost"
    )
    cert_path = settings.get("cert_path") or f"{CONFIG_DIR}/certs/cert.pem"
    key_path = settings.get("key_path") or f"{CONFIG_DIR}/certs/key.pem"
    regenerated = False
    default_cert = f"{CONFIG_DIR}/certs/cert.pem"
    default_key = f"{CONFIG_DIR}/certs/key.pem"
    legacy_auto_cert = (
        cert_path == default_cert
        and key_path == default_key
        and os.path.isfile(cert_path)
        and os.path.isfile(key_path)
        and settings.get("cert_auto_generated") is None
        and certificate_is_self_signed(cert_path)
    )
    if not os.path.isfile(cert_path) or not os.path.isfile(key_path) or legacy_auto_cert:
        cert_path, key_path = generate_local_panel_certificate(host, cert_path, key_path)
        regenerated = True
    settings["panel_tls"] = True
    settings["cert_path"] = cert_path
    settings["key_path"] = key_path
    settings["panel_host"] = normalize_cert_host(host)
    if regenerated:
        settings["cert_auto_generated"] = True
    db.save()
    if regenerated:
        db.log("panel", "info", f"Generated automatic local HTTPS certificate for {settings['panel_host']}.")
    return cert_path, key_path

# --------- TCP Socket Tuning ----------
def tune_tcp(sock: socket.socket):
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKBUF)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKBUF)
    except Exception:
        pass
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, "TCP_KEEPIDLE"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 20)
        if hasattr(socket, "TCP_KEEPINTVL"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        if hasattr(socket, "TCP_KEEPCNT"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    except Exception:
        pass

def tune_listener_socket(sock: socket.socket):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except Exception:
            pass

def dial_tcp(ip, port):
    db.log("system", "info", f"[DEBUG] dial_tcp attempting to connect to {ip}:{port}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tune_tcp(s)
    s.settimeout(DIAL_TIMEOUT)
    try:
        s.connect((ip, port))
        s.settimeout(None)
        db.log("system", "info", f"[DEBUG] dial_tcp SUCCESS connecting to {ip}:{port}")
        return s
    except Exception as e:
        db.log("system", "error", f"[DEBUG] dial_tcp FAILED connecting to {ip}:{port}: {e}")
        raise e

def recv_exact(sock, n: int):
    data = bytearray()
    while len(data) < n:
        try:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return None
            data.extend(chunk)
        except Exception:
            return None
    return bytes(data)

def is_socket_alive(sock):
    if isinstance(sock, ssl.SSLSocket):
        return True
    try:
        readable, _, _ = select.select([sock], [], [], 0)
        if not readable:
            return True
        data = sock.recv(1, socket.MSG_PEEK)
        if data == b"":
            db.log("system", "error", f"[DEBUG] is_socket_alive: socket closed by peer (recv returned b'')")
            return False
        return True
    except BlockingIOError:
        return True
    except Exception as e:
        db.log("system", "error", f"[DEBUG] is_socket_alive: exception {e}")
        return False

def clamp_int(value, default, minimum, maximum):
    try:
        value = int(value)
    except Exception:
        return default
    return max(minimum, min(maximum, value))

def valid_port(value):
    try:
        port = int(value)
    except Exception:
        return False
    return 1 <= port <= 65535

def is_tcp_port_open(host, port, timeout=0.35):
    try:
        port = int(port)
        if not valid_port(port):
            return False
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def is_local_tcp_listening(port):
    try:
        port = int(port)
        if not valid_port(port):
            return False
        wanted = f"{port:04X}"
        inspected_proc = False
        for path in ("/proc/net/tcp", "/proc/net/tcp6"):
            if not os.path.exists(path):
                continue
            inspected_proc = True
            with open(path, "r") as f:
                for line in f.readlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 4 and parts[3] == "0A" and parts[1].split(":")[1].upper() == wanted:
                        return True
        if not inspected_proc:
            return is_tcp_port_open("127.0.0.1", port, timeout=0.2)
        return False
    except Exception:
        return is_tcp_port_open("127.0.0.1", port, timeout=0.2)

def read_runtime_network_mode():
    try:
        path = os.path.join(CONFIG_DIR, ".network_mode")
        if os.path.exists(path):
            mode = open(path, "r").read().strip()
            if mode in ("host", "bridge"):
                return mode
    except Exception:
        pass
    try:
        if os.path.exists("/.dockerenv"):
            return "docker"
    except Exception:
        pass
    return "unknown"

def apply_ipv6_disabled(disable_ipv6):
    applied = []
    errors = []
    value = "1" if disable_ipv6 else "0"
    for key in ("net.ipv6.conf.all.disable_ipv6", "net.ipv6.conf.default.disable_ipv6", "net.ipv6.conf.lo.disable_ipv6"):
        try:
            res = subprocess.run(["sysctl", "-w", f"{key}={value}"], capture_output=True, text=True, timeout=4)
            if res.returncode == 0:
                applied.append(res.stdout.strip())
            else:
                errors.append(res.stderr.strip() or res.stdout.strip() or key)
        except Exception as e:
            errors.append(f"{key}: {e}")
    return {"success": not errors, "applied": applied, "errors": errors}

def normalize_tags(value):
    if value is None:
        return []
    if isinstance(value, str):
        raw_tags = [part.strip() for part in value.replace("،", ",").split(",")]
    elif isinstance(value, list):
        raw_tags = [str(part).strip() for part in value]
    else:
        raw_tags = []
    tags = []
    seen = set()
    for tag in raw_tags:
        safe = "".join(ch for ch in tag if ch.isalnum() or ch in ("-", "_", " ", ".", "#"))[:24].strip()
        if safe and safe.lower() not in seen:
            tags.append(safe)
            seen.add(safe.lower())
        if len(tags) >= 8:
            break
    return tags

def ensure_panel_secret():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(PANEL_SECRET_PATH):
        with open(PANEL_SECRET_PATH, "w") as f:
            f.write(secrets.token_urlsafe(48))
        os.chmod(PANEL_SECRET_PATH, 0o600)
    with open(PANEL_SECRET_PATH, "r") as f:
        return f.read().strip()

def encrypt_json_to_file(payload, path):
    secret = ensure_panel_secret()
    raw = json.dumps(payload, ensure_ascii=False).encode()
    proc = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", f"pass:{secret}", "-out", path],
        input=raw,
        capture_output=True
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="ignore") or "openssl encryption failed")
    os.chmod(path, 0o600)

def decrypt_json_from_file(path, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    secret = ensure_panel_secret()
    proc = subprocess.run(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", f"pass:{secret}", "-in", path],
        capture_output=True
    )
    if proc.returncode != 0:
        return default
    try:
        return json.loads(proc.stdout.decode())
    except Exception:
        return default

def load_ssh_vault():
    data = decrypt_json_from_file(SSH_VAULT_PATH, {"nodes": {}})
    if not isinstance(data, dict):
        data = {"nodes": {}}
    data.setdefault("nodes", {})
    return data

def save_ssh_vault(data):
    data.setdefault("nodes", {})
    encrypt_json_to_file(data, SSH_VAULT_PATH)

def sanitize_ssh_credential(cred):
    if not isinstance(cred, dict):
        return {}
    return {
        "host": cred.get("host", ""),
        "port": cred.get("port", 22),
        "username": cred.get("username", ""),
        "auth_method": cred.get("auth_method", "password"),
        "has_password": bool(cred.get("password")),
        "has_private_key": bool(cred.get("private_key")),
        "saved_at": cred.get("saved_at", 0)
    }

def safe_ping_host(host, count=1, timeout=1):
    if not host:
        return {"ok": False, "avg_ms": None, "loss": 100, "output": "No host"}
    try:
        res = subprocess.run(["ping", "-c", str(count), "-W", str(timeout), str(host)], capture_output=True, text=True, timeout=max(2, count * (timeout + 1)))
        output = (res.stdout or "") + (res.stderr or "")
        avg_ms = None
        match = re.search(r"= [\d.]+/([\d.]+)/", output)
        if not match:
            match = re.search(r"time=([\d.]+)", output)
        if match:
            avg_ms = float(match.group(1))
        loss = 100
        loss_match = re.search(r"(\d+(?:\.\d+)?)%\s*packet loss", output)
        if loss_match:
            loss = float(loss_match.group(1))
        return {"ok": res.returncode == 0, "avg_ms": avg_ms, "loss": loss, "output": output[-2000:]}
    except Exception as e:
        return {"ok": False, "avg_ms": None, "loss": 100, "output": str(e)}

def refresh_node_ping_async(node_id, node, max_age=20):
    now = time.time()
    stats = node.setdefault("stats", {})
    if now - stats.get("ping_checked_at", 0) < max_age:
        return
    with node_ping_lock:
        if node_id in node_ping_inflight:
            return
        node_ping_inflight.add(node_id)

    def worker():
        try:
            result = safe_ping_host(node.get("ip"), count=1, timeout=1)
            stats = node.setdefault("stats", {})
            stats["ping_checked_at"] = time.time()
            stats["ping_status"] = "ok" if result["ok"] else "failed"
            if result["avg_ms"] is not None:
                stats["ping_ms"] = round(result["avg_ms"], 1)
            else:
                stats.pop("ping_ms", None)
            db.save()
        finally:
            with node_ping_lock:
                node_ping_inflight.discard(node_id)

    threading.Thread(target=worker, daemon=True).start()

ENGINE_CATALOG = {
    "xray": {"bins": ["xray"], "repo": "XTLS/Xray-core"},
    "gost": {"bins": ["gost"], "repo": "go-gost/gost"},
    "backhaul": {"bins": ["backhaul"], "repo": "Musixal/Backhaul"},
    "rathole": {"bins": ["rathole"], "repo": "rapiz1/rathole"},
    "chisel": {"bins": ["chisel"], "repo": "jpillora/chisel"},
    "frp": {"bins": ["frpc", "frps"], "repo": "fatedier/frp"},
    "hysteria2": {"bins": ["hysteria", "hysteria2"], "repo": "apernet/hysteria"},
    "singbox": {"bins": ["sing-box", "singbox"], "repo": "SagerNet/sing-box"},
    "tuic": {"bins": ["sing-box", "singbox", "tuic-server", "tuic-client"], "repo": "tuic-protocol/tuic"},
    "naiveproxy": {"bins": ["naive", "naiveproxy"], "repo": "klzgrad/naiveproxy"},
    "shadowtls": {"bins": ["shadow-tls", "shadowtls"], "repo": "ihciah/shadow-tls"},
    "brook": {"bins": ["brook"], "repo": "txthinking/brook"},
    "mieru": {"bins": ["mieru", "mita"], "repo": "enfein/mieru"},
    "muxquantum": {"bins": [], "repo": "builtin"}
}

def engine_binary_path(binary):
    for base in (ENGINES_DIR, os.path.join(os.getcwd(), "engines"), "/app/engines"):
        path = os.path.join(base, binary)
        if os.path.exists(path):
            return path
    return ""

def list_engine_status():
    manifest_path = os.path.join(ENGINES_DIR, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}
    engines = {}
    for engine_id, info in ENGINE_CATALOG.items():
        paths = [engine_binary_path(binary) for binary in info.get("bins", [])]
        paths = [p for p in paths if p]
        installed = engine_id == "muxquantum" or bool(paths)
        engines[engine_id] = {
            "repo": info.get("repo"),
            "installed": installed,
            "paths": paths,
            "enabled": any(os.access(p, os.X_OK) for p in paths) or engine_id == "muxquantum",
            "version": manifest.get("engines", {}).get(engine_id, {}).get("tag", "bundled" if installed else ""),
            "asset": manifest.get("engines", {}).get(engine_id, {}).get("asset", "")
        }
    return engines

def control_engine_process(engine_id, action):
    info = ENGINE_CATALOG.get(engine_id)
    if not info:
        return {"success": False, "error": "Unknown engine"}
    paths = [engine_binary_path(binary) for binary in info.get("bins", [])]
    paths = [p for p in paths if p]
    killed = 0
    if action in ("stop", "restart"):
        names = [os.path.basename(p) for p in paths] + info.get("bins", [])
        for name in set(names):
            if name:
                subprocess.run(["pkill", "-f", name], capture_output=True)
                killed += 1
    if action in ("start", "restart"):
        for path in paths:
            try:
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception:
                pass
    return {"success": True, "action": action, "matched": len(paths), "signals": killed}

def check_engine_health(engine_id):
    if engine_id == "muxquantum":
        return {"success": True, "engine": engine_id, "healthy": True, "message": "Built-in Mux/Quantum engine is available."}
    info = ENGINE_CATALOG.get(engine_id)
    if not info:
        return {"success": False, "engine": engine_id, "healthy": False, "message": "Unknown engine"}
    paths = [engine_binary_path(binary) for binary in info.get("bins", [])]
    paths = [p for p in paths if p]
    if not paths:
        return {"success": True, "engine": engine_id, "healthy": False, "message": "Engine binary was not found.", "paths": []}
    results = []
    healthy = False
    for path in paths[:2]:
        executable = os.access(path, os.X_OK)
        version_out = ""
        if executable:
            for args in ([path, "--version"], [path, "-version"], [path, "version"]):
                try:
                    res = subprocess.run(args, capture_output=True, text=True, timeout=3)
                    version_out = (res.stdout or res.stderr or "").strip().splitlines()[0] if (res.stdout or res.stderr) else ""
                    healthy = healthy or res.returncode in (0, 1)
                    if version_out:
                        break
                except Exception:
                    continue
        results.append({"path": path, "executable": executable, "version": version_out})
    return {
        "success": True,
        "engine": engine_id,
        "healthy": healthy or any(r["executable"] for r in results),
        "message": "Engine binary is executable." if any(r["executable"] for r in results) else "Engine binary exists but is not executable.",
        "results": results
    }

def install_engine_archive(engine_id, filename, content):
    info = ENGINE_CATALOG.get(engine_id)
    if not info:
        raise ValueError("Unknown engine")
    wanted = set(info.get("bins", []))
    if not wanted:
        raise ValueError("This engine is built-in and has no external binary")
    os.makedirs(ENGINES_DIR, exist_ok=True)
    installed = []
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "extract")
        os.makedirs(root, exist_ok=True)
        archive = os.path.join(td, filename or "engine.bin")
        with open(archive, "wb") as f:
            f.write(content)
        if filename.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                z.extractall(root)
        elif filename.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive, "r:gz") as t:
                t.extractall(root)
        elif filename.endswith((".tar.xz", ".txz")):
            with tarfile.open(archive, "r:xz") as t:
                t.extractall(root)
        elif filename.endswith(".gz"):
            out_name = filename[:-3]
            with gzip.open(archive, "rb") as gz, open(os.path.join(root, out_name), "wb") as out:
                out.write(gz.read())
        else:
            shutil.copy2(archive, os.path.join(root, filename))
        for dirpath, _, filenames in os.walk(root):
            for item in filenames:
                if item in wanted:
                    dest = os.path.join(ENGINES_DIR, item)
                    shutil.copy2(os.path.join(dirpath, item), dest)
                    os.chmod(dest, os.stat(dest).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    installed.append(item)
    if not installed:
        raise ValueError("No expected engine binary found in archive")
    return installed

def execute_ssh_command(cred, command):
    host = str(cred.get("host", "")).strip()
    username = str(cred.get("username", "root")).strip() or "root"
    port = clamp_int(cred.get("port", 22), 22, 1, 65535)
    timeout = clamp_int(cred.get("timeout", 15), 15, 3, 120)
    if not host:
        raise ValueError("SSH host is empty")
    if not command:
        command = "uname -a && uptime"
    if len(command) > 1000:
        raise ValueError("Command is too long")

    base_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"ConnectTimeout={timeout}",
        "-p", str(port)
    ]
    env = os.environ.copy()
    temp_key = None
    try:
        if cred.get("auth_method") == "key" and cred.get("private_key"):
            fd, temp_key = tempfile.mkstemp(prefix="p00rija-ssh-key-")
            with os.fdopen(fd, "w") as f:
                f.write(cred.get("private_key", "").strip() + "\n")
            os.chmod(temp_key, 0o600)
            base_cmd += ["-i", temp_key, "-o", "BatchMode=yes"]
        elif cred.get("password"):
            if not shutil.which("sshpass"):
                raise RuntimeError("sshpass is not installed in the panel container")
            env["SSHPASS"] = cred.get("password", "")
            base_cmd = ["sshpass", "-e"] + base_cmd
        else:
            base_cmd += ["-o", "BatchMode=yes"]
        cmd = base_cmd + [f"{username}@{host}", command]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5, env=env)
        return {
            "success": res.returncode == 0,
            "returncode": res.returncode,
            "stdout": (res.stdout or "")[-12000:],
            "stderr": (res.stderr or "")[-4000:]
        }
    finally:
        if temp_key:
            try:
                os.remove(temp_key)
            except Exception:
                pass

def merge_ssh_credential(node_id, body):
    if node_id not in db.data.get("nodes", {}):
        raise KeyError("Node not found")
    vault = load_ssh_vault()
    saved = vault.get("nodes", {}).get(node_id, {})
    cred = dict(saved)
    for key in ("host", "port", "username", "auth_method", "password", "private_key", "timeout"):
        if body.get(key) not in (None, ""):
            cred[key] = body.get(key)
    if not cred.get("host"):
        cred["host"] = db.data["nodes"][node_id].get("ip", "")
    cred["port"] = clamp_int(cred.get("port", 22), 22, 1, 65535)
    cred["timeout"] = clamp_int(cred.get("timeout", 15), 15, 3, 120)
    cred["username"] = str(cred.get("username") or "root")[:80]
    cred["auth_method"] = cred.get("auth_method", "password") if cred.get("auth_method") in ("password", "key") else "password"
    return cred, vault

def save_ssh_credential_if_requested(node_id, cred, vault, should_save):
    if should_save:
        vault.setdefault("nodes", {})[node_id] = dict(cred, saved_at=time.time())
        save_ssh_vault(vault)

def make_ssh_base_command(cred, interactive=False):
    host = str(cred.get("host", "")).strip()
    username = str(cred.get("username", "root")).strip() or "root"
    port = clamp_int(cred.get("port", 22), 22, 1, 65535)
    timeout = clamp_int(cred.get("timeout", 15), 15, 3, 120)
    if not host:
        raise ValueError("SSH host is empty")
    base_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"ConnectTimeout={timeout}",
        "-o", "ServerAliveInterval=20",
        "-o", "ServerAliveCountMax=3",
        "-p", str(port)
    ]
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    temp_key = None
    if cred.get("auth_method") == "key" and cred.get("private_key"):
        fd, temp_key = tempfile.mkstemp(prefix="p00rija-ssh-key-")
        with os.fdopen(fd, "w") as f:
            f.write(cred.get("private_key", "").strip() + "\n")
        os.chmod(temp_key, 0o600)
        base_cmd += ["-i", temp_key, "-o", "BatchMode=yes"]
    elif cred.get("password"):
        if not shutil.which("sshpass"):
            raise RuntimeError("sshpass is not installed in the panel container")
        env["SSHPASS"] = cred.get("password", "")
        base_cmd = ["sshpass", "-e"] + base_cmd
    else:
        base_cmd += ["-o", "BatchMode=yes"]
    if interactive:
        base_cmd += ["-tt"]
    return base_cmd + [f"{username}@{host}"], env, temp_key

def cleanup_ssh_session(session_id):
    session = None
    with ssh_sessions_lock:
        session = ssh_sessions.pop(session_id, None)
    if not session:
        return
    proc = session.get("proc")
    if proc and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
    for fd_key in ("master_fd",):
        try:
            os.close(session.get(fd_key))
        except Exception:
            pass
    temp_key = session.get("temp_key")
    if temp_key:
        try:
            os.remove(temp_key)
        except Exception:
            pass

def read_ssh_session_output(session_id, max_bytes=65536):
    with ssh_sessions_lock:
        session = ssh_sessions.get(session_id)
    if not session:
        return "", False
    output = bytearray()
    fd = session["master_fd"]
    while len(output) < max_bytes:
        try:
            chunk = os.read(fd, min(4096, max_bytes - len(output)))
            if not chunk:
                break
            output.extend(chunk)
        except BlockingIOError:
            break
        except OSError:
            break
    session["last_read"] = time.time()
    proc = session.get("proc")
    alive = bool(proc and proc.poll() is None)
    if not alive:
        cleanup_ssh_session(session_id)
    return output.decode("utf-8", "replace"), alive

def start_ssh_session(node_id, body):
    cred, vault = merge_ssh_credential(node_id, body)
    save_ssh_credential_if_requested(node_id, cred, vault, body.get("save"))
    cmd, env, temp_key = make_ssh_base_command(cred, interactive=True)
    master_fd, slave_fd = pty.openpty()
    os.set_blocking(master_fd, False)
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            close_fds=True,
            preexec_fn=os.setsid,
        )
    finally:
        try:
            os.close(slave_fd)
        except Exception:
            pass
    session_id = secrets.token_hex(16)
    with ssh_sessions_lock:
        ssh_sessions[session_id] = {
            "node_id": node_id,
            "proc": proc,
            "master_fd": master_fd,
            "temp_key": temp_key,
            "started_at": time.time(),
            "last_read": time.time(),
        }
    time.sleep(0.2)
    output, alive = read_ssh_session_output(session_id)
    return session_id, output, alive, sanitize_ssh_credential(cred)

def write_ssh_session(session_id, data):
    with ssh_sessions_lock:
        session = ssh_sessions.get(session_id)
    if not session:
        raise KeyError("SSH session not found")
    proc = session.get("proc")
    if not proc or proc.poll() is not None:
        cleanup_ssh_session(session_id)
        raise RuntimeError("SSH session is closed")
    raw = str(data or "").encode("utf-8", "replace")
    if len(raw) > 8192:
        raise ValueError("SSH input is too large")
    os.write(session["master_fd"], raw)
    session["last_read"] = time.time()

def prune_ssh_sessions(max_idle=900):
    now = time.time()
    stale = []
    with ssh_sessions_lock:
        for sid, session in list(ssh_sessions.items()):
            proc = session.get("proc")
            if (proc and proc.poll() is not None) or now - session.get("last_read", now) > max_idle:
                stale.append(sid)
    for sid in stale:
        cleanup_ssh_session(sid)

def recommend_tunnel_profile(internal_node, external_node, internal_ping, external_ping):
    avg_values = [x.get("avg_ms") for x in (internal_ping, external_ping) if x.get("avg_ms") is not None]
    avg = sum(avg_values) / len(avg_values) if avg_values else 999
    loss = max(internal_ping.get("loss", 100), external_ping.get("loss", 100))
    stats_i = internal_node.get("stats", {})
    stats_e = external_node.get("stats", {})
    high_load = max(float(stats_i.get("cpu", 0) or 0), float(stats_e.get("cpu", 0) or 0), float(stats_i.get("ram", 0) or 0), float(stats_e.get("ram", 0) or 0)) > 80
    if high_load:
        return "easy", "منابع یکی از نودها تحت فشار است؛ پروفایل سبک‌تر پیشنهاد شد."
    if loss >= 40 or avg > 250:
        return "ultra_stealth_naive_chrome_h2", "کیفیت مسیر ضعیف/ناپایدار است؛ پوشش HTTPS/HTTP2 کم‌ریسک‌تر پیشنهاد شد."
    if avg < 140 and loss < 20:
        return "ultra_stealth_hysteria2_gecko", "مسیر UDP/QUIC قابل قبول به نظر می‌رسد؛ HTTP/3 Masquerade پیشنهاد شد."
    return "ultra_stealth_reality_h2", "برای شرایط متوسط، REALITY روی HTTP/2 تعادل خوبی بین پایداری و مخفی‌سازی دارد."

def sanitize_nodes_for_status(nodes):
    safe = {}
    for node_id, node in nodes.items():
        safe[node_id] = {
            key: value for key, value in node.items()
            if key not in ("token", "private_key")
        }
    return safe

def list_runtime_sessions():
    now = time.time()
    with active_bridges_lock:
        sessions = []
        for sid, session in active_bridges.items():
            sessions.append({
                "id": str(sid),
                "source": "panel",
                "node_id": "",
                "node_name": "Panel",
                "link_id": session.link_id,
                "target_port": session.target_port,
                "age_seconds": round(now - session.created_at, 1),
                "idle_seconds": round(now - session.last_activity, 1)
            })
        return sessions

def get_node_runtime_sessions():
    sessions = []
    now = time.time()
    for node_id, node in db.data.get("nodes", {}).items():
        if now - node.get("last_seen", 0) > 30:
            continue
        for session in node.get("stats", {}).get("runtime_sessions", []) or []:
            if not isinstance(session, dict):
                continue
            item = dict(session)
            item["source"] = "node"
            item["node_id"] = node_id
            item["node_name"] = node.get("name", node_id)
            item["id"] = f"{node_id}:{item.get('id', '')}"
            sessions.append(item)
    return sessions

def list_all_runtime_sessions():
    return list_runtime_sessions() + get_node_runtime_sessions()

def get_node_process_snapshot(limit_per_node=10):
    processes = []
    now = time.time()
    for node_id, node in db.data.get("nodes", {}).items():
        if now - node.get("last_seen", 0) > 30:
            continue
        for proc in node.get("stats", {}).get("processes", [])[:limit_per_node]:
            if not isinstance(proc, dict):
                continue
            item = dict(proc)
            item["source"] = "node"
            item["node_id"] = node_id
            item["node_name"] = node.get("name", node_id)
            processes.append(item)
    return processes

def get_all_process_snapshot():
    panel_processes = []
    for proc in get_process_snapshot():
        item = dict(proc)
        item["source"] = "panel"
        item["node_id"] = ""
        item["node_name"] = "Panel"
        panel_processes.append(item)
    return panel_processes + get_node_process_snapshot()

def close_runtime_session(session_id):
    try:
        sid = int(session_id)
    except Exception:
        return False
    with active_bridges_lock:
        session = active_bridges.get(sid)
    if not session:
        return False
    session.close()
    return True

def get_process_snapshot(limit=25):
    processes = []
    if not os.path.isdir("/proc"):
        return processes
    ticks = os.sysconf(os.sysconf_names.get("SC_CLK_TCK", "SC_CLK_TCK"))
    page_size = os.sysconf("SC_PAGE_SIZE")
    for pid_name in os.listdir("/proc"):
        if not pid_name.isdigit():
            continue
        pid = int(pid_name)
        try:
            stat_path = f"/proc/{pid}/stat"
            status_path = f"/proc/{pid}/status"
            cmd_path = f"/proc/{pid}/cmdline"
            with open(stat_path, "r") as f:
                stat = f.read().split()
            with open(status_path, "r") as f:
                status_lines = f.readlines()
            cmd = ""
            try:
                with open(cmd_path, "rb") as f:
                    cmd = f.read().replace(b"\x00", b" ").decode("utf-8", "ignore").strip()
            except Exception:
                pass
            info = {"threads": 0, "rss_kb": 0, "state": stat[2] if len(stat) > 2 else "?"}
            for line in status_lines:
                if line.startswith("Threads:"):
                    info["threads"] = int(line.split()[1])
                elif line.startswith("VmRSS:"):
                    info["rss_kb"] = int(line.split()[1])
            cpu_seconds = 0.0
            if len(stat) > 15:
                cpu_seconds = (int(stat[13]) + int(stat[14])) / ticks
            rss_pages = int(stat[23]) if len(stat) > 23 else 0
            rss_kb = info["rss_kb"] or int((rss_pages * page_size) / 1024)
            processes.append({
                "pid": pid,
                "name": stat[1].strip("()") if len(stat) > 1 else str(pid),
                "state": info["state"],
                "threads": info["threads"],
                "rss_kb": rss_kb,
                "cpu_seconds": round(cpu_seconds, 2),
                "cmd": cmd[:180]
            })
        except Exception:
            continue
    processes.sort(key=lambda p: (p["rss_kb"], p["cpu_seconds"]), reverse=True)
    return processes[:limit]

def get_own_rss_kb():
    try:
        with open(f"/proc/{os.getpid()}/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except Exception:
        pass
    try:
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            rss = rss / 1024
        return int(rss)
    except Exception:
        return 0

def optimize_runtime_resources(action="idle"):
    now = time.time()
    max_idle = clamp_int(db.data["settings"].get("max_idle_seconds", 300), 300, 30, 86400)
    closed_bridges = 0
    pruned_logins = 0
    pruned_node_commands = 0
    gc_collected = 0
    malloc_trimmed = False

    if action in ("idle", "all"):
        idle_threshold = min(max_idle, 120) if action == "all" else max_idle
        with active_bridges_lock:
            stale = [
                session for session in active_bridges.values()
                if now - getattr(session, "last_activity", now) > idle_threshold
            ]
        for session in stale[:256]:
            try:
                session.close()
                closed_bridges += 1
            except Exception:
                pass

    with active_sessions_lock:
        for session_token, login_time in list(active_sessions.items()):
            if now - login_time > 86400:
                active_sessions.pop(session_token, None)
                pruned_logins += 1

    commands = db.data.setdefault("node_commands", {})
    for nid, pending in list(commands.items()):
        fresh = [cmd for cmd in pending if now - float(cmd.get("created_at", now)) < 900]
        pruned_node_commands += len(pending) - len(fresh)
        commands[nid] = fresh
    if pruned_node_commands:
        db.save()

    if action in ("gc", "all"):
        gc_collected = gc.collect()
        if action == "all":
            gc_collected += gc.collect(2)
        try:
            libc = ctypes.CDLL("libc.so.6")
            malloc_trimmed = bool(libc.malloc_trim(0))
        except Exception:
            malloc_trimmed = False

    result = {
        "success": True,
        "action": action,
        "closed_idle_sessions": closed_bridges,
        "pruned_login_sessions": pruned_logins,
        "pruned_node_commands": pruned_node_commands,
        "gc_collected": gc_collected,
        "malloc_trimmed": malloc_trimmed,
        "threads": threading.active_count(),
        "active_tunnel_sessions": len(list_runtime_sessions()),
        "rss_kb": get_own_rss_kb()
    }
    db.log("panel", "info", f"Resource optimization executed: {result}")
    return result

def queue_node_optimization(action="idle", node_id=None):
    now = time.time()
    commands = db.data.setdefault("node_commands", {})
    queued = 0
    targets = []
    for nid, node in db.data.get("nodes", {}).items():
        if node_id and nid != node_id:
            continue
        if node.get("status") == "online" and now - node.get("last_seen", 0) <= 30:
            targets.append((nid, node))
    for nid, node in targets:
        cmd_id = secrets.token_hex(8)
        commands.setdefault(nid, []).append({
            "id": cmd_id,
            "type": "optimize",
            "action": action,
            "created_at": now
        })
        queued += 1
    if queued:
        db.save()
        db.log("panel", "info", f"Queued {queued} node optimization command(s), action={action}, node_id={node_id or 'all'}.")
    return queued

def start_temp_echo_server(port, duration=60, command_id=""):
    port = int(port)
    if not valid_port(port):
        raise ValueError("Invalid echo port")
    duration = clamp_int(duration, 60, 5, 180)
    key = f"port:{port}"
    stop_at = time.time() + duration
    with temp_echo_servers_lock:
        old = temp_echo_servers.pop(key, None)
        if old:
            try:
                old.close()
            except Exception:
                pass
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tune_listener_socket(srv)
    srv.bind(("127.0.0.1", port))
    srv.listen(256)
    srv.settimeout(1.0)
    bytes_echoed = 0

    def echo_loop():
        try:
            while time.time() < stop_at:
                try:
                    conn, _ = srv.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                threading.Thread(target=handle_temp_echo_client, args=(conn, key), daemon=True).start()
        finally:
            try:
                srv.close()
            except Exception:
                pass
            with temp_echo_servers_lock:
                if temp_echo_servers.get(key) is srv:
                    temp_echo_servers.pop(key, None)
            db.log("node", "info", f"Temporary payload echo server stopped on 127.0.0.1:{port}; bytes={bytes_echoed}.")

    def handle_temp_echo_client(conn, server_key):
        nonlocal bytes_echoed
        tune_tcp(conn)
        conn.settimeout(10)
        try:
            while time.time() < stop_at:
                chunk = conn.recv(256 * 1024)
                if not chunk:
                    break
                bytes_echoed += len(chunk)
                conn.sendall(chunk)
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    with temp_echo_servers_lock:
        temp_echo_servers[key] = srv
    threading.Thread(target=echo_loop, daemon=True).start()
    db.log("node", "info", f"Temporary payload echo server listening on 127.0.0.1:{port} for {duration}s.")
    return {"success": True, "port": port, "duration": duration, "host": "127.0.0.1"}

def stop_temp_echo_server(command_id):
    key = str(command_id or "")
    with temp_echo_servers_lock:
        srv = temp_echo_servers.pop(key, None)
    if srv:
        try:
            srv.close()
        except Exception:
            pass
        return True
    return False

def execute_node_commands(panel_url, token, private_key, commands):
    for command in commands or []:
        command_type = command.get("type")
        cmd_id = command.get("id")
        if command_type == "optimize":
            action = command.get("action", "idle")
            try:
                result = optimize_runtime_resources(action)
            except Exception as e:
                result = {"success": False, "error": str(e), "action": action}
            payload = {"id": cmd_id, "type": "optimize", "action": action, "result": result}
        elif command_type == "payload_test_echo":
            action = "start"
            try:
                result = start_temp_echo_server(command.get("port"), command.get("duration", 60), cmd_id)
            except Exception as e:
                result = {"success": False, "error": str(e), "port": command.get("port")}
            payload = {"id": cmd_id, "type": "payload_test_echo", "action": action, "result": result}
        elif command_type == "payload_test_client":
            action = "transfer"
            try:
                size_mb = clamp_int(command.get("size_mb", 4), 4, 1, 32)
                result = run_tunnel_payload_transfer(
                    command.get("host", "127.0.0.1"),
                    int(command.get("port")),
                    size_mb * 1024 * 1024,
                    timeout=clamp_int(command.get("timeout", 45), 45, 5, 120)
                )
            except Exception as e:
                result = {"success": False, "error": str(e), "port": command.get("port")}
            payload = {"id": cmd_id, "type": "payload_test_client", "action": action, "result": result}
        elif command_type == "payload_test_echo_stop":
            action = "stop"
            result = {"success": stop_temp_echo_server(command.get("target_id") or cmd_id)}
            payload = {"id": cmd_id, "type": "payload_test_echo_stop", "action": action, "result": result}
        else:
            continue
        try:
            make_panel_request(panel_url, "/api/node-command-result", token, payload, private_key=private_key)
        except Exception as e:
            db.log("node", "error", f"Failed posting node command result {cmd_id}: {e}")

def payload_chunk(seed, index, size):
    out = bytearray()
    counter = 0
    while len(out) < size:
        out.extend(hashlib.sha256(f"{seed}:{index}:{counter}".encode()).digest())
        counter += 1
    return bytes(out[:size])

def run_tunnel_payload_transfer(host, port, total_bytes, timeout=30):
    started = time.time()
    sent_hash = hashlib.sha256()
    recv_hash = hashlib.sha256()
    sent = 0
    received = 0
    seed = secrets.token_hex(16)
    chunk_size = 256 * 1024
    with socket.create_connection((host, int(port)), timeout=timeout) as sock:
        tune_tcp(sock)
        sock.settimeout(timeout)
        index = 0
        while sent < total_bytes:
            size = min(chunk_size, total_bytes - sent)
            chunk = payload_chunk(seed, index, size)
            sent_hash.update(chunk)
            sock.sendall(chunk)
            sent += size
            expected = size
            buf = bytearray()
            while len(buf) < expected:
                part = sock.recv(min(chunk_size, expected - len(buf)))
                if not part:
                    raise OSError("Connection closed before echo completed")
                buf.extend(part)
            recv_hash.update(buf)
            received += len(buf)
            index += 1
    elapsed = max(0.001, time.time() - started)
    sent_digest = sent_hash.hexdigest()
    received_digest = recv_hash.hexdigest()
    success = sent == received and sent_digest == received_digest
    error = ""
    if sent != received:
        error = f"Byte count mismatch: sent {sent}, received {received}"
    elif sent_digest != received_digest:
        error = "Payload hash mismatch: tunnel returned different bytes than it received"
    return {
        "success": success,
        "error": error,
        "bytes_sent": sent,
        "bytes_received": received,
        "sha256_sent": sent_digest,
        "sha256_received": received_digest,
        "elapsed_seconds": round(elapsed, 3),
        "mbps": round((received * 8) / elapsed / 1_000_000, 2)
    }

def queue_payload_echo_command(node_id, target_port, duration=60):
    cmd_id = secrets.token_hex(8)
    commands = db.data.setdefault("node_commands", {})
    commands.setdefault(node_id, []).append({
        "id": cmd_id,
        "type": "payload_test_echo",
        "port": int(target_port),
        "duration": int(duration),
        "created_at": time.time()
    })
    db.save()
    return cmd_id

def queue_payload_client_command(node_id, user_port, size_mb=4):
    cmd_id = secrets.token_hex(8)
    commands = db.data.setdefault("node_commands", {})
    commands.setdefault(node_id, []).append({
        "id": cmd_id,
        "type": "payload_test_client",
        "host": "127.0.0.1",
        "port": int(user_port),
        "size_mb": int(size_mb),
        "timeout": 60,
        "created_at": time.time()
    })
    db.save()
    return cmd_id

def choose_temp_link_ports(link):
    used = set()
    for field in ("bridge_port", "sync_port"):
        try:
            used.add(int(link.get(field)))
        except Exception:
            pass
    for mapping in link.get("ports", []) or []:
        try:
            used.add(int(mapping.get("user_port")))
            used.add(int(mapping.get("target_port")))
        except Exception:
            pass
    for _ in range(200):
        base = secrets.randbelow(20000) + 32000
        if base % 2:
            base += 1
        user_port = base
        target_port = base + 1
        if valid_port(user_port) and valid_port(target_port) and user_port not in used and target_port not in used:
            return user_port, target_port
    raise RuntimeError("Could not allocate temporary test ports")

def remove_temp_port_mapping(link, marker):
    before = len(link.get("ports", []))
    link["ports"] = [p for p in link.get("ports", []) if p.get("_temp_test") != marker]
    return before - len(link.get("ports", []))

def wait_for_node_command_result(node_id, cmd_id, timeout=18):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = db.data.get("nodes", {}).get(node_id, {}).get("last_command_result", {})
            if result.get("id") == cmd_id:
                return result
        except Exception:
            pass
        time.sleep(0.35)
    return None

def normalize_request_path(path):
    return (path or "/").rstrip("/") or "/"

def summarize_links_for_error():
    summary = []
    for lid, link in list(db.data.get("links", {}).items())[:20]:
        summary.append({
            "id": lid,
            "name": link.get("name", lid),
            "ports": [
                {"user_port": p.get("user_port"), "target_port": p.get("target_port")}
                for p in (link.get("ports", []) or [])[:10]
            ]
        })
    return summary

# --------- Obfuscation & Dynamic Tunnel Layer ----------
def wrap_socket_server_tls(sock, cert_path, key_path):
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        return context.wrap_socket(sock, server_side=True)
    except Exception as e:
        db.log("tls", "error", f"Failed wrapping server socket in TLS: {e}")
        raise e

def wrap_socket_client_tls(sock, sni_hostname=None):
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        server_hostname = sni_hostname if sni_hostname else "localhost"
        return context.wrap_socket(sock, server_side=False, server_hostname=server_hostname)
    except Exception as e:
        db.log("tls", "error", f"Failed wrapping client socket in TLS: {e}")
        raise e

class WSFrameParser:
    def __init__(self, sock):
        self.sock = sock

    def read_frame(self):
        h1 = recv_exact(self.sock, 2)
        if not h1:
            return None
        
        fin_opcode = h1[0]
        mask_len = h1[1]
        
        has_mask = bool(mask_len & 0x80)
        length = mask_len & 0x7f
        
        if length == 126:
            ext_len = recv_exact(self.sock, 2)
            if not ext_len: return None
            (length,) = struct.unpack("!H", ext_len)
        elif length == 127:
            ext_len = recv_exact(self.sock, 8)
            if not ext_len: return None
            (length,) = struct.unpack("!Q", ext_len)
            
        mask = None
        if has_mask:
            mask = recv_exact(self.sock, 4)
            if not mask: return None
            
        payload = recv_exact(self.sock, length)
        if payload is None: return None
        
        if has_mask:
            if length > 0:
                # Performance optimization: using int.from_bytes() and int XOR is ~80x faster
                # than a python for loop with bytearray due to C-level evaluation.
                extended_mask = (mask * (length // 4 + 1))[:length]
                int_payload = int.from_bytes(payload, 'big')
                int_mask = int.from_bytes(extended_mask, 'big')
                payload = (int_payload ^ int_mask).to_bytes(length, 'big')
            
        opcode = fin_opcode & 0x0f
        if opcode == 0x8:
            return None
            
        return payload

def make_websocket_frame(payload: bytes, is_client: bool = False) -> bytes:
    header = bytearray([0x82])  # Binary frame
    length = len(payload)
    
    if length <= 125:
        len_byte = length
    elif length <= 65535:
        len_byte = 126
    else:
        len_byte = 127
        
    if is_client:
        len_byte |= 0x80
        header.append(len_byte)
        if length > 125:
            if length <= 65535:
                header.extend(struct.pack("!H", length))
            else:
                header.extend(struct.pack("!Q", length))
        mask = secrets.token_bytes(4)
        header.extend(mask)
        if length > 0:
            # Performance optimization: using int.from_bytes() and int XOR is ~80x faster
            # than a python for loop with bytearray due to C-level evaluation.
            extended_mask = (mask * (length // 4 + 1))[:length]
            int_payload = int.from_bytes(payload, 'big')
            int_mask = int.from_bytes(extended_mask, 'big')
            header.extend((int_payload ^ int_mask).to_bytes(length, 'big'))
    else:
        header.append(len_byte)
        if length > 125:
            if length <= 65535:
                header.extend(struct.pack("!H", length))
            else:
                header.extend(struct.pack("!Q", length))
        header.extend(payload)
        
    return bytes(header)

def make_http_chunk(payload: bytes) -> bytes:
    return f"{len(payload):x}\r\n".encode() + payload + b"\r\n"

def read_http_chunk(sock) -> bytes:
    line = bytearray()
    while True:
        char = recv_exact(sock, 1)
        if not char: return None
        line.extend(char)
        if len(line) >= 2 and line[-2:] == b"\r\n":
            break
    try:
        length_str = line[:-2].decode().strip()
        length = int(length_str, 16)
    except Exception:
        return None
        
    if length == 0:
        return None
        
    payload = recv_exact(sock, length)
    if payload is None: return None
    
    crlf = recv_exact(sock, 2)
    if not crlf or crlf != b"\r\n":
        return None
        
    return payload

class TunnelSocket:
    def __init__(self, raw_sock, role, mode, config=None):
        self.raw_sock = raw_sock
        self.role = role
        self.requested_mode = mode or "tcp"
        self.mode = self.requested_mode if self.requested_mode in ("tcp", "websocket", "http_obfs") else "tcp"
        self.config = config or {}
        self.handshake_done = False
        self.ws_parser = None
        self.read_buf = b""

    def perform_handshake(self):
        if self.handshake_done:
            return True
        try:
            if self.mode == "websocket":
                if self.role in ("iran", "internal"):
                    req = self.read_http_headers()
                    if not req or "Upgrade: websocket" not in req:
                        return False
                    key = ""
                    for line in req.split("\r\n"):
                        if line.lower().startswith("sec-websocket-key:"):
                            key = line.split(":", 1)[1].strip()
                            break
                    sha1 = hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
                    accept_key = base64.b64encode(sha1).decode()
                    resp = (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
                    )
                    self.raw_sock.sendall(resp.encode())
                    self.ws_parser = WSFrameParser(self.raw_sock)
                else:
                    path = self.config.get("obfs_path", "/tunnel")
                    host = self.config.get("obfs_host", "localhost")
                    key = base64.b64encode(secrets.token_bytes(16)).decode()
                    req = (
                        f"GET {path} HTTP/1.1\r\n"
                        f"Host: {host}\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\n"
                        "Sec-WebSocket-Version: 13\r\n\r\n"
                    )
                    self.raw_sock.sendall(req.encode())
                    resp = self.read_http_headers()
                    if not resp or "101 Switching Protocols" not in resp:
                        return False
                    self.ws_parser = WSFrameParser(self.raw_sock)
            elif self.mode == "http_obfs":
                if self.role in ("iran", "internal"):
                    req = self.read_http_headers()
                    if not req or "POST" not in req:
                        return False
                    resp = (
                        "HTTP/1.1 200 OK\r\n"
                        "Server: nginx/1.24.0\r\n"
                        "Content-Type: application/octet-stream\r\n"
                        "Transfer-Encoding: chunked\r\n"
                        "Connection: keep-alive\r\n\r\n"
                    )
                    self.raw_sock.sendall(resp.encode())
                else:
                    path = self.config.get("obfs_path", "/index.php")
                    host = self.config.get("obfs_host", "speedtest.net")
                    req = (
                        f"POST {path} HTTP/1.1\r\n"
                        f"Host: {host}\r\n"
                        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
                        "Content-Type: application/octet-stream\r\n"
                        "Transfer-Encoding: chunked\r\n"
                        "Connection: keep-alive\r\n\r\n"
                    )
                    self.raw_sock.sendall(req.encode())
                    resp = self.read_http_headers()
                    if not resp or "200 OK" not in resp:
                        return False
            self.handshake_done = True
            return True
        except Exception:
            return False

    def read_http_headers(self):
        hdr = bytearray()
        while True:
            char = recv_exact(self.raw_sock, 1)
            if not char: return None
            hdr.extend(char)
            if len(hdr) >= 4 and hdr[-4:] == b"\r\n\r\n":
                break
        return hdr.decode("utf-8", errors="ignore")

    def recv(self, bufsize):
        if self.mode == "tcp":
            return self.raw_sock.recv(bufsize)

        if not self.handshake_done:
            if not self.perform_handshake():
                return b""

        if len(self.read_buf) > 0:
            res = self.read_buf[:bufsize]
            self.read_buf = self.read_buf[bufsize:]
            return res

        while True:
            if self.mode == "websocket":
                payload = self.ws_parser.read_frame()
            else:  # http_obfs
                payload = read_http_chunk(self.raw_sock)

            if payload is None:
                return b""
            if len(payload) > 0:
                break

        if len(payload) > bufsize:
            res = payload[:bufsize]
            self.read_buf = payload[bufsize:]
            return res
        else:
            return payload

    def sendall(self, data):
        if self.mode == "tcp":
            return self.raw_sock.sendall(data)

        if not self.handshake_done:
            if not self.perform_handshake():
                raise socket.error("Handshake failed")

        if self.mode == "websocket":
            frame = make_websocket_frame(data, is_client=(self.role in ("foreign", "external")))
            self.raw_sock.sendall(frame)
        else:  # http_obfs
            chunk = make_http_chunk(data)
            self.raw_sock.sendall(chunk)

    def close(self):
        self.raw_sock.close()

    def shutdown(self, how):
        try:
            self.raw_sock.shutdown(how)
        except Exception:
            pass

# --------- Core Tunnel Logic ----------
class BridgeSession:
    def __init__(self, sock_a, sock_b, link_id, target_port):
        self.sock_a = sock_a
        self.sock_b = sock_b
        self.link_id = link_id
        self.target_port = target_port
        self.last_activity = time.time()
        self.created_at = time.time()
        self.lock = threading.Lock()

    def update_activity(self):
        with self.lock:
            self.last_activity = time.time()

    def close(self):
        try: self.sock_a.close()
        except Exception: pass
        try: self.sock_b.close()
        except Exception: pass

def pipe(session: BridgeSession, a, b):
    try:
        while True:
            data = a.recv(BUF_COPY)
            if not data:
                break
            session.update_activity()
            b.sendall(data)
            session.update_activity()
    except Exception:
        pass
    finally:
        try: a.shutdown(socket.SHUT_RD)
        except Exception: pass
        try: b.shutdown(socket.SHUT_WR)
        except Exception: pass

def bridge(a, b, link_id: str, target_port: int):
    session = BridgeSession(a, b, link_id, target_port)
    session_id = id(session)
    with active_bridges_lock:
        active_bridges[session_id] = session
    try:
        t1 = threading.Thread(target=pipe, args=(session, a, b), daemon=True)
        t1.start()
        pipe(session, b, a)
        session.close()
        t1.join(timeout=2)
    finally:
        with active_bridges_lock:
            active_bridges.pop(session_id, None)
        session.close()

def start_bridge_monitor(max_idle_seconds: float):
    def monitor_loop():
        while True:
            time.sleep(10)
            now = time.time()
            stale = []
            with active_bridges_lock:
                for sid, session in list(active_bridges.items()):
                    if now - session.last_activity > max_idle_seconds:
                        stale.append(session)
            for s in stale:
                s.close()
    threading.Thread(target=monitor_loop, daemon=True).start()

# Helper to connect to Panel with fallback unverified certificate context
def make_panel_request(panel_url, path, token, payload=None, timeout=5, private_key=""):
    import urllib.request
    import urllib.error
    
    url = f"{panel_url.rstrip('/')}{path}"
    headers = {"X-Node-Token": normalize_node_token(token)}
    
    data_bytes = None
    if payload is not None:
        payload_text = json.dumps(payload)
        data_bytes = payload_text.encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        payload_text = ""
    if private_key:
        headers["X-Node-Signature"] = hmac.new(private_key.encode(), f"{path}\n{payload_text}".encode(), hashlib.sha256).hexdigest()
        
    req = urllib.request.Request(url, data=data_bytes, headers=headers)

    def open_request(context=None):
        try:
            if context is None:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read()
            with urllib.request.urlopen(req, context=context, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            raise RuntimeError(f"HTTP Error {e.code}: {detail or e.reason}") from e
    
    # Try verified SSL first if HTTPS
    if url.startswith("https://"):
        try:
            ctx = ssl.create_default_context()
            return open_request(ctx)
        except urllib.error.URLError:
            # Fallback to unverified SSL on verification error
            ctx_fallback = ssl.create_default_context()
            ctx_fallback.check_hostname = False
            ctx_fallback.verify_mode = ssl.CERT_NONE
            return open_request(ctx_fallback)
    else:
        # HTTP
        return open_request()

# --------- Iran Node Daemon Controller ----------
class IranNodeController:
    def __init__(self, panel_url, token, private_key=""):
        self.panel_url = panel_url
        self.token = token
        self.private_key = private_key
        self.active_links = {}
        self.lock = threading.Lock()
        self.running = True

    def start(self):
        db.log("iran-node", "info", "P00RIJA Iran Node Controller thread started.")
        threading.Thread(target=self.report_loop, daemon=True).start()
        threading.Thread(target=self.config_sync_loop, daemon=True).start()
        threading.Thread(target=self.engine_watchdog_loop, daemon=True).start()

    def config_sync_loop(self):
        while self.running:
            try:
                res = make_panel_request(self.panel_url, "/api/node-config", self.token, private_key=self.private_key)
                config = json.loads(res.decode())
                self.apply_config(config)
                execute_node_commands(self.panel_url, self.token, self.private_key, config.get("commands", []))
            except Exception as e:
                db.log("iran-node", "error", f"Config sync failed: {e}")
            time.sleep(5)

    def apply_config(self, config):
        settings = config.get("settings", {})
        self.engine_restart_interval = int(settings.get("engine_restart_interval", 0))
        disable_ipv6 = bool(settings.get("disable_ipv6", False))
        if getattr(self, "disable_ipv6", None) != disable_ipv6:
            self.disable_ipv6 = disable_ipv6
            apply_ipv6_disabled(disable_ipv6)
        
        with self.lock:
            active_link_ids = set()
            for link in config.get("links", []):
                link_id = link["id"]
                active_link_ids.add(link_id)
                signature = self.link_signature(link)
                current = self.active_links.get(link_id)
                if not current:
                    self.start_link(link)
                    if link_id in self.active_links:
                        self.active_links[link_id]["signature"] = signature
                elif current.get("signature") != signature:
                    self.stop_link(link_id)
                    self.start_link(link)
                    if link_id in self.active_links:
                        self.active_links[link_id]["signature"] = signature
                else:
                    self.update_link_ports(link_id, link)

            for lid in list(self.active_links.keys()):
                if lid not in active_link_ids:
                    self.stop_link(lid)

    def link_signature(self, link):
        keys = ("bridge_port", "sync_port", "pool_size", "tls_enabled", "tls_sni", "tunnel_mode", "obfs_host", "obfs_path", "profile_id", "padding_min", "padding_max", "jitter_ms", "keepalive_interval")
        ports = tuple((p.get("user_port"), p.get("target_port")) for p in link.get("ports", []))
        return tuple(link.get(k) for k in keys) + (ports,)
                    
    def engine_watchdog_loop(self):
        last_restart = time.time()
        while self.running:
            try:
                # Engine restart interval logic
                interval_minutes = getattr(self, "engine_restart_interval", 0)
                if interval_minutes > 0 and time.time() - last_restart > interval_minutes * 60:
                    db.log("iran-node", "info", f"Watchdog: Scheduled engine restart every {interval_minutes} minutes.")
                    with self.lock:
                        for lid, link_data in list(self.active_links.items()):
                            link = link_data.get("_raw_config")
                            if link:
                                self.stop_link(lid)
                                self.start_link(link)
                    last_restart = time.time()
                    
                # Engine health check logic
                with self.lock:
                    for lid, link_data in list(self.active_links.items()):
                        try:
                            # Check if bridge socket is dead
                            bridge_sock = link_data.get("bridge_sock")
                            if bridge_sock and bridge_sock.fileno() == -1:
                                db.log("iran-node", "warning", f"Watchdog: Link {lid} bridge socket is dead. Restarting link.")
                                link = link_data.get("_raw_config")
                                if link:
                                    self.stop_link(lid)
                                    self.start_link(link)
                        except Exception:
                            pass
            except Exception as e:
                db.log("iran-node", "error", f"Watchdog error: {e}")
            time.sleep(10)

    def start_link(self, link):
        link_id = link["id"]
        bridge_port = link["bridge_port"]
        sync_port = link["sync_port"]
        tls_enabled = link.get("tls_enabled", False)
        pool = Queue(maxsize=500)

        # Dynamic SSL Certificates mapping
        cert_path = ""
        key_path = ""
        if tls_enabled:
            cert_content = link.get("cert_content", "")
            key_content = link.get("key_content", "")
            if cert_content and key_content:
                cert_path = f"{CONFIG_DIR}/certs/link_{link_id}.crt"
                key_path = f"{CONFIG_DIR}/certs/link_{link_id}.key"
                try:
                    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
                    with open(cert_path, "w") as f:
                        f.write(cert_content)
                    with open(key_path, "w") as f:
                        f.write(key_content)
                except Exception as e:
                    db.log("iran-node", "error", f"Failed writing dynamic certificate to disk: {e}")
                    return

        bridge_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tune_listener_socket(bridge_srv)
        try:
            bridge_srv.bind(("0.0.0.0", bridge_port))
            bridge_srv.listen(16384)
        except Exception as e:
            db.log("iran-node", "error", f"Failed binding bridge port {bridge_port}: {e}")
            return

        sync_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tune_listener_socket(sync_srv)
        try:
            sync_srv.bind(("0.0.0.0", sync_port))
            sync_srv.listen(128)
        except Exception as e:
            bridge_srv.close()
            db.log("iran-node", "error", f"Failed binding sync port {sync_port}: {e}")
            return

        link_data = {
            "bridge_port": bridge_port,
            "sync_port": sync_port,
            "bridge_sock": bridge_srv,
            "sync_sock": sync_srv,
            "pool": pool,
            "ports": {},
            "running": True,
            "_raw_config": link,
            "direct_fallbacks": 0,
            "last_direct_error": ""
        }
        self.active_links[link_id] = link_data

        def accept_bridge():
            db.log("iran-node", "info", f"[DEBUG] accept_bridge started listening on {bridge_port}")
            while link_data["running"]:
                try:
                    c, addr = bridge_srv.accept()
                    db.log("iran-node", "info", f"[DEBUG] accept_bridge accepted connection from {addr}")
                    tune_tcp(c)
                    if tls_enabled and cert_path and key_path:
                        try:
                            c = wrap_socket_server_tls(c, cert_path, key_path)
                        except Exception as e:
                            db.log("iran-node", "error", f"[DEBUG] TLS wrap failed: {e}")
                            c.close()
                            continue
                    
                    mode = link.get("tunnel_mode", "tcp")
                    ts = TunnelSocket(c, role="internal", mode=mode, config=link)
                    if not ts.perform_handshake():
                        db.log("iran-node", "error", f"[DEBUG] Handshake failed from {addr}")
                        ts.close()
                        continue
                    try:
                        pool.put(ts, block=False)
                    except Full:
                        db.log("iran-node", "error", f"[DEBUG] Pool full from {addr}")
                        ts.close()
                except OSError:
                    if not link_data["running"]:
                        break
                    time.sleep(0.1)
                except Exception:
                    time.sleep(0.1)

        def accept_sync():
            while link_data["running"]:
                try:
                    c, _ = sync_srv.accept()
                    c.settimeout(10)
                    def handle_sync(conn):
                        try:
                            while link_data["running"]:
                                h = recv_exact(conn, 1)
                                if not h: break
                                count = h[0]
                                active_ports = []
                                for _ in range(count):
                                    pd = recv_exact(conn, 2)
                                    if not pd: return
                                    (p,) = struct.unpack("!H", pd)
                                    active_ports.append(p)
                                self.sync_auto_ports(link_id, active_ports)
                        except Exception: pass
                        finally: conn.close()
                    threading.Thread(target=handle_sync, args=(c,), daemon=True).start()
                except OSError:
                    if not link_data["running"]:
                        break
                    time.sleep(0.1)
                except Exception:
                    time.sleep(0.1)

        threading.Thread(target=accept_bridge, daemon=True).start()
        threading.Thread(target=accept_sync, daemon=True).start()
        db.log("iran-node", "info", f"Started link {link_id} (Bridge: {bridge_port}, Sync: {sync_port})")
        self.update_link_ports(link_id, link)

    def sync_auto_ports(self, link_id, active_ports):
        with self.lock:
            link_data = self.active_links.get(link_id)
            if not link_data: return
            link_data["auto_ports"] = {p: p for p in active_ports}
            self.reconcile_combined_ports(link_id, link_data)

    def update_link_ports(self, link_id, link):
        link_data = self.active_links.get(link_id)
        if not link_data: return
        configured_ports = {}
        for pm in link.get("ports", []):
            try:
                up = int(pm["user_port"])
                tp = int(pm["target_port"])
                configured_ports[up] = tp
            except Exception:
                pass
        link_data["manual_ports"] = configured_ports
        self.reconcile_combined_ports(link_id, link_data)

    def reconcile_combined_ports(self, link_id, link_data):
        combined = dict(link_data.get("auto_ports", {}))
        combined.update(link_data.get("manual_ports", {}))
        for up, tp in combined.items():
            if up not in link_data["ports"]:
                self.open_user_port(link_id, link_data, up, tp)
            elif link_data["ports"][up].get("target_port") != tp:
                self.close_user_port(link_data, up)
                self.open_user_port(link_id, link_data, up, tp)
        for up in list(link_data["ports"].keys()):
            if up not in combined:
                self.close_user_port(link_data, up)

    def reconcile_ports(self, link_id, link_data, configured_ports):
        # Kept for compatibility just in case
        self.reconcile_combined_ports(link_id, link_data)

    def open_user_port(self, link_id, link_data, user_port, target_port):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tune_listener_socket(srv)
        try:
            srv.bind(("0.0.0.0", user_port))
            srv.listen(16384)
        except Exception as e:
            db.log("iran-node", "error", f"Failed binding user port {user_port} for link {link_id}: {e}")
            return

        def handle_user(u, p):
            tune_tcp(u)
            deadline = time.time() + POOL_WAIT
            europe = None
            while time.time() < deadline:
                try:
                    cand = link_data["pool"].get(timeout=max(0.1, deadline - time.time()))
                except Empty:
                    break
                try:
                    if not is_socket_alive(cand.raw_sock):
                        cand.close()
                        continue
                except Exception:
                    cand.close()
                    continue
                europe = cand
                break

            if not europe:
                link = link_data.get("_raw_config") or {}
                peer_ip = str(link.get("peer_ip") or link.get("external_ip") or "").strip()
                if peer_ip:
                    try:
                        db.log("iran-node", "warning", f"[DEBUG] Pool empty for user port {user_port}; trying direct fallback to {peer_ip}:{link_data['bridge_port']}.")
                        europe = dial_tcp(peer_ip, link_data["bridge_port"])
                        tune_tcp(europe)
                        link_data["direct_fallbacks"] = link_data.get("direct_fallbacks", 0) + 1
                    except Exception as e:
                        link_data["last_direct_error"] = str(e)[:180]
                        db.log("iran-node", "error", f"[DEBUG] Direct fallback failed for user port {user_port} to {peer_ip}:{link_data['bridge_port']}: {e}")
                        u.close()
                        return
                else:
                    db.log("iran-node", "error", f"[DEBUG] Pool empty for user connection on port {user_port} and no external peer_ip is configured. Closing user socket.")
                    u.close()
                    return

            try:
                if hasattr(europe, "sendall"):
                    europe.sendall(struct.pack("!H", target_port))
            except Exception as e:
                db.log("iran-node", "error", f"[DEBUG] Failed to send target_port {target_port} to europe tunnel: {e}")
                u.close()
                try: europe.close()
                except Exception: pass
                return

            db.log("iran-node", "info", f"[DEBUG] Bridging user port {user_port} to target {target_port} via tunnel.")
            bridge(u, europe, link_id, target_port)

        def accept_users():
            while link_data["running"]:
                try:
                    u, _ = srv.accept()
                    threading.Thread(target=handle_user, args=(u, target_port), daemon=True).start()
                except OSError:
                    if not link_data["running"]:
                        break
                    time.sleep(0.1)
                except Exception:
                    time.sleep(0.1)

        t = threading.Thread(target=accept_users, daemon=True)
        t.start()
        link_data["ports"][user_port] = {
            "sock": srv,
            "thread": t,
            "target_port": target_port
        }
        db.log("iran-node", "info", f"Opened user port {user_port} -> Foreign:{target_port}")

    def close_user_port(self, link_data, user_port):
        pdata = link_data["ports"].pop(user_port, None)
        if pdata:
            try: pdata["sock"].close()
            except Exception: pass
            db.log("iran-node", "info", f"Closed user port {user_port}")

    def collect_link_statuses(self):
        statuses = {}
        with self.lock:
            items = list(self.active_links.items())
        for link_id, link_data in items:
            port_status = {}
            for user_port, pdata in list(link_data.get("ports", {}).items()):
                target_port = pdata.get("target_port")
                sock = pdata.get("sock")
                port_status[str(user_port)] = {
                    "user_port": user_port,
                    "target_port": target_port,
                    "listening": bool(sock and sock.fileno() != -1)
                }
            pool = link_data.get("pool")
            statuses[link_id] = {
                "running": bool(link_data.get("running")),
                "bridge_listening": bool(link_data.get("bridge_sock") and link_data["bridge_sock"].fileno() != -1),
                "sync_listening": bool(link_data.get("sync_sock") and link_data["sync_sock"].fileno() != -1),
                "pool_available": pool.qsize() if pool else 0,
                "direct_fallbacks": int(link_data.get("direct_fallbacks", 0) or 0),
                "last_direct_error": link_data.get("last_direct_error", ""),
                "ports": port_status,
                "network_mode": read_runtime_network_mode()
            }
        return statuses

    def stop_link(self, link_id):
        link_data = self.active_links.pop(link_id, None)
        if link_data:
            link_data["running"] = False
            try: link_data["bridge_sock"].close()
            except Exception: pass
            try: link_data["sync_sock"].close()
            except Exception: pass
            while True:
                try:
                    c = link_data["pool"].get_nowait()
                    c.close()
                except Empty:
                    break
            for up in list(link_data["ports"].keys()):
                self.close_user_port(link_data, up)
            db.log("iran-node", "info", f"Stopped link {link_id}")

    def report_loop(self):
        speedometer = NetSpeedometer()
        cpu_total, cpu_idle = get_cpu_percent()
        
        while self.running:
            time.sleep(3)
            cpu_t2, cpu_i2 = get_cpu_percent()
            dt_total = cpu_t2 - cpu_total
            dt_idle = cpu_i2 - cpu_idle
            cpu_pct = 100 * (1 - (dt_idle / dt_total)) if dt_total > 0 else 0.0
            cpu_total, cpu_idle = cpu_t2, cpu_i2

            ram_pct = get_ram_percent()
            rx, tx = speedometer.sample()
            
            connections = 0
            with active_bridges_lock:
                connections = len(active_bridges)

            payload = {
                "cpu": round(cpu_pct, 1),
                "ram": round(ram_pct, 1),
                "rx_speed": round(rx, 1),
                "tx_speed": round(tx, 1),
                "threads": threading.active_count(),
                "connections": connections,
                "link_statuses": self.collect_link_statuses(),
                "runtime_sessions": list_runtime_sessions(),
                "processes": get_process_snapshot(limit=10)
            }

            try:
                make_panel_request(self.panel_url, "/api/report", self.token, payload, private_key=self.private_key)
            except Exception:
                pass

# --------- Foreign Node Daemon Controller ----------
class ForeignNodeController:
    def __init__(self, panel_url, token, private_key=""):
        self.panel_url = panel_url
        self.token = token
        self.private_key = private_key
        self.active_links = {}
        self.lock = threading.Lock()
        self.running = True

    def start(self):
        db.log("foreign-node", "info", "P00RIJA Foreign Node Controller thread started.")
        threading.Thread(target=self.report_loop, daemon=True).start()
        threading.Thread(target=self.config_sync_loop, daemon=True).start()
        threading.Thread(target=self.engine_watchdog_loop, daemon=True).start()

    def config_sync_loop(self):
        while self.running:
            try:
                res = make_panel_request(self.panel_url, "/api/node-config", self.token, private_key=self.private_key)
                config = json.loads(res.decode())
                self.apply_config(config)
                execute_node_commands(self.panel_url, self.token, self.private_key, config.get("commands", []))
            except Exception as e:
                db.log("foreign-node", "error", f"Config sync failed: {e}")
            time.sleep(5)

    def apply_config(self, config):
        settings = config.get("settings", {})
        self.engine_restart_interval = int(settings.get("engine_restart_interval", 0))
        disable_ipv6 = bool(settings.get("disable_ipv6", False))
        if getattr(self, "disable_ipv6", None) != disable_ipv6:
            self.disable_ipv6 = disable_ipv6
            apply_ipv6_disabled(disable_ipv6)
        
        with self.lock:
            active_link_ids = set()
            for link in config.get("links", []):
                link_id = link["id"]
                active_link_ids.add(link_id)
                signature = self.link_signature(link)
                current = self.active_links.get(link_id)
                if not current:
                    self.start_link(link)
                elif current.get("signature") != signature:
                    self.stop_link(link_id)
                    self.start_link(link)
                else:
                    current["_raw_config"] = link
                    current["signature"] = signature

            for lid in list(self.active_links.keys()):
                if lid not in active_link_ids:
                    self.stop_link(lid)

    def engine_watchdog_loop(self):
        last_restart = time.time()
        while self.running:
            try:
                interval_minutes = getattr(self, "engine_restart_interval", 0)
                if interval_minutes > 0 and time.time() - last_restart > interval_minutes * 60:
                    db.log("foreign-node", "info", f"Watchdog: Scheduled engine restart every {interval_minutes} minutes.")
                    with self.lock:
                        for lid, link_data in list(self.active_links.items()):
                            link = link_data.get("_raw_config")
                            if link:
                                self.stop_link(lid)
                                self.start_link(link)
                    last_restart = time.time()
                    
                # No central socket check here since pool relies on TunnelSocket which handles its own reconnection.
            except Exception as e:
                db.log("foreign-node", "error", f"Watchdog error: {e}")
            time.sleep(10)

    def link_signature(self, link):
        keys = ("iran_ip", "bridge_port", "sync_port", "pool_size", "tls_enabled", "tls_sni", "tunnel_mode", "obfs_host", "obfs_path", "profile_id", "padding_min", "padding_max", "jitter_ms", "keepalive_interval")
        ports = tuple((p.get("user_port"), p.get("target_port")) for p in link.get("ports", []))
        return tuple(link.get(k) for k in keys) + (ports,)

    def start_link(self, link):
        link_id = link["id"]
        iran_ip = link["iran_ip"]
        bridge_port = link["bridge_port"]
        sync_port = link["sync_port"]
        pool_size = clamp_int(link.get("pool_size", 24), 24, 1, MAX_POOL_SIZE_PER_LINK)
        worker_count = min(pool_size, MAX_REVERSE_WORKERS_PER_LINK)
        tls_enabled = link.get("tls_enabled", False)

        link_data = {
            "iran_ip": iran_ip,
            "bridge_port": bridge_port,
            "sync_port": sync_port,
            "signature": self.link_signature(link),
            "running": True,
            "_raw_config": link,
            "direct_bridge_sock": None,
            "direct_bridge_listening": False,
            "direct_bridges": 0,
            "ready_workers": 0,
            "successful_bridges": 0,
            "worker_errors": 0,
            "last_worker_error": ""
        }
        self.active_links[link_id] = link_data

        direct_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tune_listener_socket(direct_srv)
        try:
            direct_srv.bind(("0.0.0.0", bridge_port))
            direct_srv.listen(4096)
            link_data["direct_bridge_sock"] = direct_srv
            link_data["direct_bridge_listening"] = True
        except Exception as e:
            try:
                direct_srv.close()
            except Exception:
                pass
            link_data["last_worker_error"] = f"Direct bridge listen failed on {bridge_port}: {e}"[:180]
            db.log("foreign-node", "warning", f"Direct bridge fallback could not listen on {bridge_port}: {e}")

        def accept_direct_bridge():
            srv = link_data.get("direct_bridge_sock")
            if not srv:
                return
            db.log("foreign-node", "info", f"Direct bridge fallback listening on {bridge_port}")
            while link_data["running"]:
                try:
                    conn, addr = srv.accept()
                    tune_tcp(conn)
                    def handle_direct(c, peer):
                        try:
                            hdr = recv_exact(c, 2)
                            if not hdr:
                                c.close()
                                return
                            (target_port,) = struct.unpack("!H", hdr)
                            db.log("external-node", "info", f"[DEBUG] Direct fallback from {peer} dialing target_port: {target_port}")
                            local = dial_tcp("127.0.0.1", target_port)
                            link_data["direct_bridges"] = link_data.get("direct_bridges", 0) + 1
                            bridge(local, c, link_id, target_port)
                        except Exception as e:
                            link_data["worker_errors"] = link_data.get("worker_errors", 0) + 1
                            link_data["last_worker_error"] = f"Direct fallback failed: {e}"[:180]
                            db.log("external-node", "error", f"[DEBUG] direct fallback error: {e}")
                            try:
                                c.close()
                            except Exception:
                                pass
                    threading.Thread(target=handle_direct, args=(conn, addr), daemon=True).start()
                except OSError:
                    if not link_data["running"]:
                        break
                    time.sleep(0.1)
                except Exception as e:
                    link_data["last_worker_error"] = f"Direct accept error: {e}"[:180]
                    time.sleep(0.1)

        def port_sync_loop():
            allowed_auto_ports = set()
            for value in link.get("auto_sync_ports", []):
                try:
                    port = int(value)
                    if valid_port(port):
                        allowed_auto_ports.add(port)
                except Exception:
                    pass
            while link_data["running"]:
                try:
                    c = dial_tcp(iran_ip, sync_port)
                except Exception:
                    time.sleep(SYNC_INTERVAL)
                    continue
                try:
                    while link_data["running"]:
                        ports = self.get_local_listen_ports(bridge_port, sync_port, allowed_auto_ports) if allowed_auto_ports else []
                        payload = bytes([len(ports)]) + b"".join(struct.pack("!H", p) for p in ports)
                        c.settimeout(2)
                        c.sendall(payload)
                        c.settimeout(None)
                        time.sleep(SYNC_INTERVAL)
                except Exception:
                    try: c.close()
                    except Exception: pass
                    time.sleep(SYNC_INTERVAL)

        def reverse_link_worker():
            delay = 0.2
            while link_data["running"]:
                try:
                    conn = dial_tcp(iran_ip, bridge_port)
                    
                    # Wrap TLS client
                    if tls_enabled:
                        try:
                            conn = wrap_socket_client_tls(conn, sni_hostname=link.get("tls_sni"))
                        except Exception as e:
                            db.log("external-node", "error", f"[DEBUG] External TLS wrap failed: {e}")
                            conn.close()
                            time.sleep(delay)
                            delay = min(delay * 2, 5.0)
                            continue

                    mode = link.get("tunnel_mode", "tcp")
                    ts = TunnelSocket(conn, role="external", mode=mode, config=link)
                    if not ts.perform_handshake():
                        db.log("external-node", "error", "[DEBUG] External handshake failed")
                        link_data["worker_errors"] = link_data.get("worker_errors", 0) + 1
                        link_data["last_worker_error"] = "External handshake failed"
                        ts.close()
                        time.sleep(delay)
                        delay = min(delay * 2, 5.0)
                        continue
                    
                    link_data["ready_workers"] = link_data.get("ready_workers", 0) + 1
                    try:
                        hdr = recv_exact(ts, 2)
                    finally:
                        link_data["ready_workers"] = max(0, link_data.get("ready_workers", 0) - 1)
                    if not hdr:
                        db.log("external-node", "error", "[DEBUG] External recv_exact failed to get target_port header")
                        link_data["worker_errors"] = link_data.get("worker_errors", 0) + 1
                        link_data["last_worker_error"] = "External tunnel did not receive target port"
                        ts.close()
                        time.sleep(delay)
                        delay = min(delay * 2, 5.0)
                        continue
                    (target_port,) = struct.unpack("!H", hdr)
                    
                    db.log("external-node", "info", f"[DEBUG] External dialing target_port: {target_port}")
                    local = dial_tcp("127.0.0.1", target_port)
                except Exception as e:
                    db.log("external-node", "error", f"[DEBUG] reverse_link_worker error connecting to {iran_ip}:{bridge_port} -> {e}")
                    link_data["worker_errors"] = link_data.get("worker_errors", 0) + 1
                    link_data["last_worker_error"] = str(e)[:180]
                    time.sleep(delay)
                    delay = min(delay * 2, 5.0)
                    continue

                db.log("external-node", "info", f"[DEBUG] External successfully bridged to target_port {target_port}")
                link_data["successful_bridges"] = link_data.get("successful_bridges", 0) + 1
                delay = 0.2
                bridge(local, ts, link_id, target_port)

        threading.Thread(target=port_sync_loop, daemon=True).start()
        threading.Thread(target=accept_direct_bridge, daemon=True).start()
        for _ in range(worker_count):
            threading.Thread(target=reverse_link_worker, daemon=True).start()

        db.log("foreign-node", "info", f"Started Link {link_id} (Iran IP: {iran_ip}, pool size: {pool_size}, workers: {worker_count})")

    def get_local_listen_ports(self, exclude_bridge, exclude_sync, allowed_ports=None):
        ports = set()
        allowed_ports = set(allowed_ports or [])
        for path in ("/proc/net/tcp", "/proc/net/tcp6"):
            if not os.path.exists(path): continue
            try:
                with open(path, "r") as f:
                    lines = f.readlines()
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 4 and parts[3] == "0A":
                        local_addr = parts[1]
                        port_hex = local_addr.split(":")[1]
                        port = int(port_hex, 16)
                        if port != exclude_bridge and port != exclude_sync and port in allowed_ports:
                            ports.add(port)
            except Exception:
                pass
        return sorted(list(ports))[:255]

    def stop_link(self, link_id):
        link_data = self.active_links.pop(link_id, None)
        if link_data:
            link_data["running"] = False
            try:
                if link_data.get("direct_bridge_sock"):
                    link_data["direct_bridge_sock"].close()
            except Exception:
                pass
            db.log("foreign-node", "info", f"Stopped link {link_id}")

    def collect_target_port_statuses(self):
        checks = {}
        with self.lock:
            items = list(self.active_links.items())
        for link_id, link_data in items:
            link = link_data.get("_raw_config") or {}
            link_checks = {}
            for pm in link.get("ports", []) or []:
                try:
                    user_port = int(pm.get("user_port"))
                    target_port = int(pm.get("target_port"))
                    if not valid_port(user_port) or not valid_port(target_port):
                        continue
                    open_now = is_local_tcp_listening(target_port)
                    link_checks[str(user_port)] = {
                        "user_port": user_port,
                        "target_port": target_port,
                        "target_open": open_now,
                        "checked_at": time.time()
                    }
                except Exception:
                    continue
            if link_checks:
                checks[link_id] = link_checks
        return checks

    def collect_link_statuses(self):
        statuses = {}
        with self.lock:
            items = list(self.active_links.items())
        for link_id, link_data in items:
            statuses[link_id] = {
                "running": bool(link_data.get("running")),
                "direct_bridge_listening": bool(link_data.get("direct_bridge_listening")),
                "direct_bridges": int(link_data.get("direct_bridges", 0) or 0),
                "ready_workers": int(link_data.get("ready_workers", 0) or 0),
                "successful_bridges": int(link_data.get("successful_bridges", 0) or 0),
                "worker_errors": int(link_data.get("worker_errors", 0) or 0),
                "last_worker_error": link_data.get("last_worker_error", ""),
                "network_mode": read_runtime_network_mode()
            }
        return statuses

    def report_loop(self):
        speedometer = NetSpeedometer()
        cpu_total, cpu_idle = get_cpu_percent()

        while self.running:
            time.sleep(3)
            cpu_t2, cpu_i2 = get_cpu_percent()
            dt_total = cpu_t2 - cpu_total
            dt_idle = cpu_i2 - cpu_idle
            cpu_pct = 100 * (1 - (dt_idle / dt_total)) if dt_total > 0 else 0.0
            cpu_total, cpu_idle = cpu_t2, cpu_i2

            ram_pct = get_ram_percent()
            rx, tx = speedometer.sample()

            connections = 0
            with active_bridges_lock:
                connections = len(active_bridges)

            payload = {
                "cpu": round(cpu_pct, 1),
                "ram": round(ram_pct, 1),
                "rx_speed": round(rx, 1),
                "tx_speed": round(tx, 1),
                "threads": threading.active_count(),
                "connections": connections,
                "target_port_checks": self.collect_target_port_statuses(),
                "link_statuses": self.collect_link_statuses(),
                "runtime_sessions": list_runtime_sessions(),
                "processes": get_process_snapshot(limit=10)
            }

            try:
                make_panel_request(self.panel_url, "/api/report", self.token, payload, private_key=self.private_key)
            except Exception:
                pass

# --------- Web GUI Panel (Embedded Resources) ----------
INDEX_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پنل مدیریت P00RIJA TUNNEL</title>
    <meta name="theme-color" content="#20c7b5">
    <link rel="manifest" href="/manifest.webmanifest">
    <style>
        @font-face { font-family: 'Vazirmatn'; src: url('/fonts/vazirmatn.woff2') format('woff2'); font-weight: normal; font-style: normal; font-display: swap; }
        @font-face { font-family: 'Shabnam'; src: url('/fonts/shabnam.woff2') format('woff2'); font-weight: normal; font-style: normal; font-display: swap; }
        @font-face { font-family: 'Sahel'; src: url('/fonts/sahel.woff2') format('woff2'); font-weight: normal; font-style: normal; font-display: swap; }
        @font-face { font-family: 'Inter'; src: url('/fonts/inter.woff2') format('woff2'); font-weight: normal; font-style: normal; font-display: swap; }
        @font-face { font-family: 'BYekan'; src: url('/fonts/BYekan.ttf') format('truetype'); font-weight: normal; font-style: normal; font-display: swap; }
        :root {
            --bg-main: #07100f;
            --bg-panel: #0c1716;
            --bg-card: rgba(13, 24, 23, 0.82);
            --border-card: rgba(148, 163, 184, 0.18);
            --accent-blue: #20c7b5;
            --accent-purple: #7c5cff;
            --text-primary: #f8fafc;
            --text-secondary: #9fb1bd;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --font-family: Vazirmatn, Tahoma, "Segoe UI", Arial, sans-serif;
            --select-bg: #0c1716;
            --select-fg: #f8fafc;
            color-scheme: dark;
        }

        body.theme-light {
            --bg-main: #eef7f4;
            --bg-panel: #ffffff;
            --bg-card: rgba(255, 255, 255, 0.92);
            --border-card: rgba(15, 23, 42, 0.14);
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --accent-blue: #0f9f8f;
            --accent-purple: #4f46e5;
            --select-bg: #ffffff;
            --select-fg: #0f172a;
            color-scheme: light;
        }

        body.theme-cyberpunk {
            --bg-main: #08060f;
            --bg-panel: #120820;
            --bg-card: rgba(22, 11, 36, 0.88);
            --border-card: rgba(255, 0, 153, 0.28);
            --accent-blue: #00e5ff;
            --accent-purple: #ff2bd6;
            --text-secondary: #d5b8ff;
            --select-bg: #120820;
            --select-fg: #f8fafc;
        }

        body.theme-forest {
            --bg-main: #07130d;
            --bg-panel: #0d2015;
            --bg-card: rgba(14, 38, 24, 0.88);
            --border-card: rgba(134, 239, 172, 0.22);
            --accent-blue: #34d399;
            --accent-purple: #84cc16;
            --text-secondary: #b9d6c5;
            --select-bg: #0d2015;
            --select-fg: #f8fafc;
        }

        body.theme-ocean {
            --bg-main: #06111d;
            --bg-panel: #071827;
            --bg-card: rgba(10, 31, 48, 0.88);
            --border-card: rgba(56, 189, 248, 0.24);
                    --accent-blue: #38bdf8;
            --accent-purple: #22d3ee;
            --text-secondary: #b7d4e8;
            --select-bg: #071827;
            --select-fg: #f8fafc;
        }

        body.font-vazirmatn { --font-family: Vazirmatn, Tahoma, "Segoe UI", Arial, sans-serif; }
        body.font-sahel { --font-family: Sahel, Tahoma, "Segoe UI", Arial, sans-serif; }
        body.font-shabnam { --font-family: Shabnam, Tahoma, "Segoe UI", Arial, sans-serif; }
        body.font-inter { --font-family: Inter, "Segoe UI", Arial, sans-serif; }
        body.font-byekan { --font-family: BYekan, "B Yekan", Tahoma, sans-serif; }
        body.font-system { --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: var(--font-family, inherit);
        }

        body {
            background:
                linear-gradient(145deg, rgba(32, 199, 181, 0.09), transparent 36%),
                linear-gradient(315deg, rgba(124, 92, 255, 0.08), transparent 40%),
                var(--bg-main);
            color: var(--text-primary);
            font-family: var(--font-family);
            min-height: 100vh;
            display: flex;
            overflow-x: hidden;
            font-feature-settings: "kern" 1;
        }

        .ambient-glow {
            display: none;
        }
        #glow-1 { top: -100px; left: -100px; }
        #glow-2 { bottom: -150px; right: -150px; }

        #login-screen {
            position: fixed;
            inset: 0;
            background-color: var(--bg-main);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }

        .login-card {
            width: 100%;
            max-width: 400px;
            padding: 40px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 8px;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.34);
            text-align: center;
            animation: panelEnter 0.45s ease both;
        }

        .login-logo {
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            margin-bottom: 30px;
        }

        .brand-logo {
            width: 74px;
            height: 74px;
            filter: drop-shadow(0 14px 28px rgba(32, 199, 181, 0.22));
            animation: logoPulse 3.6s ease-in-out infinite;
        }

        .brand-logo.small {
            width: 42px;
            height: 42px;
            animation-duration: 4.8s;
        }

        .brand-logo.tiny {
            width: 28px;
            height: 28px;
            animation-duration: 5.2s;
        }

        .logo-wordmark {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 0;
        }

        .form-group {
            margin-bottom: 20px;
            text-align: right;
        }

        .form-group label {
            display: block;
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }

        .form-input {
            width: 100%;
            padding: 12px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 16px;
            font-family: var(--font-family);
            transition: all 0.3s ease;
            text-align: left;
        }

        .form-input:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.15);
            background: rgba(255, 255, 255, 0.05);
        }

        .btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 20px rgba(0, 240, 255, 0.2);
        }

        .btn:active {
            transform: translateY(0) scale(0.99);
        }

        aside {
            width: 260px;
            background: var(--bg-panel);
            border-left: 1px solid var(--border-card);
            display: flex;
            flex-direction: column;
            padding: 30px 20px;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 40px;
            text-align: center;
        }

        .brand span {
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 14px 20px;
            border-radius: 8px;
            color: var(--text-secondary);
            text-decoration: none;
            font-weight: 500;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .nav-item:hover, .nav-item.active {
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-card);
            transform: translateX(-2px);
        }

        .nav-item.active {
            border-right: 4px solid var(--accent-blue);
            background: rgba(0, 240, 255, 0.03);
        }

        .nav-item i {
            width: 20px;
            height: 20px;
        }

        main {
            flex-grow: 1;
            padding: 32px;
            max-width: 1400px;
            margin: 0 auto;
            width: calc(100% - 260px);
            overflow-y: auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
        }

        .page-title h1 {
            font-size: 28px;
            font-weight: 600;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }

        .toolbar-select {
            width: auto;
            min-width: 130px;
            padding: 9px 12px;
            font-size: 13px;
            background: var(--select-bg);
        }

        select, option, button, input, textarea {
            font-family: var(--font-family);
            color: var(--text-primary);
        }

        select.form-input {
            appearance: none;
            -webkit-appearance: none;
            background-color: var(--select-bg) !important;
            color: var(--select-fg) !important;
            border-color: var(--border-card);
            background-image:
                linear-gradient(45deg, transparent 50%, var(--text-secondary) 50%),
                linear-gradient(135deg, var(--text-secondary) 50%, transparent 50%);
            background-position:
                calc(100% - 18px) calc(50% - 3px),
                calc(100% - 13px) calc(50% - 3px);
            background-size: 5px 5px, 5px 5px;
            background-repeat: no-repeat;
            padding-right: 34px;
        }

        html[dir="rtl"] select.form-input {
            background-position:
                18px calc(50% - 3px),
                23px calc(50% - 3px);
            padding-right: 16px;
            padding-left: 34px;
        }

        select option {
            background-color: var(--select-bg) !important;
            color: var(--select-fg) !important;
        }

        .mobile-menu-btn {
            display: none;
            width: auto;
            padding: 10px 12px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 8px;
            color: var(--text-primary);
        }

        .status-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-card);
            padding: 8px 16px;
            border-radius: 50px;
            font-size: 14px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--success);
            box-shadow: 0 0 10px var(--success);
            animation: statusPulse 1.9s ease-in-out infinite;
            flex: 0 0 auto;
        }

        .status-dot.offline {
            background-color: var(--danger);
            box-shadow: 0 0 10px var(--danger);
            animation-duration: 2.8s;
        }

        .status-dot.warning {
            background-color: var(--warning);
            box-shadow: 0 0 10px var(--warning);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 24px;
            margin-bottom: 30px;
        }

        .glass-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
            animation: panelEnter 0.42s ease both;
        }

        .glass-card:hover {
            border-color: rgba(0, 240, 255, 0.15);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }

        .stat-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .stat-info h3 {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 400;
            margin-bottom: 6px;
        }

        .stat-info p {
            font-size: 26px;
            font-weight: 700;
        }

        #stat-net-speed {
            white-space: nowrap;
            font-size: clamp(16px, 1.6vw, 24px);
            letter-spacing: 0;
        }

        .stat-icon {
            width: 48px;
            height: 48px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.03);
            display: flex;
            justify-content: center;
            align-items: center;
            color: var(--accent-blue);
        }

        .charts-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 30px;
        }

        .table-wrap {
            width: 100%;
            overflow-x: auto;
        }

        .link-actions {
            flex-wrap: wrap;
            justify-content: flex-end;
        }

        .btn-purple {
            background: #8b5cf6 !important;
            color: #fff !important;
            box-shadow: 0 0 12px rgba(139, 92, 246, 0.34);
        }

        .btn-cyan {
            background: #06b6d4 !important;
            color: #031014 !important;
            box-shadow: 0 0 12px rgba(6, 182, 212, 0.34);
        }

        .ssh-terminal {
            background: #050b0f;
            color: #d1fae5;
            border: 1px solid rgba(6, 182, 212, 0.35);
            border-radius: 8px;
            min-height: 360px;
            max-height: 52vh;
            overflow: auto;
            padding: 14px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
            font-size: 13px;
            line-height: 1.45;
            direction: ltr;
            text-align: left;
            white-space: pre-wrap;
            outline: none;
        }

        .ssh-terminal:focus {
            border-color: #06b6d4;
            box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.16);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: right;
            margin-top: 15px;
            min-width: 800px;
            table-layout: auto;
        }
        #table-nodes {
            min-width: 1800px;
            white-space: nowrap;
        }

        #table-nodes th,
        #table-nodes td {
            white-space: nowrap;
            vertical-align: middle;
        }

        #table-nodes .node-name-line,
        #table-nodes .node-actions-line {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            flex-wrap: nowrap;
        }

        #table-nodes .tag-row {
            display: inline-flex;
            flex-wrap: nowrap;
            margin-top: 0;
            vertical-align: middle;
        }

        #table-nodes .tag-pill {
            overflow-wrap: normal;
            white-space: nowrap;
        }

        th, td {
            padding: 16px;
            border-bottom: 1px solid var(--border-card);
        }

        th {
            font-weight: 500;
            color: var(--text-secondary);
            font-size: 14px;
        }

        td {
            font-size: 15px;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.01);
        }

        .modal {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(5px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }

        .modal-content {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            width: 90%;
            max-width: 500px;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
            animation: modalIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            max-height: 90vh;
            overflow-y: auto;
        }

        @keyframes modalIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }

        .modal-header h2 {
            font-size: 20px;
            font-weight: 600;
        }

        .modal-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
        }

        .hidden { display: none !important; }
        .text-success { color: var(--success) !important; }
        .text-danger { color: var(--danger) !important; }
        .text-warning { color: var(--warning) !important; }
        .flex-between { display: flex; justify-content: space-between; align-items: center; }
        .gap-10 { gap: 10px; }
        .mt-20 { margin-top: 20px; }
        .mb-20 { margin-bottom: 20px; }
        .w-auto { width: auto !important; }
        .p-10 { padding: 10px; }

        .tag-pill {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-card);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            display: inline-block;
            color: var(--text-primary);
            text-decoration: none;
            overflow-wrap: anywhere;
        }

        .tag-color-0 { background: rgba(32, 199, 181, 0.14); border-color: rgba(32, 199, 181, 0.42); }
        .tag-color-1 { background: rgba(124, 92, 255, 0.14); border-color: rgba(124, 92, 255, 0.42); }
        .tag-color-2 { background: rgba(245, 158, 11, 0.14); border-color: rgba(245, 158, 11, 0.42); }
        .tag-color-3 { background: rgba(16, 185, 129, 0.14); border-color: rgba(16, 185, 129, 0.42); }
        .tag-color-4 { background: rgba(239, 68, 68, 0.14); border-color: rgba(239, 68, 68, 0.42); }
        .tag-color-5 { background: rgba(59, 130, 246, 0.14); border-color: rgba(59, 130, 246, 0.42); }
        .tag-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
        .link-category summary { cursor: pointer; list-style: none; }
        .link-category summary::-webkit-details-marker { display: none; }
        .link-category-chart-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; align-items: stretch; }
        .category-metrics { display: grid; grid-template-columns: repeat(2, minmax(120px, 1fr)); gap: 10px; margin: 12px 0; }
        .category-metric { border: 1px solid var(--border-card); border-radius: 8px; padding: 10px; background: rgba(255,255,255,0.03); }
        .category-metric span { display: block; color: var(--text-secondary); font-size: 12px; margin-bottom: 4px; }
        .category-metric strong { display: block; white-space: nowrap; font-size: clamp(13px, 1.4vw, 18px); line-height: 1.25; letter-spacing: 0; }
        .category-metric.active { border-color: rgba(16,185,129,0.42); }
        .category-metric.download { border-color: rgba(59,130,246,0.42); }
        .category-metric.upload { border-color: rgba(124,92,255,0.42); }
        .category-metric.active strong { color: #10b981; }
        .category-metric.download strong { color: #3b82f6; }
        .category-metric.upload strong { color: #7c5cff; }
        .category-chart-frame { height: 180px; min-height: 180px; overflow: hidden; }

        #tab-about a.tag-pill {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.12);
        }




        .settings-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
        }

        #tab-settings .settings-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            align-items: start;
        }

        #tab-settings .settings-wide {
            grid-column: 1 / -1;
        }

        #engine-manager-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .compact-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
        }

        .help-list {
            display: grid;
            gap: 12px;
            color: var(--text-secondary);
            line-height: 1.8;
        }

        .node-role {
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .mini-metric {
            display: grid;
            gap: 6px;
            min-width: 150px;
        }

        .metric-bar {
            height: 7px;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
        }

        .metric-bar span {
            display: block;
            height: 100%;
            width: 0%;
            max-width: 100%;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
            transition: width 0.45s ease;
        }

        .resource-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .resource-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 10px;
        }

        .resource-summary .tag-pill {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }

        .node-resource-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }

        .node-resource-card {
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 12px;
            background: rgba(255,255,255,0.03);
        }

        .node-resource-card h4 {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 10px;
            font-size: 15px;
        }

        .node-resource-charts {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 12px;
        }

        .node-resource-chart {
            height: 150px;
            min-height: 150px;
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 8px;
            background: rgba(255,255,255,0.025);
            overflow: hidden;
        }

        .node-resource-chart canvas {
            display: block;
            width: 100%;
            height: 100%;
        }

        @keyframes panelEnter {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes logoPulse {
            0%, 100% { transform: translateY(0) scale(1); filter: drop-shadow(0 14px 28px rgba(32, 199, 181, 0.22)); }
            50% { transform: translateY(-2px) scale(1.025); filter: drop-shadow(0 18px 34px rgba(124, 92, 255, 0.25)); }
        }

        @keyframes statusPulse {
            0%, 100% { transform: scale(1); opacity: 0.82; }
            50% { transform: scale(1.35); opacity: 1; }
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.001ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.001ms !important;
                scroll-behavior: auto !important;
            }
        }

        @media (max-width: 1180px) {
            body { display: block; }
            aside {
                width: min(320px, 92vw);
                position: fixed;
                top: 0;
                bottom: 0;
                right: 0;
                display: none;
                flex-direction: column;
                gap: 8px;
                padding: 18px;
                overflow-y: auto;
                box-shadow: -16px 0 40px rgba(0, 0, 0, 0.28);
            }
            body.menu-open aside { display: flex; }
            .mobile-menu-btn { display: inline-flex; align-items: center; gap: 8px; }
            .brand { width: 100%; margin-bottom: 8px; }
            .nav-item { margin-bottom: 0; padding: 10px 12px; }
            main { width: 100%; padding: 18px; }
            header { align-items: flex-start; gap: 14px; flex-direction: column; }
            .header-actions { width: 100%; gap: 10px; }
            .toolbar-select { flex: 1 1 140px; min-width: 0; }
            .charts-grid, #tab-settings > div { grid-template-columns: 1fr !important; }
            .modal-content { max-height: 90vh; overflow-y: auto; }
            .flex-between { align-items: stretch; flex-direction: column; gap: 12px; }
            .link-actions { align-items: stretch; }
            .link-actions .btn, .link-actions .tag-pill, .link-actions .status-pill { width: 100% !important; justify-content: center; text-align: center; }
            .glass-card { padding: 18px; }
            table { min-width: 620px; }
            #table-nodes { min-width: 1500px; }
            .stats-grid { grid-template-columns: 1fr; }
            .link-category-chart-grid { grid-template-columns: 1fr; }
            .category-metrics { grid-template-columns: 1fr 1fr; }
            .node-resource-grid { grid-template-columns: 1fr; }
            #tab-settings .settings-grid { grid-template-columns: 1fr; }
        }

        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-main);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-blue);
        }
    </style>
</head>
<body>
    <div class="ambient-glow" id="glow-1"></div>
    <div class="ambient-glow" id="glow-2"></div>

    <div id="login-screen">
        <div class="login-card">
            <div class="login-logo">
                <img class="brand-logo" src="/icon.svg" alt="P00RIJA TUNNEL logo">
                <div class="logo-wordmark">P00RIJA TUNNEL</div>
            </div>
            <div class="compact-grid mb-20">
                <select id="login-language-select" class="form-input" onchange="setLanguage(this.value)">
                    <option value="fa">فارسی</option>
                    <option value="en">English</option>
                </select>
                <select id="login-theme-select" class="form-input" onchange="setTheme(this.value)">
                    <option value="dark">تیره</option>
                    <option value="light">روشن</option>
                    <option value="cyberpunk">سایبرپانک</option>
                    <option value="forest">جنگل</option>
                    <option value="ocean">اقیانوس</option>
                </select>
            </div>
            <form id="login-form">
                <div class="form-group">
                    <label>نام کاربری</label>
                    <input type="text" id="username" class="form-input" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label>کلمه عبور</label>
                    <input type="password" id="password" class="form-input" required autocomplete="current-password">
                </div>
                <div class="form-group hidden" id="otp-group">
                    <label>کد دو مرحله‌ای (اختیاری)</label>
                    <input type="text" id="otp" class="form-input" inputmode="numeric" autocomplete="one-time-code" placeholder="123456">
                </div>
                <button type="submit" class="btn">ورود به پنل</button>
            </form>
        </div>
    </div>

    <aside id="main-sidebar" class="hidden">
        <div class="brand">
            <img class="brand-logo small" src="/icon.svg" alt="P00RIJA TUNNEL logo">
            <span>P00RIJA Panel</span>
        </div>
        <div class="nav-item active" onclick="switchTab('dashboard')">
            <i data-lucide="gauge"></i>
            <span>داشبورد</span>
        </div>
        <div class="nav-item" onclick="switchTab('nodes')">
            <i data-lucide="server"></i>
            <span>مدیریت سرورها</span>
        </div>
        <div class="nav-item" onclick="switchTab('links')">
            <i data-lucide="split"></i>
            <span>مدیریت تانل‌ها</span>
        </div>
        <div class="nav-item" onclick="switchTab('logs')">
            <i data-lucide="terminal"></i>
            <span>لاگ‌های سیستم</span>
        </div>
        <div class="nav-item" onclick="switchTab('monitor')">
            <i data-lucide="activity"></i>
            <span>مانیتورینگ</span>
        </div>
        <div class="nav-item" onclick="switchTab('appearance')">
            <i data-lucide="palette"></i>
            <span>ظاهر و زبان</span>
        </div>
        <div class="nav-item" onclick="switchTab('settings')">
            <i data-lucide="settings"></i>
            <span>تنظیمات</span>
        </div>
        <div class="nav-item" onclick="switchTab('help')">
            <i data-lucide="book-open"></i>
            <span>راهنما</span>
        </div>
        <div class="nav-item" onclick="switchTab('about')">
            <i data-lucide="info"></i>
            <span>درباره من</span>
        </div>
        <div class="nav-item mt-20" onclick="logout()" style="margin-top: auto; border-top: 1px solid var(--border-card); padding-top: 20px;">
            <i data-lucide="log-out" class="text-danger"></i>
            <span class="text-danger">خروج</span>
        </div>
    </aside>

    <main id="main-workspace" class="hidden">
        <header>
            <div class="page-title">
                <button class="mobile-menu-btn" onclick="toggleMobileMenu()"><i data-lucide="menu"></i><span>منو</span></button>
                <h1 id="tab-title">داشبورد</h1>
            </div>
            <div class="header-actions">
                <select id="auto-refresh-select" class="form-input toolbar-select" onchange="setAutoRefresh()">
                    <option value="0">رفرش: خاموش</option>
                    <option value="1">رفرش: 1s</option>
                    <option value="3" selected>رفرش: 3s</option>
                    <option value="5">رفرش: 5s</option>
                    <option value="10">رفرش: 10s</option>
                    <option value="30">رفرش: 30s</option>
                    <option value="60">رفرش: 60s</option>
                </select>
                <select id="font-select" class="form-input toolbar-select" onchange="setFont(this.value)">
                    <option value="system">سیستم</option>
                    <option value="vazirmatn">Vazirmatn</option>
                    <option value="sahel">Sahel</option>
                    <option value="shabnam">Shabnam</option>
                    <option value="inter">Inter</option>
                    <option value="byekan">Byekan</option>
                </select>
                <select id="language-select" class="form-input toolbar-select" onchange="setLanguage(this.value)">
                    <option value="fa">فارسی</option>
                    <option value="en">English</option>
                </select>
                <select id="theme-select" class="form-input toolbar-select" onchange="setTheme(this.value)">
                    <option value="dark">تیره</option>
                    <option value="light">روشن</option>
                    <option value="cyberpunk">سایبرپانک</option>
                    <option value="forest">جنگل</option>
                    <option value="ocean">اقیانوس</option>
                </select>
                <div class="status-pill">
                    <img class="brand-logo tiny" src="/icon.svg" alt="P00RIJA TUNNEL logo">
                    <div class="status-dot"></div>
                    <span>P00RIJA PANEL فعال است</span>
                </div>
            </div>
        </header>

        <div id="tab-dashboard" class="tab-content">
            <div class="stats-grid">
                <div class="glass-card stat-card">
                    <div class="stat-info">
                        <h3>سرورها / نودها</h3>
                        <p id="stat-nodes-count">۰</p>
                    </div>
                    <div class="stat-icon"><i data-lucide="server"></i></div>
                </div>
                <div class="glass-card stat-card">
                    <div class="stat-info">
                        <h3>تانل‌های فعال</h3>
                        <p id="stat-links-count">۰</p>
                    </div>
                    <div class="stat-icon" style="color: var(--accent-purple);"><i data-lucide="git-commit"></i></div>
                </div>
                <div class="glass-card stat-card">
                    <div class="stat-info">
                        <h3>ترافیک شبکه (Rx/Tx)</h3>
                        <p id="stat-net-speed">0 MB/s</p>
                    </div>
                    <div class="stat-icon" style="color: var(--success);"><i data-lucide="activity"></i></div>
                </div>
                <div class="glass-card stat-card">
                    <div class="stat-info">
                        <h3>تردهای فعال</h3>
                        <p id="stat-threads-count">۰</p>
                    </div>
                    <div class="stat-icon" style="color: var(--warning);"><i data-lucide="cpu"></i></div>
                </div>
            </div>

            <div class="glass-card mb-20" style="padding: 15px;">
                <h2 style="margin-bottom: 15px; font-size: 16px;">وضعیت سیستم میزبان پنل</h2>
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">هسته‌های CPU</span>
                        <div id="host-cpu" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">RAM (آزاد / کل)</span>
                        <div id="host-ram" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">Swap (آزاد / کل)</span>
                        <div id="host-swap" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">دیسک (آزاد / کل)</span>
                        <div id="host-disk" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">بار سیستم / آپ‌تایم</span>
                        <div id="host-load" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">پروسس پنل</span>
                        <div id="host-process" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">Docker</span>
                        <div id="host-docker" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                </div>
            </div>

            <div class="charts-grid">
                <div class="glass-card">
                    <h2 class="mb-20">ترافیک عبوری شبکه (Live)</h2>
                    <div style="height: 300px;"><canvas id="chart-traffic"></canvas></div>
                </div>
                <div class="glass-card">
                    <h2 class="mb-20">اتصالات فعال تانل</h2>
                    <div style="height: 300px;"><canvas id="chart-connections"></canvas></div>
                </div>
            </div>
            <div class="charts-grid">
                <div class="glass-card">
                    <h2 class="mb-20">منابع سیستم پنل</h2>
                    <div style="height: 260px;"><canvas id="chart-panel-system"></canvas></div>
                </div>
                <div class="glass-card">
                    <h2 class="mb-20">Runtime پنل</h2>
                    <div style="height: 260px;"><canvas id="chart-panel-runtime"></canvas></div>
                </div>
            </div>
        </div>

        <div id="tab-nodes" class="tab-content hidden">
            <div class="flex-between mb-20">
                <h2>لیست نودها</h2>
                <div class="flex-between gap-10">
                    <button class="btn w-auto p-10" onclick="openNodeSshModal()">اتصال و کنترل SSH نود</button>
                    <button class="btn w-auto p-10" onclick="openNewNodeModal()">افزودن نود جدید</button>
                </div>
            </div>
            <div class="glass-card">
                <div class="table-wrap">
                    <table id="table-nodes">
                        <thead>
                            <tr>
                                <th>نام سرور</th>
                                <th>نقش</th>
                                <th>آدرس IP</th>
                                <th>وضعیت</th>
                                <th>منابع سرور</th>
                                <th>ترافیک</th>
                                <th>تردها/کانکشن</th>
                                <th>عملیات</th>
                            </tr>
                        </thead>
                        <tbody>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="tab-links" class="tab-content hidden">
            <div class="flex-between mb-20">
                <h2>لیست تانل‌ها (لینک‌ها)</h2>
                <button class="btn w-auto p-10" onclick="openNewLinkModal()">افزودن تانل جدید</button>
            </div>
            <details class="glass-card mb-20 link-category">
                <summary class="flex-between mb-20">
                    <h2>پروفایل‌های تانل</h2>
                    <span class="tag-pill">آماده + شخصی</span>
                </summary>
                <div class="compact-grid">
                    <input id="profile-name" class="form-input" placeholder="نام پروفایل">
                    <select id="profile-engine" class="form-input" onchange="syncProfileModeOptions()">
                        <option value="builtin">Built-in Reverse</option>
                        <option value="gost">GOST</option>
                        <option value="backhaul">Backhaul</option>
                        <option value="rathole">Rathole</option>
                        <option value="chisel">Chisel</option>
                        <option value="frp">FRP</option>
                        <option value="xray">Xray</option>
                        <option value="muxquantum">Mux/Quantum</option>
                        <option value="hysteria2">Hysteria 2</option>
                        <option value="singbox">sing-box</option>
                        <option value="tuic">TUIC</option>
                        <option value="naiveproxy">NaiveProxy</option>
                        <option value="shadowtls">ShadowTLS</option>
                        <option value="brook">Brook</option>
                        <option value="mieru">Mieru</option>
                    </select>
                    <select id="profile-mode" class="form-input">
                        <option value="websocket">WebSocket</option>
                        <option value="http_obfs">HTTP Obfs</option>
                        <option value="tcp">TCP Raw</option>
                    </select>
                    <input id="profile-pool" type="number" class="form-input" value="120" placeholder="Pool">
                    <input id="profile-host" class="form-input" value="speedtest.net" placeholder="Host / SNI">
                    <input id="profile-path" class="form-input" value="/tunnel" placeholder="Path">
                    <input id="profile-jitter" type="number" class="form-input" value="0" placeholder="Jitter ms">
                </div>
                <div class="flex-between gap-10 mt-20">
                    <button class="btn w-auto p-10" onclick="saveProfile()">ذخیره پروفایل</button>
                    <button class="btn w-auto p-10" onclick="exportProfiles()">خروجی پروفایل‌ها</button>
                </div>
                <textarea id="profile-import" class="form-input mt-20" rows="4" placeholder="Paste exported profiles JSON"></textarea>
                <button class="btn w-auto p-10 mt-20" onclick="importProfiles()">ورود پروفایل‌ها</button>
            </details>
            <div id="link-category-charts" class="link-category-chart-grid mb-20"></div>
            <div id="links-container" style="display: flex; flex-direction: column; gap: 24px;">
            </div>
        </div>

        <div id="tab-logs" class="tab-content hidden">
            <div class="flex-between mb-20">
                <h2>لاگ‌های سیستم</h2>
                <button class="btn w-auto p-10" onclick="exportLogsCSV()">خروجی CSV</button>
            </div>
            <div class="glass-card" style="max-height: 600px; overflow-y: auto;">
                <div class="table-wrap">
                    <table id="table-logs">
                        <thead>
                            <tr>
                                <th>زمان ثبت</th>
                                <th>منبع</th>
                                <th>سطح لاگ</th>
                                <th>شرح لاگ</th>
                            </tr>
                        </thead>
                        <tbody>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="tab-monitor" class="tab-content hidden">
            <div class="flex-between mb-20">
                <h2>مانیتورینگ سشن‌ها، تردها و پروسس‌ها</h2>
                <button class="btn w-auto p-10" onclick="fetchRuntime()">بروزرسانی دستی</button>
            </div>
            <div class="settings-grid">
                <div class="glass-card">
                    <h3 class="mb-20">سشن‌های فعال تانل</h3>
                    <div class="table-wrap">
                        <table id="table-sessions">
                            <thead><tr><th>شناسه</th><th>تانل</th><th>مقصد</th><th>عمر</th><th>بیکاری</th><th>عملیات</th></tr></thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
                <div class="glass-card">
                    <h3 class="mb-20">پروسس‌های سیستم</h3>
                    <div class="table-wrap">
                        <table id="table-processes">
                            <thead><tr><th>PID</th><th>نام</th><th>RSS</th><th>تردها</th><th>زمان CPU</th><th>عملیات</th></tr></thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
                <div class="glass-card">
                    <h3 class="mb-20">مدیریت منابع سرور</h3>
                    <div id="resource-summary" class="resource-summary mb-20">
                        <span class="tag-pill">تردها <strong id="resource-threads">0</strong></span>
                        <span class="tag-pill">سشن‌ها <strong id="resource-sessions">0</strong></span>
                        <span class="tag-pill">RSS <strong id="resource-rss">0 MB</strong></span>
                    </div>
                    <div class="form-group">
                        <label>محدوده بهینه‌سازی</label>
                        <select id="resource-scope" class="form-input">
                            <option value="all">پنل و همه نودهای آنلاین</option>
                            <option value="panel">فقط پنل</option>
                            <option value="nodes">فقط نودهای آنلاین</option>
                        </select>
                    </div>
                    <div class="resource-actions">
                        <button class="btn w-auto p-10" onclick="optimizeResources('idle')">پاک‌سازی سشن‌های Idle</button>
                        <button class="btn w-auto p-10" onclick="optimizeResources('gc')">پاک‌سازی RAM/GC</button>
                        <button class="btn w-auto p-10" onclick="optimizeResources('all')" style="background: var(--warning);">بهینه‌سازی کامل منابع</button>
                    </div>
                    <p id="resource-result" class="mt-20" style="color: var(--text-secondary); line-height: 1.8;"></p>
                </div>
                <div class="glass-card">
                    <h3 class="mb-20">منابع زنده نودها</h3>
                    <div id="node-resource-grid" class="node-resource-grid"></div>
                </div>
            </div>
        </div>

        <div id="tab-appearance" class="tab-content hidden">
            <div class="settings-grid">
                <div class="glass-card">
                    <h2 class="mb-20">ظاهر، فونت و زبان</h2>
                    <div class="compact-grid">
                        <div class="form-group">
                            <label>زبان پنل</label>
                            <select id="appearance-language" class="form-input" onchange="setLanguage(this.value)">
                                <option value="fa">فارسی</option>
                                <option value="en">English</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>تم رنگی</label>
                            <select id="appearance-theme" class="form-input" onchange="setTheme(this.value)">
                                <option value="dark">تیره</option>
                                <option value="light">روشن</option>
                                <option value="cyberpunk">سایبرپانک</option>
                                <option value="forest">جنگل</option>
                                <option value="ocean">اقیانوس</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>فونت برنامه</label>
                            <select id="appearance-font" class="form-input" onchange="setFont(this.value)">
                                <option value="system">سیستم</option>
                                <option value="vazirmatn">Vazirmatn</option>
                                <option value="sahel">Sahel</option>
                                <option value="shabnam">Shabnam</option>
                                <option value="inter">Inter</option>
                                <option value="byekan">Byekan</option>
                            </select>
                        </div>
                    </div>
                </div>
                </div>
            </div>
        </div>

        <div id="tab-settings" class="tab-content hidden">
            <h2>تنظیمات پنل</h2>
            <div class="settings-grid">
                <div class="glass-card mt-20">
                    <form id="form-settings-pass" class="mb-20">
                        <h3 class="mb-20">تغییر مشخصات مدیریت</h3>
                        <div class="form-group">
                            <label>نام کاربری</label>
                            <input type="text" id="setting-username" class="form-input" required autocomplete="username">
                        </div>
                        <div class="form-group">
                            <label>کلمه عبور جدید</label>
                            <input type="password" id="setting-password" class="form-input" required autocomplete="new-password">
                        </div>
                        <button type="submit" class="btn w-auto p-10">بروزرسانی مشخصات ورود</button>
                    </form>
                </div>

                <div class="glass-card mt-20">
                    <h3 class="mb-20">امنیت ورود</h3>
                    <form id="form-settings-security">
                        <div class="form-group">
                            <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="setting-two-factor" style="width: 18px; height: 18px;">
                                فعال‌سازی ورود دو مرحله‌ای TOTP
                            </label>
                        </div>
                        <div class="form-group">
                            <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="setting-biometric" style="width: 18px; height: 18px;">
                                فعال‌سازی بایومتریک مرورگر برای Quick Unlock
                            </label>
                        </div>
                        <button type="submit" class="btn w-auto p-10">ثبت تنظیمات امنیتی</button>
                    </form>
                    <p id="totp-secret-box" class="tag-pill mt-20 hidden" style="direction:ltr; text-align:left;"></p>
                </div>

                <div class="glass-card mt-20">
                    <h3 class="mb-20">تنظیمات نمایش</h3>
                    <form id="form-settings-display" class="mb-20">
                        <div class="form-group">
                            <label>واحد نمایش ترافیک در داشبورد و جدول نودها</label>
                            <select id="setting-traffic-unit" class="form-input">
                                <option value="MB">مگابایت بر ثانیه (MB/s)</option>
                                <option value="KB">کیلوبایت بر ثانیه (KB/s)</option>
                            </select>
                        </div>
                        <button type="submit" class="btn w-auto p-10">اعمال تنظیمات نمایش</button>
                    </form>
                </div>

                <div class="glass-card mt-20">
                    <h3 class="mb-20">تنظیمات شبکه</h3>
                    <form id="form-settings-network" class="mb-20">
                        <div class="form-group">
                            <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="setting-disable-ipv6" style="width: 18px; height: 18px;">
                                غیرفعال‌سازی سراسری IPv6 (توصیه شده در ایران)
                            </label>
                            <small style="display:block; margin-top:5px; opacity:0.8;">در صورت اختلال و بسته شدن IPV6 این گزینه را فعال کنید تا ارتباط شبکه قطع نشود.</small>
                        </div>
                        <div class="form-group">
                            <label>زمان اعمال و ریست مجدد هسته (به دقیقه، 0 برای غیرفعال کردن)</label>
                            <input type="number" id="setting-engine-restart-interval" class="form-input" min="0" value="0">
                            <small style="display:block; margin-top:5px; opacity:0.8;">برای پایداری بیشتر، هسته‌ها می‌توانند به صورت زمان‌بندی شده ریست شوند تا حافظه و منابع آزاد شود.</small>
                        </div>
                        <button type="submit" class="btn w-auto p-10">اعمال تنظیمات شبکه</button>
                    </form>
                </div>
                
                <div class="glass-card mt-20 settings-wide">
                    <h3 class="mb-20">مدیریت هسته‌ها (Engine Management)</h3>
                    <div id="engine-manager-grid" class="compact-grid"></div>
                    <small style="display:block; margin-top:10px; opacity:0.8;">هسته‌ها از پوشه آفلاین engines داخل image استفاده می‌کنند. نصب از GitHub فقط وقتی لازم است که اینترنت در دسترس باشد.</small>
                </div>
                
                <div class="glass-card mt-20 settings-wide">
                    <h3 class="mb-20">تنظیمات SSL/TLS وب پنل (HTTPS)</h3>
                    <form id="form-settings-tls" class="mb-20">
                        <div class="form-group">
                            <label style="display: inline-flex; align-items: center; gap: 8px;">
                                <input type="checkbox" id="setting-panel-tls" style="width: 18px; height: 18px;" checked disabled>
                                HTTPS اجباری برای وب پنل
                            </label>
                            <small style="display:block; margin-top:5px; opacity:0.8;">در صورت نبود certificate معتبر، پنل به صورت خودکار certificate محلی می‌سازد.</small>
                        </div>
                        <div class="form-group">
                            <label>مسیر Certificate (.pem)</label>
                            <input type="text" id="setting-cert-path" class="form-input" placeholder="/opt/p00rija/certs/cert.pem">
                        </div>
                        <div class="form-group">
                            <label>مسیر Private Key (.pem)</label>
                            <input type="text" id="setting-key-path" class="form-input" placeholder="/opt/p00rija/certs/key.pem">
                        </div>
                        <button type="submit" class="btn w-auto p-10" style="margin-bottom: 10px;">ثبت تنظیمات SSL</button>
                    </form>
                    <hr style="border: 0; border-top: 1px solid var(--border-card); margin: 20px 0;">

                    <h4 class="mb-20">ساخت Certificate محلی برای IP یا Hostname</h4>
                    <form id="form-local-cert" class="mb-20">
                        <div class="form-group">
                            <label>IP یا Hostname پنل</label>
                            <input type="text" id="local-cert-host" class="form-input" placeholder="127.0.0.1 یا panel.local" required>
                        </div>
                        <button type="submit" class="btn w-auto p-10" style="background: var(--accent-blue);">ساخت و اعمال Certificate محلی</button>
                    </form>
                    <hr style="border: 0; border-top: 1px solid var(--border-card); margin: 20px 0;">
                    
                    <h4 class="mb-20">دریافت Certificate خودکار Let's Encrypt</h4>
                    <form id="form-acme-cert" class="mb-20">
                        <div class="form-group">
                            <label>آدرس دامنه (مثال: panel.yourdomain.com)</label>
                            <input type="text" id="acme-domain" class="form-input" placeholder="panel.yourdomain.com" required>
                        </div>
                        <div class="form-group">
                            <label>ایمیل (جهت ثبت‌نام در Let's Encrypt)</label>
                            <input type="email" id="acme-email" class="form-input" placeholder="admin@yourdomain.com" required>
                        </div>
                        <button type="submit" class="btn w-auto p-10" style="background: var(--accent-purple);">دریافت و نصب گواهینامه SSL</button>
                    </form>
                    
                    <button class="btn w-auto p-10 mt-20" onclick="restartPanel()" style="background: var(--danger);">اعمال تغییرات و ریستارت وب پنل</button>
                </div>
            </div>
        </div>

        <div id="tab-help" class="tab-content hidden">
            <div class="glass-card">
                <div style="text-align: center;">
                    <img src="/icon.svg" style="width: 120px; height: 120px; display: block; margin: 0 auto 20px;" alt="P00RIJA Logo">
                    <h2 class="mb-20">راهنمای سریع داشبورد</h2>
                </div>
                <div class="help-list">
                    <p>۱. در مدیریت سرورها، ابتدا نودهای داخلی و خارجی را ثبت کنید. اگر یک سرور هم پنل است و هم نود داخلی، همان سرور را به عنوان Internal Node هم اضافه کنید تا در ساخت تانل قابل انتخاب باشد.</p>
                    <p>۲. در مدیریت تانل‌ها، از پروفایل‌های آماده برای شروع سریع استفاده کنید. بعد از انتخاب پروفایل، Engine، Transport، Network، TLS، SNI، Path و Pool همچنان قابل تغییر هستند.</p>
                    <p>۳. برای هر تانل Bridge Port و Sync Port روی نود داخلی باید آزاد و یکتا باشد. اگر پورت تکراری باشد، پنل قبل از ذخیره خطا می‌دهد.</p>
                    <p>۴. بعد از ساخت تانل، Port Forwarding را اضافه کنید. User/Internal Port همان پورتی است که روی نود داخلی باز می‌شود و Target Port به سرویس سمت نود خارجی اشاره می‌کند.</p>
                    <p>۵. دکمه توقف تانل، تانل را از کانفیگ نودها خارج می‌کند و با ادامه دوباره به نودها تحویل داده می‌شود. برای اعمال عملی، چند ثانیه تا polling بعدی نود صبر کنید.</p>
                    <p>۶. اگر TLS تانل فعال است، SNI و Host را هماهنگ انتخاب کنید. برای وب پنل، تنظیمات HTTPS در Settings فقط با مسیر Certificate و Key معتبر و ریستارت پنل کامل اعمال می‌شود.</p>
                    <p>۷. نمودارهای Dashboard و وضعیت منابع/ترافیک مدیریت سرورها با Refresh Time بالای صفحه به صورت زنده به‌روزرسانی می‌شوند. برای تست فوری، مقدار ۳ ثانیه را انتخاب کنید.</p>
                    <p>۸. در Monitor می‌توانید sessionهای فعال، مصرف RSS و تعداد threadها را ببینید و پاک‌سازی idle یا GC را اجرا کنید.</p>
                    <p>۹. نام کاربری و رمز پیش‌فرض دیتابیس تازه admin/admin است؛ در نصب wizard رمز جدید بگذارید و بعد از ورود آن را تغییر دهید.</p>
                </div>
            </div>
        </div>

        <div id="tab-about" class="tab-content hidden">
            <div class="glass-card">
                <div style="text-align: center;">
                    <img src="/icon.svg" style="width: 120px; height: 120px; display: block; margin: 0 auto 20px;" alt="P00RIJA Logo">
                    <h2 class="mb-20">درباره من</h2>
                </div>
                <p class="mb-20" style="color: var(--text-secondary); line-height: 1.9; text-align: center;">P00RIJA TUNNEL برای مدیریت متمرکز تانل‌های معکوس در سناریوهای چندنودی ساخته شده است؛ جایی که پنل باید هم وضعیت سرورها را زنده ببیند، هم پروفایل‌های مختلف تانلینگ را کنترل کند، و هم امکان توقف، ادامه، و ویرایش عملیاتی تانل‌ها را بدون دستکاری دستی کانفیگ‌ها بدهد.</p>
                <div class="compact-grid mb-20">
                    <div style="padding: 16px; border: 1px solid var(--border-card); border-radius: 8px;">
                        <h3 class="mb-20">تمرکز پروژه</h3>
                        <p style="color: var(--text-secondary); line-height: 1.8;">پایداری ارتباط، انتخاب هوشمند پروفایل، مانیتورینگ منابع، و مدیریت امن نودها با توکن و امضای درخواست.</p>
                    </div>
                    <div style="padding: 16px; border: 1px solid var(--border-card); border-radius: 8px;">
                        <h3 class="mb-20">برای چه سناریویی؟</h3>
                        <p style="color: var(--text-secondary); line-height: 1.8;">پنل مرکزی، نودهای داخلی، نودهای خارجی، شبکه‌های جدا، و تانل‌هایی که باید زیر بار واقعی قابل مشاهده و قابل کنترل باشند.</p>
                    </div>
                </div>
                <div class="compact-grid">
                    <div class="tag-pill">نسخه: <span id="about-version">1.3.0</span></div>
                    <div class="tag-pill">لایسنس: <span id="about-license">GPL-3.0</span></div>
                    <a class="tag-pill" href="https://github.com/Poorija" target="_blank" rel="noopener">گیت‌هاب: github.com/Poorija</a>
                    <a class="tag-pill" href="mailto:mohammadmahdi.farhadianfard@gmail.com">mohammadmahdi.farhadianfard@gmail.com</a>
                </div>
            </div>
        </div>
    </main>

    <div id="modal-add-node" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="node-modal-title">افزودن نود جدید</h2>
                <button class="modal-close" onclick="closeModal('modal-add-node')"><i data-lucide="x"></i></button>
            </div>
            <form id="form-add-node">
                <div class="form-group">
                    <label>نام نود (مثال: INTERNAL-Node-1)</label>
                    <input type="text" id="node-name" class="form-input" required>
                </div>
                <div class="form-group">
                    <label>نقش نود</label>
                    <select id="node-role" class="form-input">
                        <option value="internal">نود داخلی (Internal Node)</option>
                        <option value="external">نود خارجی (External Node)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>آدرس IP سرور</label>
                    <input type="text" id="node-ip" class="form-input" placeholder="1.2.3.4" required>
                </div>
                <div class="form-group">
                    <label>تگ‌های نود</label>
                    <input type="text" id="node-tags" class="form-input" placeholder="iran, edge, vip">
                </div>
                <button type="submit" id="node-submit-btn" class="btn">ثبت نود جدید</button>
            </form>
        </div>
    </div>

    <div id="loading-overlay" class="modal" style="z-index: 9999; background: rgba(0, 0, 0, 0.8);">
        <div class="modal-content" style="max-width: 300px; text-align: center; background: transparent; border: none; box-shadow: none;">
            <div class="spinner" style="border: 4px solid rgba(255, 255, 255, 0.3); border-radius: 50%; border-top: 4px solid var(--primary); width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 15px auto;"></div>
            <h3 style="color: white;" data-tx="در حال آزمایش، صبر کنید...|Testing, please wait...">در حال آزمایش، صبر کنید...</h3>
        </div>
    </div>
    <div id="modal-node-test" class="modal">
        <div class="modal-content" style="max-width: 720px;">
            <div class="modal-header">
                <h2>تست ارتباط سرور</h2>
                <button class="modal-close" onclick="closeModal('modal-node-test')"><i data-lucide="x"></i></button>
            </div>
            <div id="node-test-loading" class="mb-20" style="display:flex; align-items:center; gap:12px;">
                <div class="spinner" style="border: 3px solid rgba(255,255,255,0.18); border-top-color: var(--accent-blue); width: 28px; height: 28px; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <strong>در حال تست ارتباط، چند لحظه صبر کنید...</strong>
            </div>
            <pre id="node-test-result" class="form-input" style="min-height: 220px; white-space: pre-wrap; direction:ltr; text-align:left;"></pre>
        </div>
    </div>
    
    <div id="modal-show-token" class="modal">
        <div class="modal-content" style="text-align: center;">
            <div class="modal-header">
                <h2>توکن امنیتی نود ایجاد شده</h2>
                <button class="modal-close" onclick="closeModal('modal-show-token')"><i data-lucide="x"></i></button>
            </div>
            <p class="mb-20 text-warning" style="font-size: 14px;">توکن و کلید خصوصی را هر دو در نصب نود وارد کنید. این اطلاعات حساس می‌باشد، در حفظ و افشا نشدن آنها دقت کنید.</p>
            <div class="form-group">
                <label>Node Token</label>
                <div style="display:flex; gap:8px; align-items:center;">
                    <input type="text" id="generated-token-input" class="form-input" readonly style="text-align: center; font-size: 14px; font-weight: bold; border-color: var(--accent-blue);">
                    <button type="button" class="btn w-auto p-10 btn-purple" onclick="copyFieldValue('generated-token-input')">کپی</button>
                </div>
            </div>
            <div class="form-group">
                <label>Node Private Key</label>
                <div style="display:flex; gap:8px; align-items:center;">
                    <input type="text" id="generated-private-key-input" class="form-input" readonly style="text-align: center; font-size: 13px; font-weight: bold; border-color: var(--accent-purple); direction:ltr;">
                    <button type="button" class="btn w-auto p-10 btn-purple" onclick="copyFieldValue('generated-private-key-input')">کپی</button>
                </div>
            </div>
            <div class="form-group">
                <label>Installer Values</label>
                <div style="display:flex; gap:8px; align-items:flex-start;">
                    <textarea id="generated-node-setup-input" class="form-input" readonly rows="5" style="font-family: monospace; font-size: 13px; direction:ltr; text-align:left; resize: vertical;"></textarea>
                    <button type="button" class="btn w-auto p-10 btn-purple" onclick="copyFieldValue('generated-node-setup-input')">کپی</button>
                </div>
            </div>
            <button class="btn mt-20" onclick="closeModal('modal-show-token')">تایید و بستن</button>
        </div>
    </div>
    <div id="modal-show-config" class="modal">
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2>کانفیگ موتور تانلینگ (Engine Config)</h2>
                <button class="modal-close" onclick="closeModal('modal-show-config')"><i data-lucide="x"></i></button>
            </div>
            <div class="form-group">
                <textarea id="engine-config-content" class="form-input" readonly rows="15" style="font-family: monospace; font-size: 13px; text-align: left; direction: ltr; resize: none;"></textarea>
            </div>
            <button class="btn" onclick="closeModal('modal-show-config')">بستن</button>
        </div>
    </div>
    <div id="modal-node-ssh" class="modal">
        <div class="modal-content" style="max-width: 980px;">
            <div class="modal-header">
                <h2>اتصال و کنترل SSH نود</h2>
                <button class="modal-close" onclick="closeSshTerminal(true); closeModal('modal-node-ssh')"><i data-lucide="x"></i></button>
            </div>
            <form id="form-node-ssh">
                <div class="compact-grid">
                    <div class="form-group">
                        <label>نود</label>
                        <select id="ssh-node-id" class="form-input" onchange="fillSshFromNode()"></select>
                    </div>
                    <div class="form-group">
                        <label>هاست / IP</label>
                        <input id="ssh-host" class="form-input" placeholder="192.0.2.10">
                    </div>
                    <div class="form-group">
                        <label>پورت</label>
                        <input id="ssh-port" type="number" class="form-input" value="22">
                    </div>
                    <div class="form-group">
                        <label>نام کاربری</label>
                        <input id="ssh-username" class="form-input" value="root">
                    </div>
                    <div class="form-group">
                        <label>روش احراز هویت</label>
                        <select id="ssh-auth-method" class="form-input" onchange="toggleSshAuthFields()">
                            <option value="password">رمز عبور</option>
                            <option value="key">کلید خصوصی</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Timeout ثانیه</label>
                        <input id="ssh-timeout" type="number" class="form-input" value="15">
                    </div>
                </div>
                <div id="ssh-password-group" class="form-group">
                    <label>رمز عبور</label>
                    <input id="ssh-password" type="password" class="form-input" autocomplete="new-password">
                </div>
                <div id="ssh-key-group" class="form-group hidden">
                    <label>کلید خصوصی</label>
                    <textarea id="ssh-private-key" class="form-input" rows="5" style="font-family: monospace; direction:ltr; text-align:left;"></textarea>
                </div>
                <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer;">
                    <input id="ssh-save" type="checkbox" style="width:18px;height:18px;">
                    ذخیره رمزنگاری‌شده مشخصات اتصال برای این نود
                </label>
                <div class="flex-between gap-10 mt-20" style="justify-content:flex-start; flex-wrap:wrap;">
                    <button type="submit" class="btn w-auto btn-cyan">اتصال ترمینال</button>
                    <button type="button" class="btn w-auto p-10" onclick="sendSshTerminalInput('\u0003')">Ctrl+C</button>
                    <button type="button" class="btn w-auto p-10 btn-danger" onclick="closeSshTerminal()">قطع اتصال</button>
                    <button type="button" class="btn w-auto p-10" onclick="saveSshOnly()">فقط ذخیره مشخصات</button>
                    <span id="ssh-status" class="tag-pill">آماده اتصال</span>
                </div>
                <div id="ssh-output" class="ssh-terminal mt-20" tabindex="0" spellcheck="false"></div>
            </form>
        </div>
    </div>
    <div id="modal-add-link" class="modal">
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2 id="link-modal-title">ایجاد تانل (لینک) جدید</h2>
                <button class="modal-close" onclick="closeModal('modal-add-link')"><i data-lucide="x"></i></button>
            </div>
            <form id="form-add-link">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div class="form-group">
                        <label>نام تانل</label>
                        <input type="text" id="link-name" class="form-input" placeholder="Tunnel-Tehran-Frankfurt" required>
                    </div>
                    <div class="form-group">
                        <label>تعداد اتصالات رزرو (Pool Size)</label>
                        <input type="number" id="link-pool-size" class="form-input" value="150" required>
                    </div>
                </div>

                <div class="form-group">
                    <label>پروفایل آماده یا شخصی</label>
                    <select id="link-profile" class="form-input" onchange="applySelectedProfile()">
                        <option value="custom">شخصی / پیشرفته</option>
                    </select>
                </div>

                <div class="form-group">
                    <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="checkbox" id="link-easy-mode" style="width: 18px; height: 18px;" onchange="toggleEasyMode()">
                        Easy Mode برای ساخت سریع تانل
                    </label>
                </div>

                <div class="form-group">
                    <label>تگ‌های تانل</label>
                    <input type="text" id="link-tags" class="form-input" placeholder="video, vip, tehran">
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div class="form-group">
                        <label>انتخاب نود داخلی (Internal Node)</label>
                        <select id="link-iran-node" class="form-input"></select>
                    </div>
                    <div class="form-group">
                        <label>انتخاب نود خارجی (External Node)</label>
                        <select id="link-foreign-node" class="form-input"></select>
                    </div>
                </div>
                <div class="form-group">
                    <div class="flex-between gap-10" style="justify-content:flex-start; flex-wrap:wrap;">
                        <button type="button" class="btn w-auto p-10" onclick="smartTestSelectedNodes()">تست هوشمند و پیشنهاد پروفایل</button>
                        <button type="button" class="btn w-auto p-10" onclick="quickSpaceTunnel()" style="background: linear-gradient(135deg, #10b981, #3b82f6);">بزن بریم فضا !</button>
                        <span id="smart-test-result" class="tag-pill">آماده تست مسیر بین دو نود</span>
                    </div>
                </div>
                <div class="compact-grid advanced-link-field">
                    <div class="form-group">
                        <label>هسته تانل</label>
                        <select id="link-engine" class="form-input" onchange="syncTunnelOptions()">
                            <option value="builtin">Built-in Reverse</option>
                            <option value="gost">GOST</option>
                            <option value="backhaul">Backhaul</option>
                            <option value="rathole">Rathole</option>
                            <option value="chisel">Chisel</option>
                            <option value="frp">FRP</option>
                            <option value="xray">Xray</option>
                            <option value="muxquantum">Mux/Quantum</option>
                            <option value="hysteria2">Hysteria 2 (UDP)</option>
                            <option value="singbox">sing-box</option>
                            <option value="tuic">TUIC</option>
                            <option value="naiveproxy">NaiveProxy</option>
                            <option value="shadowtls">ShadowTLS</option>
                            <option value="brook">Brook</option>
                            <option value="mieru">Mieru</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>ترنسپورت</label>
                        <select id="link-transport" class="form-input" onchange="syncTransportTls()">
                            <option value="tcp">TCP</option>
                            <option value="udp">UDP</option>
                            <option value="ws">WebSocket</option>
                            <option value="wss">WebSocket TLS</option>
                            <option value="wsmux">WSMux</option>
                            <option value="grpc">gRPC</option>
                            <option value="tcpmux">TCPMux</option>
                            <option value="kcp">KCP</option>
                            <option value="quic">QUIC</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>شبکه</label>
                        <select id="link-network" class="form-input" onchange="syncNetworkMode()">
                            <option value="tcp">TCP</option>
                            <option value="udp">UDP</option>
                            <option value="tcp_udp">TCP + UDP</option>
                        </select>
                    </div>
                </div>
                
                <div class="advanced-link-field" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div class="form-group">
                        <label>پورت پل ارتباطی (Bridge Port)</label>
                        <input type="number" id="link-bridge-port" class="form-input" value="7000" required>
                    </div>
                    <div class="form-group">
                        <label>پورت هماهنگ‌سازی (Sync Port)</label>
                        <input type="number" id="link-sync-port" class="form-input" value="7001" required>
                    </div>
                </div>

                <div class="form-group advanced-link-field">
                    <label>روش تانلینگ (Tunnel Mode)</label>
                    <select id="link-tunnel-mode" class="form-input" onchange="syncModeTransport()">
                        <option value="tcp">TCP Tunnel (پیشفرض و خام)</option>
                        <option value="udp">UDP Tunnel</option>
                        <option value="websocket">WebSocket Tunnel (شبیه‌ساز وب)</option>
                        <option value="http_obfs">HTTP Obfuscation (پوشش ترافیک معمولی)</option>
                        <option value="grpc">gRPC Tunnel</option>
                        <option value="tcpmux">TCPMux</option>
                        <option value="wsmux">WSMux</option>
                        <option value="kcp">KCP</option>
                        <option value="quic">QUIC</option>
                        <option value="vless_reality">Xray VLESS Reality</option>
                    </select>
                </div>
                
                <div class="form-group advanced-link-field">
                    <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="checkbox" id="link-tls-enabled" style="width: 18px; height: 18px;" onchange="toggleObfsOptions()">
                        امن‌سازی با پروتکل TLS (Secure Connection)
                    </label>
                </div>
                
                <!-- Advanced Parameters Section -->
                <div id="obfs-advanced-section" class="hidden" style="border-top: 1px solid var(--border-card); padding-top: 15px; margin-top: 15px;">
                    <h4 class="mb-20">تنظیمات پیشرفته مبهم‌سازی (Advanced Obfuscation)</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div class="form-group">
                            <label>آدرس Host هدر (مبهم‌سازی)</label>
                            <input type="text" id="link-obfs-host" class="form-input" value="speedtest.net">
                        </div>
                        <div class="form-group">
                            <label>مسیر درخواست (Path)</label>
                            <input type="text" id="link-obfs-path" class="form-input" value="/tunnel">
                        </div>
                    </div>
                    <div class="form-group" id="tls-sni-group">
                        <label>مقدار SNI در پروتکل TLS</label>
                        <input type="text" id="link-tls-sni" class="form-input" value="speedtest.net">
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
                        <div class="form-group">
                            <label>Padding Min</label>
                            <input type="number" id="link-padding-min" class="form-input" value="0">
                        </div>
                        <div class="form-group">
                            <label>Padding Max</label>
                            <input type="number" id="link-padding-max" class="form-input" value="0">
                        </div>
                        <div class="form-group">
                            <label>Jitter ms</label>
                            <input type="number" id="link-jitter-ms" class="form-input" value="0">
                        </div>
                        <div class="form-group">
                            <label>Keepalive sec</label>
                            <input type="number" id="link-keepalive" class="form-input" value="25">
                        </div>
                    </div>
                    <div id="xray-options" class="hidden">
                        <h4 class="mb-20">تنظیمات Xray (VLESS Reality)</h4>
                        <div class="compact-grid">
                            <input id="link-xray-protocol" class="form-input" value="vless" placeholder="Protocol (vless)">
                            <input id="link-xray-security" class="form-input" value="reality" placeholder="Security (reality)">
                            <input id="link-xray-flow" class="form-input" value="xtls-rprx-vision" placeholder="Flow (xtls-rprx-vision)">
                            <input id="link-xray-uuid" class="form-input" placeholder="UUID (auto if empty)">
                            <input id="link-xray-sni" class="form-input" value="www.microsoft.com" placeholder="SNI / ServerName (e.g. microsoft.com)">
                            <input id="link-xray-shortid" class="form-input" placeholder="ShortId (auto if empty)">
                            <input id="link-xray-public-key" class="form-input" placeholder="Public Key (auto if empty)">
                            <input id="link-xray-private-key" class="form-input" placeholder="Private Key (auto if empty)">
                        </div>
                    </div>
                </div>
                
                <button type="submit" id="link-submit-button" class="btn mt-20">ایجاد تانل</button>
            </form>
        </div>
    </div>

    <div id="modal-sync-xui" class="modal">
        <div class="modal-content" style="max-width: 500px;">
            <div class="modal-header">
                <h2>همگام‌سازی از X-UI</h2>
                <button class="modal-close" onclick="closeModal('modal-sync-xui')"><i data-lucide="x"></i></button>
            </div>
            <form id="form-sync-xui">
                <input type="hidden" id="sync-xui-link-id">
                <div class="form-group">
                    <label>آدرس پنل (مثال: http://192.168.1.10:2053)</label>
                    <input type="url" id="sync-xui-url" class="form-input" required>
                </div>
                <div class="compact-grid">
                    <div class="form-group">
                        <label>نام کاربری</label>
                        <input type="text" id="sync-xui-username" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label>رمز عبور</label>
                        <input type="password" id="sync-xui-password" class="form-input" required>
                    </div>
                </div>
                <button type="submit" class="btn mt-20">شروع همگام‌سازی پورت‌ها</button>
            </form>
        </div>
    </div>
    <script>
        let token = localStorage.getItem('token');
        let currentTab = 'dashboard';
        let charts = {};
        let categoryCharts = {};
        let nodeResourceCharts = {};
        let lastLinksSignature = '';
        let lastProfilesSignature = '';
        let autoRefreshTimer = null;
        let autoRefreshInFlight = false;
        const COLOR_ACTIVE = '#10b981';
        const COLOR_DOWNLOAD = '#3b82f6';
        const COLOR_UPLOAD = '#7c5cff';
        let linkCategoryOpenStates = {};
        try {
            linkCategoryOpenStates = JSON.parse(localStorage.getItem('p00rija_link_category_open') || '{}') || {};
        } catch (err) {
            linkCategoryOpenStates = {};
        }
        let statusInterval = null;
        let latestStatus = {};
        let currentLang = localStorage.getItem('p00rija_lang') || 'fa';
        let currentTheme = localStorage.getItem('p00rija_theme') || 'dark';
        let currentFont = localStorage.getItem('p00rija_font') || 'vazirmatn';
        let sshTerminalSessionId = null;
        let sshTerminalPoller = null;

        const translations = {
            dashboard: { fa: 'داشبورد', en: 'Dashboard' },
            nodes: { fa: 'مدیریت سرورها', en: 'Nodes' },
            links: { fa: 'مدیریت تانل‌ها', en: 'Tunnels' },
            logs: { fa: 'لاگ‌های سیستم', en: 'Logs' },
            settings: { fa: 'تنظیمات', en: 'Settings' },
            monitor: { fa: 'مانیتورینگ', en: 'Monitor' },
            appearance: { fa: 'ظاهر و زبان', en: 'Appearance' },
            help: { fa: 'راهنما', en: 'Help' },
            about: { fa: 'درباره من', en: 'About' },
            online: { fa: 'آنلاین', en: 'Online' },
            offline: { fa: 'آفلاین', en: 'Offline' },
            connected: { fa: 'برقرار', en: 'Connected' },
            disconnected: { fa: 'قطع', en: 'Disconnected' },
            internal: { fa: 'داخلی', en: 'Internal' },
            external: { fa: 'خارجی', en: 'External' },
            delete: { fa: 'حذف', en: 'Delete' },
            close: { fa: 'قطع', en: 'Close' }
        };

        function t(key) {
            return translations[key]?.[currentLang] || key;
        }

        function tx(fa, en) {
            return currentLang === 'en' ? en : fa;
        }

        function applyPreferences() {
            document.body.classList.remove('theme-light', 'theme-cyberpunk', 'theme-forest', 'theme-ocean', 'font-vazirmatn', 'font-sahel', 'font-shabnam', 'font-inter', 'font-system', 'font-byekan');
            if (currentTheme !== 'dark') document.body.classList.add(`theme-${currentTheme}`);
            document.body.classList.add(`font-${currentFont}`);
            document.documentElement.lang = currentLang;
            document.documentElement.dir = currentLang === 'fa' ? 'rtl' : 'ltr';
            document.title = tx('پنل مدیریت P00RIJA TUNNEL', 'P00RIJA TUNNEL Management Panel');
            ['language-select', 'appearance-language', 'login-language-select'].forEach(id => { const el = document.getElementById(id); if (el) el.value = currentLang; });
            ['theme-select', 'appearance-theme', 'login-theme-select'].forEach(id => { const el = document.getElementById(id); if (el) el.value = currentTheme; });
            ['font-select', 'appearance-font'].forEach(id => { const el = document.getElementById(id); if (el) el.value = currentFont; });
            applyStaticTranslations();
            applyAttributeTranslations();
        }

        const staticEnglish = {
            'پنل مدیریت P00RIJA TUNNEL': 'P00RIJA TUNNEL Management Panel',
            'فارسی': 'Persian',
            'تیره': 'Dark',
            'روشن': 'Light',
            'سایبرپانک': 'Cyberpunk',
            'جنگل': 'Forest',
            'اقیانوس': 'Ocean',
            'سیستم': 'System',
            'منو': 'Menu',
            'رفرش: خاموش': 'Refresh: Off',
            'رفرش: 1s': 'Refresh: 1s',
            'رفرش: 3s': 'Refresh: 3s',
            'رفرش: 5s': 'Refresh: 5s',
            'رفرش: 10s': 'Refresh: 10s',
            'رفرش: 30s': 'Refresh: 30s',
            'رفرش: 60s': 'Refresh: 60s',
            'نام کاربری': 'Username',
            'کلمه عبور': 'Password',
            'کد دو مرحله‌ای (اختیاری)': 'Two-factor code (optional)',
            'ورود به پنل': 'Sign in',
            'داشبورد': 'Dashboard',
            'مدیریت سرورها': 'Nodes',
            'مدیریت تانل‌ها': 'Tunnels',
            'لاگ‌های سیستم': 'Logs',
            'مانیتورینگ': 'Monitor',
            'ظاهر و زبان': 'Appearance',
            'تنظیمات': 'Settings',
            'راهنما': 'Help',
            'درباره من': 'About',
            'خروج': 'Logout',
            'کل سرورها': 'Total nodes',
            'تانل‌های فعال': 'Active tunnels',
            'ترافیک شبکه (Rx/Tx)': 'Network traffic (Rx/Tx)',
            'تردهای فعال': 'Active threads',
            'وضعیت سیستم میزبان پنل': 'Panel host system status',
            'ترافیک عبوری شبکه (Live)': 'Live network traffic',
            'اتصالات فعال تانل': 'Active tunnel connections',
            'P00RIJA PANEL فعال است': 'P00RIJA PANEL is active',
            'لیست نودها': 'Node list',
            'افزودن خودکار نودهای نمونه': 'Auto add starter nodes',
            'افزودن نود جدید': 'Add node',
            'ویرایش نود': 'Edit node',
            'ذخیره تغییرات': 'Save changes',
            'نام سرور': 'Server name',
            'نقش': 'Role',
            'آدرس IP': 'IP address',
            'وضعیت': 'Status',
            'منابع سرور': 'Server resources',
            'ترافیک': 'Traffic',
            'تردها/کانکشن': 'Threads/connections',
            'عملیات': 'Actions',
            'لیست تانل‌ها (لینک‌ها)': 'Tunnel links',
            'افزودن تانل جدید': 'Add tunnel',
            'خروجی CSV': 'Export CSV',
            'زمان ثبت': 'Time',
            'منبع': 'Source',
            'سطح لاگ': 'Log level',
            'شرح لاگ': 'Log message',
            'مانیتورینگ سشن‌ها، تردها و پروسس‌ها': 'Sessions, threads and process monitoring',
            'بروزرسانی': 'Refresh',
            'سشن‌های فعال تانل': 'Active tunnel sessions',
            'پروسس‌های سیستم': 'System processes',
            'مدیریت منابع سرور': 'Server resource management',
            'پاک‌سازی سشن‌های Idle': 'Clean idle sessions',
            'پاک‌سازی RAM/GC': 'Clean RAM/GC',
            'بهینه‌سازی کامل منابع': 'Full resource optimization',
            'ظاهر، فونت و زبان': 'Appearance, font and language',
            'زبان پنل': 'Panel language',
            'تم رنگی': 'Theme',
            'فونت': 'Font',
            'پروفایل‌های تانل': 'Tunnel profiles',
            'آماده + شخصی': 'Preset + Custom',
            'ورود پروفایل‌ها': 'Import profiles',
            'Profile name': 'Profile name',
            'ترنسپورت': 'Transport',
            'شبکه': 'Network',
            'رمز عبور': 'Password',
            'کلید خصوصی': 'Private key',
            'دستور': 'Command',
            'هاست / IP': 'Host / IP',
            'پورت': 'Port',
            'PID': 'PID',
            'هسته‌های CPU': 'CPU cores',
            'RAM (آزاد / کل)': 'RAM (Free / Total)',
            'Swap (آزاد / کل)': 'Swap (Free / Total)',
            'دیسک (آزاد / کل)': 'Disk (Free / Total)',
            'بار سیستم / آپ‌تایم': 'Load / Uptime',
            'پروسس پنل': 'Panel process',
            'نام': 'Name',
            'RSS': 'RSS',
            'تردها': 'Threads',
            'سشن‌ها': 'Sessions',
            'زمان CPU': 'CPU time',
            'CPU Cores': 'CPU cores',
            'RAM (Free / Total)': 'RAM (Free / Total)',
            'Swap (Free / Total)': 'Swap (Free / Total)',
            'Disk (Free / Total)': 'Disk (Free / Total)',
            'Load / Uptime': 'Load / Uptime',
            'Panel Process': 'Panel process',
            'Docker وضعیت': 'Docker status',
            'ذخیره پروفایل': 'Save profile',
            'خروجی پروفایل‌ها': 'Export profiles',
            'تنظیمات پنل': 'Panel settings',
            'تغییر مشخصات مدیریت': 'Admin credentials',
            'کلمه عبور جدید': 'New password',
            'بروزرسانی مشخصات ورود': 'Update login',
            'امنیت ورود': 'Login security',
            'فعال‌سازی ورود دو مرحله‌ای TOTP': 'Enable TOTP two-factor login',
            'فعال‌سازی بایومتریک مرورگر برای Quick Unlock': 'Enable browser biometric quick unlock',
            'ثبت تنظیمات امنیتی': 'Save security settings',
            'تنظیمات SSL/TLS وب پنل (HTTPS)': 'Panel SSL/TLS settings (HTTPS)',
            'فعال‌سازی HTTPS برای وب پنل': 'Enable HTTPS for panel',
            'ثبت تنظیمات SSL': 'Save SSL settings',
            "دریافت Certificate خودکار Let's Encrypt": "Automatic Let's Encrypt certificate",
            'مسیر Certificate (.pem)': 'Certificate path (.pem)',
            'مسیر Private Key (.pem)': 'Private key path (.pem)',
            'آدرس دامنه (مثال: panel.yourdomain.com)': 'Domain name (example: panel.yourdomain.com)',
            "ایمیل (جهت ثبت‌نام در Let's Encrypt)": "Email (for Let's Encrypt registration)",
            'دریافت و نصب گواهینامه SSL': 'Get and install SSL certificate',
            'اعمال تغییرات و ریستارت وب پنل': 'Apply changes and restart panel',
            '۱. در بخش مدیریت سرورها، نود داخلی و نود خارجی را ثبت کنید و توکن هر نود را در همان سرور وارد کنید.': '1. In Nodes, register an internal node and an external node, then enter each node token on that server.',
            '۲. در مدیریت تانل‌ها، یک پروفایل Easy/Hard/Resilient یا پروفایل شخصی انتخاب کنید، سپس Bridge/Sync port را بسازید.': '2. In Tunnels, choose an Easy/Hard/Resilient or custom profile, then create the Bridge/Sync ports.',
            '۳. در هر تانل، port forwarding اضافه کنید تا ورودی نود داخلی به سرویس مقصد روی نود خارجی وصل شود.': '3. Add port forwarding on each tunnel so internal-node input reaches the destination service on the external node.',
            '۴. در Monitor می‌توانید sessionهای تانل و پروسس‌های سیستم را ببینید و در صورت نیاز session یا process را قطع کنید.': '4. In Monitor, review tunnel sessions and system processes, then close a session or process when needed.',
            '۵. از Appearance می‌توانید زبان، تم، فونت و profile bundle را مدیریت کنید. PWA هم از همین پنل قابل install شدن است.': '5. In Appearance, manage language, theme, font, and profile bundles. The PWA can also be installed from the same panel.',
            '۶. نام کاربری و رمز پیش‌فرض دیتابیس تازه admin/admin است؛ در نصب wizard رمز جدید بگذارید و بعد از ورود آن را تغییر دهید.': '6. A fresh database defaults to admin/admin. Set a new password in the setup wizard and change it after login.',
            'P00RIJA TUNNEL یک پنل مدیریت تانل معکوس چندنودی برای اتصال پایدار نودهای داخلی و خارجی با پروفایل‌های قابل تنظیم، مانیتورینگ runtime و داشبورد دو زبانه است.': 'P00RIJA TUNNEL is a multi-node reverse tunnel control panel for stable internal/external node connectivity with configurable profiles, runtime monitoring, and a bilingual dashboard.',
            'توکن امنیتی نود ایجاد شده': 'Generated node security token',
            'این توکن فقط یکبار نمایش داده می‌شود. لطفاً آن را ذخیره کنید تا در راه‌اندازی کلاینت استفاده کنید.': 'This token is shown only once. Save it for node setup.',
            'توکن و کلید خصوصی را هر دو در نصب نود وارد کنید. این اطلاعات حساس می‌باشد، در حفظ و افشا نشدن آنها دقت کنید.': 'Enter both the token and private key during node installation. This information is sensitive; keep it protected and do not disclose it.',
            'تایید و بستن': 'Confirm and close',
            'ایجاد تانل': 'Create tunnel',
            'افزودن نود جدید': 'Add node',
            'نام نود (مثال: INTERNAL-Node-1)': 'Node name (example: INTERNAL-Node-1)',
            'نقش نود': 'Node role',
            'نود داخلی (Internal Node)': 'Internal node',
            'نود خارجی (External Node)': 'External node',
            'آدرس IP سرور': 'Server IP address',
            'ثبت نود جدید': 'Save node',
            'ویرایش نود': 'Edit node',
            'ذخیره تغییرات': 'Save changes',
            'ایجاد تانل (لینک) جدید': 'Create new tunnel link',
            'نام تانل': 'Tunnel name',
            'تعداد اتصالات رزرو (Pool Size)': 'Reserved connections (Pool Size)',
            'پروفایل آماده یا شخصی': 'Preset or custom profile',
            'انتخاب نود داخلی (Internal Node)': 'Select internal node',
            'انتخاب نود خارجی (External Node)': 'Select external node',
            'هسته تانل': 'Tunnel engine',
            'پورت پل ارتباطی (Bridge Port)': 'Bridge port',
            'پورت هماهنگ‌سازی (Sync Port)': 'Sync port',
            'روش تانلینگ (Tunnel Mode)': 'Tunnel mode',
            'TCP Tunnel (پیشفرض و خام)': 'TCP Tunnel (default raw mode)',
            'WebSocket Tunnel (شبیه‌ساز وب)': 'WebSocket Tunnel (web-like traffic)',
            'HTTP Obfuscation (پوشش ترافیک معمولی)': 'HTTP Obfuscation (normal traffic cover)',
            'امن‌سازی با پروتکل TLS (Secure Connection)': 'Secure with TLS protocol',
            'تنظیمات پیشرفته مبهم‌سازی (Advanced Obfuscation)': 'Advanced obfuscation settings',
            'آدرس Host هدر (مبهم‌سازی)': 'Header host address (obfuscation)',
            'مسیر درخواست (Path)': 'Request path',
            'مقدار SNI در پروتکل TLS': 'TLS SNI value',
            'تنظیمات Xray': 'Xray settings',
            'اتصال و کنترل SSH نود': 'Node SSH connection and control',
            'نود': 'Node',
            'روش احراز هویت': 'Authentication method',
            'Timeout ثانیه': 'Timeout seconds',
            'ذخیره رمزنگاری‌شده مشخصات اتصال برای این نود': 'Save encrypted connection details for this node',
            'اتصال و اجرا': 'Connect and run',
            'فقط ذخیره مشخصات': 'Save credentials only',
            'آماده اتصال': 'Ready to connect',
            'تگ‌های نود': 'Node tags',
            'تگ‌های تانل': 'Tunnel tags',
            'Easy Mode برای ساخت سریع تانل': 'Easy Mode for fast tunnel creation',
            'تست هوشمند و پیشنهاد پروفایل': 'Smart test and profile recommendation',
            'بزن بریم فضا !': 'Launch quick tunnel!',
            'آماده تست مسیر بین دو نود': 'Ready to test the path between two nodes',
            'کانفیگ موتور تانلینگ (Engine Config)': 'Tunneling engine config',
            'بستن': 'Close',
            'تست ارتباط سرور': 'Server connection test',
            'در حال تست ارتباط، چند لحظه صبر کنید...': 'Testing connection, please wait...',
            'مدیریت هسته‌ها (Engine Management)': 'Engine management',
            'هسته‌ها از پوشه آفلاین engines داخل image استفاده می‌کنند. نصب از GitHub فقط وقتی لازم است که اینترنت در دسترس باشد.': 'Engines are loaded from the offline engines folder inside the image. GitHub install is only needed when internet access is available.',
            'تنظیمات نمایش': 'Display settings',
            'تنظیمات شبکه': 'Network settings',
            'تنظیمات شبکه و هسته‌ها': 'Network and engine settings',
            'غیرفعال سازی IPv6 روی سیستم عامل': 'Disable IPv6 on the operating system',
            'زمان اعمال و ریست مجدد هسته (به دقیقه، 0 برای غیرفعال کردن)': 'Engine scheduled restart interval (minutes, 0 to disable)',
            'برای پایداری بیشتر، هسته‌ها می‌توانند به صورت زمان‌بندی شده ریست شوند تا حافظه و منابع آزاد شود.': 'For better stability, engines can be restarted on a schedule to release memory and resources.',
            'ثبت تنظیمات شبکه': 'Save network settings',
            'Runtime پنل': 'Panel runtime',
            'منابع نودها': 'Node resources',
            'پروسس‌های سیستم': 'System processes',
            'شناسه': 'ID',
            'تانل': 'Tunnel',
            'مقصد': 'Target',
            'پورت مقصد': 'Target port',
            'عمر': 'Age',
            'بیکاری': 'Idle',
            'نام': 'Name',
            'زمان CPU': 'CPU time',
            'بهینه‌سازی انجام شد': 'Optimization completed',
            'سشن‌های بسته‌شده': 'closed sessions',
            'فرمان نودها': 'node commands',
            'نودی برای نمایش نیست': 'No nodes to show',
            'نسخه:': 'Version:',
            'لایسنس:': 'License:',
            'گیت‌هاب: github.com/Poorija': 'GitHub: github.com/Poorija',
            'شخصی / پیشرفته': 'Custom / Advanced',
            'پاک‌سازی ثبت نشده': 'No cleanup yet',
            'آخرین پاک‌سازی': 'Last cleanup',
            'روی نود': 'On node',
            'این سشن تانل بسته شود؟': 'Close this tunnel session?',
            'JSON پروفایل نامعتبر است.': 'Invalid profile JSON.',
            'پروفایل ذخیره شد.': 'Profile saved.',
            'پروفایل‌ها وارد شدند.': 'Profiles imported.',
            'آپدیت از گیت‌هاب': 'GitHub update',
            'آپدیت دستی از فایل': 'Manual file update',
            'انتخاب فایل': 'Choose file',
            'توقف': 'Stop',
            'ادامه': 'Resume',
            'ریست': 'Restart',
            'آماده': 'Ready',
            'غیرفعال': 'Disabled',
            'نصب نشده': 'Missing',
            'درباره من': 'About me',
            'راهنمای سریع داشبورد': 'Quick dashboard guide',
            '۱. در مدیریت سرورها، ابتدا نودهای داخلی و خارجی را ثبت کنید. اگر یک سرور هم پنل است و هم نود داخلی، همان سرور را به عنوان Internal Node هم اضافه کنید تا در ساخت تانل قابل انتخاب باشد.': '1. In Nodes, register internal and external nodes first. If one server is both the panel and an internal node, add that same server as an Internal Node too so it can be selected when creating tunnels.',
            '۲. در مدیریت تانل‌ها، از پروفایل‌های آماده برای شروع سریع استفاده کنید. بعد از انتخاب پروفایل، Engine، Transport، Network، TLS، SNI، Path و Pool همچنان قابل تغییر هستند.': '2. In Tunnels, use preset profiles for a fast start. After choosing a profile, Engine, Transport, Network, TLS, SNI, Path, and Pool remain editable.',
            '۳. برای هر تانل Bridge Port و Sync Port روی نود داخلی باید آزاد و یکتا باشد. اگر پورت تکراری باشد، پنل قبل از ذخیره خطا می‌دهد.': '3. Each tunnel needs unique free Bridge and Sync ports on the internal node. The panel rejects duplicate ports before saving.',
            '۴. بعد از ساخت تانل، Port Forwarding را اضافه کنید. User/Internal Port همان پورتی است که روی نود داخلی باز می‌شود و Target Port به سرویس سمت نود خارجی اشاره می‌کند.': '4. After creating a tunnel, add port forwarding. User/Internal Port is opened on the internal node, and Target Port points to the service on the external node.',
            '۵. دکمه توقف تانل، تانل را از کانفیگ نودها خارج می‌کند و با ادامه دوباره به نودها تحویل داده می‌شود. برای اعمال عملی، چند ثانیه تا polling بعدی نود صبر کنید.': '5. Pause removes the tunnel from node configs; Resume sends it back to the nodes. Wait a few seconds for the next node polling cycle to apply it.',
            '۶. اگر TLS تانل فعال است، SNI و Host را هماهنگ انتخاب کنید. برای وب پنل، تنظیمات HTTPS در Settings فقط با مسیر Certificate و Key معتبر و ریستارت پنل کامل اعمال می‌شود.': '6. If tunnel TLS is enabled, keep SNI and Host aligned. For the web panel, HTTPS settings fully apply only with valid Certificate/Key paths and a panel restart.',
            '۷. نمودارهای Dashboard و وضعیت منابع/ترافیک مدیریت سرورها با Refresh Time بالای صفحه به صورت زنده به‌روزرسانی می‌شوند. برای تست فوری، مقدار ۳ ثانیه را انتخاب کنید.': '7. Dashboard charts and node resource/traffic status refresh live according to the Refresh Time at the top. Choose 3 seconds for quick testing.',
            '۸. در Monitor می‌توانید sessionهای فعال، مصرف RSS و تعداد threadها را ببینید و پاک‌سازی idle یا GC را اجرا کنید.': '8. In Monitor, review active sessions, RSS usage, and thread counts, then run idle cleanup or GC.',
            '۹. نام کاربری و رمز پیش‌فرض دیتابیس تازه admin/admin است؛ در نصب wizard رمز جدید بگذارید و بعد از ورود آن را تغییر دهید.': '9. A fresh database defaults to admin/admin. Set a new password in the setup wizard and change it after first login.',
            'P00RIJA TUNNEL برای مدیریت متمرکز تانل‌های معکوس در سناریوهای چندنودی ساخته شده است؛ جایی که پنل باید هم وضعیت سرورها را زنده ببیند، هم پروفایل‌های مختلف تانلینگ را کنترل کند، و هم امکان توقف، ادامه، و ویرایش عملیاتی تانل‌ها را بدون دستکاری دستی کانفیگ‌ها بدهد.': 'P00RIJA TUNNEL is built for centralized reverse-tunnel management in multi-node scenarios where the panel must watch server status live, control multiple tunneling profiles, and provide operational pause, resume, and editing without manual config edits.',
            'تمرکز پروژه': 'Project focus',
            'پایداری ارتباط، انتخاب هوشمند پروفایل، مانیتورینگ منابع، و مدیریت امن نودها با توکن و امضای درخواست.': 'Connection stability, smart profile selection, resource monitoring, and secure node management with tokens and signed requests.',
            'برای چه سناریویی؟': 'Designed for',
            'پنل مرکزی، نودهای داخلی، نودهای خارجی، شبکه‌های جدا، و تانل‌هایی که باید زیر بار واقعی قابل مشاهده و قابل کنترل باشند.': 'A central panel, internal nodes, external nodes, separate networks, and tunnels that must remain observable and controllable under real load.',
            'فونت‌ها به صورت stack داخلی تعریف شده‌اند و اگر فونت روی سیستم کاربر نصب باشد استفاده می‌شود؛ در غیر این صورت پنل به فونت امن سیستم برمی‌گردد.': 'Fonts are defined as local stacks. If a font exists on the user system it is used; otherwise the panel falls back to a safe system font.'
        };
        const originalTextNodes = new WeakMap();

        const attributeEnglish = {
            'node-name': 'INTERNAL-Node-1',
            'profile-import': 'Paste exported profiles JSON',
            'profile-name': 'Profile name',
            'profile-host': 'Host / SNI',
            'profile-path': 'Path',
            'ssh-host': 'Host or IP address',
            'ssh-command': 'uname -a && uptime && free -h',
            'link-name': 'Tunnel-Tehran-Frankfurt',
            'link-tags': 'video, vip, tehran'
        };

        function applyStaticTranslations() {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            const nodes = [];
            while (walker.nextNode()) nodes.push(walker.currentNode);
            nodes.forEach(node => {
                if (!originalTextNodes.has(node)) originalTextNodes.set(node, node.nodeValue);
                const original = originalTextNodes.get(node);
                const raw = original.trim();
                if (!raw) return;
                if (currentLang === 'en' && staticEnglish[raw]) node.nodeValue = original.replace(raw, staticEnglish[raw]);
                if (currentLang === 'fa') node.nodeValue = original;
            });
        }

        function applyAttributeTranslations() {
            Object.keys(attributeEnglish).forEach(id => {
                const el = document.getElementById(id);
                if (!el) return;
                if (!el.dataset.faPlaceholder) el.dataset.faPlaceholder = el.getAttribute('placeholder') || '';
                el.setAttribute('placeholder', currentLang === 'en' ? attributeEnglish[id] : el.dataset.faPlaceholder);
            });
        }

        function setLanguage(lang) {
            currentLang = lang;
            localStorage.setItem('p00rija_lang', lang);
            applyPreferences();
            switchTab(currentTab, true);
            if (latestStatus.nodes) {
                updateDashboard(latestStatus);
                renderCurrentTab(latestStatus);
            }
        }

        function setTheme(theme) {
            currentTheme = theme;
            localStorage.setItem('p00rija_theme', theme);
            applyPreferences();
        }

        function setFont(font) {
            currentFont = font;
            localStorage.setItem('p00rija_font', font);
            applyPreferences();
        }

        async function fetchSettings() {
            if (!token) return;
            try {
                const res = await fetch('/api/status', {
                    headers: { 'Authorization': `Bearer ${token}` },
                    cache: 'no-store'
                });
                if (!res.ok) return;
                latestStatus = await res.json();
                updateLoginSecurity(latestStatus);
            } catch (err) {
                console.warn('Settings bootstrap skipped:', err);
            }
        }

        function applyTheme() {
            applyPreferences();
        }

        function createInlineIcons(root = document) {
            const icons = {
                gauge: 'M4 13a8 8 0 0 1 16 0 M12 13l4-4',
                server: 'M4 6h16v5H4z M4 13h16v5H4z',
                split: 'M6 4v5a3 3 0 0 0 3 3h6 M15 7l3-3 3 3 M15 17l3 3 3-3',
                terminal: 'M4 6l5 5-5 5 M11 18h9',
                settings: 'M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8z M4 12h3 M17 12h3 M12 4v3 M12 17v3',
                'log-out': 'M5 4h8v4 M13 16v4H5V4 M12 12h9 M18 9l3 3-3 3',
                activity: 'M4 13h4l3-7 4 12 3-5h2',
                cpu: 'M8 8h8v8H8z M4 9h3 M4 15h3 M17 9h3 M17 15h3 M9 4v3 M15 4v3 M9 17v3 M15 17v3',
                x: 'M6 6l12 12 M18 6L6 18',
                'git-commit': 'M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8z M2 12h6 M16 12h6',
                'arrow-right': 'M5 12h14 M13 6l6 6-6 6',
                palette: 'M12 4a8 8 0 0 0 0 16h1.5a2 2 0 0 0 1.7-3h1.3A5.5 5.5 0 0 0 12 4z M7 10h.01 M10 7h.01 M14 7h.01 M17 10h.01',
                'book-open': 'M4 5h6a4 4 0 0 1 4 4v11a4 4 0 0 0-4-4H4z M20 5h-6a4 4 0 0 0-4 4v11a4 4 0 0 1 4-4h6z',
                info: 'M12 8h.01 M11 12h1v5h1 M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
                menu: 'M4 6h16 M4 12h16 M4 18h16'
            };
            root.querySelectorAll('i[data-lucide]').forEach(el => {
                const name = el.getAttribute('data-lucide');
                const pathData = icons[name] || icons.activity;
                const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
                svg.setAttribute("viewBox", "0 0 24 24");
                svg.setAttribute("width", "20");
                svg.setAttribute("height", "20");
                svg.setAttribute("fill", "none");
                svg.setAttribute("stroke", "currentColor");
                svg.setAttribute("stroke-width", "2");
                svg.setAttribute("stroke-linecap", "round");
                svg.setAttribute("stroke-linejoin", "round");
                svg.setAttribute("aria-hidden", "true");
                const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
                path.setAttribute("d", pathData);
                svg.appendChild(path);
                while (el.firstChild) {
                    el.removeChild(el.firstChild);
                }
                el.appendChild(svg);
            });
        }

        function esc(value) {
            return String(value ?? '').replace(/[&<>"']/g, ch => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            }[ch]));
        }

        function cssEscape(value) {
            if (window.CSS && CSS.escape) return CSS.escape(String(value));
            return String(value).replace(/["\\\\]/g, '\\\\$&');
        }

        function formatBytes(value) {
            const bytes = Number(value || 0);
            if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
            if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
            if (bytes >= 1024) return `${(bytes / 1024).toFixed(2)} KB`;
            return `${bytes} B`;
        }

        function safeDomId(value) {
            return String(value || 'node').replace(/[^a-zA-Z0-9_-]/g, '_');
        }

        function parseTags(value) {
            if (Array.isArray(value)) return value.map(v => String(v).trim()).filter(Boolean).slice(0, 8);
            return String(value || '').replace(/،/g, ',').split(',').map(v => v.trim()).filter(Boolean).slice(0, 8);
        }

        function renderTags(tags = []) {
            return parseTags(tags).map((tag, idx) => `<span class="tag-pill tag-color-${idx % 6}">${esc(tag)}</span>`).join('');
        }

        applyPreferences();
        createInlineIcons();
        fetchPublicSettings();

        if (token) {
            showPanel();
        }

        async function fetchPublicSettings() {
            try {
                const res = await fetch('/api/public-settings');
                if (!res.ok) return;
                updateLoginSecurity(await res.json());
            } catch (err) {
                updateLoginSecurity({ two_factor_enabled: false });
            }
        }

        function updateLoginSecurity(settings) {
            const group = document.getElementById('otp-group');
            const otp = document.getElementById('otp');
            const enabled = !!settings.two_factor_enabled;
            if (group) group.classList.toggle('hidden', !enabled);
            if (otp) {
                otp.required = enabled;
                if (!enabled) otp.value = '';
            }
        }

        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;
            const otp = document.getElementById('otp').value;
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: u, password: p, otp })
                });
                if (res.ok) {
                    const data = await res.json();
                    token = data.token;
                    localStorage.setItem('token', token);
                    await maybeRegisterBiometric();
                    showPanel();
                } else {
                    alert(tx('نام کاربری یا کلمه عبور نادرست است.', 'Username or password is incorrect.'));
                }
            } catch (err) {
                console.error("Login flow error:", err);
                alert(tx('خطا در پردازش ورود (کنسول مرورگر را بررسی کنید).', 'Error processing login (check browser console).'));
            }
        });

        async function maybeRegisterBiometric() {
            if (typeof latestStatus === 'undefined' || !latestStatus || !latestStatus.biometric_enabled || !window.PublicKeyCredential) return;
            if (localStorage.getItem('p00rija_bio_registered') === '1') return;
            try {
                await navigator.credentials.create({
                    publicKey: {
                        challenge: crypto.getRandomValues(new Uint8Array(32)),
                        rp: { name: 'P00RIJA TUNNEL' },
                        user: { id: crypto.getRandomValues(new Uint8Array(16)), name: 'admin', displayName: 'P00RIJA Admin' },
                        pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
                        authenticatorSelection: { authenticatorAttachment: 'platform', userVerification: 'preferred' },
                        timeout: 30000
                    }
                });
                localStorage.setItem('p00rija_bio_registered', '1');
            } catch (err) {
                console.warn('Biometric registration skipped:', err);
            }
        }

        async function fetchXrayVersions() {
            if (!document.getElementById('setting-xray-version')) return;
            try {
                let data = null;
                const cached = localStorage.getItem('xray_versions_cache');
                const cachedTime = localStorage.getItem('xray_versions_time');
                if (cached && cachedTime && (Date.now() - parseInt(cachedTime)) < 3600000) {
                    data = JSON.parse(cached);
                } else {
                    const res = await fetch('https://api.github.com/repos/XTLS/Xray-core/releases');
                    if (res.ok) {
                        data = await res.json();
                        localStorage.setItem('xray_versions_cache', JSON.stringify(data));
                        localStorage.setItem('xray_versions_time', Date.now().toString());
                    } else {
                        throw new Error('Rate limited');
                    }
                }
                populateXrayVersions(data);
                document.getElementById('xray-version-status').innerText = 'نسخه‌ها با موفقیت دریافت شدند.';
            } catch (err) {
                console.warn('Github fetch failed, using fallback.', err);
                const fallback = [
                    { tag_name: 'v1.8.24', prerelease: false, draft: false },
                    { tag_name: 'v1.8.23', prerelease: false, draft: false },
                    { tag_name: 'v1.8.1', prerelease: false, draft: false },
                    { tag_name: 'v1.8.0', prerelease: false, draft: false },
                    { tag_name: 'v1.7.5', prerelease: false, draft: false }
                ];
                populateXrayVersions(fallback);
                document.getElementById('xray-version-status').innerText = 'استفاده از لیست پشتیبان (محدودیت گیت‌هاب).';
            }
        }
        function populateXrayVersions(data) {
            const sel = document.getElementById('setting-xray-version');
            if (!sel) return;
            sel.innerHTML = '<option value="latest">آخرین نسخه (latest)</option>';
            let added = 0;
            for (const release of data) {
                if (release.prerelease || release.draft) continue;
                const opt = document.createElement('option');
                opt.value = release.tag_name;
                opt.innerText = release.tag_name;
                sel.appendChild(opt);
                added++;
                if (added >= 5) break;
            }
        }

        function showPanel() {
            document.getElementById('login-screen').classList.add('hidden');
            document.getElementById('main-sidebar').classList.remove('hidden');
            document.getElementById('main-workspace').classList.remove('hidden');
            try { initCharts(); } catch(e) { console.error('initCharts error:', e); }
            try { startPolling(); } catch(e) { console.error('startPolling error:', e); }
            try { switchTab('dashboard', true); } catch(e) { console.error('switchTab error:', e); }
            try { fetchStatus(); } catch(e) { console.error('fetchStatus error:', e); }
        }

        function toggleMobileMenu() {
            document.body.classList.toggle('menu-open');
        }

        function logout(reload = false) {
            token = null;
            localStorage.removeItem('token');
            if (autoRefreshTimer) {
                clearInterval(autoRefreshTimer);
                autoRefreshTimer = null;
            }
            document.getElementById('main-sidebar').classList.add('hidden');
            document.getElementById('main-workspace').classList.add('hidden');
            document.getElementById('login-screen').classList.remove('hidden');
            if (reload) location.reload();
        }

        function startPolling() {
            document.getElementById("auto-refresh-select").value = "3";
            setAutoRefresh();
        }

        function switchTab(tabId, skipFetch = false) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

            document.getElementById(`tab-${tabId}`).classList.remove('hidden');
            const navItems = Array.from(document.querySelectorAll('.nav-item'));
            const activeNav = navItems.find(el => el.getAttribute('onclick') && el.getAttribute('onclick').includes(`'${tabId}'`));
            if (activeNav) activeNav.classList.add('active');
            currentTab = tabId;

            const titles = {
                dashboard: t('dashboard'),
                nodes: t('nodes'),
                links: t('links'),
                logs: t('logs'),
                monitor: t('monitor'),
                appearance: t('appearance'),
                settings: t('settings'),
                help: t('help'),
                about: t('about')
            };
            document.getElementById('tab-title').innerText = titles[tabId];
            if (tabId === 'monitor') fetchRuntime();
            if (tabId === 'settings' && latestStatus) {
                document.getElementById('setting-username').value = latestStatus.admin_username || 'admin';
                document.getElementById('setting-traffic-unit').value = localStorage.getItem('trafficUnit') || 'MB';
                document.getElementById('setting-panel-tls').checked = latestStatus.panel_tls || false;
                document.getElementById('setting-cert-path').value = latestStatus.cert_path || '';
                document.getElementById('setting-key-path').value = latestStatus.key_path || '';
                document.getElementById('setting-two-factor').checked = latestStatus.two_factor_enabled || false;
                document.getElementById('setting-biometric').checked = latestStatus.biometric_enabled || false;
                const disableIpv6El = document.getElementById('setting-disable-ipv6');
                if (disableIpv6El) disableIpv6El.checked = latestStatus.disable_ipv6 || false;
                const engineRestartIntervalEl = document.getElementById('setting-engine-restart-interval');
                if (engineRestartIntervalEl) engineRestartIntervalEl.value = latestStatus.engine_restart_interval || 0;
            }
            if (!skipFetch) fetchStatus();
            if (window.innerWidth <= 900) document.body.classList.remove('menu-open');
        }

        function initCharts() {
            if (charts.traffic) return;
            charts.traffic = { canvas: document.getElementById('chart-traffic'), series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_DOWNLOAD, COLOR_UPLOAD] };
            charts.connections = { canvas: document.getElementById('chart-connections'), series: [Array(20).fill(0)], colors: [COLOR_ACTIVE] };
            charts.panelSystem = { canvas: document.getElementById('chart-panel-system'), series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_ACTIVE, COLOR_UPLOAD] };
            charts.panelRuntime = { canvas: document.getElementById('chart-panel-runtime'), series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_ACTIVE, COLOR_DOWNLOAD] };
            drawChart(charts.traffic, 'MB/s', [tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
            drawChart(charts.connections, '', [tx('اتصالات', 'Connections')]);
            drawChart(charts.panelSystem, '%', ['CPU', 'RAM']);
            drawChart(charts.panelRuntime, '', ['Threads', 'Sessions']);
        }

        function drawChart(chart, unit = '', labels = []) {
            const canvas = chart.canvas;
            const parent = canvas.parentElement;
            const dpr = window.devicePixelRatio || 1;
            const width = Math.max(240, parent.clientWidth || canvas.clientWidth || 320);
            const height = Math.max(140, parent.clientHeight || canvas.clientHeight || 220);
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;

            const ctx = canvas.getContext('2d');
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, width, height);
            const pad = 24;
            const topPad = 35; // extra padding for legend
            let flatSeries = [];
            chart.series.forEach(arr => { flatSeries = flatSeries.concat(arr); });
            const max = Math.max(1, ...flatSeries);
            const isLightChart = document.body.classList.contains('theme-light');
            const gridColor = isLightChart ? 'rgba(15,23,42,0.16)' : 'rgba(255,255,255,0.07)';
            const axisTextColor = isLightChart ? 'rgba(15,23,42,0.72)' : 'rgba(255,255,255,0.56)';
            const legendTextColor = isLightChart ? 'rgba(15,23,42,0.88)' : 'rgba(255,255,255,0.86)';
            ctx.strokeStyle = gridColor;
            ctx.lineWidth = 1;
            for (let i = 0; i < 5; i++) {
                const y = topPad + ((height - topPad - pad) / 4) * i;
                ctx.beginPath();
                ctx.moveTo(pad, y);
                ctx.lineTo(width - pad, y);
                ctx.stroke();
                
                // Draw Y axis labels
                ctx.fillStyle = axisTextColor;
                ctx.font = '10px Vazirmatn, Tahoma, sans-serif';
                ctx.textAlign = 'right';
                const val = max - (max / 4) * i;
                ctx.fillText(val.toFixed(1) + (unit ? ' ' + unit : ''), width - pad, y - 5);
            }
            chart.series.forEach((points, idx) => {
                ctx.strokeStyle = chart.colors[idx];
                ctx.lineWidth = 2;
                ctx.beginPath();
                points.forEach((point, i) => {
                    const x = pad + ((width - pad * 2) / (points.length - 1)) * i;
                    const safePoint = Math.max(0, Math.min(Number(point) || 0, max));
                    const y = height - pad - ((height - topPad - pad) * safePoint / max);
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                });
                ctx.stroke();
            });
            
            // Draw Legends
            if (labels && labels.length > 0) {
                let currentX = pad;
                labels.forEach((label, idx) => {
                    ctx.fillStyle = chart.colors[idx];
                    ctx.fillRect(currentX, 10, 10, 10);
                    ctx.fillStyle = legendTextColor;
                    ctx.textAlign = 'left';
                    ctx.font = '12px Vazirmatn, Tahoma, sans-serif';
                    ctx.fillText(label, currentX + 15, 20);
                    currentX += ctx.measureText(label).width + 30;
                });
            }
        }

        async function fetchStatus(options = {}) {
            if (!token) return;
            try {
                const res = await fetch('/api/status', {
                    headers: { 'Authorization': `Bearer ${token}` },
                    cache: 'no-store'
                });
                if (res.status === 401) {
                    logout(false);
                    return;
                }
                if (!res.ok) return;
                const status = await res.json();
                latestStatus = status;
                updateDashboard(status);
                renderEngineManager(status.engines || {});
                populateProfiles(status.tunnel_profiles || {}, { preserveSelection: isModalVisible('modal-add-link') });
                document.getElementById('about-version').innerText = status.version || '1.3.0';
                document.getElementById('about-license').innerText = status.license || 'GPL-3.0';
                updateLoginSecurity(status);
                if (status.biometric_enabled) maybeRegisterBiometric();

                renderCurrentTab(status, options);
                return status;
            } catch (err) {
                console.error("Fetch status failed:", err);
            }
        }

        function renderCurrentTab(status, options = {}) {
            if (currentTab === 'nodes') {
                renderNodes(status.nodes || {});
            } else if (currentTab === 'links') {
                renderLinksLive(status.links || {}, status.nodes || {});
            } else if (currentTab === 'logs') {
                renderLogs(status.logs || []);
            } else if (currentTab === 'monitor') {
                fetchRuntime();
            } else if (currentTab === 'dashboard' && options.forceChartRedraw) {
                drawLiveCharts(status);
            }
        }

        function populateProfiles(profiles, options = {}) {
            const select = document.getElementById('link-profile');
            if (!select) return;
            const signature = JSON.stringify(Object.entries(profiles || {}).sort(([a], [b]) => a.localeCompare(b)).map(([id, profile]) => [id, profile?.name, profile?.engine, profile?.tunnel_mode]));
            if (options.preserveSelection && signature === lastProfilesSignature) return;
            const current = select.value || 'custom';
            const focused = document.activeElement === select;
            select.innerHTML = `<option value="custom">${tx('شخصی / پیشرفته', 'Custom / Advanced')}</option>`;
            const groups = {};
            const categoryName = (id, profile) => {
                if (id === 'easy' || id === 'hard' || id === 'resilient') return tx('ساده و پیشنهادی', 'Recommended');
                if ((profile.engine || '').includes('muxquantum') || id.includes('muxquantum')) return 'Mux/Quantum';
                if (id.includes('ultra_stealth') || ['naiveproxy', 'shadowtls', 'singbox', 'tuic', 'hysteria2'].includes(profile.engine)) return tx('مخفی‌سازی و شرایط سخت', 'Stealth / strict filtering');
                if (['xray', 'gost', 'backhaul', 'rathole', 'chisel', 'frp'].includes(profile.engine)) return tx('کلاسیک و پایدار', 'Classic / stable');
                return tx('سایر', 'Other');
            };
            Object.entries(profiles).forEach(([id, profile]) => {
                const category = categoryName(id, profile || {});
                groups[category] = groups[category] || [];
                groups[category].push([id, profile]);
            });
            Object.entries(groups).forEach(([category, items]) => {
                const group = document.createElement('optgroup');
                group.label = category;
                items.sort((a, b) => (a[1].name || a[0]).localeCompare(b[1].name || b[0])).forEach(([id, profile]) => {
                    const opt = document.createElement('option');
                    opt.value = id;
                    opt.innerText = profile.name || id;
                    group.appendChild(opt);
                });
                select.appendChild(group);
            });
            select.value = profiles[current] ? current : 'custom';
            lastProfilesSignature = signature;
            if (focused) select.focus();
        }

        function isModalVisible(id) {
            const modal = document.getElementById(id);
            return !!modal && modal.style.display !== 'none' && getComputedStyle(modal).display !== 'none';
        }

        function populateLinkNodeSelects(nodes, options = {}) {
            const selectIR = document.getElementById('link-iran-node');
            const selectForeign = document.getElementById('link-foreign-node');
            if (!selectIR || !selectForeign) return;
            const preserveSelection = options.preserveSelection !== false;
            const currentIR = preserveSelection ? selectIR.value : '';
            const currentForeign = preserveSelection ? selectForeign.value : '';
            const focusedId = document.activeElement?.id || '';

            selectIR.innerHTML = '';
            selectForeign.innerHTML = '';
            Object.entries(nodes || {}).forEach(([nid, n]) => {
                const opt = document.createElement('option');
                opt.value = nid;
                opt.innerText = `${n.name || nid} (${n.ip || '-'})`;
                if (n.role === 'internal' || n.role === 'iran') selectIR.appendChild(opt);
                else selectForeign.appendChild(opt);
            });

            if (currentIR && Array.from(selectIR.options).some(opt => opt.value === currentIR)) {
                selectIR.value = currentIR;
            }
            if (currentForeign && Array.from(selectForeign.options).some(opt => opt.value === currentForeign)) {
                selectForeign.value = currentForeign;
            }
            if (focusedId === 'link-iran-node') selectIR.focus();
            if (focusedId === 'link-foreign-node') selectForeign.focus();
        }

        function getTargetPortCheck(nodes, linkId, link, userPort) {
            const foreignNode = (nodes || {})[link.external_node_id || link.foreign_node_id] || {};
            const checks = foreignNode.stats?.target_port_checks?.[linkId] || {};
            return checks[String(userPort)] || {};
        }

        function targetPortStatusMarkup(check) {
            const known = check && check.target_open !== undefined;
            if (!known) return `<span style="opacity:.75;">${tx('در انتظار گزارش نود خارجی', 'Waiting for external node report')}</span>`;
            if (check.target_open === true) return `<span class="text-success">${tx('مقصد خارجی باز است', 'External target open')}</span>`;
            return `<span class="text-danger">${tx('مقصد خارجی بسته است', 'External target closed')}</span>`;
        }

        function linkRuntimeHealth(nodes, linkId, link) {
            const irNode = (nodes || {})[link.internal_node_id || link.iran_node_id] || {};
            const foreignNode = (nodes || {})[link.external_node_id || link.foreign_node_id] || {};
            const internalStatus = irNode.stats?.link_statuses?.[linkId] || {};
            const externalStatus = foreignNode.stats?.link_statuses?.[linkId] || {};
            const nodesOnline = irNode.status === 'online' && foreignNode.status === 'online';
            const anyUserPort = (link.ports || []).some(port => internalStatus.ports?.[String(port.user_port)]?.listening === true);
            const poolReady = Number(internalStatus.pool_available || 0) > 0 || Number(externalStatus.ready_workers || 0) > 0;
            const directReady = externalStatus.direct_bridge_listening === true;
            const runtimeKnown = internalStatus.running !== undefined || externalStatus.running !== undefined;
            const ready = nodesOnline && !link.paused && (!runtimeKnown || (internalStatus.running && externalStatus.running && anyUserPort && (poolReady || directReady)));
            let reason = '';
            if (!nodesOnline) reason = tx('یکی از نودها آفلاین است', 'One node is offline');
            else if (link.paused) reason = tx('تانل متوقف است', 'Tunnel is paused');
            else if (runtimeKnown && !internalStatus.running) reason = tx('نود داخلی تانل را اجرا نکرده است', 'Internal node has not started the tunnel');
            else if (runtimeKnown && !externalStatus.running) reason = tx('نود خارجی تانل را اجرا نکرده است', 'External node has not started the tunnel');
            else if (runtimeKnown && !anyUserPort) reason = tx('پورت ورودی روی نود داخلی باز نشده است', 'Internal input port is not listening');
            else if (runtimeKnown && !poolReady && !directReady) reason = tx('نه اتصال رزرو آماده است و نه پل مستقیم نود خارجی باز است', 'No reverse worker is ready and external direct bridge is not listening');
            if (!reason && externalStatus.last_worker_error) reason = externalStatus.last_worker_error;
            return { ready, reason, internalStatus, externalStatus };
        }

        function updateDashboard(status) {
            const nodeList = Object.values(status.nodes || {});
            const totalNodes = nodeList.length;
            const onlineNodes = nodeList.filter(node => node.status === 'online').length;
            document.getElementById('stat-nodes-count').innerText = `${onlineNodes} / ${totalNodes}`;
            document.getElementById('stat-links-count').innerText = Object.keys(status.links || {}).length;
            
            let totalRx = 0, totalTx = 0, totalThreads = 0, totalConns = 0;
            nodeList.forEach(node => {
                if (node.status === 'online' && node.stats) {
                    totalRx += node.stats.rx_speed || 0;
                    totalTx += node.stats.tx_speed || 0;
                    totalThreads += node.stats.threads || 0;
                    totalConns += node.stats.connections || 0;
                }
            });

            const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
            const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
            const rxVal = (totalRx / divisor).toFixed(2);
            const txVal = (totalTx / divisor).toFixed(2);
            
            document.getElementById('stat-net-speed').innerText = `${rxVal} / ${txVal} ${trafficUnit}/s`;
            document.getElementById('stat-threads-count').innerText = totalThreads;

            pushLiveChartPoints(parseFloat(rxVal), parseFloat(txVal), totalConns, trafficUnit);
            
            if (status.host_info) {
                document.getElementById('host-cpu').innerText = status.host_info.cpu_cores + ' Cores';
                document.getElementById('host-ram').innerText = status.host_info.ram_free_gb + ' GB / ' + status.host_info.ram_total_gb + ' GB';
                document.getElementById('host-swap').innerText = status.host_info.swap_free_gb + ' GB / ' + status.host_info.swap_total_gb + ' GB';
                document.getElementById('host-disk').innerText = status.host_info.disk_free_gb + ' GB / ' + status.host_info.disk_total_gb + ' GB';
                const uptime = Number(status.host_info.uptime_seconds || 0);
                const uptimeText = uptime ? `${Math.floor(uptime / 86400)}d ${Math.floor((uptime % 86400) / 3600)}h` : '-';
                const load = (status.host_info.load_avg || []).join(' / ') || '-';
                document.getElementById('host-load').innerText = `${load} | ${uptimeText}`;
                document.getElementById('host-process').innerText = `PID ${status.host_info.panel_pid || '-'} | RSS ${status.host_info.panel_rss_mb || 0} MB`;
                const docker = status.host_info.docker || {};
                document.getElementById('host-docker').innerText = docker.available ? `${docker.containers_running}/${docker.containers_total} Containers | ${docker.images} Images` : tx('در دسترس نیست', 'Unavailable');
            }
            pushPanelSystemChart(status, totalThreads, totalConns);
        }

        function pushPanelSystemChart(status, totalThreads, totalConns) {
            const host = status.host_info || {};
            const cores = Math.max(1, Number(host.cpu_cores || 1));
            const load1 = Number((host.load_avg || [0])[0] || 0);
            const cpuLoadPercent = Math.min(100, (load1 / cores) * 100);
            const ramTotal = Number(host.ram_total_gb || 0);
            const ramFree = Number(host.ram_free_gb || 0);
            const ramUsedPercent = ramTotal > 0 ? Math.max(0, Math.min(100, ((ramTotal - ramFree) / ramTotal) * 100)) : 0;
            if (charts.panelSystem) {
                charts.panelSystem.series[0].shift();
                charts.panelSystem.series[0].push(parseFloat(cpuLoadPercent.toFixed(1)));
                charts.panelSystem.series[1].shift();
                charts.panelSystem.series[1].push(parseFloat(ramUsedPercent.toFixed(1)));
                drawChart(charts.panelSystem, '%', ['CPU', 'RAM']);
            }
            if (charts.panelRuntime) {
                charts.panelRuntime.series[0].shift();
                charts.panelRuntime.series[0].push(Number(totalThreads || 0));
                charts.panelRuntime.series[1].shift();
                charts.panelRuntime.series[1].push(Number(totalConns || 0));
                drawChart(charts.panelRuntime, '', ['Threads', 'Sessions']);
            }
        }

        function pushLiveChartPoints(rxVal, txVal, totalConns, trafficUnit) {
            if (charts.traffic) {
                charts.traffic.series[0].shift();
                charts.traffic.series[0].push(rxVal);
                charts.traffic.series[1].shift();
                charts.traffic.series[1].push(txVal);
                drawChart(charts.traffic, trafficUnit + '/s', [tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
            }

            if (charts.connections) {
                charts.connections.series[0].shift();
                charts.connections.series[0].push(totalConns);
                drawChart(charts.connections, '', [tx('اتصالات', 'Connections')]);
            }
        }

        function drawLiveCharts(status) {
            if (!status || !charts.traffic || !charts.connections) return;
            const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
            drawChart(charts.traffic, trafficUnit + '/s', [tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
            drawChart(charts.connections, '', [tx('اتصالات', 'Connections')]);
        }

        function renderNodes(nodes) {
            const tbody = document.querySelector('#table-nodes tbody');
            const existingRows = new Map(Array.from(tbody.querySelectorAll('tr[data-node-id]')).map(row => [row.dataset.nodeId, row]));
            const seen = new Set();
            
            const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
            const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
            
            Object.keys(nodes).forEach(nid => {
                seen.add(nid);
                const n = nodes[nid];
                const stats = n.stats || { cpu: 0, ram: 0, rx_speed: 0, tx_speed: 0, threads: 0, connections: 0 };
                const isOnline = n.status === 'online';
                const isPaused = n.paused;
                const statusClass = isPaused ? 'text-warning' : (isOnline ? 'text-success' : 'text-danger');
                const statusText = isPaused ? tx('متوقف', 'Paused') : (isOnline ? t('online') : t('offline'));
                const pingText = isPaused
                    ? `<span class="text-warning" title="${tx('نود متوقف است', 'Node is paused')}"> ! </span>`
                    : (!isOnline || stats.ping_status === 'failed'
                        ? `<span class="text-danger" title="${tx('قطع یا بدون پاسخ ping', 'Disconnected or ping failed')}">∞</span>`
                        : (stats.ping_ms !== undefined ? `<span class="text-success">${esc(stats.ping_ms)} ms</span>` : `<span style="opacity:.7;">...</span>`));
                
                const tr = existingRows.get(nid) || document.createElement('tr');
                tr.dataset.nodeId = nid;
                tr.innerHTML = `
                    <td><div class="node-name-line"><strong>${esc(n.name)}</strong><span class="tag-row">${renderTags(n.tags || [])}</span></div></td>
                    <td><span class="tag-pill node-role"><span class="status-dot ${isOnline ? '' : 'offline'}"></span>${(n.role === 'internal' || n.role === 'iran') ? t('internal') : t('external')}</span></td>
                    <td><code>${esc(n.ip)}</code></td>
                    <td><span class="status-pill"><span class="status-dot ${isOnline ? (isPaused ? 'warning' : '') : 'offline'}"></span><span class="${statusClass}">${statusText}</span><span style="margin-inline-start:8px;">${pingText}</span></span></td>
                    <td>${tx('پردازنده', 'CPU')}: ${esc(stats.cpu)}% | ${tx('رم', 'RAM')}: ${esc(stats.ram)}%</td>
                    <td>${tx('دانلود', 'Download')}: ${(stats.rx_speed / divisor).toFixed(1)} ${trafficUnit}/s | ${tx('آپلود', 'Upload')}: ${(stats.tx_speed / divisor).toFixed(1)} ${trafficUnit}/s</td>
                    <td>${tx('تردها', 'Threads')}: ${stats.threads} | ${tx('فعال', 'Active')}: ${stats.connections}</td>
                    <td>
                        <div class="node-actions-line">
                            <button class="btn w-auto p-10 btn-danger" onclick="deleteNode('${nid}')" style="background: var(--danger);">${t('delete')}</button>
                            <button class="btn w-auto p-10" onclick="togglePauseNode('${nid}')" style="background: var(--warning); color: #000;">${isPaused ? tx('فعال‌سازی', 'Resume') : tx('توقف', 'Pause')}</button>
                            <button class="btn w-auto p-10" onclick="editNode('${nid}')" style="background: #10b981; color: white; box-shadow: 0 0 10px #10b981;">${tx('ویرایش', 'Edit')}</button>
                            <button class="btn w-auto p-10" onclick="testNodeConnection('${nid}')">${tx('تست ارتباط', 'Test connection')}</button>
                            <button class="btn w-auto p-10 btn-purple" onclick="openNodeSecrets('${nid}')">${tx('توکن/کلید', 'Token/Key')}</button>
                            <button class="btn w-auto p-10 btn-cyan" onclick="openNodeSshModal('${nid}')">SSH</button>
                        </div>
                    </td>
                `;
                if (!existingRows.has(nid)) tbody.appendChild(tr);
            });
            existingRows.forEach((row, nid) => {
                if (!seen.has(nid)) row.remove();
            });
        }

        function linkCategoryKey(link) {
            return `${link.engine || 'builtin'} / ${link.tunnel_mode || 'tcp'}`;
        }

        function estimateCategoryTraffic(items, nodes) {
            const nodeIds = new Set();
            items.forEach(({ link }) => {
                nodeIds.add(link.internal_node_id || link.iran_node_id);
                nodeIds.add(link.external_node_id || link.foreign_node_id);
            });
            let rx = 0, tx = 0;
            nodeIds.forEach(nid => {
                const stats = nodes[nid]?.stats || {};
                rx += Number(stats.rx_speed || 0);
                tx += Number(stats.tx_speed || 0);
            });
            return { rx, tx };
        }

        function linksStructureSignature(links) {
            return JSON.stringify(Object.entries(links || {}).sort(([a], [b]) => a.localeCompare(b)).map(([id, link]) => [
                id, link.name, link.engine, link.tunnel_mode, link.internal_node_id || link.iran_node_id,
                link.external_node_id || link.foreign_node_id, link.bridge_port, link.sync_port,
                JSON.stringify(link.ports || []), JSON.stringify(link.tags || [])
            ]));
        }

        function renderLinksLive(links, nodes) {
            const signature = linksStructureSignature(links);
            if (signature !== lastLinksSignature || !document.querySelector('#links-container .link-category')) {
                renderLinks(links, nodes);
            } else {
                updateLinkLiveSections(links, nodes);
            }
        }

        function renderLinks(links, nodes) {
            const container = document.getElementById('links-container');
            const chartsContainer = document.getElementById('link-category-charts');
            const shouldRestoreScroll = currentTab === 'links';
            const scrollX = window.scrollX;
            const scrollY = window.scrollY;
            lastLinksSignature = linksStructureSignature(links);
            container.innerHTML = '';
            if (chartsContainer) chartsContainer.innerHTML = '';

            populateLinkNodeSelects(nodes || {}, { preserveSelection: isModalVisible('modal-add-link') });

            const grouped = {};
            Object.entries(links).forEach(([lid, link]) => {
                const key = linkCategoryKey(link);
                grouped[key] = grouped[key] || [];
                grouped[key].push({ id: lid, link });
            });

            Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).forEach(([category, items], categoryIndex) => {
                const active = items.filter(({ id, link }) => {
                    return linkRuntimeHealth(nodes, id, link).ready;
                }).length;
                const traffic = estimateCategoryTraffic(items, nodes);
                const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
                const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
                const chartId = `category-chart-${categoryIndex}`;
                if (chartsContainer) {
                    const chartCard = document.createElement('div');
                    chartCard.className = 'glass-card';
                    chartCard.dataset.category = category;
                    chartCard.innerHTML = `
                        <div class="flex-between">
                            <h3 style="font-size: 16px;">${esc(category)}</h3>
                            <span class="tag-pill">${tx('گراف زنده دسته', 'Live category chart')}</span>
                        </div>
                        <div class="category-metrics">
                            <div class="category-metric active"><span>${tx('تانل فعال', 'Active tunnels')}</span><strong data-category-active>${active}</strong></div>
                            <div class="category-metric"><span>${tx('کل تانل‌ها', 'Total tunnels')}</span><strong data-category-total>${items.length}</strong></div>
                            <div class="category-metric download"><span>${tx('دانلود', 'Download')}</span><strong data-category-rx>${(traffic.rx / divisor).toFixed(2)} ${trafficUnit}/s</strong></div>
                            <div class="category-metric upload"><span>${tx('آپلود', 'Upload')}</span><strong data-category-tx>${(traffic.tx / divisor).toFixed(2)} ${trafficUnit}/s</strong></div>
                        </div>
                        <div class="category-chart-frame"><canvas id="${chartId}"></canvas></div>
                    `;
                    chartsContainer.appendChild(chartCard);
                }

                const details = document.createElement('details');
                details.className = 'glass-card link-category';
                details.dataset.category = category;
                details.open = !!linkCategoryOpenStates[category];
                details.addEventListener('toggle', () => {
                    linkCategoryOpenStates[category] = details.open;
                    localStorage.setItem('p00rija_link_category_open', JSON.stringify(linkCategoryOpenStates));
                });
                details.innerHTML = `
                    <summary>
                        <div class="flex-between">
                            <div>
                                <h3>${esc(category)}</h3>
                                <div class="tag-row">
                                    <span class="tag-pill tag-color-3">${tx('فعال', 'Active')}: ${active}</span>
                                    <span class="tag-pill tag-color-0">${tx('کل', 'Total')}: ${items.length}</span>
                                </div>
                            </div>
                            <span class="tag-pill">${tx('باز/بسته کردن دسته', 'Toggle category')}</span>
                        </div>
                    </summary>
                    <div style="display: flex; flex-direction: column; gap: 16px; margin-top: 16px;"></div>
                `;
                const inner = details.querySelector('summary + div');
                items.forEach(({ id: lid, link: l }) => {
                    const irNode = nodes[l.internal_node_id || l.iran_node_id] || { name: tx('نامشخص', 'Unknown') };
                    const foreignNode = nodes[l.external_node_id || l.foreign_node_id] || { name: tx('نامشخص', 'Unknown') };
                    const isPaused = !!l.paused;
                    const health = linkRuntimeHealth(nodes, lid, l);
                    const isLinked = health.ready;
                    const modeText = `${l.engine || 'builtin'} / ${l.tunnel_mode === 'websocket' ? 'WebSocket' : (l.tunnel_mode === 'http_obfs' ? 'HTTP Obfs' : l.tunnel_mode || 'TCP RAW')}`;
                    const tlsText = l.tls_enabled ? ' + TLS (Secure)' : '';
                    const portRows = (l.ports || []).map((port, index) => {
                        const targetStatus = targetPortStatusMarkup(getTargetPortCheck(nodes, lid, l, port.user_port));
                        return `<tr>
                            <td><code>${esc(port.user_port)}</code><br><small class="text-success">${tx('روی نود داخلی listen می‌شود', 'Listens on internal node')}</small></td>
                            <td><code>${esc(port.target_port)}</code><br><small data-target-port-status data-user-port="${esc(port.user_port)}">${targetStatus}</small></td>
                            <td data-port-link-status data-user-port="${esc(port.user_port)}">${isLinked ? `<span class="text-success">${tx('تانل برقرار', 'Tunnel connected')}</span>` : `<span class="text-danger" title="${esc(health.reason)}">${tx('تانل آماده نیست', 'Tunnel not ready')}</span>`}</td>
                            <td>
                                <div class="flex-between gap-10" style="justify-content:flex-start; flex-wrap:wrap;">
                                    <button class="btn w-auto p-10" onclick="editPortMapping('${lid}', ${index}, ${esc(port.user_port)}, ${esc(port.target_port)})" style="background: #10b981; color: white; font-size: 12px; padding: 4px 8px;">${tx('ویرایش', 'Edit')}</button>
                                    <button class="btn w-auto p-10 btn-purple" onclick="testPortPayload('${lid}', ${index})" style="font-size: 12px; padding: 4px 8px;">${tx('تست پکیج', 'Payload test')}</button>
                                    <button class="btn w-auto p-10" onclick="deletePortMapping('${lid}', ${index})" style="background: var(--danger); font-size: 12px; padding: 4px 8px;">${t('delete')}</button>
                                </div>
                            </td>
                        </tr>`;
                    }).join('');
                    const card = document.createElement('div');
                    card.dataset.linkId = lid;
                    card.style.border = '1px solid var(--border-card)';
                    card.style.borderRadius = '8px';
                    card.style.padding = '16px';
                    card.innerHTML = `
                        <div class="flex-between mb-20">
                            <div>
                                <h3 style="font-size: 18px; margin-bottom: 6px;">${esc(l.name)} <span class="tag-pill" style="background: rgba(0,240,255,0.1); border-color: var(--accent-blue);">${modeText}${tlsText}</span></h3>
                                <p style="font-size: 14px; color: var(--text-secondary);">
                                    ${tx('نود داخلی', 'Internal node')}: <strong>${esc(irNode.name)}</strong> <i data-lucide="arrow-right"></i> ${tx('نود خارجی', 'External node')}: <strong>${esc(foreignNode.name)}</strong>
                                </p>
                                <div class="tag-row">${renderTags(l.tags || [])}</div>
                            </div>
                            <div class="flex-between gap-10 link-actions">
                                <span class="tag-pill">${tx('پل', 'Bridge')}: ${l.bridge_port} | ${tx('همگام‌سازی', 'Sync')}: ${l.sync_port}</span>
                                <span class="status-pill" data-link-status-pill title="${esc(health.reason)}">
                                    <div class="status-dot" data-link-status-dot style="background-color: ${isPaused ? 'var(--warning)' : (isLinked ? 'var(--success)' : 'var(--danger)')}; box-shadow: 0 0 10px ${isPaused ? 'var(--warning)' : (isLinked ? 'var(--success)' : 'var(--danger)')};"></div>
                                    <span data-link-status-text>${isPaused ? tx('متوقف', 'Paused') : (isLinked ? t('connected') : t('disconnected'))}</span>
                                </span>
                                <button class="btn w-auto p-10 btn-danger" onclick="deleteLink('${lid}')" style="background: var(--danger);">${tx('حذف تانل', 'Delete tunnel')}</button>
                                <button class="btn w-auto p-10" onclick="togglePauseLink('${lid}')" style="background: var(--warning); color: #000;">${isPaused ? tx('ادامه', 'Resume') : tx('توقف', 'Pause')}</button>
                                <button class="btn w-auto p-10" onclick="editLink('${lid}')" style="background: #10b981; color: white; box-shadow: 0 0 10px #10b981;">${tx('ویرایش', 'Edit')}</button>
                                <button class="btn w-auto p-10" onclick="testLink('${lid}')">${tx('تست اتصال', 'Test connection')}</button>
                                <button class="btn w-auto p-10" onclick="showEngineConfig('${lid}')">${tx('نمایش کانفیگ موتور', 'Show engine config')}</button>
                            </div>
                        </div>
                        <div style="border-top: 1px solid var(--border-card); padding-top: 15px;">
                            <h4 class="mb-20">${tx('لیست پورت‌های هدایت شده (Port Forwarding)', 'Forwarded ports (Port Forwarding)')}</h4>
                            <table>
                                <thead><tr><th>${tx('پورت ورودی داخلی', 'Internal input port')}</th><th>${tx('پورت مقصد خارجی', 'External target port')}</th><th>${tx('وضعیت', 'Status')}</th><th>${tx('عملیات', 'Actions')}</th></tr></thead>
                                <tbody>
                                    ${portRows}
                                    <tr>
                                        <td><input type="text" id="add-user-port-${lid}" class="form-input" placeholder="${tx('پورت داخلی (یا بازه)', 'Internal port/range')}" style="padding: 6px; font-size: 14px;"></td>
                                        <td><input type="text" id="add-target-port-${lid}" class="form-input" placeholder="${tx('پورت خارجی (یا بازه)', 'External port/range')}" style="padding: 6px; font-size: 14px;"></td>
                                        <td>-</td>
                                        <td><button class="btn w-auto p-10" onclick="addPortMapping('${lid}')" style="font-size: 12px; padding: 6px 12px;">${tx('افزودن پورت', 'Add port')}</button></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    `;
                    inner.appendChild(card);
                });
                container.appendChild(details);
                const canvas = document.getElementById(chartId);
                if (!canvas) return;
                categoryCharts[category] = categoryCharts[category] || { canvas, series: [Array(20).fill(0), Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_ACTIVE, COLOR_DOWNLOAD, COLOR_UPLOAD] };
                categoryCharts[category].canvas = canvas;
                categoryCharts[category].colors = [COLOR_ACTIVE, COLOR_DOWNLOAD, COLOR_UPLOAD];
                categoryCharts[category].series[0].shift();
                categoryCharts[category].series[0].push(active);
                categoryCharts[category].series[1].shift();
                categoryCharts[category].series[1].push(parseFloat((traffic.rx / divisor).toFixed(2)));
                categoryCharts[category].series[2].shift();
                categoryCharts[category].series[2].push(parseFloat((traffic.tx / divisor).toFixed(2)));
                drawChart(categoryCharts[category], '', [tx('فعال', 'Active'), tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
            });
            createInlineIcons(container);
            if (shouldRestoreScroll) {
                requestAnimationFrame(() => window.scrollTo(scrollX, scrollY));
            }
        }

        function updateLinkLiveSections(links, nodes) {
            const grouped = {};
            Object.entries(links || {}).forEach(([lid, link]) => {
                const key = linkCategoryKey(link);
                grouped[key] = grouped[key] || [];
                grouped[key].push({ id: lid, link });
            });
            const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
            const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
            Object.entries(grouped).forEach(([category, items]) => {
                const active = items.filter(({ id, link }) => {
                    return linkRuntimeHealth(nodes, id, link).ready;
                }).length;
                const traffic = estimateCategoryTraffic(items, nodes);
                const chartCard = document.querySelector(`#link-category-charts [data-category="${cssEscape(category)}"]`);
                if (chartCard) {
                    const activeEl = chartCard.querySelector('[data-category-active]');
                    const totalEl = chartCard.querySelector('[data-category-total]');
                    const rxEl = chartCard.querySelector('[data-category-rx]');
                    const txEl = chartCard.querySelector('[data-category-tx]');
                    if (activeEl) activeEl.innerText = active;
                    if (totalEl) totalEl.innerText = items.length;
                    if (rxEl) rxEl.innerText = `${(traffic.rx / divisor).toFixed(2)} ${trafficUnit}/s`;
                    if (txEl) txEl.innerText = `${(traffic.tx / divisor).toFixed(2)} ${trafficUnit}/s`;
                }
                const chart = categoryCharts[category];
                if (chart) {
                    chart.series[0].shift();
                    chart.series[0].push(active);
                    chart.series[1].shift();
                    chart.series[1].push(parseFloat((traffic.rx / divisor).toFixed(2)));
                    chart.series[2].shift();
                    chart.series[2].push(parseFloat((traffic.tx / divisor).toFixed(2)));
                    drawChart(chart, '', [tx('فعال', 'Active'), tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
                }
            });
            Object.entries(links || {}).forEach(([lid, link]) => {
                const card = document.querySelector(`[data-link-id="${cssEscape(lid)}"]`);
                if (!card) return;
                const isPaused = !!link.paused;
                const health = linkRuntimeHealth(nodes, lid, link);
                const isLinked = health.ready;
                const color = isPaused ? 'var(--warning)' : (isLinked ? 'var(--success)' : 'var(--danger)');
                const dot = card.querySelector('[data-link-status-dot]');
                const text = card.querySelector('[data-link-status-text]');
                if (dot) {
                    dot.style.backgroundColor = color;
                    dot.style.boxShadow = `0 0 10px ${color}`;
                }
                const pill = card.querySelector('[data-link-status-pill]');
                if (pill) pill.title = health.reason || '';
                if (text) text.innerText = isPaused ? tx('متوقف', 'Paused') : (isLinked ? t('connected') : t('disconnected'));
                (link.ports || []).forEach(port => {
                    const portStatusEl = card.querySelector(`[data-port-link-status][data-user-port="${cssEscape(port.user_port)}"]`);
                    if (portStatusEl) {
                        portStatusEl.innerHTML = isLinked
                            ? `<span class="text-success">${tx('تانل برقرار', 'Tunnel connected')}</span>`
                            : `<span class="text-danger" title="${esc(health.reason)}">${tx('تانل آماده نیست', 'Tunnel not ready')}</span>`;
                    }
                    const statusEl = card.querySelector(`[data-target-port-status][data-user-port="${cssEscape(port.user_port)}"]`);
                    if (statusEl) statusEl.innerHTML = targetPortStatusMarkup(getTargetPortCheck(nodes, lid, link, port.user_port));
                });
            });
        }

        function renderLogs(logs) {
            const tbody = document.querySelector('#table-logs tbody');
            tbody.innerHTML = '';
            
            const reversed = [...logs].reverse();
            reversed.forEach(entry => {
                let lvlClass = '';
                if (entry.level === 'error') lvlClass = 'text-danger';
                else if (entry.level === 'warning') lvlClass = 'text-warning';
                else lvlClass = 'text-success';

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="color: var(--text-secondary); font-size: 13px;">${esc(entry.timestamp)}</td>
                    <td><strong>${esc(entry.source)}</strong></td>
                    <td class="${lvlClass}">${esc(entry.level).toUpperCase()}</td>
                    <td><code>${esc(entry.message)}</code></td>
                `;
                tbody.appendChild(tr);
            });
        }

        const tunnelOptionMatrix = {
            builtin: {
                transports: [['tcp', 'TCP'], ['websocket', 'WebSocket'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['tcp', 'TCP Tunnel'], ['websocket', 'WebSocket Tunnel'], ['http_obfs', 'HTTP Obfuscation']],
                networks: [['tcp', 'TCP']]
            },
            gost: {
                transports: [['tcp', 'TCP'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS'], ['grpc', 'gRPC']],
                modes: [['websocket', 'WebSocket Tunnel'], ['http_obfs', 'HTTP Obfuscation'], ['grpc', 'gRPC Tunnel']],
                networks: [['tcp', 'TCP']]
            },
            backhaul: {
                transports: [['tcp', 'TCP'], ['udp', 'UDP'], ['tcpmux', 'TCPMux'], ['wsmux', 'WSMux']],
                modes: [['tcp', 'TCP Tunnel'], ['udp', 'UDP Tunnel'], ['tcpmux', 'TCPMux'], ['wsmux', 'WSMux'], ['websocket', 'WebSocket Tunnel']],
                networks: [['tcp', 'TCP'], ['udp', 'UDP']]
            },
            rathole: {
                transports: [['tcp', 'TCP'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['tcp', 'TCP Tunnel'], ['websocket', 'WebSocket Tunnel']],
                networks: [['tcp', 'TCP']]
            },
            chisel: {
                transports: [['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['websocket', 'WebSocket Tunnel'], ['http_obfs', 'HTTP Obfuscation']],
                networks: [['tcp', 'TCP']]
            },
            frp: {
                transports: [['tcp', 'TCP'], ['udp', 'UDP'], ['kcp', 'KCP'], ['quic', 'QUIC']],
                modes: [['tcp', 'TCP Tunnel'], ['udp', 'UDP Tunnel'], ['tcp_udp', 'TCP + UDP'], ['kcp', 'KCP'], ['quic', 'QUIC']],
                networks: [['tcp', 'TCP'], ['udp', 'UDP'], ['tcp_udp', 'TCP + UDP']]
            },
            xray: {
                transports: [['tcp', 'TCP'], ['grpc', 'gRPC TLS'], ['h2', 'HTTP/2 TLS'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['vless_reality', 'Xray VLESS Reality'], ['reality_grpc', 'REALITY gRPC'], ['reality_h2', 'REALITY HTTP/2'], ['reality_ws', 'REALITY WebSocket']],
                networks: [['tcp', 'TCP']]
            },
            muxquantum: {
                transports: [['tcpmux', 'TCPMux'], ['httpsmux', 'HTTPSMux'], ['quantummux', 'QuantumMux'], ['tunmux', 'TunMux'], ['mux_wss', 'Mux WSS'], ['mux_h2', 'Mux HTTP/2 TLS'], ['mux_h3', 'Mux HTTP/3 QUIC'], ['mux_quic', 'Mux QUIC'], ['mux_grpc', 'Mux gRPC TLS'], ['mux_shadowtls', 'Mux ShadowTLS'], ['mux_reality', 'Mux REALITY'], ['mux_anytls', 'Mux AnyTLS'], ['mux_naive', 'Mux Naive HTTPS'], ['mux_kcp', 'Mux KCP']],
                modes: [['tcpmux', 'TCPMux'], ['httpsmux', 'HTTPSMux'], ['quantummux', 'QuantumMux'], ['tunmux', 'TunMux'], ['mux_wss', 'Mux WSS'], ['mux_h2', 'Mux HTTP/2 TLS'], ['mux_h3', 'Mux HTTP/3 QUIC'], ['mux_quic', 'Mux QUIC'], ['mux_grpc', 'Mux gRPC TLS'], ['mux_shadowtls', 'Mux ShadowTLS'], ['mux_reality', 'Mux REALITY'], ['mux_anytls', 'Mux AnyTLS'], ['mux_naive', 'Mux Naive HTTPS'], ['mux_kcp', 'Mux KCP UDP']],
                networks: [['tcp', 'TCP'], ['udp', 'UDP']]
            },
            hysteria2: {
                transports: [['quic', 'QUIC'], ['h3', 'HTTP/3 Masquerade']],
                modes: [['quic', 'QUIC'], ['http3_masquerade', 'HTTP/3 Masquerade'], ['hysteria2_salamander', 'Salamander Obfuscation'], ['hysteria2_gecko', 'Gecko Obfuscation']],
                networks: [['udp', 'UDP']]
            },
            singbox: {
                transports: [['tcp', 'TCP'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS'], ['grpc', 'gRPC'], ['h2', 'HTTP/2 TLS'], ['h3', 'HTTP/3 QUIC'], ['shadowtls', 'ShadowTLS'], ['tuic', 'TUIC'], ['anytls', 'AnyTLS'], ['naive', 'Naive HTTPS'], ['ech', 'ECH TLS']],
                modes: [['vless_reality', 'VLESS REALITY'], ['reality_grpc', 'REALITY gRPC'], ['reality_h2', 'REALITY HTTP/2'], ['reality_ws', 'REALITY WS'], ['shadowtls', 'ShadowTLS'], ['shadowtls_ws', 'ShadowTLS + WS'], ['shadowtls_h2', 'ShadowTLS + HTTP/2'], ['tuic_quic', 'TUIC QUIC'], ['quic', 'Hysteria2 QUIC'], ['http3_masquerade', 'HTTP/3 Masquerade'], ['hysteria2_salamander', 'Hysteria2 Salamander'], ['hysteria2_gecko', 'Hysteria2 Gecko'], ['naive_https', 'Naive HTTPS'], ['naive_h2', 'Naive HTTP/2'], ['http2_tls', 'HTTP/2 TLS'], ['anytls', 'AnyTLS'], ['anytls_h2', 'AnyTLS HTTP/2'], ['anytls_ws', 'AnyTLS WebSocket'], ['ech_tls', 'ECH TLS'], ['ech_h2', 'ECH HTTP/2'], ['websocket', 'WebSocket TLS'], ['grpc', 'gRPC TLS']],
                networks: [['tcp', 'TCP'], ['udp', 'UDP']]
            },
            tuic: {
                transports: [['tuic', 'TUIC'], ['quic', 'QUIC']],
                modes: [['tuic_quic', 'TUIC QUIC'], ['quic', 'QUIC']],
                networks: [['udp', 'UDP']]
            },
            naiveproxy: {
                transports: [['naive', 'Naive HTTPS'], ['h2', 'HTTP/2 TLS']],
                modes: [['naive_https', 'Naive HTTPS Camouflage'], ['naive_h2', 'Naive HTTP/2 Chrome-like'], ['http2_tls', 'HTTP/2 TLS']],
                networks: [['tcp', 'TCP']]
            },
            shadowtls: {
                transports: [['shadowtls', 'ShadowTLS'], ['wss', 'WebSocket TLS'], ['h2', 'HTTP/2 TLS']],
                modes: [['shadowtls', 'ShadowTLS'], ['shadowtls_ws', 'ShadowTLS + WS'], ['shadowtls_h2', 'ShadowTLS + HTTP/2']],
                networks: [['tcp', 'TCP']]
            },
            brook: {
                transports: [['tcp', 'TCP'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['tcp', 'Brook TCP'], ['websocket', 'Brook WS'], ['http_obfs', 'Brook Web-like']],
                networks: [['tcp', 'TCP']]
            },
            mieru: {
                transports: [['tcp', 'TCP'], ['h2', 'HTTP/2 TLS'], ['wss', 'WebSocket TLS']],
                modes: [['http2_tls', 'HTTP/2 TLS'], ['websocket', 'WebSocket TLS'], ['tcp', 'TCP']],
                networks: [['tcp', 'TCP']]
            }
        };

        function setSelectOptions(select, options, preferred) {
            if (!select) return;
            const current = preferred || select.value;
            select.innerHTML = options.map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join('');
            select.value = options.some(([value]) => value === current) ? current : options[0]?.[0] || '';
        }

        const modeTransportMap = {
            websocket: 'ws', http_obfs: 'ws', grpc: 'grpc', tcpmux: 'tcpmux', httpsmux: 'httpsmux',
            quantummux: 'quantummux', tunmux: 'tunmux', kcp: 'kcp', quic: 'quic', udp: 'udp',
            tcp: 'tcp', tcp_udp: 'tcp', vless_reality: 'tcp', reality_grpc: 'grpc', reality_h2: 'h2',
            reality_ws: 'wss', shadowtls: 'shadowtls', shadowtls_ws: 'shadowtls', shadowtls_h2: 'shadowtls',
            tuic_quic: 'tuic', naive_https: 'naive', naive_h2: 'h2', http2_tls: 'h2',
            http3_masquerade: 'h3', hysteria2_salamander: 'quic', hysteria2_gecko: 'h3',
            anytls: 'anytls', anytls_h2: 'anytls', anytls_ws: 'anytls', ech_tls: 'ech', ech_h2: 'ech',
            mux_wss: 'mux_wss', mux_h2: 'mux_h2', mux_h3: 'mux_h3', mux_quic: 'mux_quic',
            mux_grpc: 'mux_grpc', mux_shadowtls: 'mux_shadowtls', mux_reality: 'mux_reality',
            mux_anytls: 'mux_anytls', mux_naive: 'mux_naive', mux_kcp: 'mux_kcp'
        };
        const udpTunnelModes = ['udp', 'kcp', 'quic', 'tuic_quic', 'http3_masquerade', 'hysteria2_salamander', 'hysteria2_gecko', 'mux_h3', 'mux_quic', 'mux_kcp'];
        const tlsTunnelModes = ['websocket', 'http_obfs', 'grpc', 'wss', 'httpsmux', 'mux_wss', 'mux_h2', 'mux_h3', 'mux_quic', 'mux_grpc', 'mux_shadowtls', 'mux_reality', 'mux_anytls', 'mux_naive', 'quic', 'vless_reality', 'reality_grpc', 'reality_h2', 'reality_ws', 'shadowtls', 'shadowtls_ws', 'shadowtls_h2', 'tuic_quic', 'naive_https', 'naive_h2', 'http2_tls', 'http3_masquerade', 'hysteria2_salamander', 'hysteria2_gecko', 'anytls', 'anytls_h2', 'anytls_ws', 'ech_tls', 'ech_h2'];
        const tlsTransports = ['wss', 'httpsmux', 'quic', 'h2', 'h3', 'grpc', 'shadowtls', 'tuic', 'naive', 'anytls', 'ech', 'mux_wss', 'mux_h2', 'mux_h3', 'mux_quic', 'mux_grpc', 'mux_shadowtls', 'mux_reality', 'mux_anytls', 'mux_naive'];

        function syncTunnelOptions(preferred = {}) {
            const engine = document.getElementById('link-engine').value;
            const config = tunnelOptionMatrix[engine] || tunnelOptionMatrix.builtin;
            setSelectOptions(document.getElementById('link-transport'), config.transports, preferred.transport);
            setSelectOptions(document.getElementById('link-network'), config.networks, preferred.network);
            setSelectOptions(document.getElementById('link-tunnel-mode'), config.modes, preferred.mode);
            syncTransportTls();
            toggleEngineOptions();
            toggleObfsOptions();
        }

        function syncProfileModeOptions() {
            const engine = document.getElementById('profile-engine')?.value || 'builtin';
            const config = tunnelOptionMatrix[engine] || tunnelOptionMatrix.builtin;
            setSelectOptions(document.getElementById('profile-mode'), config.modes);
        }

        function syncTransportTls() {
            const transport = document.getElementById('link-transport').value;
            const tlsEl = document.getElementById('link-tls-enabled');
            if (tlsTransports.includes(transport)) tlsEl.checked = true;
            if (transport === 'udp') tlsEl.checked = false;
            toggleObfsOptions();
        }

        function syncNetworkMode() {
            const network = document.getElementById('link-network').value;
            const mode = document.getElementById('link-tunnel-mode');
            if (network === 'udp' && !udpTunnelModes.includes(mode.value)) mode.value = 'udp';
            if (network === 'tcp_udp') mode.value = 'tcp_udp';
            toggleObfsOptions();
        }

        function syncModeTransport() {
            const mode = document.getElementById('link-tunnel-mode').value;
            const transport = document.getElementById('link-transport');
            const network = document.getElementById('link-network');
            if (modeTransportMap[mode] && Array.from(transport.options).some(o => o.value === modeTransportMap[mode])) transport.value = modeTransportMap[mode];
            if (udpTunnelModes.includes(mode) && Array.from(network.options).some(o => o.value === 'udp')) network.value = 'udp';
            if (mode === 'tcp_udp' && Array.from(network.options).some(o => o.value === 'tcp_udp')) network.value = 'tcp_udp';
            syncTransportTls();
        }

        function toggleObfsOptions() {
            const mode = document.getElementById('link-tunnel-mode').value;
            const tls = document.getElementById('link-tls-enabled').checked;
            const section = document.getElementById('obfs-advanced-section');
            const tlsGroup = document.getElementById('tls-sni-group');
            const obfsModes = tlsTunnelModes.concat(['wsmux']);
            
            if (obfsModes.includes(mode) || tls) {
                section.classList.remove('hidden');
            } else {
                section.classList.add('hidden');
            }
            
            if (tls) {
                tlsGroup.classList.remove('hidden');
            } else {
                tlsGroup.classList.add('hidden');
            }
        }

        function toggleEasyMode() {
            const enabled = document.getElementById('link-easy-mode')?.checked;
            document.querySelectorAll('.advanced-link-field').forEach(el => el.classList.toggle('hidden', !!enabled));
            if (enabled) {
                const profileSelect = document.getElementById('link-profile');
                if (latestStatus.tunnel_profiles?.easy && profileSelect.value !== 'easy') {
                    profileSelect.value = 'easy';
                    applySelectedProfile();
                }
                document.getElementById('link-engine').value = 'builtin';
                syncTunnelOptions({ transport: 'websocket', network: 'tcp', mode: 'websocket' });
                document.getElementById('link-tls-enabled').checked = true;
                document.getElementById('link-pool-size').value = 80;
            }
            toggleObfsOptions();
        }

        function applySelectedProfile() {
            const profileId = document.getElementById('link-profile').value;
            const profile = latestStatus.tunnel_profiles?.[profileId];
            if (!profile) {
                syncTunnelOptions();
                return;
            }
            document.getElementById('link-engine').value = profile.engine || 'builtin';
            syncTunnelOptions({ transport: profile.transport || profile.tunnel_mode || 'tcp', network: profile.network || 'tcp', mode: profile.tunnel_mode || 'websocket' });
            document.getElementById('link-tls-enabled').checked = !!profile.tls_enabled;
            document.getElementById('link-pool-size').value = profile.pool_size || 100;
            document.getElementById('link-obfs-host').value = profile.obfs_host || 'speedtest.net';
            document.getElementById('link-obfs-path').value = profile.obfs_path || '/tunnel';
            document.getElementById('link-tls-sni').value = profile.tls_sni || profile.obfs_host || 'speedtest.net';
            document.getElementById('link-padding-min').value = profile.padding_min || 0;
            document.getElementById('link-padding-max').value = profile.padding_max || 0;
            document.getElementById('link-jitter-ms').value = profile.jitter_ms || 0;
            document.getElementById('link-keepalive').value = profile.keepalive_interval || 25;
            document.getElementById('link-xray-protocol').value = profile.xray_protocol || 'vless';
            document.getElementById('link-xray-security').value = profile.xray_security || 'reality';
            document.getElementById('link-xray-flow').value = profile.xray_flow || 'xtls-rprx-vision';
            document.getElementById('link-xray-uuid').value = profile.xray_uuid || '';
            document.getElementById('link-xray-sni').value = profile.xray_sni || 'www.microsoft.com';
            document.getElementById('link-xray-shortid').value = profile.xray_shortid || '';
            document.getElementById('link-xray-public-key').value = profile.xray_public_key || '';
            document.getElementById('link-xray-private-key').value = profile.xray_private_key || '';
            toggleObfsOptions();
            toggleEngineOptions();
        }

        function toggleEngineOptions() {
            const engine = document.getElementById('link-engine').value;
            document.getElementById('xray-options').classList.toggle('hidden', engine !== 'xray');
        }

        async function fetchRuntime() {
            if (!token) return;
            try {
                const [sessionsRes, processesRes, resourcesRes] = await Promise.all([
                    fetch('/api/runtime/sessions', { headers: { 'Authorization': `Bearer ${token}` } }),
                    fetch('/api/runtime/processes', { headers: { 'Authorization': `Bearer ${token}` } }),
                    fetch('/api/runtime/resources', { headers: { 'Authorization': `Bearer ${token}` } })
                ]);
                if (sessionsRes.ok) renderSessions((await sessionsRes.json()).sessions || []);
                if (processesRes.ok) renderProcesses((await processesRes.json()).processes || []);
                if (resourcesRes.ok) renderResources(await resourcesRes.json());
            } catch (err) {
                console.error('Runtime fetch failed', err);
            }
        }

        function renderResources(resources) {
            const threads = document.getElementById('resource-threads');
            const sessions = document.getElementById('resource-sessions');
            const rss = document.getElementById('resource-rss');
            if (threads) threads.innerText = resources.threads ?? 0;
            if (sessions) sessions.innerText = resources.active_tunnel_sessions ?? 0;
            if (rss) rss.innerText = `${((resources.rss_kb || 0) / 1024).toFixed(1)} MB`;
            const grid = document.getElementById('node-resource-grid');
            if (grid) {
                const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
                const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
                grid.innerHTML = (resources.nodes || []).map(node => {
                    const safeId = safeDomId(node.id || node.name || 'node');
                    const result = node.last_command_result?.result;
                    const resultText = result ? `${tx('آخرین پاک‌سازی', 'Last cleanup')}: ${esc(node.last_command_result.action)} | RSS ${((result.rss_kb || 0) / 1024).toFixed(1)} MB` : tx('پاک‌سازی ثبت نشده', 'No cleanup yet');
                    return `
                        <div class="node-resource-card" data-resource-node-id="${esc(node.id || node.name || '')}">
                            <h4><span>${esc(node.name)}</span><span class="status-pill"><span class="status-dot ${node.status === 'online' ? '' : 'offline'}"></span>${node.status === 'online' ? t('online') : t('offline')}</span></h4>
                            <div class="tag-row">
                                <span class="tag-pill">CPU ${esc(node.cpu)}%</span>
                                <span class="tag-pill">RAM ${esc(node.ram)}%</span>
                                <span class="tag-pill">${tx('تردها', 'Threads')} ${esc(node.threads)}</span>
                                <span class="tag-pill">${tx('فعال', 'Active')} ${esc(node.connections)}</span>
                            </div>
                            <div class="tag-row">
                                <span class="tag-pill tag-color-5">${tx('دانلود', 'Download')} ${(Number(node.rx_speed || 0) / divisor).toFixed(2)} ${trafficUnit}/s</span>
                                <span class="tag-pill tag-color-1">${tx('آپلود', 'Upload')} ${(Number(node.tx_speed || 0) / divisor).toFixed(2)} ${trafficUnit}/s</span>
                            </div>
                            <div class="node-resource-charts">
                                <div class="node-resource-chart"><canvas id="node-load-chart-${safeId}"></canvas></div>
                                <div class="node-resource-chart"><canvas id="node-traffic-chart-${safeId}"></canvas></div>
                            </div>
                            <small style="display:block; margin-top:10px; color: var(--text-secondary);">${resultText}</small>
                        </div>
                    `;
                }).join('') || `<span class="tag-pill">${tx('نودی برای نمایش نیست', 'No nodes to show')}</span>`;
                (resources.nodes || []).forEach(node => drawNodeResourceCharts(node, divisor, trafficUnit));
            }
        }

        function drawNodeResourceCharts(node, divisor, trafficUnit) {
            const rawId = String(node.id || node.name || 'node');
            const safeId = safeDomId(rawId);
            const loadCanvas = document.getElementById(`node-load-chart-${safeId}`);
            const trafficCanvas = document.getElementById(`node-traffic-chart-${safeId}`);
            nodeResourceCharts[rawId] = nodeResourceCharts[rawId] || {
                load: { canvas: loadCanvas, series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_ACTIVE, COLOR_UPLOAD] },
                traffic: { canvas: trafficCanvas, series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_DOWNLOAD, COLOR_UPLOAD] }
            };
            const item = nodeResourceCharts[rawId];
            item.load.canvas = loadCanvas;
            item.traffic.canvas = trafficCanvas;
            item.load.series[0].shift();
            item.load.series[0].push(Number(node.cpu || 0));
            item.load.series[1].shift();
            item.load.series[1].push(Number(node.ram || 0));
            item.traffic.series[0].shift();
            item.traffic.series[0].push(Number(node.rx_speed || 0) / divisor);
            item.traffic.series[1].shift();
            item.traffic.series[1].push(Number(node.tx_speed || 0) / divisor);
            if (loadCanvas) drawChart(item.load, '%', ['CPU', 'RAM']);
            if (trafficCanvas) drawChart(item.traffic, `${trafficUnit}/s`, [tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
        }

        function renderSessions(sessions) {
            const tbody = document.querySelector('#table-sessions tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            sessions.forEach(s => {
                const tr = document.createElement('tr');
                const isPanelSession = (s.source || 'panel') === 'panel';
                tr.innerHTML = `<td><code>${esc(s.id)}</code><br><small>${esc(s.node_name || 'Panel')}</small></td><td>${esc(s.link_id)}</td><td>${esc(s.target_port)}</td><td>${esc(s.age_seconds)}s</td><td>${esc(s.idle_seconds)}s</td><td>${isPanelSession ? `<button class="btn w-auto p-10" style="background: var(--danger);" onclick="closeSession('${esc(s.id)}')">${t('close')}</button>` : `<span class="tag-pill">${tx('روی نود', 'On node')}</span>`}</td>`;
                tbody.appendChild(tr);
            });
        }

        function renderProcesses(processes) {
            const tbody = document.querySelector('#table-processes tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            processes.forEach(p => {
                const tr = document.createElement('tr');
                tr.title = p.cmd || '';
                const isPanelProcess = (p.source || 'panel') === 'panel';
                tr.innerHTML = `<td><code>${esc(p.pid)}</code><br><small>${esc(p.node_name || 'Panel')}</small></td><td>${esc(p.name)}</td><td>${(Number(p.rss_kb || 0) / 1024).toFixed(1)} MB</td><td>${esc(p.threads)}</td><td>${esc(p.cpu_seconds)}s</td><td>${isPanelProcess ? `<button class="btn w-auto p-10" style="background: var(--danger);" onclick="terminateProcess(${Number(p.pid)})">SIGTERM</button>` : `<span class="tag-pill">${tx('نود', 'Node')}</span>`}</td>`;
                tbody.appendChild(tr);
            });
        }

        async function closeSession(id) {
            if (!confirm(tx('این سشن تانل بسته شود؟', 'Close this tunnel session?'))) return;
            const res = await fetch(`/api/runtime/sessions?id=${encodeURIComponent(id)}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) fetchRuntime();
        }

        async function terminateProcess(pid) {
            if (!confirm(`Send SIGTERM to process ${pid}?`)) return;
            const res = await fetch(`/api/runtime/processes?pid=${encodeURIComponent(pid)}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) fetchRuntime();
        }

        async function optimizeResources(action) {
            const scope = document.getElementById('resource-scope')?.value || 'all';
            const res = await fetch('/api/runtime/optimize', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, scope })
            });
            const data = await res.json();
            const box = document.getElementById('resource-result');
            if (box) {
                box.innerText = res.ok
                    ? `${tx('بهینه‌سازی انجام شد', 'Optimization completed')}: ${tx('سشن‌های بسته‌شده', 'closed sessions')} ${data.closed_idle_sessions || 0}, GC ${data.gc_collected || 0}, ${tx('فرمان نودها', 'node commands')} ${data.queued_nodes || 0}, RSS ${((data.rss_kb || 0) / 1024).toFixed(1)} MB`
                    : `${tx('خطا', 'Error')}: ${data.error || tx('ناشناخته', 'Unknown')}`;
            }
            if (res.ok) renderResources(data);
            fetchRuntime();
        }

        async function testLink(lid) {
            const res = await fetch(`/api/links/test?id=${encodeURIComponent(lid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) {
                const data = await res.json();
                alert(`${tx('تست اتصال', 'Connection test')}: ${data.success ? tx('فعال', 'LIVE') : tx('آماده نیست', 'NOT READY')}\\n${tx('نود داخلی', 'Internal')}: ${data.internal_live}\\n${tx('نود خارجی', 'External')}: ${data.external_live}\\n${tx('هسته', 'Engine')}: ${data.engine}`);
            }
        }

        async function showEngineConfig(lid) {
            const res = await fetch(`/api/links/engine-config?id=${encodeURIComponent(lid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) {
                const data = await res.json();
                document.getElementById('engine-config-content').value = JSON.stringify(data, null, 2);
                openModal('modal-show-config');
            }
        }

        document.getElementById('form-sync-xui')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.innerText = tx('در حال اتصال و همگام‌سازی...', 'Syncing...');

            const payload = {
                link_id: document.getElementById('sync-xui-link-id').value,
                url: document.getElementById('sync-xui-url').value,
                username: document.getElementById('sync-xui-username').value,
                password: document.getElementById('sync-xui-password').value
            };

            try {
                const res = await fetch('/api/sync/xui', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                const data = await res.json();
                if (res.ok) {
                    alert(`${tx('همگام‌سازی موفق!', 'Sync Successful!')}\n${data.added} ${tx('پورت جدید از مجموع', 'new ports added from total')} ${data.total} ${tx('پورت فعال پنل شما اضافه شد.', 'active ports in your panel.')}`);
                    closeModal('modal-sync-xui');
                    fetchStatus();
                } else {
                    alert(`${tx('خطا', 'Error')}: ${data.error || tx('شکست در ارتباط', 'Connection failed')}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                btn.disabled = false;
                btn.innerText = tx('شروع همگام‌سازی پورت‌ها', 'Start Syncing');
            }
        });

        async function testNodeConnection(nid) {
            const loading = document.getElementById('node-test-loading');
            const result = document.getElementById('node-test-result');
            if (loading) loading.style.display = 'flex';
            if (result) result.textContent = '';
            openModal('modal-node-test');
            try {
                const res = await fetch(`/api/nodes/test?id=${encodeURIComponent(nid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
                const data = await res.json();
                if (loading) loading.style.display = 'none';
                if (res.ok) {
                    if (result) result.textContent = data.result || 'No output';
                } else {
                    if (result) result.textContent = data.error || tx('خطا در تست ارتباط', 'Test failed');
                }
            } catch (err) { 
                if (loading) loading.style.display = 'none';
                if (result) result.textContent = tx('خطا در ارتباط', 'Connection error');
            }
        }

        function showGeneratedNodeCredentials(created) {
            const list = Array.isArray(created) ? created : [created];
            const first = list[0] || {};
            const tokenEl = document.getElementById('generated-token-input');
            const keyEl = document.getElementById('generated-private-key-input');
            const setupEl = document.getElementById('generated-node-setup-input');
            if (tokenEl) tokenEl.value = first.token || '';
            if (keyEl) keyEl.value = first.private_key || '';
            if (setupEl) {
                setupEl.value = list.map(n => [
                    `Node: ${n.name || n.node_id || 'node'}`,
                    `Node token: ${n.token || ''}`,
                    `Node private key: ${n.private_key || ''}`
                ].join('\\n')).join('\\n\\n');
            }
            openModal('modal-show-token');
        }

        async function copyFieldValue(id) {
            const el = document.getElementById(id);
            const value = el?.value || el?.textContent || '';
            if (!value) return;
            try {
                await navigator.clipboard.writeText(value);
                alert(tx('کپی شد.', 'Copied.'));
            } catch (err) {
                if (el?.select) {
                    el.select();
                    document.execCommand('copy');
                    alert(tx('کپی شد.', 'Copied.'));
                }
            }
        }

        async function openNodeSecrets(nid) {
            try {
                const res = await fetch(`/api/nodes/secrets?id=${encodeURIComponent(nid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
                const data = await res.json();
                if (!res.ok) {
                    alert(data.error || tx('امکان دریافت مشخصات نود نیست.', 'Could not load node credentials.'));
                    return;
                }
                showGeneratedNodeCredentials({
                    node_id: data.node_id,
                    name: data.name,
                    token: data.token,
                    private_key: data.private_key
                });
            } catch (err) {
                alert(tx('خطا در دریافت مشخصات نود', 'Node credential loading failed'));
            }
        }

        async function autoAddNodes() {
            const res = await fetch('/api/nodes/auto', { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) {
                const data = await res.json();
                if (data.created.length) {
                    showGeneratedNodeCredentials(data.created);
                } else {
                    alert('Starter nodes already exist.');
                }
                fetchStatus();
            }
        }

        async function saveProfile() {
            const engine = document.getElementById('profile-engine')?.value || 'builtin';
            const mode = document.getElementById('profile-mode').value;
            const profileConfig = tunnelOptionMatrix[engine] || tunnelOptionMatrix.builtin;
            const mappedTransport = modeTransportMap[mode];
            const transport = (mappedTransport && profileConfig.transports.some(([value]) => value === mappedTransport)) ? mappedTransport : profileConfig.transports[0]?.[0] || 'tcp';
            const network = udpTunnelModes.includes(mode) ? 'udp' : (mode === 'tcp_udp' ? 'tcp_udp' : 'tcp');
            const payload = {
                name: document.getElementById('profile-name').value || 'Custom Profile',
                engine,
                tunnel_mode: mode,
                transport,
                network,
                pool_size: parseInt(document.getElementById('profile-pool').value || '120'),
                obfs_host: document.getElementById('profile-host').value,
                obfs_path: document.getElementById('profile-path').value,
                jitter_ms: parseInt(document.getElementById('profile-jitter').value || '0'),
                tls_enabled: tlsTunnelModes.includes(mode) || tlsTransports.includes(transport),
                padding_min: 0,
                padding_max: 96,
                keepalive_interval: 25
            };
            const res = await fetch('/api/profiles', { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            if (res.ok) {
                latestStatus.tunnel_profiles = (await res.json()).profiles;
                populateProfiles(latestStatus.tunnel_profiles);
                alert(tx('پروفایل ذخیره شد.', 'Profile saved.'));
            }
        }

        function exportProfiles() {
            window.location.href = `/api/profiles/export?token=${token}`;
        }

        async function importProfiles() {
            try {
                const payload = JSON.parse(document.getElementById('profile-import').value);
                const res = await fetch('/api/profiles/import', { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (res.ok) {
                    latestStatus.tunnel_profiles = (await res.json()).profiles;
                    populateProfiles(latestStatus.tunnel_profiles);
                    alert(tx('پروفایل‌ها وارد شدند.', 'Profiles imported.'));
                }
            } catch (err) {
                alert(tx('JSON پروفایل نامعتبر است.', 'Invalid profile JSON.'));
            }
        }

        async function deleteNode(nid) {
            if (!confirm(tx('آیا مایل به حذف این نود هستید؟ تمام تانل‌های مربوطه نیز حذف خواهند شد.', 'Delete this node? All related tunnels will also be removed.'))) return;
            const res = await fetch(`/api/nodes?id=${nid}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) fetchStatus();
        }

        async function deleteLink(lid) {
            if (!confirm(tx('آیا مایل به حذف این تانل هستید؟', 'Delete this tunnel?'))) return;
            const res = await fetch(`/api/links?id=${lid}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) fetchStatus();
        }

        async function addPortMapping(lid) {
            const userPort = document.getElementById(`add-user-port-${lid}`).value;
            const targetPort = document.getElementById(`add-target-port-${lid}`).value;
            if (!userPort || !targetPort) {
                alert(tx('لطفا هر دو پورت یا بازه را وارد کنید.', 'Please enter both ports or ranges.'));
                return;
            }
            const res = await fetch(`/api/links/ports?id=${lid}`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_port: userPort.trim(), target_port: targetPort.trim() })
            });
            if (res.ok) {
                fetchStatus();
            } else {
                const data = await res.json();
                alert(`${tx('خطا', 'Error')}: ${data.error || data.message || tx('ثبت ناموفق', 'Save failed')}`);
            }
        }

        async function editPortMapping(lid, index, currentUserPort, currentTargetPort) {
            const userPort = prompt(tx('پورت ورودی داخلی جدید را وارد کنید:', 'Enter the new internal input port:'), currentUserPort);
            if (userPort === null) return;
            const targetPort = prompt(tx('پورت مقصد خارجی جدید را وارد کنید:', 'Enter the new external target port:'), currentTargetPort);
            if (targetPort === null) return;
            const res = await fetch(`/api/links/ports/edit?id=${encodeURIComponent(lid)}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ index, user_port: userPort.trim(), target_port: targetPort.trim() })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                fetchStatus();
            } else {
                alert(`${tx('خطا در ویرایش پورت', 'Port edit failed')}: ${data.error || data.message || tx('ثبت ناموفق', 'Save failed')}`);
            }
        }

        async function testPortPayload(lid, index) {
            if (!latestStatus?.capabilities?.payload_test_client) {
                alert(tx('پنل در حال اجرا هنوز نسخه جدید تست پکیج را ندارد. پنل را با آخرین پکیج آفلاین آپدیت و container را restart کنید.', 'The running panel does not have the new payload test backend yet. Update the panel with the latest offline package and restart the container.'));
                return;
            }
            const currentLink = latestStatus?.links?.[lid];
            if (!currentLink || !Array.isArray(currentLink.ports) || index < 0 || index >= currentLink.ports.length) {
                alert(`${tx('اطلاعات تانل یا پورت در صفحه قدیمی است. وضعیت را دوباره دریافت می‌کنم؛ چند ثانیه بعد دوباره تست کنید.', 'The tunnel or port data on this screen is stale. Refreshing status; try again in a few seconds.')}\\nlink=${lid || '-'} index=${index}`);
                fetchStatus();
                return;
            }
            const sizeInput = prompt(tx('حجم پکیج تست را به مگابایت وارد کنید:', 'Enter payload test size in MB:'), '4');
            if (sizeInput === null) return;
            const sizeMb = Math.max(1, Math.min(32, parseInt(sizeInput, 10) || 4));
            openModal('loading-overlay');
            const loadingText = document.querySelector('#loading-overlay h3');
            const oldLoadingText = loadingText?.innerText;
            if (loadingText) loadingText.innerText = tx('در حال انتقال پکیج تست از مسیر تانل...', 'Transferring test payload through the tunnel...');
            try {
                const res = await fetch('/api/links/payload-test', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ id: lid, link_id: lid, index, size_mb: sizeMb })
                });
                const raw = await res.text();
                let data = {};
                try {
                    data = raw ? JSON.parse(raw) : {};
                } catch (err) {
                    data = { error: `${tx('پاسخ غیر JSON از سرور', 'Non-JSON server response')}: ${raw.slice(0, 500)}` };
                }
                if (res.ok && data.success) {
                    const transfer = data.transfer || {};
                    alert(`${tx('تست واقعی تانل موفق بود', 'Real tunnel payload test succeeded')}\\n${tx('مسیر اصلی', 'Main mapping')}: ${data.user_port} -> ${data.target_port}\\n${tx('مسیر تست موقت', 'Temporary test path')}: ${data.test_user_port} -> ${data.test_target_port}\\n${tx('حجم', 'Size')}: ${data.size_mb} MB\\n${tx('دریافت شده', 'Received')}: ${formatBytes(transfer.bytes_received || 0)}\\n${tx('زمان', 'Time')}: ${transfer.elapsed_seconds}s\\n${tx('سرعت', 'Speed')}: ${transfer.mbps} Mbps`);
                } else {
                    const transfer = data.transfer || {};
                    const detail = transfer.bytes_sent !== undefined
                        ? `\\n${tx('ارسال', 'Sent')}: ${formatBytes(transfer.bytes_sent || 0)} | ${tx('دریافت', 'Received')}: ${formatBytes(transfer.bytes_received || 0)}\\nSHA sent: ${(transfer.sha256_sent || '').slice(0, 16)}...\\nSHA recv: ${(transfer.sha256_received || '').slice(0, 16)}...`
                        : '';
                    const hint = data.hint ? `\\n${data.hint}` : '';
                    const available = Array.isArray(data.available_links) && data.available_links.length
                        ? `\\n${tx('تانل‌های موجود روی سرور', 'Available server tunnels')}: ${data.available_links.map(l => `${l.name || l.id} (${l.id})`).join(', ')}`
                        : '';
                    const httpInfo = res.ok ? '' : `\\nHTTP ${res.status} ${res.statusText || ''}`;
                    alert(`${tx('تست واقعی تانل ناموفق بود', 'Real tunnel payload test failed')}${httpInfo}\\n${data.error || tx('خطای نامشخص', 'Unknown error')}\\n${data.echo_result?.error || ''}${detail}${hint}${available}`);
                }
            } catch (err) {
                alert(`${tx('تست واقعی تانل ناموفق بود', 'Real tunnel payload test failed')}\\n${err.message || err}`);
            } finally {
                if (loadingText && oldLoadingText) loadingText.innerText = oldLoadingText;
                closeModal('loading-overlay');
                fetchStatus();
            }
        }

        async function deletePortMapping(lid, index) {
            if (!confirm(tx('آیا مایل به حذف این پورت فورواردینگ هستید؟', 'Delete this port forwarding rule?'))) return;
            const res = await fetch(`/api/links/ports?id=${lid}&index=${index}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) fetchStatus();
        }

        let currentEditNodeId = null;
        let currentEditLinkId = null;

        function setNodeFormMode(mode) {
            const editing = mode === 'edit';
            const title = document.getElementById('node-modal-title');
            const submit = document.getElementById('node-submit-btn');
            if (title) title.innerText = editing ? tx('ویرایش نود', 'Edit node') : tx('افزودن نود جدید', 'Add node');
            if (submit) submit.innerText = editing ? tx('ذخیره تغییرات', 'Save changes') : tx('ثبت نود جدید', 'Save node');
        }

        function openNewNodeModal() {
            currentEditNodeId = null;
            document.getElementById('form-add-node').reset();
            setNodeFormMode('add');
            openModal('modal-add-node');
        }

        function editNode(nid) {
            const nodes = latestStatus?.nodes || {};
            if (!nodes[nid]) return;
            const n = nodes[nid];
            currentEditNodeId = nid;
            document.getElementById('node-name').value = n.name || '';
            document.getElementById('node-role').value = n.role || 'internal';
            document.getElementById('node-ip').value = n.ip || '';
            document.getElementById('node-tags').value = parseTags(n.tags || []).join(', ');
            setNodeFormMode('edit');
            openModal('modal-add-node');
        }

        async function togglePauseNode(nid) {
            const res = await fetch(`/api/nodes/toggle-pause?id=${encodeURIComponent(nid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) fetchStatus();
            else alert(tx('عملیات ناموفق بود.', 'Operation failed.'));
        }

        function populateSshNodeSelect(selected = '') {
            const select = document.getElementById('ssh-node-id');
            if (!select) return;
            select.innerHTML = '';
            Object.entries(latestStatus?.nodes || {}).forEach(([nid, node]) => {
                const opt = document.createElement('option');
                opt.value = nid;
                opt.innerText = `${node.name || nid} (${node.ip || '-'})`;
                select.appendChild(opt);
            });
            if (selected && latestStatus?.nodes?.[selected]) select.value = selected;
        }

        function openNodeSshModal(nid = '') {
            populateSshNodeSelect(nid);
            fillSshFromNode();
            closeSshTerminal(true);
            document.getElementById('ssh-output').textContent = '';
            document.getElementById('ssh-status').innerText = tx('آماده اتصال', 'Ready');
            openModal('modal-node-ssh');
            setTimeout(() => document.getElementById('ssh-output')?.focus(), 120);
        }

        function fillSshFromNode() {
            const nid = document.getElementById('ssh-node-id')?.value;
            const node = latestStatus?.nodes?.[nid] || {};
            const saved = latestStatus?.ssh_saved_nodes?.[nid] || {};
            document.getElementById('ssh-host').value = saved.host || node.ip || '';
            document.getElementById('ssh-port').value = saved.port || 22;
            document.getElementById('ssh-username').value = saved.username || 'root';
            document.getElementById('ssh-auth-method').value = saved.auth_method || 'password';
            document.getElementById('ssh-password').placeholder = saved.has_password ? tx('رمز ذخیره شده است؛ برای تغییر وارد کنید', 'Saved; enter to change') : '';
            document.getElementById('ssh-private-key').placeholder = saved.has_private_key ? tx('کلید ذخیره شده است؛ برای تغییر وارد کنید', 'Saved; enter to change') : '';
            document.getElementById('ssh-password').value = '';
            document.getElementById('ssh-private-key').value = '';
            toggleSshAuthFields();
        }

        function toggleSshAuthFields() {
            const method = document.getElementById('ssh-auth-method')?.value || 'password';
            document.getElementById('ssh-password-group')?.classList.toggle('hidden', method !== 'password');
            document.getElementById('ssh-key-group')?.classList.toggle('hidden', method !== 'key');
        }

        function sshPayloadBase() {
            return {
                node_id: document.getElementById('ssh-node-id').value,
                host: document.getElementById('ssh-host').value,
                port: parseInt(document.getElementById('ssh-port').value || '22'),
                username: document.getElementById('ssh-username').value,
                auth_method: document.getElementById('ssh-auth-method').value,
                password: document.getElementById('ssh-password').value,
                private_key: document.getElementById('ssh-private-key').value,
                timeout: parseInt(document.getElementById('ssh-timeout').value || '15')
            };
        }

        async function saveSshOnly() {
            const res = await fetch('/api/nodes/ssh/save', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(sshPayloadBase())
            });
            document.getElementById('ssh-status').innerText = res.ok ? tx('ذخیره شد', 'Saved') : tx('ذخیره ناموفق بود', 'Save failed');
            if (res.ok) fetchStatus();
        }

        function appendSshOutput(text) {
            if (!text) return;
            const terminal = document.getElementById('ssh-output');
            terminal.textContent += text;
            terminal.scrollTop = terminal.scrollHeight;
        }

        async function pollSshTerminal() {
            if (!sshTerminalSessionId) return;
            try {
                const res = await fetch('/api/nodes/ssh/read', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sshTerminalSessionId })
                });
                const data = await res.json().catch(() => ({}));
                if (res.ok) {
                    appendSshOutput(data.output || '');
                    if (!data.alive) {
                        document.getElementById('ssh-status').innerText = tx('اتصال بسته شد', 'Session closed');
                        closeSshTerminal(true);
                    }
                }
            } catch (err) {}
        }

        async function sendSshTerminalInput(data) {
            if (!sshTerminalSessionId || !data) return;
            try {
                const res = await fetch('/api/nodes/ssh/write', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sshTerminalSessionId, data })
                });
                const result = await res.json().catch(() => ({}));
                if (res.ok) {
                    appendSshOutput(result.output || '');
                    if (!result.alive) closeSshTerminal(true);
                } else {
                    appendSshOutput(`\\n${result.error || 'SSH write failed'}\\n`);
                }
            } catch (err) {
                appendSshOutput(`\\n${err.message}\\n`);
            }
        }

        async function closeSshTerminal(silent = false) {
            const sessionId = sshTerminalSessionId;
            sshTerminalSessionId = null;
            if (sshTerminalPoller) {
                clearInterval(sshTerminalPoller);
                sshTerminalPoller = null;
            }
            if (sessionId) {
                try {
                    await fetch('/api/nodes/ssh/close', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: sessionId })
                    });
                } catch (err) {}
            }
            if (!silent) document.getElementById('ssh-status').innerText = tx('قطع شد', 'Disconnected');
        }

        document.getElementById('ssh-output')?.addEventListener('keydown', (e) => {
            if (!sshTerminalSessionId) return;
            e.preventDefault();
            const specialKeys = {
                ArrowUp: '\\x1b[A',
                ArrowDown: '\\x1b[B',
                ArrowRight: '\\x1b[C',
                ArrowLeft: '\\x1b[D',
                Home: '\\x1b[H',
                End: '\\x1b[F',
                Delete: '\\x1b[3~',
                PageUp: '\\x1b[5~',
                PageDown: '\\x1b[6~',
            };
            if (e.key === 'Enter') sendSshTerminalInput('\\r');
            else if (e.key === 'Backspace') sendSshTerminalInput('\\x7f');
            else if (e.key === 'Tab') sendSshTerminalInput('\\t');
            else if (specialKeys[e.key]) sendSshTerminalInput(specialKeys[e.key]);
            else if (e.ctrlKey && e.key.toLowerCase() === 'c') sendSshTerminalInput('\\u0003');
            else if (e.ctrlKey && e.key.toLowerCase() === 'd') sendSshTerminalInput('\\u0004');
            else if (e.ctrlKey && e.key.toLowerCase() === 'l') {
                document.getElementById('ssh-output').textContent = '';
                sendSshTerminalInput('\\f');
            } else if (e.key.length === 1) sendSshTerminalInput(e.key);
        });

        document.getElementById('ssh-output')?.addEventListener('paste', (e) => {
            if (!sshTerminalSessionId) return;
            e.preventDefault();
            const text = e.clipboardData?.getData('text') || '';
            if (text) sendSshTerminalInput(text.replace(/\\n/g, '\\r'));
        });

        function suggestNextLinkPorts() {
            const used = new Set();
            Object.values(latestStatus?.links || {}).forEach(link => {
                [link.bridge_port, link.sync_port].forEach(port => {
                    const numericPort = parseInt(port);
                    if (numericPort > 0) used.add(numericPort);
                });
                (link.ports || []).forEach(mapping => {
                    const numericPort = parseInt(mapping.user_port);
                    if (numericPort > 0) used.add(numericPort);
                });
            });
            let bridgePort = 7000;
            while (used.has(bridgePort) || used.has(bridgePort + 1)) bridgePort += 2;
            setLinkFormValue('link-bridge-port', bridgePort);
            setLinkFormValue('link-sync-port', bridgePort + 1);
        }

        async function smartTestSelectedNodes() {
            const internalId = document.getElementById('link-iran-node').value;
            const externalId = document.getElementById('link-foreign-node').value;
            const resultEl = document.getElementById('smart-test-result');
            if (!internalId || !externalId) {
                alert(tx('ابتدا دو نود را انتخاب کنید.', 'Choose both nodes first.'));
                return;
            }
            resultEl.innerText = tx('در حال تست هوشمند مسیر...', 'Running smart path test...');
            const res = await fetch('/api/links/smart-test', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ internal_node_id: internalId, external_node_id: externalId })
            });
            const data = await res.json();
            if (!res.ok) {
                resultEl.innerText = data.error || tx('تست ناموفق بود', 'Test failed');
                return;
            }
            if (data.recommended_profile_id && latestStatus.tunnel_profiles?.[data.recommended_profile_id]) {
                document.getElementById('link-profile').value = data.recommended_profile_id;
                applySelectedProfile();
            }
            const ip = data.internal?.ping?.avg_ms ?? '∞';
            const ep = data.external?.ping?.avg_ms ?? '∞';
            resultEl.innerText = `${tx('پیشنهاد', 'Recommended')}: ${data.recommended_profile?.name || data.recommended_profile_id} | ${ip}ms / ${ep}ms`;
        }

        async function quickSpaceTunnel() {
            const internalId = document.getElementById('link-iran-node').value;
            const externalId = document.getElementById('link-foreign-node').value;
            if (!internalId || !externalId) {
                alert(tx('ابتدا دو نود را انتخاب کنید.', 'Choose both nodes first.'));
                return;
            }
            suggestNextLinkPorts();
            const internalNode = latestStatus.nodes?.[internalId] || {};
            const externalNode = latestStatus.nodes?.[externalId] || {};
            const payload = {
                name: `Space-${internalNode.name || 'internal'}-${externalNode.name || 'external'}`.slice(0, 90),
                profile_id: 'easy',
                tags: ['space', 'quick'],
                internal_node_id: internalId,
                external_node_id: externalId,
                engine: 'builtin',
                transport: 'websocket',
                network: 'tcp',
                bridge_port: parseInt(document.getElementById('link-bridge-port').value || '7000'),
                sync_port: parseInt(document.getElementById('link-sync-port').value || '7001'),
                pool_size: 24,
                tunnel_mode: 'websocket',
                tls_enabled: true,
                tls_sni: 'speedtest.net',
                obfs_host: 'speedtest.net',
                obfs_path: '/assets/ws',
                padding_min: 0,
                padding_max: 32,
                jitter_ms: 0,
                keepalive_interval: 25
            };
            const res = await fetch('/api/links', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                closeModal('modal-add-link');
                fetchStatus();
            } else {
                alert(`${tx('خطا در ایجاد تانل', 'Tunnel creation error')}: ${data.error || data.message || tx('ثبت ناموفق', 'Save failed')}`);
            }
        }

        function openNewLinkModal() {
            currentEditLinkId = null;
            const form = document.getElementById('form-add-link');
            form.reset();
            populateLinkNodeSelects(latestStatus?.nodes || {}, { preserveSelection: false });
            document.getElementById('link-modal-title').innerText = tx('ایجاد تانل (لینک) جدید', 'Create new tunnel link');
            document.getElementById('link-submit-button').innerText = tx('ایجاد تانل', 'Create tunnel');
            document.getElementById('link-profile').value = 'custom';
            document.getElementById('link-tags').value = '';
            document.getElementById('link-easy-mode').checked = true;
            syncTunnelOptions({ transport: 'tcp', network: 'tcp', mode: 'tcp' });
            suggestNextLinkPorts();
            toggleEasyMode();
            openModal('modal-add-link');
        }

        function setLinkFormValue(id, value) {
            const el = document.getElementById(id);
            if (!el) return;
            if (el.type === 'checkbox') el.checked = !!value;
            else el.value = value ?? '';
        }

        function editLink(lid) {
            const link = latestStatus?.links?.[lid];
            if (!link) return;
            currentEditLinkId = lid;
            document.getElementById('link-modal-title').innerText = tx('ویرایش تانل', 'Edit tunnel');
            document.getElementById('link-submit-button').innerText = tx('ذخیره تغییرات تانل', 'Save tunnel changes');
            populateLinkNodeSelects(latestStatus?.nodes || {}, { preserveSelection: false });
            setLinkFormValue('link-name', link.name || '');
            setLinkFormValue('link-profile', link.profile_id || 'custom');
            setLinkFormValue('link-tags', parseTags(link.tags || []).join(', '));
            setLinkFormValue('link-easy-mode', false);
            setLinkFormValue('link-iran-node', link.internal_node_id || link.iran_node_id || '');
            setLinkFormValue('link-foreign-node', link.external_node_id || link.foreign_node_id || '');
            setLinkFormValue('link-engine', link.engine || 'builtin');
            syncTunnelOptions({ transport: link.transport || link.tunnel_mode || 'tcp', network: link.network || 'tcp', mode: link.tunnel_mode || 'tcp' });
            setLinkFormValue('link-bridge-port', link.bridge_port || 7000);
            setLinkFormValue('link-sync-port', link.sync_port || 7001);
            setLinkFormValue('link-pool-size', link.pool_size || 100);
            setLinkFormValue('link-tls-enabled', !!link.tls_enabled);
            setLinkFormValue('link-tls-sni', link.tls_sni || link.obfs_host || 'speedtest.net');
            setLinkFormValue('link-obfs-host', link.obfs_host || 'speedtest.net');
            setLinkFormValue('link-obfs-path', link.obfs_path || '/tunnel');
            setLinkFormValue('link-padding-min', link.padding_min || 0);
            setLinkFormValue('link-padding-max', link.padding_max || 0);
            setLinkFormValue('link-jitter-ms', link.jitter_ms || 0);
            setLinkFormValue('link-keepalive', link.keepalive_interval || 25);
            setLinkFormValue('link-xray-protocol', link.xray_protocol || 'vless');
            setLinkFormValue('link-xray-security', link.xray_security || 'reality');
            setLinkFormValue('link-xray-flow', link.xray_flow || 'xtls-rprx-vision');
            setLinkFormValue('link-xray-uuid', link.xray_uuid || '');
            setLinkFormValue('link-xray-sni', link.xray_sni || 'www.microsoft.com');
            setLinkFormValue('link-xray-shortid', link.xray_shortid || '');
            setLinkFormValue('link-xray-public-key', link.xray_public_key || '');
            setLinkFormValue('link-xray-private-key', link.xray_private_key || '');
            toggleObfsOptions();
            toggleEasyMode();
            openModal('modal-add-link');
        }

        async function togglePauseLink(lid) {
            const res = await fetch(`/api/links/toggle-pause?id=${encodeURIComponent(lid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) fetchStatus();
            else alert(tx('عملیات ناموفق بود.', 'Operation failed.'));
        }

        document.getElementById('form-add-node').addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                name: document.getElementById('node-name').value,
                role: document.getElementById('node-role').value,
                ip: document.getElementById('node-ip').value,
                tags: parseTags(document.getElementById('node-tags').value)
            };
            
            let url = '/api/nodes';
            if (currentEditNodeId) {
                url = '/api/nodes/edit';
                payload.id = currentEditNodeId;
            }

            const res = await fetch(url, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                const data = await res.json();
                closeModal('modal-add-node');
                document.getElementById('form-add-node').reset();
                
                if (!currentEditNodeId) {
                    showGeneratedNodeCredentials(data);
                }
                currentEditNodeId = null;
                setNodeFormMode('add');
                fetchStatus();
            } else {
                alert(tx('عملیات ناموفق بود.', 'Operation failed.'));
            }
        });

        document.getElementById('form-node-ssh').addEventListener('submit', async (e) => {
            e.preventDefault();
            const statusEl = document.getElementById('ssh-status');
            const outEl = document.getElementById('ssh-output');
            await closeSshTerminal(true);
            statusEl.innerText = tx('در حال اتصال ترمینال...', 'Opening terminal...');
            outEl.textContent = '';
            const payload = {
                ...sshPayloadBase(),
                save: document.getElementById('ssh-save').checked
            };
            const res = await fetch('/api/nodes/ssh/start', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                sshTerminalSessionId = data.session_id;
                statusEl.innerText = data.alive ? tx('ترمینال متصل است', 'Terminal connected') : tx('اتصال بسته شد', 'Session closed');
                appendSshOutput(data.output || '');
                sshTerminalPoller = setInterval(pollSshTerminal, 900);
                outEl.focus();
                fetchStatus();
            } else {
                statusEl.innerText = tx('اتصال ناموفق بود', 'Connection failed');
                outEl.textContent = data.error || tx('خطا در ارتباط SSH', 'SSH error');
            }
        });

        document.getElementById('form-add-link').addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!document.getElementById('link-iran-node').value || !document.getElementById('link-foreign-node').value) {
                alert(tx('برای ساخت تانل باید حداقل یک نود داخلی و یک نود خارجی ثبت شده باشد.', 'At least one internal node and one external node are required to create a tunnel.'));
                return;
            }
            const payload = {
                name: document.getElementById('link-name').value,
                profile_id: document.getElementById('link-profile').value,
                tags: parseTags(document.getElementById('link-tags').value),
                internal_node_id: document.getElementById('link-iran-node').value,
                external_node_id: document.getElementById('link-foreign-node').value,
                engine: document.getElementById('link-engine').value,
                transport: document.getElementById('link-transport').value,
                network: document.getElementById('link-network').value,
                bridge_port: parseInt(document.getElementById('link-bridge-port').value),
                sync_port: parseInt(document.getElementById('link-sync-port').value),
                pool_size: parseInt(document.getElementById('link-pool-size').value),
                tunnel_mode: document.getElementById('link-tunnel-mode').value,
                tls_enabled: document.getElementById('link-tls-enabled').checked,
                tls_sni: document.getElementById('link-tls-sni').value,
                obfs_host: document.getElementById('link-obfs-host').value,
                obfs_path: document.getElementById('link-obfs-path').value,
                padding_min: parseInt(document.getElementById('link-padding-min').value || '0'),
                padding_max: parseInt(document.getElementById('link-padding-max').value || '0'),
                jitter_ms: parseInt(document.getElementById('link-jitter-ms').value || '0'),
                keepalive_interval: parseInt(document.getElementById('link-keepalive').value || '25'),
                xray_protocol: document.getElementById('link-xray-protocol').value,
                xray_security: document.getElementById('link-xray-security').value,
                xray_flow: document.getElementById('link-xray-flow').value,
                xray_uuid: document.getElementById('link-xray-uuid').value,
                xray_sni: document.getElementById('link-xray-sni').value,
                xray_shortid: document.getElementById('link-xray-shortid').value,
                xray_public_key: document.getElementById('link-xray-public-key').value,
                xray_private_key: document.getElementById('link-xray-private-key').value
            };
            let url = '/api/links';
            if (currentEditLinkId) {
                url = '/api/links/edit';
                payload.id = currentEditLinkId;
            }
            const res = await fetch(url, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                closeModal('modal-add-link');
                document.getElementById('form-add-link').reset();
                currentEditLinkId = null;
                fetchStatus();
            } else {
                const data = await res.json();
                alert(`${tx('خطا در ایجاد تانل', 'Tunnel creation error')}: ${data.message || tx('ثبت ناموفق', 'Save failed')}`);
            }
        });

        document.getElementById('form-settings-pass').addEventListener('submit', async (e) => {
            e.preventDefault();
            const u = document.getElementById('setting-username').value;
            const p = document.getElementById('setting-password').value;
            const res = await fetch('/api/settings/password', {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username: u, password: p })
            });
            if (res.ok) {
                alert(tx('مشخصات ورود با موفقیت بروزرسانی شد.', 'Login credentials updated successfully.'));
                document.getElementById('setting-password').value = '';
            } else {
                alert(tx('خطا در ثبت مشخصات.', 'Could not save credentials.'));
            }
        });

        document.getElementById('form-settings-network').addEventListener('submit', async (e) => {
            e.preventDefault();
            const disable_ipv6 = document.getElementById('setting-disable-ipv6').checked;
            const engine_restart_interval = parseInt(document.getElementById('setting-engine-restart-interval').value) || 0;
            
            const res = await fetch('/api/settings/network', {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ disable_ipv6, engine_restart_interval })
            });
            if (res.ok) {
                alert(tx('تنظیمات شبکه با موفقیت بروزرسانی و بر روی سرور اعمال شد.', 'Network settings applied successfully.'));
                fetchStatus();
            } else {
                alert(tx('خطا در ثبت تنظیمات.', 'Could not save settings.'));
            }
        });
        
        document.getElementById('form-settings-display').addEventListener('submit', (e) => {
            e.preventDefault();
            const unit = document.getElementById('setting-traffic-unit').value;
            localStorage.setItem('trafficUnit', unit);
            alert(tx('تنظیمات نمایش ذخیره شد.', 'Display settings saved.'));
            updateDashboard(latestStatus);
            renderNodes(latestStatus?.nodes || {});
        });

        function renderEngineManager(engines) {
            const grid = document.getElementById('engine-manager-grid');
            if (!grid) return;
            const order = ['xray', 'singbox', 'hysteria2', 'tuic', 'naiveproxy', 'shadowtls', 'gost', 'backhaul', 'rathole', 'chisel', 'frp', 'brook', 'mieru', 'muxquantum'];
            grid.innerHTML = order.map(engine => {
                const info = engines?.[engine] || {};
                const status = info.installed ? (info.enabled ? tx('آماده', 'Ready') : tx('غیرفعال', 'Disabled')) : tx('نصب نشده', 'Missing');
                const color = info.installed ? (info.enabled ? 'text-success' : 'text-warning') : 'text-danger';
                return `
                    <div style="padding:14px; border:1px solid var(--border-card); border-radius:8px;">
                        <div class="flex-between mb-20">
                            <h4>${esc(engine)}</h4>
                            <span class="${color}">${status}</span>
                        </div>
                        <div class="tag-row">
                            <span class="tag-pill">${esc(info.version || '-')}</span>
                            <span class="tag-pill">${esc(info.repo || 'builtin')}</span>
                        </div>
                        <div class="flex-between gap-10 mt-20" style="justify-content:flex-start; flex-wrap:wrap;">
                            <button class="btn w-auto p-10" onclick="installEngine('${engine}')" ${engine === 'muxquantum' ? 'disabled' : ''}>${tx('آپدیت از گیت‌هاب', 'GitHub update')}</button>
                            <button class="btn w-auto p-10" onclick="controlEngine('${engine}', 'stop')" ${engine === 'muxquantum' ? 'disabled' : ''}>${tx('توقف', 'Stop')}</button>
                            <button class="btn w-auto p-10" onclick="controlEngine('${engine}', 'start')" ${engine === 'muxquantum' ? 'disabled' : ''}>${tx('ادامه', 'Resume')}</button>
                            <button class="btn w-auto p-10" onclick="controlEngine('${engine}', 'restart')" ${engine === 'muxquantum' ? 'disabled' : ''}>${tx('ریست', 'Restart')}</button>
                            <button class="btn w-auto p-10" onclick="healthCheckEngine('${engine}')">${tx('تست سلامت', 'Health test')}</button>
                        </div>
                        <input id="engine-upload-${engine}" type="file" class="form-input mt-20" accept=".zip,.gz,.tgz,.xz,.txz,.tar.gz,.tar.xz">
                        <button class="btn w-auto p-10 mt-20" onclick="uploadEngine('${engine}')" ${engine === 'muxquantum' ? 'disabled' : ''}>${tx('آپدیت دستی از فایل', 'Manual file update')}</button>
                        <small id="engine-health-${engine}" style="display:block; margin-top:10px; color: var(--text-secondary); line-height:1.7;"></small>
                    </div>
                `;
            }).join('');
        }

        async function installEngine(engineType) {
            const version = 'latest';
            
            if (!confirm(tx(`آیا از نصب/بروزرسانی هسته ${engineType} نسخه ${version} اطمینان دارید؟\nاین عملیات ممکن است چند دقیقه زمان ببرد.`, `Are you sure you want to install/update ${engineType} to version ${version}?\nThis may take a few minutes.`))) return;
            
            const res = await fetch(`/api/engines/install`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ engine: engineType, version: version })
            });
            if (res.ok) {
                alert(tx('درخواست نصب/آپدیت هسته ثبت شد. وضعیت را از لاگ‌ها دنبال کنید.', 'Engine install/update queued. Check logs for progress.'));
            } else {
                alert(tx('خطا در نصب هسته.', 'Failed to install engine.'));
            }
        }

        async function controlEngine(engineType, action) {
            const res = await fetch('/api/engines/control', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ engine: engineType, action })
            });
            if (res.ok) {
                const data = await res.json();
                renderEngineManager(data.engines || {});
                fetchStatus();
            } else {
                const data = await res.json().catch(() => ({}));
                alert(data.error || tx('عملیات هسته ناموفق بود.', 'Engine operation failed.'));
            }
        }

        async function healthCheckEngine(engineType) {
            const statusEl = document.getElementById(`engine-health-${engineType}`);
            if (statusEl) statusEl.innerText = tx('در حال تست سلامت هسته...', 'Checking engine health...');
            const res = await fetch('/api/engines/health', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ engine: engineType })
            });
            const data = await res.json().catch(() => ({}));
            const ok = res.ok && data.healthy;
            const detail = (data.results || []).map(r => `${r.path || '-'} ${r.executable ? 'OK' : 'NOEXEC'} ${r.version || ''}`.trim()).join(' | ');
            if (statusEl) {
                statusEl.className = ok ? 'text-success' : 'text-danger';
                statusEl.innerText = `${ok ? tx('سالم', 'Healthy') : tx('نیازمند بررسی', 'Needs attention')}: ${data.message || data.error || ''}${detail ? ' | ' + detail : ''}`;
            } else {
                alert(data.message || data.error || tx('نتیجه تست سلامت دریافت نشد.', 'No health result returned.'));
            }
        }

        async function uploadEngine(engineType) {
            const input = document.getElementById(`engine-upload-${engineType}`);
            const file = input?.files?.[0];
            if (!file) {
                alert(tx('ابتدا فایل هسته را انتخاب کنید.', 'Choose an engine archive first.'));
                return;
            }
            const buffer = await file.arrayBuffer();
            let binary = '';
            const bytes = new Uint8Array(buffer);
            for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
            const content_base64 = btoa(binary);
            const res = await fetch('/api/engines/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ engine: engineType, filename: file.name, content_base64 })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                alert(tx('هسته با فایل دستی آپدیت شد.', 'Engine manually updated.'));
                renderEngineManager(data.engines || {});
                fetchStatus();
            } else {
                alert(data.error || tx('آپدیت دستی ناموفق بود.', 'Manual update failed.'));
            }
        }

        document.getElementById('form-settings-tls').addEventListener('submit', async (e) => {
            e.preventDefault();
            const cert = document.getElementById('setting-cert-path').value;
            const key = document.getElementById('setting-key-path').value;
            
            const res = await fetch('/api/settings/tls', {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ panel_tls: true, cert_path: cert, key_path: key })
            });
            if (res.ok) {
                alert(tx('تنظیمات SSL ثبت شد. جهت اعمال نهایی روی دکمه "اعمال تغییرات و ریستارت وب پنل" کلیک کنید.', 'SSL settings were saved. Click "Apply changes and restart panel" to apply them.'));
                fetchStatus();
            } else {
                const data = await res.json().catch(() => ({}));
                alert(`${tx('خطا در ثبت تنظیمات SSL', 'Could not save SSL settings')}: ${data.error || tx('مسیر گواهی و کلید را بررسی کنید.', 'Check certificate and key paths.')}`);
            }
        });

        document.getElementById('form-settings-security').addEventListener('submit', async (e) => {
            e.preventDefault();
            const biometricRequested = document.getElementById('setting-biometric').checked;
            if (biometricRequested && !window.PublicKeyCredential) {
                alert(tx('این مرورگر یا محیط فعلی از WebAuthn/بایومتریک پشتیبانی نمی‌کند.', 'This browser/environment does not support WebAuthn/biometric login.'));
                return;
            }
            const res = await fetch('/api/settings/security', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    two_factor_enabled: document.getElementById('setting-two-factor').checked,
                    biometric_enabled: biometricRequested
                })
            });
            if (res.ok) {
                const data = await res.json();
                const box = document.getElementById('totp-secret-box');
                if (data.two_factor_secret) {
                    box.innerText = `TOTP Secret: ${data.two_factor_secret}`;
                    box.classList.remove('hidden');
                } else {
                    box.classList.add('hidden');
                }
                alert('Security options saved.');
                fetchStatus();
            } else {
                alert('Security settings failed.');
            }
        });

        document.getElementById('form-local-cert').addEventListener('submit', async (e) => {
            e.preventDefault();
            const host = document.getElementById('local-cert-host').value.trim();
            const res = await fetch('/api/certificates/local', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ host })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                document.getElementById('setting-panel-tls').checked = true;
                document.getElementById('setting-cert-path').value = data.cert_path || '';
                document.getElementById('setting-key-path').value = data.key_path || '';
                alert(tx('Certificate محلی ساخته و در تنظیمات اعمال شد. برای فعال شدن HTTPS پنل را ریستارت کنید.', 'Local certificate was generated and applied. Restart the panel to enable HTTPS.'));
                fetchStatus();
            } else {
                alert(`${tx('خطا در ساخت Certificate محلی', 'Local certificate error')}: ${data.error || tx('ناشناخته', 'Unknown')}`);
            }
        });

        document.getElementById('form-acme-cert').addEventListener('submit', async (e) => {
            e.preventDefault();
            const dom = document.getElementById('acme-domain').value;
            const mail = document.getElementById('acme-email').value;
            
            alert(tx('دریافت گواهی ممکن است تا ۱ دقیقه طول بکشد. لطفا صبور باشید...', 'Certificate issuance can take up to 1 minute. Please wait...'));
            
            try {
                const res = await fetch('/api/certificates/generate', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ domain: dom, email: mail })
                });
                if (res.ok) {
                    alert(tx("گواهینامه SSL با موفقیت از Let's Encrypt دریافت شد و مسیرها ست شدند.", "SSL certificate was issued by Let's Encrypt and paths were set."));
                    fetchStatus();
                } else {
                    const data = await res.json();
                    alert(`${tx('خطا در صدور گواهینامه', 'Certificate issuance error')}: ${data.error || tx('ناشناخته', 'Unknown')}`);
                }
            } catch (err) {
                alert(tx('خطا در ارتباط با سرور.', 'Could not connect to the server.'));
            }
        });

        async function restartPanel() {
            if (!confirm(tx('آیا مایل به ریستارت پنل جهت اعمال تغییرات SSL هستید؟ در حین ریستارت پنل برای لحظاتی از دسترس خارج می‌شود.', 'Restart the panel to apply SSL changes? The panel may be unavailable for a short time.'))) return;
            try {
                await fetch('/api/settings/restart', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                alert(tx('پنل در حال ریستارت است. صفحه را پس از ۱۰ ثانیه مجددا بارگذاری کنید.', 'The panel is restarting. Reload the page after 10 seconds.'));
                logout(true);
            } catch (err) {
                // Ignore as server exits
                alert(tx('درخواست ریستارت ارسال شد. صفحه را رفرش کنید.', 'Restart request sent. Refresh the page.'));
                logout(true);
            }
        }

        function exportLogsCSV() {
            window.location.href = `/api/logs/csv?token=${token}`;
        }

        function openModal(id) {
            document.getElementById(id).style.display = 'flex';
        }
        function closeModal(id) {
            document.getElementById(id).style.display = 'none';
        }

        async function cleanupLegacyBrowserCache() {
            try {
                if ('serviceWorker' in navigator) {
                    const regs = await navigator.serviceWorker.getRegistrations();
                    await Promise.all(regs.map(reg => reg.unregister()));
                }
                if ('caches' in window) {
                    const keys = await caches.keys();
                    await Promise.all(keys.filter(key => key.startsWith('p00rija-')).map(key => caches.delete(key)));
                }
            } catch (err) {
                console.warn('Legacy browser cache cleanup skipped:', err);
            }
        }
        cleanupLegacyBrowserCache();

        fetchSettings();
        applyTheme();

        async function runLiveRefreshTick() {
            if (!token || autoRefreshInFlight) return;
            autoRefreshInFlight = true;
            try {
                await fetchStatus({ forceChartRedraw: currentTab === 'dashboard' });
            } finally {
                autoRefreshInFlight = false;
            }
        }

        function setAutoRefresh() {
            let val = parseInt(document.getElementById("auto-refresh-select").value);
            if (autoRefreshTimer) clearInterval(autoRefreshTimer);
            autoRefreshTimer = null;
            if (val > 0) {
                runLiveRefreshTick();
                autoRefreshTimer = setInterval(runLiveRefreshTick, val * 1000);
            }
        }
    </script>
</body>
</html>
"""

# --------- REST HTTP Panel Server (Threading Interface) ----------
class P00RIJAThreadingHTTPServer(ThreadingHTTPServer):
    request_queue_size = 1024
    daemon_threads = True
    allow_reuse_address = True

class P00RIJAAutoTLSServer(P00RIJAThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, ssl_context):
        self.ssl_context = ssl_context
        super().__init__(server_address, RequestHandlerClass)

    def get_request(self):
        sock, addr = self.socket.accept()
        try:
            sock.settimeout(5)
            first = sock.recv(1, socket.MSG_PEEK)
            if first and first[0] == 0x16:
                sock = self.ssl_context.wrap_socket(sock, server_side=True)
        except ssl.SSLError as e:
            try:
                sock.close()
            except Exception:
                pass
            raise OSError(f"TLS handshake failed: {e}") from e
        except socket.timeout:
            try:
                sock.close()
            except Exception:
                pass
            raise OSError("Connection timed out waiting for data")
        except Exception:
            pass
        return sock, addr

class P00RIJAHTTPHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def end_headers(self):
        # Prevent CORS wildcard attack
        origin = "*"
        try:
            origin = self.headers.get("Origin", "*")
        except Exception:
            origin = "*"
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Node-Token')
        if db.data["settings"].get("panel_tls", PANEL_TLS_FORCED):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()

    def do_OPTIONS(self):
        parsed_url = urlparse(self.path)
        path = normalize_request_path(parsed_url.path)
        # Exempt /api/ paths from HTTPS redirect (matching do_GET behavior)
        # This prevents CORS preflight failures for API calls on dual HTTP/HTTPS port
        if not path.startswith("/api/") and self.redirect_plain_http_to_https():
            return
        self.send_response(200)
        self.end_headers()

    def redirect_plain_http_to_https(self):
        if isinstance(self.connection, ssl.SSLSocket):
            return False
        
        # Check proxy headers to avoid redirect loops when behind a reverse proxy handling HTTPS
        forwarded_proto = self.headers.get("X-Forwarded-Proto", "").lower()
        if "https" in forwarded_proto:
            return False
        if self.headers.get("X-Forwarded-Ssl", "").lower() == "on":
            return False
        if self.headers.get("X-Forwarded-Scheme", "").lower() == "https":
            return False
        if self.headers.get("Front-End-Https", "").lower() == "on":
            return False
            
        host = "localhost"
        try:
            host = self.headers.get("Host", host)
        except Exception:
            pass
        target = f"https://{host}{self.path}"
        self.send_response(308)
        self.send_header("Location", target)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.end_headers()
        return True

    def check_auth(self):
        auth_hdr = self.headers.get("Authorization")
        if not auth_hdr or not auth_hdr.startswith("Bearer "):
            return False
        token = auth_hdr.split(" ")[1]
        now = time.time()
        with active_sessions_lock:
            for session_token, login_time in list(active_sessions.items()):
                if now - login_time > 86400:
                    active_sessions.pop(session_token, None)
            if token in active_sessions:
                active_sessions[token] = now
                return True
        return False

    def get_post_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 1024 * 1024:
            raise ValueError("Request body too large")
        return self.rfile.read(content_length).decode('utf-8')

    def handle_payload_test(self, query=None, body=None):
        query = query or {}
        try:
            if body is None:
                raw_body = self.get_post_body()
                body = json.loads(raw_body or "{}")
            link_id = body.get("id") or body.get("link_id") or query.get("id", [""])[0] or query.get("link_id", [""])[0]
            try:
                mapping_index = int(body.get("index", query.get("index", ["0"])[0]))
            except Exception:
                mapping_index = 0
            size_mb = clamp_int(body.get("size_mb", query.get("size_mb", ["4"])[0]), 4, 1, 32)
            link = db.data["links"].get(link_id)
            if not link:
                self.send_json({
                    "error": "Payload test link not found",
                    "received_id": link_id,
                    "received_index": mapping_index,
                    "available_links": summarize_links_for_error()
                }, 404)
                return
            ports = link.get("ports", [])
            if not (0 <= mapping_index < len(ports)):
                self.send_json({
                    "error": "Invalid payload test mapping index",
                    "link_id": link_id,
                    "received_index": mapping_index,
                    "ports_count": len(ports),
                    "ports": [
                        {"index": i, "user_port": p.get("user_port"), "target_port": p.get("target_port")}
                        for i, p in enumerate(ports)
                    ]
                }, 400)
                return
            mapping = ports[mapping_index]
            user_port = int(mapping.get("user_port"))
            target_port = int(mapping.get("target_port"))
            if not valid_port(user_port) or not valid_port(target_port):
                self.send_json({"error": "Invalid port mapping", "link_id": link_id, "mapping_index": mapping_index}, 400)
                return
            internal_id = link.get("internal_node_id", link.get("iran_node_id"))
            external_id = link.get("external_node_id", link.get("foreign_node_id"))
            internal_node = db.data["nodes"].get(internal_id, {})
            external_node = db.data["nodes"].get(external_id, {})
            now = time.time()
            internal_live = internal_node.get("status") == "online" and now - internal_node.get("last_seen", 0) <= 30
            external_live = external_node.get("status") == "online" and now - external_node.get("last_seen", 0) <= 30
            if not internal_live or not external_live:
                self.send_json({
                    "error": "Both internal and external nodes must be online",
                    "internal_live": internal_live,
                    "external_live": external_live,
                    "internal_node": internal_node.get("name", internal_id),
                    "external_node": external_node.get("name", external_id)
                }, 400)
                return
            internal_host = str(internal_node.get("ip") or "").strip()
            if not internal_host:
                self.send_json({"error": "Internal node IP is empty", "internal_node": internal_node.get("name", internal_id)}, 400)
                return

            temp_marker = f"payload_{secrets.token_hex(6)}"
            temp_user_port, temp_target_port = choose_temp_link_ports(link)
            link.setdefault("ports", []).append({
                "user_port": temp_user_port,
                "target_port": temp_target_port,
                "_temp_test": temp_marker
            })
            db.save()
            echo_payload = {}
            transfer = {}
            try:
                # Give both nodes one config-sync/report cycle to open the temporary mapping.
                time.sleep(7)
                cmd_id = queue_payload_echo_command(external_id, temp_target_port, duration=90)
                echo_result = wait_for_node_command_result(external_id, cmd_id, timeout=22)
                if not echo_result:
                    self.send_json({
                        "error": "External node did not start the temporary payload echo service. Update/restart the external node and try again.",
                        "link_id": link_id,
                        "test_user_port": temp_user_port,
                        "test_target_port": temp_target_port
                    }, 504)
                    return
                echo_payload = echo_result.get("result", {})
                if not echo_payload.get("success"):
                    self.send_json({
                        "error": "External temporary payload echo service failed",
                        "echo_result": echo_payload,
                        "test_user_port": temp_user_port,
                        "test_target_port": temp_target_port
                    }, 500)
                    return

                client_id = queue_payload_client_command(internal_id, temp_user_port, size_mb=size_mb)
                client_result = wait_for_node_command_result(internal_id, client_id, timeout=75)
                if not client_result:
                    self.send_json({
                        "error": "Internal node did not finish the payload transfer command. Check internal node logs and restart the node.",
                        "test_user_port": temp_user_port,
                        "test_target_port": temp_target_port,
                        "echo_result": echo_payload
                    }, 504)
                    return
                transfer = client_result.get("result", {})
            finally:
                removed = remove_temp_port_mapping(link, temp_marker)
                if removed:
                    db.save()

            production_hint = ""
            if not transfer.get("success"):
                production_hint = "If this test fails while nodes are online, check node Docker network mode. Real VPN/user traffic needs host network mode or explicitly published user ports on the internal node, and host-network access to target services on the external node."
            db.log("panel", "info", f"Payload tunnel self-test for '{link.get('name', link_id)}' temp {temp_user_port}->{temp_target_port}: {transfer}.")
            self.send_json({
                "success": bool(transfer.get("success")),
                "error": "" if transfer.get("success") else transfer.get("error", "Payload transfer validation failed"),
                "hint": production_hint,
                "link_id": link_id,
                "mapping_index": mapping_index,
                "user_port": user_port,
                "target_port": target_port,
                "test_user_port": temp_user_port,
                "test_target_port": temp_target_port,
                "internal_node": internal_node.get("name", internal_id),
                "external_node": external_node.get("name", external_id),
                "size_mb": size_mb,
                "echo_result": echo_payload,
                "transfer": transfer
            }, 200 if transfer.get("success") else 502)
        except Exception as e:
            self.send_json({"error": f"Payload tunnel test failed: {e}"}, 500)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = normalize_request_path(parsed_url.path)
        query = parse_qs(parsed_url.query)

        if not path.startswith("/api/") and self.redirect_plain_http_to_https():
            return

        # Let's Encrypt / ACME HTTP-01 Webroot challenge route
        if path.startswith("/.well-known/acme-challenge/"):
            filename = os.path.basename(path)
            filepath = os.path.join(f"{CONFIG_DIR}/acme_webroot/.well-known/acme-challenge/", filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(content.encode())
                    return
                except Exception:
                    pass
            self.send_response(404)
            self.end_headers()
            return

        if path in ("/", "/index.html", "/login", "/nodes", "/links", "/logs", "/settings", "/monitor", "/appearance", "/help", "/about"):
            self.send_html(INDEX_HTML)
            return

        if path.startswith("/fonts/"):
            font_name = os.path.basename(path)
            font_dirs = [
                os.environ.get("P00RIJA_FONTS_DIR", ""),
                "/app/fonts",
                os.path.join(CONFIG_DIR, "fonts"),
                os.path.join(os.getcwd(), "fonts"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
            ]
            filepath = ""
            for font_dir in font_dirs:
                if not font_dir:
                    continue
                candidate = os.path.join(font_dir, font_name)
                if os.path.exists(candidate):
                    filepath = candidate
                    break
            if filepath:
                try:
                    with open(filepath, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    if path.endswith(".woff2"):
                        self.send_header("Content-Type", "font/woff2")
                    elif path.endswith(".woff"):
                        self.send_header("Content-Type", "font/woff")
                    elif path.endswith(".ttf"):
                        self.send_header("Content-Type", "font/ttf")
                    self.send_header("Cache-Control", "public, max-age=31536000")
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception:
                    pass
            self.send_response(404)
            self.end_headers()
            return

        if path == "/manifest.webmanifest":
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "name": "P00RIJA TUNNEL Panel",
                "short_name": "P00RIJA",
                "start_url": "/",
                "scope": "/",
                "display": "standalone",
                "background_color": "#07100f",
                "theme_color": "#20c7b5",
                "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}]
            }).encode("utf-8"))
            return

        if path == "/sw.js":
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write((
                "self.addEventListener('install',e=>self.skipWaiting());\n"
                "self.addEventListener('activate',e=>e.waitUntil((async()=>{if(self.caches){const keys=await caches.keys();await Promise.all(keys.map(k=>caches.delete(k)));}await self.registration.unregister();await self.clients.claim();})()));\n"
            ).encode("utf-8"))
            return

        if path == "/icon.svg":
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.end_headers()
            self.wfile.write(APP_LOGO_SVG.encode("utf-8"))
            return

        if path == "/api/public-settings":
            self.send_json({
                "version": APP_VERSION,
                "license": APP_LICENSE,
                "two_factor_enabled": db.data["settings"].get("two_factor_enabled", False),
                "biometric_enabled": db.data["settings"].get("biometric_enabled", False),
                "panel_tls": True,
                "https_required": True
            })
            return

        if path == "/api/node-config":
            node_token = normalize_node_token(self.headers.get("X-Node-Token"))
            matched_node_id = None
            for nid, n in db.data["nodes"].items():
                if n.get("token") == node_token:
                    matched_node_id = nid
                    break
            
            if not matched_node_id:
                self.send_json({"error": "Unauthorized Node"}, 401)
                return

            node = db.data["nodes"][matched_node_id]
            if not valid_node_signature(node, path, "", self.headers.get("X-Node-Signature")):
                self.send_json({"error": "Invalid node signature"}, 401)
                return
            node_links = []
            for lid, l in db.data["links"].items():
                if l.get("paused", False):
                    continue
                if l.get("internal_node_id", l.get("iran_node_id")) == matched_node_id or l.get("external_node_id", l.get("foreign_node_id")) == matched_node_id:
                    other_ip = ""
                    if role_matches(node.get("type", node.get("role", "unknown")), "external"):
                        iran_node = db.data["nodes"].get(l.get("internal_node_id", l.get("iran_node_id")), {})
                        other_ip = iran_node.get("ip", "")
                    else:
                        external_node = db.data["nodes"].get(l.get("external_node_id", l.get("foreign_node_id")), {})
                        other_ip = external_node.get("ip", "")
                    
                    link_config = {
                        "id": lid,
                        "iran_ip": other_ip,
                        "peer_ip": other_ip,
                        "bridge_port": l["bridge_port"],
                        "sync_port": l["sync_port"],
                        "pool_size": l.get("pool_size", 100),
                        "ports": l.get("ports", []),
                        "engine": l.get("engine", "builtin"),
                        "transport": l.get("transport", l.get("tunnel_mode", "tcp")),
                        "network": l.get("network", "tcp"),
                        "tunnel_mode": l.get("tunnel_mode", "tcp"),
                        "tls_enabled": l.get("tls_enabled", False),
                        "tls_sni": l.get("tls_sni", "speedtest.net"),
                        "obfs_host": l.get("obfs_host", "speedtest.net"),
                        "obfs_path": l.get("obfs_path", "/tunnel"),
                        "profile_id": l.get("profile_id", "custom"),
                        "padding_min": l.get("padding_min", 0),
                        "padding_max": l.get("padding_max", 0),
                        "jitter_ms": l.get("jitter_ms", 0),
                        "keepalive_interval": l.get("keepalive_interval", 25),
                        "xray_config": xray_config_for_link(l, node.get("type", node.get("role", "unknown"))) if l.get("engine") == "xray" else None,
                        "muxquantum_config": muxquantum_config_for_link(lid, l, node.get("type", node.get("role", "unknown")), other_ip) if l.get("engine") == "muxquantum" else None,
                        "hysteria2_config": hysteria2_config_for_link(l, node.get("type", node.get("role", "unknown"))) if l.get("engine") == "hysteria2" else None
                    }

                    # Attach SSL certificates on-the-fly for Iran Node TLS
                    if l.get("tls_enabled") and role_matches(node.get("type", node.get("role", "unknown")), "internal"):
                        cert_path = db.data["settings"].get("cert_path", f"{CONFIG_DIR}/certs/cert.pem")
                        key_path = db.data["settings"].get("key_path", f"{CONFIG_DIR}/certs/key.pem")
                        try:
                            with open(cert_path, "r") as f:
                                link_config["cert_content"] = f.read()
                            with open(key_path, "r") as f:
                                link_config["key_content"] = f.read()
                        except Exception as e:
                            db.log("panel", "error", f"Failed reading SSL cert for link sync: {e}")

                    node_links.append(link_config)

            if node.get("paused", False):
                node_links = []

            node_commands = db.data.setdefault("node_commands", {}).get(matched_node_id, [])
            self.send_json({
                "role": node.get("type", node.get("role", "unknown")), 
                "links": node_links,
                "commands": node_commands[:8],
                "settings": {
                    "engine_restart_interval": db.data["settings"].get("engine_restart_interval", 0),
                    "disable_ipv6": db.data["settings"].get("disable_ipv6", False)
                }
            })
            return

        if path.startswith("/api/"):
            if path in ("/api/logs/csv", "/api/profiles/export") and "token" in query:
                csv_token = query["token"][0]
                with active_sessions_lock:
                    has_csv_session = csv_token in active_sessions
                if not has_csv_session:
                    self.send_response(401)
                    self.end_headers()
                    return
            elif not self.check_auth():
                self.send_json({"error": "Unauthorized"}, 401)
                return

            if path == "/api/status":
                now = time.time()
                tunnel_profiles, profiles_changed = ensure_tunnel_profiles()
                for nid, n in db.data["nodes"].items():
                    if n.get("status") == "online" and now - n.get("last_seen", 0) > 30:
                        n["status"] = "offline"
                    if not n.get("paused") and n.get("ip"):
                        refresh_node_ping_async(nid, n)
                if profiles_changed:
                    db.save()

                self.send_json({
                    "nodes": sanitize_nodes_for_status(db.data["nodes"]),
                    "links": db.data["links"],
                    "logs": db.data["logs"],
                    "admin_username": db.data["admin"]["username"],
                    "panel_tls": True,
                    "cert_path": db.data["settings"].get("cert_path", ""),
                    "key_path": db.data["settings"].get("key_path", ""),
                    "version": APP_VERSION,
                    "build": APP_BUILD,
                    "capabilities": {
                        "payload_test": True,
                        "payload_test_client": True,
                        "direct_bridge_fallback": True,
                        "link_runtime_health": True
                    },
                    "license": APP_LICENSE,
                    "author_github": APP_AUTHOR_GITHUB,
                    "author_email": APP_AUTHOR_EMAIL,
                    "two_factor_enabled": db.data["settings"].get("two_factor_enabled", False),
                    "biometric_enabled": db.data["settings"].get("biometric_enabled", False),
                    "disable_ipv6": db.data["settings"].get("disable_ipv6", False),
                    "engine_restart_interval": db.data["settings"].get("engine_restart_interval", 0),
                    "tunnel_profiles": tunnel_profiles,
                    "engines": list_engine_status(),
                    "ssh_saved_nodes": {nid: sanitize_ssh_credential(cred) for nid, cred in load_ssh_vault().get("nodes", {}).items()},
                    "runtime_sessions": list_all_runtime_sessions(),
                    "host_info": get_host_info()
                })
                return

            if path == "/api/nodes/secrets":
                node_id = query.get("id", [""])[0]
                node = db.data.get("nodes", {}).get(node_id)
                if not node:
                    self.send_json({"error": "Node not found"}, 404)
                    return
                self.send_json({
                    "success": True,
                    "node_id": node_id,
                    "name": node.get("name", node_id),
                    "role": node.get("role", ""),
                    "ip": node.get("ip", ""),
                    "token": node.get("token", ""),
                    "private_key": node.get("private_key", ""),
                    "public_key": node.get("public_key", ""),
                    "setup": "\n".join([
                        f"Node: {node.get('name', node_id)}",
                        f"Node token: {node.get('token', '')}",
                        f"Node private key: {node.get('private_key', '')}",
                    ])
                })
                return

            if path == "/api/links/smart-test":
                try:
                    body = json.loads(self.get_post_body())
                    internal_id = body.get("internal_node_id")
                    external_id = body.get("external_node_id")
                    internal = db.data["nodes"].get(internal_id)
                    external = db.data["nodes"].get(external_id)
                    if not internal or not external:
                        self.send_json({"error": "Both nodes are required"}, 400)
                        return
                    internal_ping = safe_ping_host(internal.get("ip"), count=2, timeout=2)
                    external_ping = safe_ping_host(external.get("ip"), count=2, timeout=2)
                    profile_id, reason = recommend_tunnel_profile(internal, external, internal_ping, external_ping)
                    profiles, changed = ensure_tunnel_profiles()
                    if changed:
                        db.save()
                    self.send_json({
                        "success": True,
                        "internal": {"id": internal_id, "name": internal.get("name"), "ping": internal_ping},
                        "external": {"id": external_id, "name": external.get("name"), "ping": external_ping},
                        "recommended_profile_id": profile_id,
                        "recommended_profile": profiles.get(profile_id, {}),
                        "reason": reason
                    })
                except Exception as e:
                    self.send_json({"error": f"Smart test failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/save":
                try:
                    body = json.loads(self.get_post_body())
                    node_id = body.get("node_id")
                    if node_id not in db.data["nodes"]:
                        self.send_json({"error": "Node not found"}, 404)
                        return
                    vault = load_ssh_vault()
                    vault["nodes"][node_id] = {
                        "host": str(body.get("host") or db.data["nodes"][node_id].get("ip", ""))[:255],
                        "port": clamp_int(body.get("port", 22), 22, 1, 65535),
                        "username": str(body.get("username") or "root")[:80],
                        "auth_method": body.get("auth_method", "password") if body.get("auth_method") in ("password", "key") else "password",
                        "password": str(body.get("password") or "")[:1000],
                        "private_key": str(body.get("private_key") or "")[:20000],
                        "timeout": clamp_int(body.get("timeout", 15), 15, 3, 120),
                        "saved_at": time.time()
                    }
                    save_ssh_vault(vault)
                    db.log("panel", "info", f"Saved encrypted SSH profile for node '{db.data['nodes'][node_id].get('name', node_id)}'.")
                    self.send_json({"success": True, "credential": sanitize_ssh_credential(vault["nodes"][node_id])})
                except Exception as e:
                    self.send_json({"error": f"SSH save failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/start":
                try:
                    prune_ssh_sessions()
                    body = json.loads(self.get_post_body())
                    node_id = body.get("node_id")
                    if node_id not in db.data["nodes"]:
                        self.send_json({"error": "Node not found"}, 404)
                        return
                    session_id, output, alive, credential = start_ssh_session(node_id, body)
                    db.log("panel", "info", f"Started interactive SSH terminal for node '{db.data['nodes'][node_id].get('name', node_id)}'.")
                    self.send_json({"success": True, "session_id": session_id, "output": output, "alive": alive, "credential": credential})
                except Exception as e:
                    self.send_json({"error": f"SSH terminal start failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/write":
                try:
                    body = json.loads(self.get_post_body())
                    session_id = body.get("session_id")
                    write_ssh_session(session_id, body.get("data", ""))
                    output, alive = read_ssh_session_output(session_id)
                    self.send_json({"success": True, "output": output, "alive": alive})
                except Exception as e:
                    self.send_json({"error": f"SSH terminal write failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/read":
                try:
                    body = json.loads(self.get_post_body())
                    output, alive = read_ssh_session_output(body.get("session_id"))
                    self.send_json({"success": True, "output": output, "alive": alive})
                except Exception as e:
                    self.send_json({"error": f"SSH terminal read failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/close":
                try:
                    body = json.loads(self.get_post_body())
                    cleanup_ssh_session(body.get("session_id"))
                    self.send_json({"success": True})
                except Exception as e:
                    self.send_json({"error": f"SSH terminal close failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/run":
                try:
                    body = json.loads(self.get_post_body())
                    node_id = body.get("node_id")
                    if node_id not in db.data["nodes"]:
                        self.send_json({"error": "Node not found"}, 404)
                        return
                    vault = load_ssh_vault()
                    saved = vault.get("nodes", {}).get(node_id, {})
                    cred = dict(saved)
                    for key in ("host", "port", "username", "auth_method", "password", "private_key", "timeout"):
                        if body.get(key) not in (None, ""):
                            cred[key] = body.get(key)
                    if not cred.get("host"):
                        cred["host"] = db.data["nodes"][node_id].get("ip", "")
                    if body.get("save"):
                        vault.setdefault("nodes", {})[node_id] = dict(cred, saved_at=time.time())
                        save_ssh_vault(vault)
                    result = execute_ssh_command(cred, body.get("command", "uname -a && uptime"))
                    self.send_json({"success": result["success"], "result": result, "credential": sanitize_ssh_credential(cred)})
                except Exception as e:
                    self.send_json({"error": f"SSH command failed: {e}"}, 400)
                return

            if path == "/api/engines/health":
                try:
                    body = json.loads(self.get_post_body())
                    self.send_json(check_engine_health(body.get("engine")))
                except Exception as e:
                    self.send_json({"success": False, "healthy": False, "error": f"Engine health check failed: {e}"}, 400)
                return

            if path == "/api/engines/control":
                try:
                    body = json.loads(self.get_post_body())
                    engine_id = body.get("engine")
                    action = body.get("action")
                    if action not in ("start", "stop", "restart"):
                        self.send_json({"error": "Invalid action"}, 400)
                        return
                    result = control_engine_process(engine_id, action)
                    if not result.get("success"):
                        self.send_json(result, 400)
                        return
                    db.log("panel", "info", f"Engine control: {engine_id} -> {action}.")
                    self.send_json({"success": True, "result": result, "engines": list_engine_status()})
                except Exception as e:
                    self.send_json({"error": f"Engine control failed: {e}"}, 400)
                return

            if path == "/api/engines/upload":
                try:
                    body = json.loads(self.get_post_body())
                    engine_id = body.get("engine")
                    filename = str(body.get("filename") or "")
                    content = base64.b64decode(body.get("content_base64") or "")
                    installed = install_engine_archive(engine_id, filename, content)
                    db.log("panel", "info", f"Manually updated engine {engine_id}: {installed}.")
                    self.send_json({"success": True, "installed": installed, "engines": list_engine_status()})
                except Exception as e:
                    self.send_json({"error": f"Manual engine update failed: {e}"}, 400)
                return

            if path.startswith("/api/nodes/toggle-pause"):
                query = parse_qs(urlparse(self.path).query)
                node_id = query.get("id", [None])[0]
                if not node_id or node_id not in db.data["nodes"]:
                    self.send_json({"error": "Node not found"}, 404)
                    return
                node = db.data["nodes"][node_id]
                node["paused"] = not node.get("paused", False)
                db.save()
                self.send_json({"success": True, "paused": node["paused"]})
                return

            if path.startswith("/api/nodes/test"):
                query = parse_qs(urlparse(self.path).query)
                node_id = query.get("id", [None])[0]
                if not node_id or node_id not in db.data["nodes"]:
                    self.send_json({"error": "Node not found"}, 404)
                    return
                ip = db.data["nodes"][node_id].get("ip")
                if not ip:
                    self.send_json({"error": "No IP assigned to node"}, 400)
                    return
                try:
                    # 1. Ping Node IP
                    cmd1 = ["ping", "-c", "3", "-W", "2", ip]
                    res1 = subprocess.run(cmd1, capture_output=True, text=True)
                    out = f"==== Node Connection ({ip}) ====\n{res1.stdout}{res1.stderr}\n"
                    
                    if res1.returncode == 0:
                        lines = [l for l in res1.stdout.split('\n') if 'time=' in l or 'avg' in l]
                        if lines:
                            import re
                            ms_match = re.search(r'time=([\d\.]+)', lines[0])
                            if ms_match:
                                db.data["nodes"][node_id].setdefault("stats", {})["ping_ms"] = float(ms_match.group(1))
                                
                    # 2. Ping Internet
                    cmd2 = ["ping", "-c", "3", "-W", "2", "1.1.1.1"]
                    res2 = subprocess.run(cmd2, capture_output=True, text=True)
                    out += f"\n==== Internet Connection (1.1.1.1) ====\n{res2.stdout}{res2.stderr}"

                    self.send_json({"success": True, "result": out.strip()})
                except FileNotFoundError:
                    self.send_json({"error": "Ping command not found on server"}, 500)
                except Exception as e:
                    self.send_json({"error": f"Ping error: {e}"}, 500)
                return

            if path.startswith("/api/links/toggle-pause"):
                query = parse_qs(urlparse(self.path).query)
                link_id = query.get("id", [None])[0]
                if not link_id or link_id not in db.data["links"]:
                    self.send_json({"error": "Link not found"}, 404)
                    return
                link = db.data["links"][link_id]
                link["paused"] = not link.get("paused", False)
                db.save()
                db.log("panel", "info", f"Tunnel link '{link.get('name', link_id)}' {'paused' if link['paused'] else 'resumed'}.")
                self.send_json({"success": True, "paused": link["paused"]})
                return


            if path == "/api/runtime/processes":
                self.send_json({"processes": get_all_process_snapshot()})
                return

            if path == "/api/runtime/sessions":
                self.send_json({"sessions": list_all_runtime_sessions(), "threads": threading.active_count()})
                return

            if path == "/api/runtime/resources":
                all_sessions = list_all_runtime_sessions()
                now = time.time()
                node_resources = []
                node_threads = 0
                for nid, n in db.data.get("nodes", {}).items():
                    online = n.get("status") == "online" and now - n.get("last_seen", 0) <= 30
                    stats = n.get("stats") or {}
                    if online:
                        node_threads += int(stats.get("threads") or 0)
                    node_resources.append({
                        "id": nid,
                        "name": n.get("name", nid),
                        "role": n.get("role", n.get("type", "")),
                        "status": "online" if online else "offline",
                        "cpu": stats.get("cpu", 0),
                        "ram": stats.get("ram", 0),
                        "rx_speed": stats.get("rx_speed", 0),
                        "tx_speed": stats.get("tx_speed", 0),
                        "threads": stats.get("threads", 0),
                        "connections": stats.get("connections", 0),
                        "last_command_result": n.get("last_command_result")
                    })
                self.send_json({
                    "threads": threading.active_count() + node_threads,
                    "active_tunnel_sessions": len(all_sessions),
                    "rss_kb": get_own_rss_kb(),
                    "nodes": node_resources
                })
                return

            if path == "/api/links/test":
                link_id = query.get("id", [""])[0]
                link = db.data["links"].get(link_id)
                if not link:
                    self.send_json({"error": "Link not found"}, 404)
                    return
                now = time.time()
                internal_node = db.data["nodes"].get(link.get("internal_node_id", link.get("iran_node_id")), {})
                external_node = db.data["nodes"].get(link.get("external_node_id", link.get("foreign_node_id")), {})
                internal_live = internal_node.get("status") == "online" and now - internal_node.get("last_seen", 0) <= 30
                external_live = external_node.get("status") == "online" and now - external_node.get("last_seen", 0) <= 30
                self.send_json({
                    "success": internal_live and external_live,
                    "internal_live": internal_live,
                    "external_live": external_live,
                    "engine": link.get("engine", "builtin"),
                    "active_sessions": [s for s in list_runtime_sessions() if s["link_id"] == link_id]
                })
                return

            if path == "/api/links/payload-test":
                self.handle_payload_test(query, body={})
                return

            if path == "/api/links/payload-test" and False:
                try:
                    body = json.loads(self.get_post_body())
                    link_id = body.get("id") or query.get("id", [""])[0]
                    mapping_index = int(body.get("index", 0))
                    size_mb = clamp_int(body.get("size_mb", 4), 4, 1, 32)
                    link = db.data["links"].get(link_id)
                    if not link:
                        self.send_json({"error": "Link not found"}, 404)
                        return
                    ports = link.get("ports", [])
                    if not (0 <= mapping_index < len(ports)):
                        self.send_json({"error": "Invalid mapping index"}, 400)
                        return
                    mapping = ports[mapping_index]
                    user_port = int(mapping.get("user_port"))
                    target_port = int(mapping.get("target_port"))
                    if not valid_port(user_port) or not valid_port(target_port):
                        self.send_json({"error": "Invalid port mapping"}, 400)
                        return
                    internal_id = link.get("internal_node_id", link.get("iran_node_id"))
                    external_id = link.get("external_node_id", link.get("foreign_node_id"))
                    internal_node = db.data["nodes"].get(internal_id, {})
                    external_node = db.data["nodes"].get(external_id, {})
                    now = time.time()
                    internal_live = internal_node.get("status") == "online" and now - internal_node.get("last_seen", 0) <= 30
                    external_live = external_node.get("status") == "online" and now - external_node.get("last_seen", 0) <= 30
                    if not internal_live or not external_live:
                        self.send_json({
                            "error": "Both internal and external nodes must be online",
                            "internal_live": internal_live,
                            "external_live": external_live
                        }, 400)
                        return
                    internal_host = str(internal_node.get("ip") or "").strip()
                    if not internal_host:
                        self.send_json({"error": "Internal node IP is empty"}, 400)
                        return

                    temp_marker = f"payload_{secrets.token_hex(6)}"
                    temp_user_port, temp_target_port = choose_temp_link_ports(link)
                    link.setdefault("ports", []).append({
                        "user_port": temp_user_port,
                        "target_port": temp_target_port,
                        "_temp_test": temp_marker
                    })
                    db.save()
                    echo_payload = {}
                    transfer = {}
                    try:
                        # Give both nodes one config-sync/report cycle to open the temporary mapping.
                        time.sleep(7)
                        cmd_id = queue_payload_echo_command(external_id, temp_target_port, duration=90)
                        echo_result = wait_for_node_command_result(external_id, cmd_id, timeout=22)
                        if not echo_result:
                            self.send_json({"error": "External node did not start the temporary payload echo service. Update/restart the external node and try again."}, 504)
                            return
                        echo_payload = echo_result.get("result", {})
                        if not echo_payload.get("success"):
                            self.send_json({
                                "error": "External temporary payload echo service failed",
                                "echo_result": echo_payload,
                                "test_user_port": temp_user_port,
                                "test_target_port": temp_target_port
                            }, 500)
                            return

                        client_id = queue_payload_client_command(internal_id, temp_user_port, size_mb=size_mb)
                        client_result = wait_for_node_command_result(internal_id, client_id, timeout=75)
                        if not client_result:
                            self.send_json({
                                "error": "Internal node did not finish the payload transfer command. Check internal node logs and restart the node.",
                                "test_user_port": temp_user_port,
                                "test_target_port": temp_target_port,
                                "echo_result": echo_payload
                            }, 504)
                            return
                        transfer = client_result.get("result", {})
                    finally:
                        removed = remove_temp_port_mapping(link, temp_marker)
                        if removed:
                            db.save()

                    production_hint = ""
                    if not transfer.get("success"):
                        production_hint = "If this test fails while nodes are online, check node Docker network mode. Real VPN/user traffic needs host network mode or explicitly published user ports on the internal node, and host-network access to target services on the external node."
                    db.log("panel", "info", f"Payload tunnel self-test for '{link.get('name', link_id)}' temp {temp_user_port}->{temp_target_port}: {transfer}.")
                    self.send_json({
                        "success": bool(transfer.get("success")),
                        "error": "" if transfer.get("success") else transfer.get("error", "Payload transfer validation failed"),
                        "hint": production_hint,
                        "link_id": link_id,
                        "mapping_index": mapping_index,
                        "user_port": user_port,
                        "target_port": target_port,
                        "test_user_port": temp_user_port,
                        "test_target_port": temp_target_port,
                        "internal_node": internal_node.get("name", internal_id),
                        "external_node": external_node.get("name", external_id),
                        "size_mb": size_mb,
                        "echo_result": echo_payload,
                        "transfer": transfer
                    }, 200 if transfer.get("success") else 502)
                except Exception as e:
                    self.send_json({"error": f"Payload tunnel test failed: {e}"}, 500)
                return

            if path == "/api/links/engine-config":
                link_id = query.get("id", [""])[0]
                link = db.data["links"].get(link_id)
                if not link:
                    self.send_json({"error": "Link not found"}, 404)
                    return
                if link.get("engine") == "hysteria2":
                    self.send_json({
                        "internal": hysteria2_config_for_link(link, "internal"),
                        "external": hysteria2_config_for_link(link, "external")
                    })
                elif link.get("engine") == "muxquantum":
                    other_ip = link.get("external_ip", link.get("iran_ip", "127.0.0.1"))
                    self.send_json({
                        "internal": muxquantum_config_for_link(link_id, link, "internal", other_ip),
                        "external": muxquantum_config_for_link(link_id, link, "external", other_ip)
                    })
                else:
                    self.send_json({
                        "internal": xray_config_for_link(link, "internal"),
                        "external": xray_config_for_link(link, "external")
                    })
                return

            if path == "/api/profiles/export":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Disposition", 'attachment; filename="p00rija_tunnel_profiles.json"')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "version": APP_VERSION,
                    "profiles": db.data["settings"].get("tunnel_profiles", default_tunnel_profiles())
                }, indent=2).encode("utf-8"))
                return

            if path == "/api/logs":
                self.send_json(db.data["logs"])
                return

            if path == "/api/logs/csv":
                self.send_response(200)
                self.send_header("Content-Type", "text/csv")
                self.send_header("Content-Disposition", 'attachment; filename="p00rija_logs.csv"')
                self.end_headers()
                
                csv_out = "Timestamp,Source,Level,Message\n"
                for entry in db.data["logs"]:
                    csv_out += f'"{entry["timestamp"]}","{entry["source"]}","{entry["level"]}","{entry["message"].replace(chr(34), chr(34)+chr(34))}"\n'
                self.wfile.write(csv_out.encode("utf-8"))
                return

        if path.startswith("/api/"):
            self.send_json({"error": "API endpoint not found", "method": "GET", "path": path}, 404)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = normalize_request_path(parsed_url.path)
        query = parse_qs(parsed_url.query)

        # Exempt /api/ paths from HTTPS redirect (matching do_GET behavior)
        # This prevents login and other API POST requests from being redirected
        if not path.startswith("/api/") and self.redirect_plain_http_to_https():
            return

        if path == "/api/login":
            try:
                body = json.loads(self.get_post_body())
                username = body.get("username")
                password = body.get("password")
                otp = body.get("otp")
                pwd_hash = hashlib.sha256(password.encode()).hexdigest()

                if username == db.data["admin"]["username"] and pwd_hash == db.data["admin"]["password_hash"]:
                    if db.data["settings"].get("two_factor_enabled"):
                        if not verify_totp(db.data["settings"].get("two_factor_secret", ""), otp):
                            self.send_json({"error": "Invalid two-factor code"}, 401)
                            return
                    session_token = secrets.token_hex(16)
                    with active_sessions_lock:
                        active_sessions[session_token] = time.time()
                    self.send_json({"token": session_token})
                    db.log("panel", "info", f"Admin user '{username}' successfully logged in.")
                else:
                    self.send_json({"error": "Invalid credentials"}, 401)
            except Exception:
                self.send_json({"error": "Bad request"}, 400)
            return

        if path == "/api/report":
            node_token = normalize_node_token(self.headers.get("X-Node-Token"))
            matched_node_id = None
            for nid, n in db.data["nodes"].items():
                if n.get("token") == node_token:
                    matched_node_id = nid
                    break

            if not matched_node_id:
                self.send_json({"error": "Unauthorized Node"}, 401)
                return

            try:
                body_text = self.get_post_body()
                stats = json.loads(body_text)
                node = db.data["nodes"][matched_node_id]
                if not valid_node_signature(node, path, body_text, self.headers.get("X-Node-Signature")):
                    self.send_json({"error": "Invalid node signature"}, 401)
                    return
                node["status"] = "online"
                node["last_seen"] = time.time()
                if "ping_ms" in node.get("stats", {}):
                    stats["ping_ms"] = node["stats"]["ping_ms"]
                node["stats"] = stats
                self.send_json({"success": True})
            except Exception:
                self.send_json({"error": "Bad request"}, 400)
            return

        if path == "/api/node-command-result":
            node_token = normalize_node_token(self.headers.get("X-Node-Token"))
            matched_node_id = None
            for nid, n in db.data["nodes"].items():
                if n.get("token") == node_token:
                    matched_node_id = nid
                    break
            if not matched_node_id:
                self.send_json({"error": "Unauthorized Node"}, 401)
                return
            try:
                body_text = self.get_post_body()
                body = json.loads(body_text)
                node = db.data["nodes"][matched_node_id]
                if not valid_node_signature(node, path, body_text, self.headers.get("X-Node-Signature")):
                    self.send_json({"error": "Invalid node signature"}, 401)
                    return
                cmd_id = body.get("id")
                node["last_command_result"] = {
                    "id": cmd_id,
                    "type": body.get("type"),
                    "action": body.get("action"),
                    "result": body.get("result", {}),
                    "received_at": time.time()
                }
                commands = db.data.setdefault("node_commands", {}).get(matched_node_id, [])
                db.data["node_commands"][matched_node_id] = [cmd for cmd in commands if cmd.get("id") != cmd_id]
                db.save()
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": f"Bad command result: {e}"}, 400)
            return

        if path.startswith("/api/"):
            if not self.check_auth():
                self.send_json({"error": "Unauthorized"}, 401)
                return

            if path == "/api/links/payload-test":
                self.handle_payload_test(query)
                return

            if path == "/api/links/smart-test":
                try:
                    body = json.loads(self.get_post_body())
                    internal_id = body.get("internal_node_id")
                    external_id = body.get("external_node_id")
                    internal = db.data["nodes"].get(internal_id)
                    external = db.data["nodes"].get(external_id)
                    if not internal or not external:
                        self.send_json({"error": "Both nodes are required"}, 400)
                        return
                    internal_ping = safe_ping_host(internal.get("ip"), count=2, timeout=2)
                    external_ping = safe_ping_host(external.get("ip"), count=2, timeout=2)
                    profile_id, reason = recommend_tunnel_profile(internal, external, internal_ping, external_ping)
                    profiles, changed = ensure_tunnel_profiles()
                    if changed:
                        db.save()
                    self.send_json({
                        "success": True,
                        "internal": {"id": internal_id, "name": internal.get("name"), "ping": internal_ping},
                        "external": {"id": external_id, "name": external.get("name"), "ping": external_ping},
                        "recommended_profile_id": profile_id,
                        "recommended_profile": profiles.get(profile_id, {}),
                        "reason": reason
                    })
                except Exception as e:
                    self.send_json({"error": f"Smart test failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/save":
                try:
                    body = json.loads(self.get_post_body())
                    node_id = body.get("node_id")
                    if node_id not in db.data["nodes"]:
                        self.send_json({"error": "Node not found"}, 404)
                        return
                    vault = load_ssh_vault()
                    vault["nodes"][node_id] = {
                        "host": str(body.get("host") or db.data["nodes"][node_id].get("ip", ""))[:255],
                        "port": clamp_int(body.get("port", 22), 22, 1, 65535),
                        "username": str(body.get("username") or "root")[:80],
                        "auth_method": body.get("auth_method", "password") if body.get("auth_method") in ("password", "key") else "password",
                        "password": str(body.get("password") or "")[:1000],
                        "private_key": str(body.get("private_key") or "")[:20000],
                        "timeout": clamp_int(body.get("timeout", 15), 15, 3, 120),
                        "saved_at": time.time()
                    }
                    save_ssh_vault(vault)
                    db.log("panel", "info", f"Saved encrypted SSH profile for node '{db.data['nodes'][node_id].get('name', node_id)}'.")
                    self.send_json({"success": True, "credential": sanitize_ssh_credential(vault["nodes"][node_id])})
                except Exception as e:
                    self.send_json({"error": f"SSH save failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/start":
                try:
                    prune_ssh_sessions()
                    body = json.loads(self.get_post_body())
                    node_id = body.get("node_id")
                    if node_id not in db.data["nodes"]:
                        self.send_json({"error": "Node not found"}, 404)
                        return
                    session_id, output, alive, credential = start_ssh_session(node_id, body)
                    db.log("panel", "info", f"Started interactive SSH terminal for node '{db.data['nodes'][node_id].get('name', node_id)}'.")
                    self.send_json({"success": True, "session_id": session_id, "output": output, "alive": alive, "credential": credential})
                except Exception as e:
                    self.send_json({"error": f"SSH terminal start failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/write":
                try:
                    body = json.loads(self.get_post_body())
                    session_id = body.get("session_id")
                    write_ssh_session(session_id, body.get("data", ""))
                    output, alive = read_ssh_session_output(session_id)
                    self.send_json({"success": True, "output": output, "alive": alive})
                except Exception as e:
                    self.send_json({"error": f"SSH terminal write failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/read":
                try:
                    body = json.loads(self.get_post_body())
                    output, alive = read_ssh_session_output(body.get("session_id"))
                    self.send_json({"success": True, "output": output, "alive": alive})
                except Exception as e:
                    self.send_json({"error": f"SSH terminal read failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/close":
                try:
                    body = json.loads(self.get_post_body())
                    cleanup_ssh_session(body.get("session_id"))
                    self.send_json({"success": True})
                except Exception as e:
                    self.send_json({"error": f"SSH terminal close failed: {e}"}, 400)
                return

            if path == "/api/nodes/ssh/run":
                try:
                    body = json.loads(self.get_post_body())
                    node_id = body.get("node_id")
                    if node_id not in db.data["nodes"]:
                        self.send_json({"error": "Node not found"}, 404)
                        return
                    vault = load_ssh_vault()
                    saved = vault.get("nodes", {}).get(node_id, {})
                    cred = dict(saved)
                    for key in ("host", "port", "username", "auth_method", "password", "private_key", "timeout"):
                        if body.get(key) not in (None, ""):
                            cred[key] = body.get(key)
                    if not cred.get("host"):
                        cred["host"] = db.data["nodes"][node_id].get("ip", "")
                    if body.get("save"):
                        vault.setdefault("nodes", {})[node_id] = dict(cred, saved_at=time.time())
                        save_ssh_vault(vault)
                    result = execute_ssh_command(cred, body.get("command", "uname -a && uptime"))
                    self.send_json({"success": result["success"], "result": result, "credential": sanitize_ssh_credential(cred)})
                except Exception as e:
                    self.send_json({"error": f"SSH command failed: {e}"}, 400)
                return

            if path == "/api/engines/health":
                try:
                    body = json.loads(self.get_post_body())
                    self.send_json(check_engine_health(body.get("engine")))
                except Exception as e:
                    self.send_json({"success": False, "healthy": False, "error": f"Engine health check failed: {e}"}, 400)
                return

            if path == "/api/engines/control":
                try:
                    body = json.loads(self.get_post_body())
                    engine_id = body.get("engine")
                    action = body.get("action")
                    if action not in ("start", "stop", "restart"):
                        self.send_json({"error": "Invalid action"}, 400)
                        return
                    result = control_engine_process(engine_id, action)
                    if not result.get("success"):
                        self.send_json(result, 400)
                        return
                    db.log("panel", "info", f"Engine control: {engine_id} -> {action}.")
                    self.send_json({"success": True, "result": result, "engines": list_engine_status()})
                except Exception as e:
                    self.send_json({"error": f"Engine control failed: {e}"}, 400)
                return

            if path == "/api/engines/upload":
                try:
                    body = json.loads(self.get_post_body())
                    engine_id = body.get("engine")
                    filename = str(body.get("filename") or "")
                    content = base64.b64decode(body.get("content_base64") or "")
                    installed = install_engine_archive(engine_id, filename, content)
                    db.log("panel", "info", f"Manually updated engine {engine_id}: {installed}.")
                    self.send_json({"success": True, "installed": installed, "engines": list_engine_status()})
                except Exception as e:
                    self.send_json({"error": f"Manual engine update failed: {e}"}, 400)
                return

            if path == "/api/runtime/optimize":
                try:
                    body_text = self.get_post_body()
                    body = json.loads(body_text) if body_text else {}
                    action = str(body.get("action", "idle"))
                    scope = str(body.get("scope", "all"))
                    if action not in ("idle", "gc", "all"):
                        self.send_json({"error": "Invalid optimization action"}, 400)
                        return
                    if scope not in ("panel", "nodes", "all"):
                        self.send_json({"error": "Invalid optimization scope"}, 400)
                        return
                    panel_result = optimize_runtime_resources(action) if scope in ("panel", "all") else None
                    queued_nodes = queue_node_optimization(action) if scope in ("nodes", "all") else 0
                    self.send_json({
                        "success": True,
                        "action": action,
                        "scope": scope,
                        "panel": panel_result,
                        "queued_nodes": queued_nodes,
                        "closed_idle_sessions": (panel_result or {}).get("closed_idle_sessions", 0),
                        "gc_collected": (panel_result or {}).get("gc_collected", 0),
                        "rss_kb": (panel_result or {}).get("rss_kb", get_own_rss_kb())
                    })
                except Exception as e:
                    self.send_json({"error": f"Optimization failed: {e}"}, 500)
                return

            if path == "/api/nodes":
                try:
                    body = json.loads(self.get_post_body())
                    name = body.get("name")
                    role = body.get("role")
                    ip = body.get("ip")
                    tags = normalize_tags(body.get("tags"))

                    role = normalize_role(role)
                    if not name or role not in ("internal", "external") or not ip:
                        self.send_json({"error": "Missing parameters"}, 400)
                        return
                    if len(str(name)) > 80 or len(str(ip)) > 255:
                        self.send_json({"error": "Invalid node name or IP"}, 400)
                        return
                    node_id = f"node_{str(uuid.uuid4())[:8]}"
                    node_token = f"tok_{secrets.token_hex(8)}"
                    private_key, public_key = make_node_keypair()
                    db.data["nodes"][node_id] = {
                        "name": name,
                        "role": role,
                        "ip": ip,
                        "token": node_token,
                        "public_key": public_key,
                        "private_key": private_key,
                        "status": "offline",
                        "last_seen": 0,
                        "tags": tags,
                        "stats": {}
                    }
                    db.save()
                    db.log("panel", "info", f"Registered new node '{name}' ({role.upper()}) at IP {ip}.")
                    self.send_json({"success": True, "node_id": node_id, "token": node_token, "private_key": private_key, "public_key": public_key})
                except Exception:
                    self.send_json({"error": "Bad request"}, 400)
                return

            if path == "/api/nodes/edit":
                try:
                    body = json.loads(self.get_post_body())
                    node_id = body.get("id")
                    name = body.get("name")
                    role = body.get("role")
                    ip = body.get("ip")
                    tags = normalize_tags(body.get("tags"))

                    if not node_id or node_id not in db.data["nodes"]:
                        self.send_json({"error": "Node not found"}, 404)
                        return

                    role = normalize_role(role)
                    if not name or role not in ("internal", "external") or not ip:
                        self.send_json({"error": "Missing parameters"}, 400)
                        return
                        
                    node = db.data["nodes"][node_id]
                    node["name"] = name
                    node["role"] = role
                    node["ip"] = ip
                    node["tags"] = tags
                    db.save()
                    db.log("panel", "info", f"Edited node '{name}' ({role.upper()}) at IP {ip}.")
                    self.send_json({"success": True})
                except Exception:
                    self.send_json({"error": "Bad request"}, 400)
                return

            if path == "/api/nodes/register":
                try:
                    body = json.loads(self.get_post_body())
                    api_key = body.get("api_key")
                    expected_key = db.data["settings"].get("node_api_key") or NODE_ENROLLMENT_API_KEY
                    if not expected_key or not hmac.compare_digest(str(api_key or ""), str(expected_key)):
                        self.send_json({"error": "Invalid node API key"}, 401)
                        return
                    name = body.get("name") or f"node-{str(uuid.uuid4())[:8]}"
                    role = normalize_role(body.get("role"))
                    ip = body.get("ip") or self.client_address[0]
                    tags = normalize_tags(body.get("tags"))
                    if role not in ("internal", "external"):
                        self.send_json({"error": "Invalid node role"}, 400)
                        return
                    node_id = f"node_{str(uuid.uuid4())[:8]}"
                    node_token = f"tok_{secrets.token_hex(8)}"
                    private_key, public_key = make_node_keypair()
                    db.data["nodes"][node_id] = {
                        "name": str(name)[:80],
                        "role": role,
                        "ip": str(ip)[:255],
                        "token": node_token,
                        "public_key": public_key,
                        "private_key": private_key,
                        "status": "offline",
                        "last_seen": 0,
                        "tags": tags,
                        "stats": {}
                    }
                    db.save()
                    db.log("panel", "info", f"Node self-registered as '{name}' ({role}).")
                    self.send_json({"success": True, "node_id": node_id, "token": node_token, "private_key": private_key, "public_key": public_key})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/nodes/auto":
                try:
                    created = []
                    existing_names = {n.get("name") for n in db.data["nodes"].values()}
                    
                    internal_idx = 1
                    while f"INTERNAL-Node-{internal_idx}" in existing_names:
                        internal_idx += 1
                    internal_name = f"INTERNAL-Node-{internal_idx}"
                    
                    external_idx = 1
                    while f"EXTERNAL-Node-{external_idx}" in existing_names:
                        external_idx += 1
                    external_name = f"EXTERNAL-Node-{external_idx}"
                    
                    presets = [
                        (internal_name, "internal", "10.10.10.10"),
                        (external_name, "external", "20.20.20.20")
                    ]
                    
                    for name, role, ip in presets:
                        node_id = f"node_{str(uuid.uuid4())[:8]}"
                        node_token = f"tok_{secrets.token_hex(8)}"
                        private_key, public_key = make_node_keypair()
                        db.data["nodes"][node_id] = {
                            "name": name,
                            "role": role,
                            "ip": ip,
                            "token": node_token,
                            "public_key": public_key,
                            "private_key": private_key,
                            "status": "offline",
                            "last_seen": 0,
                            "tags": [],
                            "stats": {}
                        }
                        created.append({"node_id": node_id, "name": name, "role": role, "ip": ip, "token": node_token, "private_key": private_key, "public_key": public_key})
                    db.save()
                    db.log("panel", "info", f"Auto-registered {len(created)} starter nodes.")
                    self.send_json({"success": True, "created": created})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path in ("/api/links", "/api/links/edit"):
                try:
                    body = json.loads(self.get_post_body())
                    edit_mode = path == "/api/links/edit"
                    link_id = body.get("id") if edit_mode else f"link_{str(uuid.uuid4())[:8]}"
                    existing_link = db.data["links"].get(link_id, {}) if edit_mode else {}
                    if edit_mode and not existing_link:
                        self.send_json({"error": "Link not found"}, 404)
                        return
                    name = body.get("name")
                    internal_node_id = body.get("internal_node_id") or body.get("iran_node_id")
                    external_node_id = body.get("external_node_id") or body.get("foreign_node_id")
                    profile_id = body.get("profile_id", "custom")
                    profiles = db.data["settings"].get("tunnel_profiles", default_tunnel_profiles())
                    profile = profiles.get(profile_id, {}) if profile_id != "custom" else {}
                    bridge_port = int(body.get("bridge_port", 7000))
                    sync_port = int(body.get("sync_port", 7001))
                    pool_size = clamp_int(body.get("pool_size", profile.get("pool_size", 100)), 100, 1, 500)

                    engine = body.get("engine") or profile.get("engine", "builtin")
                    transport = body.get("transport") or profile.get("transport", profile.get("tunnel_mode", "tcp"))
                    network = body.get("network") or profile.get("network", "tcp")
                    tunnel_mode = body.get("tunnel_mode") or profile.get("tunnel_mode", "tcp")
                    tls_enabled = bool(body.get("tls_enabled", profile.get("tls_enabled", False)))
                    tls_sni = body.get("tls_sni") or profile.get("tls_sni", profile.get("obfs_host", "speedtest.net"))
                    obfs_host = body.get("obfs_host") or profile.get("obfs_host", "speedtest.net")
                    obfs_path = body.get("obfs_path") or profile.get("obfs_path", "/tunnel")
                    tags = normalize_tags(body.get("tags", existing_link.get("tags", [])))
                    padding_min = clamp_int(body.get("padding_min", profile.get("padding_min", 0)), 0, 0, 4096)
                    padding_max = clamp_int(body.get("padding_max", profile.get("padding_max", 0)), 0, 0, 4096)
                    jitter_ms = clamp_int(body.get("jitter_ms", profile.get("jitter_ms", 0)), 0, 0, 5000)
                    keepalive_interval = clamp_int(body.get("keepalive_interval", profile.get("keepalive_interval", 25)), 25, 5, 300)
                    xray_protocol = body.get("xray_protocol") or profile.get("xray_protocol", "vless")
                    xray_security = body.get("xray_security") or profile.get("xray_security", "reality")
                    xray_flow = body.get("xray_flow") or profile.get("xray_flow", "xtls-rprx-vision")
                    xray_uuid = body.get("xray_uuid") or str(uuid.uuid4())
                    xray_sni = body.get("xray_sni") or profile.get("xray_sni", "www.microsoft.com")
                    xray_shortid = body.get("xray_shortid") or profile.get("xray_shortid", secrets.token_hex(8))
                    
                    xray_private_key = body.get("xray_private_key") or profile.get("xray_private_key", "")
                    xray_public_key = body.get("xray_public_key") or profile.get("xray_public_key", "")
                    
                    if not xray_private_key or not xray_public_key:
                        try:
                            # Generate a x25519 key pair if Xray is available, else use a placeholder
                            if os.path.exists("engines/xray"):
                                out = subprocess.run(["engines/xray", "x25519"], capture_output=True, text=True).stdout
                                for line in out.splitlines():
                                    if "Private key:" in line: xray_private_key = line.split("Private key:")[1].strip()
                                    if "Public key:" in line: xray_public_key = line.split("Public key:")[1].strip()
                            else:
                                xray_private_key = "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM="
                                xray_public_key = "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM="
                        except:
                            xray_private_key = "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM="
                            xray_public_key = "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM="

                    if not name or internal_node_id not in db.data["nodes"] or external_node_id not in db.data["nodes"]:
                        self.send_json({"error": "Invalid nodes chosen"}, 400)
                        return
                    if not role_matches(db.data["nodes"][internal_node_id].get("type", db.data["nodes"][internal_node_id].get("role", "unknown")), "internal") or not role_matches(db.data["nodes"][external_node_id].get("type", db.data["nodes"][external_node_id].get("role", "unknown")), "external"):
                        self.send_json({"error": "Internal and external node roles are required"}, 400)
                        return
                    if not valid_port(bridge_port) or not valid_port(sync_port) or bridge_port == sync_port:
                        self.send_json({"error": "Invalid bridge or sync port"}, 400)
                        return
                    if engine not in ("builtin", "gost", "backhaul", "rathole", "chisel", "frp", "xray", "muxquantum", "hysteria2", "singbox", "tuic", "naiveproxy", "shadowtls", "brook", "mieru"):
                        self.send_json({"error": "Invalid tunnel engine"}, 400)
                        return
                    if tunnel_mode not in ("tcp", "udp", "websocket", "http_obfs", "grpc", "tcpmux", "wsmux", "tcp_udp", "kcp", "quic", "vless_reality", "reality_grpc", "reality_h2", "reality_ws", "httpsmux", "quantummux", "tunmux", "mux_wss", "mux_h2", "mux_h3", "mux_quic", "mux_grpc", "mux_shadowtls", "mux_reality", "mux_anytls", "mux_naive", "mux_kcp", "shadowtls", "shadowtls_ws", "shadowtls_h2", "tuic_quic", "naive_https", "naive_h2", "http2_tls", "http3_masquerade", "hysteria2_salamander", "hysteria2_gecko", "anytls", "anytls_h2", "anytls_ws", "ech_tls", "ech_h2"):
                        self.send_json({"error": "Invalid tunnel mode"}, 400)
                        return
                    if transport not in ("tcp", "udp", "ws", "wss", "websocket", "wsmux", "grpc", "tcpmux", "kcp", "quic", "httpsmux", "quantummux", "tunmux", "mux_wss", "mux_h2", "mux_h3", "mux_quic", "mux_grpc", "mux_shadowtls", "mux_reality", "mux_anytls", "mux_naive", "mux_kcp", "h2", "h3", "shadowtls", "tuic", "naive", "anytls", "ech"):
                        self.send_json({"error": "Invalid transport"}, 400)
                        return
                    if network not in ("tcp", "udp", "tcp_udp"):
                        self.send_json({"error": "Invalid network"}, 400)
                        return
                    if len(str(name)) > 100 or len(str(obfs_host)) > 255 or not str(obfs_path).startswith("/"):
                        self.send_json({"error": "Invalid tunnel metadata"}, 400)
                        return

                    for lid, l in db.data["links"].items():
                        if edit_mode and lid == link_id:
                            continue
                        if l.get("internal_node_id", l.get("iran_node_id")) == internal_node_id:
                            if l["bridge_port"] == bridge_port or l["sync_port"] == sync_port:
                                self.send_json({"error": "Bridge or Sync port is already occupied on Iran node"}, 400)
                                return

                    db.data["links"][link_id] = {
                        "name": name,
                        "internal_node_id": internal_node_id,
                        "external_node_id": external_node_id,
                        "iran_node_id": internal_node_id,
                        "foreign_node_id": external_node_id,
                        "bridge_port": bridge_port,
                        "sync_port": sync_port,
                        "pool_size": pool_size,
                        "engine": engine,
                        "transport": transport,
                        "network": network,
                        "tunnel_mode": tunnel_mode,
                        "tls_enabled": tls_enabled,
                        "tls_sni": tls_sni,
                        "obfs_host": obfs_host,
                        "obfs_path": obfs_path,
                        "profile_id": profile_id,
                        "tags": tags,
                        "padding_min": padding_min,
                        "padding_max": max(padding_min, padding_max),
                        "jitter_ms": jitter_ms,
                        "keepalive_interval": keepalive_interval,
                        "xray_protocol": xray_protocol,
                        "xray_security": xray_security,
                        "xray_flow": xray_flow,
                        "xray_uuid": xray_uuid,
                        "xray_sni": xray_sni,
                        "xray_shortid": xray_shortid,
                        "xray_public_key": xray_public_key,
                        "xray_private_key": xray_private_key,
                        "paused": bool(existing_link.get("paused", False)),
                        "ports": existing_link.get("ports", [])
                    }
                    db.save()
                    db.log("panel", "info", f"{'Updated' if edit_mode else 'Created'} tunnel link '{name}' (Mode: {tunnel_mode}, TLS: {tls_enabled}).")
                    self.send_json({"success": True, "link_id": link_id})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/links/ports/edit":
                try:
                    link_id = query.get("id", [""])[0]
                    body = json.loads(self.get_post_body())
                    index = int(body.get("index", -1))
                    user_port = int(str(body.get("user_port", "")).strip())
                    target_port = int(str(body.get("target_port", "")).strip())
                    if link_id not in db.data["links"]:
                        self.send_json({"error": "Link not found"}, 404)
                        return
                    if not valid_port(user_port) or not valid_port(target_port):
                        self.send_json({"error": "Invalid port value"}, 400)
                        return
                    link = db.data["links"][link_id]
                    if not (0 <= index < len(link.get("ports", []))):
                        self.send_json({"error": "Invalid mapping index"}, 400)
                        return
                    duplicate = any(int(p.get("user_port", 0)) == user_port and i != index for i, p in enumerate(link.get("ports", [])))
                    if duplicate:
                        self.send_json({"error": "Internal input port is already mapped in this tunnel"}, 400)
                        return
                    old = dict(link["ports"][index])
                    link["ports"][index] = {"user_port": user_port, "target_port": target_port}
                    db.save()
                    db.log("panel", "info", f"Edited port mapping {old.get('user_port')} -> {old.get('target_port')} to {user_port} -> {target_port} in tunnel '{link['name']}'.")
                    self.send_json({"success": True, "mapping": link["ports"][index]})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/links/ports":
                try:
                    link_id = query.get("id")[0]
                    body = json.loads(self.get_post_body())
                    u_port_str = str(body.get("user_port")).strip()
                    t_port_str = str(body.get("target_port")).strip()

                    if link_id not in db.data["links"]:
                        self.send_json({"error": "Link not found"}, 404)
                        return

                    link = db.data["links"][link_id]
                    
                    def parse_range(pstr):
                        if "-" in pstr:
                            parts = pstr.split("-")
                            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                                return int(parts[0]), int(parts[1])
                        elif pstr.isdigit():
                            return int(pstr), int(pstr)
                        return None, None

                    u_start, u_end = parse_range(u_port_str)
                    t_start, t_end = parse_range(t_port_str)

                    if None in (u_start, u_end, t_start, t_end) or not (valid_port(u_start) and valid_port(u_end) and valid_port(t_start) and valid_port(t_end)):
                        self.send_json({"error": "Invalid port value or range"}, 400)
                        return
                    
                    if (u_end - u_start) != (t_end - t_start):
                        self.send_json({"error": "Port ranges must be of equal length"}, 400)
                        return

                    if (u_end - u_start) > 200:
                        self.send_json({"error": "Range too large. Max 200 ports at once."}, 400)
                        return

                    existing_ports = {p["user_port"] for p in link["ports"]}
                    
                    added = 0
                    for offset in range((u_end - u_start) + 1):
                        curr_u = u_start + offset
                        curr_t = t_start + offset
                        if curr_u not in existing_ports:
                            link["ports"].append({"user_port": curr_u, "target_port": curr_t})
                            added += 1

                    db.save()
                    db.log("panel", "info", f"Mapped {added} ports from range {u_port_str} -> {t_port_str} in tunnel '{link['name']}'.")
                    self.send_json({"success": True, "added": added})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/sync/xui":
                try:
                    body = json.loads(self.get_post_body())
                    link_id = body.get("link_id")
                    xui_url = body.get("url", "").rstrip("/")
                    xui_user = body.get("username")
                    xui_pass = body.get("password")
                    
                    if not link_id or link_id not in db.data["links"]:
                        self.send_json({"error": "Link not found"}, 404)
                        return
                    if not xui_url or not xui_user or not xui_pass:
                        self.send_json({"error": "Missing X-UI credentials"}, 400)
                        return

                    import urllib.request, urllib.parse, urllib.error
                    
                    # 1. Login
                    login_data = urllib.parse.urlencode({"username": xui_user, "password": xui_pass}).encode('utf-8')
                    login_req = urllib.request.Request(f"{xui_url}/login", data=login_data)
                    # Ignore SSL errors if using fake certs
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    try:
                        resp = urllib.request.urlopen(login_req, context=ctx, timeout=10)
                        cookie = resp.headers.get('Set-Cookie')
                        if not cookie:
                            self.send_json({"error": "Login failed (No cookie returned)"}, 401)
                            return
                    except Exception as e:
                        self.send_json({"error": f"Failed to connect or login to X-UI: {e}"}, 400)
                        return

                    # 2. Fetch inbounds
                    list_req = urllib.request.Request(f"{xui_url}/panel/api/inbounds/list")
                    list_req.add_header('Cookie', cookie)
                    list_req.add_header('Accept', 'application/json')
                    
                    try:
                        resp = urllib.request.urlopen(list_req, context=ctx, timeout=10)
                        data = json.loads(resp.read().decode('utf-8'))
                        if not data.get("success"):
                            self.send_json({"error": "Failed to fetch inbounds from X-UI API"}, 400)
                            return
                        inbounds = data.get("obj", [])
                    except Exception as e:
                        self.send_json({"error": f"Failed to fetch inbounds: {e}"}, 400)
                        return

                    # 3. Extract active ports
                    ports = set()
                    for ib in inbounds:
                        if ib.get("enable"):
                            ports.add(int(ib.get("port")))
                    
                    if not ports:
                        self.send_json({"error": "No active inbounds found in X-UI panel"}, 400)
                        return

                    # 4. Map ports on the link
                    link = db.data["links"][link_id]
                    existing_ports = {p["user_port"] for p in link.get("ports", [])}
                    
                    added = 0
                    for port in ports:
                        if port not in existing_ports:
                            link.setdefault("ports", []).append({"user_port": port, "target_port": port})
                            added += 1

                    db.save()
                    db.log("panel", "info", f"Synced {added} new ports from X-UI panel to link '{link['name']}'.")
                    self.send_json({"success": True, "added": added, "total": len(ports)})
                except Exception as e:
                    self.send_json({"error": f"Error parsing request or syncing: {e}"}, 400)
                return

            if path == "/api/settings/network":
                try:
                    body = json.loads(self.get_post_body())
                    disable_ipv6 = body.get("disable_ipv6", False)
                    engine_restart_interval = body.get("engine_restart_interval", 0)
                    
                    db.data["settings"]["disable_ipv6"] = disable_ipv6
                    db.data["settings"]["engine_restart_interval"] = engine_restart_interval
                    db.save()
                    
                    ipv6_result = apply_ipv6_disabled(disable_ipv6)
                    db.log("panel", "info", f"Network settings updated. disable_ipv6={disable_ipv6}, engine_restart_interval={engine_restart_interval}, ipv6_applied={ipv6_result['success']}.")
                        
                    self.send_json({"success": True, "ipv6": ipv6_result, "engine_restart_interval": engine_restart_interval})
                except Exception as e:
                    self.send_json({"error": f"Failed: {e}"}, 500)
                return

            if path == "/api/settings/password":
                try:
                    body = json.loads(self.get_post_body())
                    username = body.get("username")
                    password = body.get("password")
                    if not username or not password:
                        self.send_json({"error": "Missing parameters"}, 400)
                        return

                    db.data["admin"]["username"] = username
                    db.data["admin"]["password_hash"] = hashlib.sha256(password.encode()).hexdigest()
                    db.save()
                    active_sessions.clear()
                    db.log("panel", "info", f"Admin credentials updated. Username changed to '{username}'. Sessions cleared.")
                    self.send_json({"success": True})
                except Exception:
                    self.send_json({"error": "Bad request"}, 400)
                return

            if path == "/api/settings/tls":
                try:
                    body = json.loads(self.get_post_body())
                    panel_tls = True
                    cert_path = body.get("cert_path", f"{CONFIG_DIR}/certs/cert.pem")
                    key_path = body.get("key_path", f"{CONFIG_DIR}/certs/key.pem")
                    if not cert_path or not key_path or not os.path.isfile(cert_path) or not os.path.isfile(key_path):
                        host = body.get("host") or db.data["settings"].get("panel_host") or "localhost"
                        cert_path, key_path = generate_local_panel_certificate(host, cert_path, key_path)
                        db.data["settings"]["cert_auto_generated"] = True
                    else:
                        db.data["settings"]["cert_auto_generated"] = False
                    db.data["settings"]["panel_tls"] = panel_tls
                    db.data["settings"]["cert_path"] = cert_path
                    db.data["settings"]["key_path"] = key_path
                    db.save()
                    db.log("panel", "info", "Panel SSL/TLS settings updated.")
                    self.send_json({"success": True})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/settings/security":
                try:
                    body = json.loads(self.get_post_body())
                    enable_2fa = bool(body.get("two_factor_enabled", False))
                    enable_bio = bool(body.get("biometric_enabled", False))
                    if enable_2fa and not db.data["settings"].get("two_factor_secret"):
                        db.data["settings"]["two_factor_secret"] = make_totp_secret()
                    db.data["settings"]["two_factor_enabled"] = enable_2fa
                    db.data["settings"]["biometric_enabled"] = enable_bio
                    db.save()
                    db.log("panel", "info", f"Security options updated. 2FA={enable_2fa}, biometric={enable_bio}.")
                    self.send_json({
                        "success": True,
                        "two_factor_secret": db.data["settings"].get("two_factor_secret", "") if enable_2fa else ""
                    })
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/certificates/local":
                try:
                    body = json.loads(self.get_post_body())
                    host = normalize_cert_host(body.get("host", "localhost"))
                    if not host:
                        self.send_json({"error": "Valid IP or hostname is required"}, 400)
                        return
                    cert_path, key_path = generate_local_panel_certificate(host)
                    db.data["settings"]["cert_path"] = cert_path
                    db.data["settings"]["key_path"] = key_path
                    db.data["settings"]["panel_tls"] = True
                    db.data["settings"]["cert_auto_generated"] = True
                    db.save()
                    db.log("panel", "info", f"Generated local SSL certificate for {host}.")
                    self.send_json({"success": True, "cert_path": cert_path, "key_path": key_path})
                except FileNotFoundError:
                    self.send_json({"error": "openssl command not found"}, 500)
                except Exception as e:
                    self.send_json({"error": f"Local certificate failed: {e}"}, 500)
                return

            if path == "/api/profiles":
                try:
                    body = json.loads(self.get_post_body())
                    profile_id = str(body.get("id") or f"custom_{str(uuid.uuid4())[:8]}")
                    profile_id = "".join(ch for ch in profile_id if ch.isalnum() or ch in ("_", "-"))[:40] or f"custom_{str(uuid.uuid4())[:8]}"
                    profiles, _ = ensure_tunnel_profiles()
                    profiles[profile_id] = {
                        "name": str(body.get("name", profile_id))[:80],
                        "engine": body.get("engine", "builtin"),
                        "transport": body.get("transport", body.get("tunnel_mode", "websocket")),
                        "network": body.get("network", "tcp"),
                        "tunnel_mode": body.get("tunnel_mode", "websocket"),
                        "tls_enabled": bool(body.get("tls_enabled", True)),
                        "pool_size": clamp_int(body.get("pool_size", 100), 100, 1, 500),
                        "obfs_host": str(body.get("obfs_host", "speedtest.net"))[:255],
                        "obfs_path": str(body.get("obfs_path", "/tunnel"))[:255],
                        "padding_min": clamp_int(body.get("padding_min", 0), 0, 0, 4096),
                        "padding_max": clamp_int(body.get("padding_max", 64), 64, 0, 4096),
                        "jitter_ms": clamp_int(body.get("jitter_ms", 0), 0, 0, 5000),
                        "keepalive_interval": clamp_int(body.get("keepalive_interval", 25), 25, 5, 300)
                    }
                    if profiles[profile_id]["engine"] not in ("builtin", "gost", "backhaul", "rathole", "chisel", "frp", "xray", "muxquantum", "hysteria2", "singbox", "tuic", "naiveproxy", "shadowtls", "brook", "mieru"):
                        self.send_json({"error": "Invalid tunnel engine"}, 400)
                        return
                    if profiles[profile_id]["tunnel_mode"] not in ("tcp", "udp", "websocket", "http_obfs", "grpc", "tcpmux", "wsmux", "tcp_udp", "kcp", "quic", "vless_reality", "reality_grpc", "reality_h2", "reality_ws", "httpsmux", "quantummux", "tunmux", "mux_wss", "mux_h2", "mux_h3", "mux_quic", "mux_grpc", "mux_shadowtls", "mux_reality", "mux_anytls", "mux_naive", "mux_kcp", "shadowtls", "shadowtls_ws", "shadowtls_h2", "tuic_quic", "naive_https", "naive_h2", "http2_tls", "http3_masquerade", "hysteria2_salamander", "hysteria2_gecko", "anytls", "anytls_h2", "anytls_ws", "ech_tls", "ech_h2"):
                        self.send_json({"error": "Invalid tunnel mode"}, 400)
                        return
                    if profiles[profile_id]["transport"] not in ("tcp", "udp", "ws", "wss", "websocket", "wsmux", "grpc", "tcpmux", "kcp", "quic", "httpsmux", "quantummux", "tunmux", "mux_wss", "mux_h2", "mux_h3", "mux_quic", "mux_grpc", "mux_shadowtls", "mux_reality", "mux_anytls", "mux_naive", "mux_kcp", "h2", "h3", "shadowtls", "tuic", "naive", "anytls", "ech"):
                        self.send_json({"error": "Invalid transport"}, 400)
                        return
                    if not profiles[profile_id]["obfs_path"].startswith("/"):
                        profiles[profile_id]["obfs_path"] = "/" + profiles[profile_id]["obfs_path"]
                    profiles[profile_id]["padding_max"] = max(profiles[profile_id]["padding_min"], profiles[profile_id]["padding_max"])
                    db.save()
                    db.log("panel", "info", f"Saved tunnel profile '{profiles[profile_id]['name']}'.")
                    self.send_json({"success": True, "profile_id": profile_id, "profiles": profiles})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/profiles/import":
                try:
                    body = json.loads(self.get_post_body())
                    incoming = body.get("profiles", body)
                    if not isinstance(incoming, dict):
                        self.send_json({"error": "Invalid profile bundle"}, 400)
                        return
                    profiles = db.data["settings"].setdefault("tunnel_profiles", default_tunnel_profiles())
                    for profile_id, profile in incoming.items():
                        if isinstance(profile, dict):
                            safe_id = "".join(ch for ch in str(profile_id) if ch.isalnum() or ch in ("_", "-"))[:40]
                            if safe_id:
                                profiles[safe_id] = profile
                    db.save()
                    db.log("panel", "info", "Imported tunnel profile bundle.")
                    self.send_json({"success": True, "profiles": profiles})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/certificates/generate":
                try:
                    body = json.loads(self.get_post_body())
                    domain = body.get("domain")
                    email = body.get("email")

                    if not domain or not email:
                        self.send_json({"error": "Domain and email are required"}, 400)
                        return

                    # Create ACME directory
                    acme_root = f"{CONFIG_DIR}/acme_webroot"
                    os.makedirs(f"{acme_root}/.well-known/acme-challenge", exist_ok=True)

                    # Ensure certbot is installed
                    subprocess.run(["apt-get", "update", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["apt-get", "install", "-y", "certbot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    # Run certbot in webroot mode securely
                    cmd = [
                        "certbot", "certonly", "--webroot",
                        "-w", acme_root,
                        "-d", domain,
                        "--agree-tos",
                        "--non-interactive"
                    ]
                    if email:
                        cmd.extend(["--email", email])
                    else:
                        cmd.append("--register-unsafely-without-email")
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if res.returncode == 0:
                        # Copy generated certs to CONFIG_DIR/certs
                        os.makedirs(f"{CONFIG_DIR}/certs", exist_ok=True)
                        import shutil
                        shutil.copy(f"/etc/letsencrypt/live/{domain}/fullchain.pem", f"{CONFIG_DIR}/certs/cert.pem")
                        shutil.copy(f"/etc/letsencrypt/live/{domain}/privkey.pem", f"{CONFIG_DIR}/certs/key.pem")
                        
                        db.data["settings"]["cert_path"] = f"{CONFIG_DIR}/certs/cert.pem"
                        db.data["settings"]["key_path"] = f"{CONFIG_DIR}/certs/key.pem"
                        db.data["settings"]["panel_tls"] = True
                        db.data["settings"]["cert_auto_generated"] = False
                        db.save()
                        
                        db.log("panel", "info", f"Successfully generated SSL certificate for '{domain}' via Let's Encrypt.")
                        self.send_json({"success": True})
                    else:
                        db.log("panel", "error", f"Certbot failed: {res.stderr}")
                        self.send_json({"error": f"Certbot execution failed: {res.stderr}"}, 500)
                except Exception as e:
                    self.send_json({"error": f"Internal error: {e}"}, 500)
                return

            if path == "/api/engines/install":
                try:
                    body = json.loads(self.get_post_body())
                    engine_type = body.get("engine")
                    version = body.get("version", "latest")
                    
                    if engine_type not in ENGINE_CATALOG or engine_type == "muxquantum":
                        self.send_json({"error": "Engine type not supported"}, 400)
                        return

                    def do_install_engine():
                        try:
                            script_path = "/app/download_engines.py" if os.path.exists("/app/download_engines.py") else os.path.join(os.getcwd(), "download_engines.py")
                            if not os.path.exists(script_path):
                                raise RuntimeError("download_engines.py is not available in this image")
                            cmd = [sys.executable, script_path, "--engine", engine_type]
                            db.log("panel", "info", f"Installing/updating engine {engine_type} from GitHub releases...")
                            res = subprocess.run(cmd, cwd="/app" if os.path.exists("/app") else os.getcwd(), capture_output=True, text=True, timeout=240)
                            if res.returncode != 0:
                                raise RuntimeError((res.stderr or res.stdout)[-2000:])
                            db.log("panel", "info", f"Successfully installed engine {engine_type}: {(res.stdout or '').splitlines()[-3:]}")
                        except Exception as e:
                            db.log("panel", "error", f"Failed to install engine {engine_type}: {e}")

                    threading.Thread(target=do_install_engine, daemon=True).start()
                    self.send_json({"success": True, "engine": engine_type, "version": version})
                except Exception as e:
                    self.send_json({"error": f"Bad request: {e}"}, 400)
                return

            if path == "/api/settings/restart":
                def do_restart():
                    time.sleep(1)
                    db.log("panel", "info", "Restarting P00RIJA PANEL server to apply changes...")
                    # Sanitize sys.argv for safe exec
                    safe_args = [sys.executable, os.path.abspath(__file__)]
                    if "--panel" in sys.argv: safe_args.append("--panel")
                    if "--internal" in sys.argv: safe_args.append("--internal")
                    if "--external" in sys.argv: safe_args.append("--external")
                    os.execv(sys.executable, safe_args)
                
                threading.Thread(target=do_restart, daemon=True).start()
                self.send_json({"success": True})
                return

        if path.startswith("/api/"):
            self.send_json({"error": "API endpoint not found", "method": "POST", "path": path}, 404)
            return
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed_url = urlparse(self.path)
        path = normalize_request_path(parsed_url.path)
        query = parse_qs(parsed_url.query)

        if path.startswith("/api/"):
            if not self.check_auth():
                self.send_json({"error": "Unauthorized"}, 401)
                return

            if path == "/api/nodes":
                node_id = query.get("id", [""])[0]
                if node_id in db.data["nodes"]:
                    node = db.data["nodes"].pop(node_id)
                    for lid in list(db.data["links"].keys()):
                        l = db.data["links"][lid]
                        if l["iran_node_id"] == node_id or l["foreign_node_id"] == node_id:
                            db.data["links"].pop(lid)
                    db.save()
                    db.log("panel", "info", f"Deleted node '{node['name']}' and its associated tunnel links.")
                    self.send_json({"success": True})
                else:
                    self.send_json({"error": "Node not found"}, 404)
                return

            if path == "/api/links":
                link_id = query.get("id", [""])[0]
                if link_id in db.data["links"]:
                    link = db.data["links"].pop(link_id)
                    db.save()
                    db.log("panel", "info", f"Deleted tunnel link '{link['name']}'.")
                    self.send_json({"success": True})
                else:
                    self.send_json({"error": "Link not found"}, 404)
                return

            if path == "/api/links/ports":
                link_id = query.get("id", [""])[0]
                try:
                    index = int(query.get("index", ["-1"])[0])
                except Exception:
                    index = -1
                if link_id in db.data["links"]:
                    link = db.data["links"][link_id]
                    if 0 <= index < len(link["ports"]):
                        removed = link["ports"].pop(index)
                        db.save()
                        db.log("panel", "info", f"Removed port mapping {removed['user_port']} -> {removed['target_port']} from tunnel '{link['name']}'.")
                        self.send_json({"success": True})
                    else:
                        self.send_json({"error": "Invalid mapping index"}, 400)
                else:
                        self.send_json({"error": "Link not found"}, 404)
                return

            if path == "/api/runtime/sessions":
                session_id = query.get("id", [""])[0]
                if close_runtime_session(session_id):
                    db.log("panel", "warning", f"Closed runtime bridge session {session_id}.")
                    self.send_json({"success": True})
                else:
                    self.send_json({"error": "Session not found"}, 404)
                return

            if path == "/api/runtime/processes":
                # Removed dangerous arbitrary process termination endpoint
                self.send_json({"error": "This endpoint has been disabled for security reasons"}, 403)
                return

        if path.startswith("/api/"):
            self.send_json({"error": "API endpoint not found", "method": "DELETE", "path": path}, 404)
            return
        self.send_response(404)
        self.end_headers()

# --------- CLI Setup Wizard ----------
def start_setup_wizard():
    print("==================================================")
    print("           P00RIJA TUNNEL Setup Wizard            ")
    print("==================================================")
    print("Please select the role of this server:")
    print("1) Panel (Central management web console)")
    print("2) Internal Node (Handles local entry listeners)")
    print("3) External Node (Establish reverse tunnels to internal nodes)")
    role_choice = input("Selection (1-3): ").strip()

    if role_choice == "1":
        import random
        rand_port = random.randint(10000, 60000)
        port_input = input(f"Web panel port (default: {rand_port}): ").strip()
        port = int(port_input) if port_input else rand_port
        
        api_port_input = input("Node API port (default: 8000): ").strip()
        api_port = int(api_port_input) if api_port_input else 8000
        
        username = input("Admin username (default: admin): ").strip() or "admin"
        password = ""
        while not password:
            password = input("Admin password (required): ").strip()
        
        config = {
            "role": "panel",
            "port": port,
            "api_port": api_port
        }
        db.data["settings"]["port"] = port
        db.data["settings"]["api_port"] = api_port
        db.data["admin"]["username"] = username
        db.data["admin"]["password_hash"] = hashlib.sha256(password.encode()).hexdigest()
        db.save()
        
    elif role_choice in ("2", "3"):
        role = "internal" if role_choice == "2" else "external"
        panel_url = ""
        while not panel_url:
            panel_url = input("Web Panel API URL (e.g. http://1.2.3.4:8080): ").strip()
        token = ""
        while not token:
            token = input("Node Token (from the Panel UI): ").strip()

        config = {
            "role": role,
            "panel_url": panel_url.rstrip("/"),
            "token": token
        }
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Configuration written to {CONFIG_PATH}. Start container/service to run.")

# --------- Main Entry Point ----------
def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        start_setup_wizard()
        sys.exit(0)

    if not os.path.exists(CONFIG_PATH):
        if sys.stdin.isatty():
            start_setup_wizard()
        else:
            print(f"Error: configuration file '{CONFIG_PATH}' not found. Run with --setup first.")
            sys.exit(1)

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    role = config.get("role")
    
    if role == "panel":
        port = config.get("port", 8080)
        api_port = config.get("api_port")
        max_idle_seconds = db.data["settings"].get("max_idle_seconds", 300)
        try:
            cert_path, key_path = ensure_panel_https_config(config)
        except Exception as e:
            print(f"[PANEL] Fatal: could not prepare HTTPS certificate: {e}", flush=True)
            sys.exit(1)
        start_bridge_monitor(max_idle_seconds)
        
        def run_server(listen_port):
            server_address = ("", listen_port)
            
            try:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
                httpd = P00RIJAAutoTLSServer(server_address, P00RIJAHTTPHandler, ssl_context)
                print(f"[PANEL] Central Management Panel running securely on HTTPS port {listen_port} with HTTP redirect")
            except Exception as e:
                print(f"[PANEL] Fatal: HTTPS is required and TLS setup failed on port {listen_port}: {e}", flush=True)
                raise
                
            db.log("panel", "info", f"P00RIJA PANEL started on port {listen_port}.")
            httpd.serve_forever()

        if api_port and int(api_port) != int(port):
            api_thread = threading.Thread(target=run_server, args=(int(api_port),), daemon=True)
            api_thread.start()

        try:
            run_server(int(port))
        except KeyboardInterrupt:
            print("Shutting down Panel server.")

    elif role in ("iran", "internal"):
        panel_url = config.get("panel_url")
        token = config.get("token")
        private_key = config.get("private_key", "")
        
        max_idle_seconds = float(os.environ.get("P00RIJA_MAX_IDLE", "300"))
        start_bridge_monitor(max_idle_seconds)
        
        controller = IranNodeController(panel_url, token, private_key)
        controller.start()
        print(f"[IR-NODE] Node daemon started. Polling panel: {panel_url}")
        
        while True:
            try: time.sleep(3600)
            except KeyboardInterrupt: break

    elif role in ("eu", "foreign", "external"):
        panel_url = config.get("panel_url")
        token = config.get("token")
        private_key = config.get("private_key", "")
        
        max_idle_seconds = float(os.environ.get("P00RIJA_MAX_IDLE", "300"))
        start_bridge_monitor(max_idle_seconds)
        
        controller = ForeignNodeController(panel_url, token, private_key)
        controller.start()
        print(f"[EXTERNAL-NODE] Node daemon started. Polling panel: {panel_url}")
        
        while True:
            try: time.sleep(3600)
            except KeyboardInterrupt: break

if __name__ == "__main__":
    main()
