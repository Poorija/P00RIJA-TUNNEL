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
import zlib
from queue import Queue, Empty, Full
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from p00rija_core.engines import (
        build_engine_catalog,
        engine_binary_path as core_engine_binary_path,
        list_engine_status as core_list_engine_status,
        control_engine_process as core_control_engine_process,
        check_engine_health as core_check_engine_health,
        install_engine_archive as core_install_engine_archive,
    )
    from p00rija_core.tunnel_methods import (
        EXTRA_ENGINE_CATALOG,
        EXTRA_TUNNEL_ENGINES,
        EXTRA_TUNNEL_MODES,
        EXTRA_TRANSPORTS,
        EXTRA_TUNNEL_PROFILES,
        TUNNEL_OPTION_MATRIX_EXTRA,
        aead_config_for_link,
        amneziawg_config_for_link,
        default_tunnel_profiles,
        ensure_tunnel_profiles as core_ensure_tunnel_profiles,
        hysteria2_config_for_link,
        muxquantum_config_for_link,
        profile_decision_metadata,
        raw_socket_config_for_link,
        rating_level,
        ssh_config_for_link,
        singbox_config_for_link,
        masque_config_for_link,
        stunnel_config_for_link,
        wireguard_config_for_link,
        xray_config_for_link,
    )
    from p00rija_core.security import (
        certificate_is_self_signed,
        generate_local_panel_certificate,
        make_node_keypair,
        make_totp_secret,
        node_public_from_private,
        normalize_cert_host,
        normalize_node_token,
        normalize_role,
        role_matches,
        unique_cert_hosts,
        valid_node_signature,
        verify_totp,
    )
    from p00rija_core.metrics import (
        NetSpeedometer,
        get_cpu_percent,
        get_host_info,
        get_own_rss_kb,
        get_ram_percent,
    )
    from p00rija_core.database import P00RIJADB
    from p00rija_core.api import describe_api_surface, dispatch_dashboard_get, dispatch_node_ssh_request, dispatch_nodes_get, dispatch_nodes_post, dispatch_public_system_get
    from p00rija_core.links_api import dispatch_links_delete, dispatch_links_get, dispatch_links_post
    from p00rija_core.runtime_api import dispatch_runtime_get
    from p00rija_core.backup_migration import (
        build_encrypted_backup,
        list_server_backups,
        migrate_backup_over_ssh,
        normalize_panel_url,
        restore_encrypted_backup,
    )
    from p00rija_core.ui import (
        APP_LOGO_SVG,
        INDEX_HTML,
        PANEL_PAGE_ROUTES,
        build_manifest,
        font_content_type,
        service_worker_script,
    )
    from p00rija_core.system_audit import build_system_audit as core_build_system_audit
    from p00rija_core.engine_updates import check_engine_updates as core_check_engine_updates
    from p00rija_core.versioning import node_version_status
    from p00rija_core.host_control import (
        host_control_available,
        host_control_status,
        submit_host_control,
    )
except Exception:
    build_engine_catalog = None
    core_engine_binary_path = None
    core_list_engine_status = None
    core_control_engine_process = None
    core_check_engine_health = None
    core_install_engine_archive = None
    EXTRA_ENGINE_CATALOG = {}
    EXTRA_TUNNEL_ENGINES = set()
    EXTRA_TUNNEL_MODES = set()
    EXTRA_TRANSPORTS = set()
    EXTRA_TUNNEL_PROFILES = {}
    TUNNEL_OPTION_MATRIX_EXTRA = {}
    aead_config_for_link = None
    amneziawg_config_for_link = None
    default_tunnel_profiles = None
    core_ensure_tunnel_profiles = None
    hysteria2_config_for_link = None
    muxquantum_config_for_link = None
    profile_decision_metadata = None
    raw_socket_config_for_link = None
    rating_level = None
    ssh_config_for_link = None
    stunnel_config_for_link = None
    wireguard_config_for_link = None
    xray_config_for_link = None
    singbox_config_for_link = None
    masque_config_for_link = None
    certificate_is_self_signed = None
    generate_local_panel_certificate = None
    make_node_keypair = None
    make_totp_secret = None
    node_public_from_private = None
    normalize_cert_host = None
    normalize_node_token = None
    normalize_role = None
    role_matches = None
    unique_cert_hosts = None
    valid_node_signature = None
    verify_totp = None
    NetSpeedometer = None
    get_cpu_percent = None
    get_host_info = None
    get_own_rss_kb = None
    get_ram_percent = None
    P00RIJADB = None
    describe_api_surface = lambda: {"route_count": 0, "groups": {}, "routes": []}
    dispatch_dashboard_get = None
    dispatch_node_ssh_request = None
    dispatch_nodes_get = None
    dispatch_nodes_post = None
    dispatch_public_system_get = None
    dispatch_links_delete = None
    dispatch_links_get = None
    dispatch_links_post = None
    dispatch_runtime_get = None
    build_encrypted_backup = None
    list_server_backups = None
    migrate_backup_over_ssh = None
    normalize_panel_url = None
    restore_encrypted_backup = None
    APP_LOGO_SVG = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='12' fill='#07100f'/><path d='M14 25h36M50 25l-8-8M50 25l-8 8M50 39H14M14 39l8-8M14 39l8 8' stroke='#20c7b5' stroke-width='5' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    INDEX_HTML = "<!doctype html><html><head><meta charset='utf-8'><title>P00RIJA TUNNEL</title></head><body><h1>P00RIJA TUNNEL</h1><p>Panel UI module is not available.</p></body></html>"
    PANEL_PAGE_ROUTES = ("/", "/index.html")
    build_manifest = lambda: b"{}"
    font_content_type = lambda path: "application/octet-stream"
    service_worker_script = lambda: b""
    core_build_system_audit = None
    core_check_engine_updates = None
    node_version_status = None
    host_control_available = None
    host_control_status = None
    submit_host_control = None

# --------- Constants & Configuration ----------
CONFIG_DIR = os.environ.get("P00RIJA_CONFIG_DIR", "/opt/p00rija")
CONFIG_PATH = os.environ.get("P00RIJA_CONFIG_PATH", f"{CONFIG_DIR}/p00rija_config.json")
DB_PATH = os.environ.get("P00RIJA_DB_PATH", f"{CONFIG_DIR}/p00rija_db.json")
PANEL_SECRET_PATH = os.environ.get("P00RIJA_PANEL_SECRET_PATH", f"{CONFIG_DIR}/panel_secret")
SSH_VAULT_PATH = os.environ.get("P00RIJA_SSH_VAULT_PATH", f"{CONFIG_DIR}/ssh_credentials.enc")
ENGINES_DIR = os.environ.get("P00RIJA_ENGINES_DIR", "/usr/local/bin")
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
NODE_UPDATE_DIR = os.path.join(CONFIG_DIR, "node_update_packages")
def env_float(name, default, minimum):
    try:
        return max(minimum, float(os.environ.get(name, str(default))))
    except Exception:
        return default

def env_int(name, default, minimum):
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except Exception:
        return default

SOCKBUF = env_int("P00RIJA_SOCKET_BUFFER_BYTES", 2 * 1024 * 1024, 256 * 1024)
BUF_COPY = env_int("P00RIJA_COPY_BUFFER_BYTES", 512 * 1024, 64 * 1024)
POOL_WAIT = env_float("P00RIJA_POOL_WAIT", 5.0, 0.5)
SYNC_INTERVAL = env_float("P00RIJA_SYNC_INTERVAL", 3.0, 1.0)
DIAL_TIMEOUT = env_float("P00RIJA_DIAL_TIMEOUT", 5.0, 1.0)
NODE_UPDATE_DOWNLOAD_TIMEOUT = env_int("P00RIJA_NODE_UPDATE_DOWNLOAD_TIMEOUT", 1800, 60)
NODE_UPDATE_DOWNLOAD_RETRIES = env_int("P00RIJA_NODE_UPDATE_DOWNLOAD_RETRIES", 4, 1)
APP_VERSION = "1.9.95"
APP_BUILD = "speedtest-preflight-cleanup-hotfix-20260621"
APP_LICENSE = "GPL-3.0"
APP_AUTHOR_GITHUB = "https://github.com/Poorija"
APP_AUTHOR_EMAIL = "mohammadmahdi.farhadianfard@gmail.com"
NODE_ENROLLMENT_API_KEY = os.environ.get("P00RIJA_NODE_API_KEY", "")
PANEL_TLS_FORCED = True
try:
    MAX_REVERSE_WORKERS_PER_LINK = max(1, int(os.environ.get("P00RIJA_MAX_REVERSE_WORKERS_PER_LINK", "16")))
except Exception:
    MAX_REVERSE_WORKERS_PER_LINK = 16
try:
    MAX_POOL_SIZE_PER_LINK = max(1, int(os.environ.get("P00RIJA_MAX_POOL_SIZE_PER_LINK", "32")))
except Exception:
    MAX_POOL_SIZE_PER_LINK = 32
SMART_THREAD_GUARD_ENABLED = os.environ.get("P00RIJA_SMART_THREAD_GUARD", "1").lower() not in ("0", "false", "no", "off")
THREAD_GUARD_INTERVAL = env_float("P00RIJA_THREAD_GUARD_INTERVAL", 5.0, 2.0)
IDLE_RESERVE_TTL = env_float("P00RIJA_IDLE_RESERVE_TTL", 90.0, 15.0)
MIN_READY_WORKERS_PER_LINK = env_int("P00RIJA_MIN_READY_WORKERS_PER_LINK", 2, 1)
BRIDGE_HALF_CLOSE_GRACE = env_float("P00RIJA_BRIDGE_HALF_CLOSE_GRACE", 15.0, 2.0)
DIRECT_BRIDGE_FALLBACK_ENABLED = os.environ.get("P00RIJA_DIRECT_BRIDGE_FALLBACK", "0").lower() in ("1", "true", "yes", "on")
WEBSOCKET_MASK_CLIENT_FRAMES = os.environ.get("P00RIJA_WEBSOCKET_MASK_CLIENT", "0").lower() in ("1", "true", "yes", "on")
THREAD_PRESSURE_SOFT = env_int("P00RIJA_THREAD_PRESSURE_SOFT", 160, 20)
THREAD_PRESSURE_HARD = env_int("P00RIJA_THREAD_PRESSURE_HARD", 320, 40)
RSS_PRESSURE_SOFT_KB = env_int("P00RIJA_RSS_PRESSURE_SOFT_MB", 512, 64) * 1024
RSS_PRESSURE_HARD_KB = env_int("P00RIJA_RSS_PRESSURE_HARD_MB", 1024, 128) * 1024
GUARDIAN_SCAN_INTERVAL = env_float("P00RIJA_GUARDIAN_SCAN_INTERVAL", 15.0, 5.0)
OPTIMIZE_COMMAND_DEDUP_SECONDS = env_float("P00RIJA_OPTIMIZE_COMMAND_DEDUP_SECONDS", 20.0, 5.0)
MAX_PANEL_REQUEST_THREADS = env_int("P00RIJA_MAX_PANEL_REQUEST_THREADS", 64, 8)
BONDING_MAX_LANES = min(16, env_int("P00RIJA_BONDING_MAX_LANES", 16, 2))
BONDING_FRAME_SIZE = env_int("P00RIJA_BONDING_FRAME_SIZE", 128 * 1024, 16 * 1024)
BONDING_JOIN_TIMEOUT = env_float("P00RIJA_BONDING_JOIN_TIMEOUT", 8.0, 2.0)
BONDING_LANE_STEPS = (16, 12, 10, 8, 6, 4, 2)
node_ping_lock = threading.Lock()
node_ping_inflight = set()
ssh_sessions = {}
ssh_sessions_lock = threading.Lock()
# Logo and embedded panel UI assets are provided by p00rija_core.ui.


# Global runtime variables
active_sessions = {}  # token -> login_time
active_sessions_lock = threading.Lock()
runtime_controller = None
active_bridges = {}   # session_id -> BridgeSession
active_bridges_lock = threading.Lock()
temp_echo_servers = {}
temp_echo_servers_lock = threading.Lock()
temp_iperf_servers = {}
temp_iperf_servers_lock = threading.Lock()
speedtest_jobs = {}
speedtest_jobs_lock = threading.Lock()
iperf_install_lock = threading.Lock()
update_manifest_lock = threading.Lock()
update_hash_cache = {}
update_manifest_cache = {"created_at": 0.0, "files": {}}
node_heartbeat_persist_lock = threading.Lock()
last_node_heartbeat_persist = 0.0
NODE_HEARTBEAT_PERSIST_INTERVAL = env_float("P00RIJA_NODE_HEARTBEAT_PERSIST_INTERVAL", 15.0, 5.0)
HYSTERIA2_DEFAULT_UP_MBPS = env_int("P00RIJA_HYSTERIA2_UP_MBPS", 30, 1)
HYSTERIA2_DEFAULT_DOWN_MBPS = env_int("P00RIJA_HYSTERIA2_DOWN_MBPS", 50, 1)
HYSTERIA2_PROCESS_RESTART_DELAY = env_float("P00RIJA_HYSTERIA2_RESTART_DELAY", 3.0, 1.0)
BOND_MAGIC = b"PBD1"
BOND_FRAME_HEADER = struct.Struct("!QII")
BOND_JOIN_HEADER = struct.Struct("!4sQBBH")
BOND_TARGET_SENTINEL = 0
MUX_MAGIC = b"PMX1"
MUX_TARGET_SENTINEL = 65535
MUX_JOIN_HEADER = struct.Struct("!4sBB")
MUX_FRAME_HEADER = struct.Struct("!BIII")
MUX_FRAME_OPEN = 1
MUX_FRAME_DATA = 2
MUX_FRAME_FIN = 3
MUX_FRAME_RST = 4
MUX_FRAME_PING = 5
MUX_FRAME_PONG = 6
MUX_MAX_FRAME_SIZE = env_int("P00RIJA_MUX_FRAME_SIZE", 64 * 1024, 16 * 1024)
MUX_MAX_STREAMS_PER_CARRIER = env_int("P00RIJA_MUX_MAX_STREAMS_PER_CARRIER", 512, 32)
MUX_MAX_CARRIERS = min(8, env_int("P00RIJA_MUX_MAX_CARRIERS", 8, 2))
MUX_KEEPALIVE_INTERVAL = env_float("P00RIJA_MUX_KEEPALIVE_INTERVAL", 12.0, 3.0)
MUX_DEAD_TIMEOUT = env_float("P00RIJA_MUX_DEAD_TIMEOUT", 45.0, 12.0)
bond_groups = {}
bond_groups_lock = threading.Lock()

# --------- System Metrics Collector (Linux Only) ----------
# System metrics are provided by p00rija_core.metrics.

# Built-in tunnel profiles are provided by p00rija_core.tunnel_methods.

# Node enrollment and role helpers are provided by p00rija_core.security.
# External engine config builders are provided by p00rija_core.tunnel_methods.

# TOTP and certificate helpers are provided by p00rija_core.security.
# --------- Database Manager ----------
db = P00RIJADB(DB_PATH, config_dir=CONFIG_DIR, node_api_key=NODE_ENROLLMENT_API_KEY, default_profiles_factory=default_tunnel_profiles)

def persist_node_heartbeats_if_due():
    """Persist all in-memory node heartbeats at a bounded global cadence."""
    global last_node_heartbeat_persist
    now = time.time()
    if now - last_node_heartbeat_persist < NODE_HEARTBEAT_PERSIST_INTERVAL:
        return False
    if not node_heartbeat_persist_lock.acquire(blocking=False):
        return False
    try:
        now = time.time()
        if now - last_node_heartbeat_persist < NODE_HEARTBEAT_PERSIST_INTERVAL:
            return False
        db.save()
        last_node_heartbeat_persist = now
        return True
    finally:
        node_heartbeat_persist_lock.release()

def ensure_tunnel_profiles():
    if core_ensure_tunnel_profiles:
        return core_ensure_tunnel_profiles(db.data["settings"])
    return db.data["settings"].setdefault("tunnel_profiles", default_tunnel_profiles()), False

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
        try:
            s.close()
        except Exception:
            pass
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
        try:
            # Reserve TLS tunnels are idle until the Iran side assigns them.
            # A readable idle TLS fd therefore means EOF/close-notify (or
            # unexpected data) and must not be handed to a new V2Ray client.
            readable, _, exceptional = select.select([sock], [], [sock], 0)
            return not readable and not exceptional
        except Exception:
            return False
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

def get_local_listening_tcp_ports(limit=2048):
    ports = set()
    try:
        for path in ("/proc/net/tcp", "/proc/net/tcp6"):
            if not os.path.exists(path):
                continue
            with open(path, "r") as source:
                for line in source.readlines()[1:]:
                    parts = line.split()
                    if len(parts) < 4 or parts[3] != "0A":
                        continue
                    port = int(parts[1].split(":")[1], 16)
                    if valid_port(port):
                        ports.add(port)
                    if len(ports) >= limit:
                        break
    except Exception:
        pass
    return sorted(ports)[:limit]

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


_TRANSPORT_CAPABILITY_CACHE = {}
_TRANSPORT_CAPABILITY_LOCK = threading.Lock()


def binary_advertises_feature(binary, feature):
    cache_key = (binary, feature)
    with _TRANSPORT_CAPABILITY_LOCK:
        if cache_key in _TRANSPORT_CAPABILITY_CACHE:
            return _TRANSPORT_CAPABILITY_CACHE[cache_key]
    binary_path = engine_binary_path(binary)
    supported = False
    if binary_path:
        try:
            probe = subprocess.run(
                [binary_path, "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=2,
                check=False,
            )
            supported = feature.lower() in (probe.stdout or "").lower()
        except Exception:
            supported = False
    with _TRANSPORT_CAPABILITY_LOCK:
        _TRANSPORT_CAPABILITY_CACHE[cache_key] = supported
    return supported


def runtime_transport_capabilities():
    brutal_available = os.path.isdir("/sys/module/brutal")
    try:
        available_cc = open("/proc/sys/net/ipv4/tcp_available_congestion_control", "r").read().split()
        brutal_available = brutal_available or "brutal" in available_cc
    except Exception:
        available_cc = []
    installed_engines = [
        engine_id for engine_id, info in ENGINE_CATALOG.items()
        if not info.get("bins") or any(engine_binary_path(binary) for binary in info.get("bins", []))
    ]
    return {
        "ech": bool(engine_binary_path("singbox")),
        "masque_connect_udp": bool(engine_binary_path("masque")),
        # The bundled ferneast engine implements CONNECT-UDP. CONNECT-IP config
        # export is available, but runtime activation is gated on an engine that
        # explicitly advertises CONNECT-IP support.
        "masque_connect_ip": binary_advertises_feature("masque", "connect-ip"),
        "masque_connect_ip_config": True,
        "xhttp_reality": bool(engine_binary_path("xray")),
        "adaptive_smux": True,
        "tcp_brutal": brutal_available,
        "tcp_congestion_controls": available_cc,
        "iperf3": bool(shutil.which("iperf3")),
        "installed_engines": installed_engines,
    }

def read_docker_host_gateway():
    try:
        with open("/proc/net/route", "r") as source:
            for line in source.readlines()[1:]:
                parts = line.split()
                if len(parts) < 4 or parts[1] != "00000000" or not (int(parts[3], 16) & 2):
                    continue
                raw = bytes.fromhex(parts[2])
                return socket.inet_ntoa(raw[::-1])
    except Exception:
        pass
    return ""

def read_published_port_ranges():
    try:
        path = os.path.join(CONFIG_DIR, ".publish_ranges")
        return open(path, "r").read().strip() if os.path.isfile(path) else ""
    except Exception:
        return ""

def target_mapping_for_port(link, target_port):
    for mapping in link.get("ports", []) or []:
        try:
            if int(mapping.get("target_port")) == int(target_port):
                return mapping
        except Exception:
            continue
    return {}

def target_service_candidates(link, target_port):
    mapping = target_mapping_for_port(link, target_port)
    configured = str(
        mapping.get("target_host")
        or link.get("target_host")
        or link.get("target_service_host")
        or ""
    ).strip()
    candidates = []
    if configured:
        candidates.append(configured)
    if mapping.get("_temp_test"):
        candidates.append("127.0.0.1")
    elif read_runtime_network_mode() in ("bridge", "docker"):
        gateway = read_docker_host_gateway()
        if gateway:
            candidates.append(gateway)
        candidates.extend(("host.docker.internal", "127.0.0.1"))
    else:
        candidates.append("127.0.0.1")
    result = []
    for host in candidates:
        if host and host not in result:
            result.append(host)
    return result

def dial_target_service(link, target_port):
    errors = []
    for host in target_service_candidates(link, target_port):
        try:
            return dial_tcp(host, target_port), host
        except Exception as exc:
            errors.append(f"{host}: {exc}")
    raise OSError(
        f"Target service {target_port} is unreachable via "
        + ("; ".join(errors) if errors else "no target host candidate")
    )

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

if build_engine_catalog:
    ENGINE_CATALOG = build_engine_catalog(EXTRA_ENGINE_CATALOG)
else:
    ENGINE_CATALOG = {
        "xray": {"bins": ["xray"], "repo": "XTLS/Xray-core"},
        "gost": {"bins": ["gost"], "repo": "go-gost/gost"},
        "backhaul": {"bins": ["backhaul"], "repo": "Musixal/Backhaul"},
        "rathole": {"bins": ["rathole"], "repo": "rapiz1/rathole"},
        "chisel": {"bins": ["chisel"], "repo": "jpillora/chisel"},
        "frp": {"bins": ["frpc", "frps"], "repo": "fatedier/frp"},
        "hysteria2": {"bins": ["hysteria", "hysteria2"], "repo": "apernet/hysteria"},
        "singbox": {"bins": ["sing-box", "singbox"], "repo": "SagerNet/sing-box"},
        "tuic": {"bins": ["tuic-server", "tuic-client"], "repo": "tuic-protocol/tuic"},
        "masque": {"bins": ["masque-tunnel"], "repo": "ferneast/masque-tunnel"},
        "naiveproxy": {"bins": ["naive", "naiveproxy"], "repo": "klzgrad/naiveproxy"},
        "shadowtls": {"bins": ["shadow-tls", "shadowtls"], "repo": "ihciah/shadow-tls"},
        "brook": {"bins": ["brook"], "repo": "txthinking/brook"},
        "mieru": {"bins": ["mieru", "mita"], "repo": "enfein/mieru"},
        "muxquantum": {"bins": [], "repo": "builtin"}
    }
    ENGINE_CATALOG.update(EXTRA_ENGINE_CATALOG)

VALID_TUNNEL_ENGINES = {
    "builtin", "gost", "backhaul", "rathole", "chisel", "frp", "xray", "muxquantum",
    "hysteria2", "singbox", "tuic", "masque", "naiveproxy", "shadowtls", "brook", "mieru"
} | set(EXTRA_TUNNEL_ENGINES)

VALID_TUNNEL_MODES = {
    "tcp", "udp", "websocket", "http_obfs", "grpc", "tcpmux", "wsmux", "tcp_udp", "kcp",
    "quic", "vless_reality", "reality_grpc", "reality_h2", "reality_ws", "httpsmux",
    "quantummux", "tunmux", "mux_wss", "mux_h2", "mux_h3", "mux_quic", "mux_grpc",
    "mux_shadowtls", "mux_reality", "mux_anytls", "mux_naive", "mux_kcp", "shadowtls",
    "shadowtls_ws", "shadowtls_h2", "tuic_quic", "naive_https", "naive_h2", "http2_tls",
    "http3_masquerade", "hysteria2_salamander", "hysteria2_gecko", "anytls", "anytls_h2",
    "anytls_ws", "ech_tls", "ech_h2", "masque_connect_udp", "masque_quic_proxy",
    "xhttp", "tuic_udp_over_stream", "turn_tls"
} | set(EXTRA_TUNNEL_MODES)

VALID_TUNNEL_TRANSPORTS = {
    "tcp", "udp", "ws", "wss", "websocket", "wsmux", "grpc", "tcpmux", "kcp", "quic",
    "httpsmux", "quantummux", "tunmux", "mux_wss", "mux_h2", "mux_h3", "mux_quic",
    "mux_grpc", "mux_shadowtls", "mux_reality", "mux_anytls", "mux_naive", "mux_kcp",
    "h2", "h3", "shadowtls", "tuic", "naive", "anytls", "ech", "masque_h3",
    "connect_udp", "xhttp", "udp_over_stream", "turn_tls"
} | set(EXTRA_TRANSPORTS)

def engine_binary_path(binary):
    if core_engine_binary_path:
        return core_engine_binary_path(binary, ENGINES_DIR, os.getcwd())
    for base in (ENGINES_DIR, os.path.join(os.getcwd(), "engines"), "/app/engines"):
        path = os.path.join(base, binary)
        if os.path.exists(path):
            return path
    return ""

def list_engine_status():
    if core_list_engine_status:
        return core_list_engine_status(ENGINE_CATALOG, ENGINES_DIR, os.getcwd())
    manifest = {}
    for manifest_path in (
        os.path.join(ENGINES_DIR, "manifest.json"),
        os.path.join(os.getcwd(), "engines", "manifest.json"),
        "/app/engines/manifest.json",
        "/usr/local/bin/manifest.json",
    ):
        if not os.path.exists(manifest_path):
            continue
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            break
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

def load_installed_engine_manifest():
    for manifest_path in (
        os.path.join(ENGINES_DIR, "manifest.json"),
        os.path.join(CONFIG_DIR, "engines", "manifest.json"),
        os.path.join(APP_ROOT, "engines", "manifest.json"),
    ):
        try:
            with open(manifest_path, encoding="utf-8") as source:
                return json.load(source)
        except Exception:
            continue
    return {}

def check_all_engine_updates(engine_id=""):
    if not core_check_engine_updates:
        return {"success": False, "error": "Engine update checker is unavailable"}
    return core_check_engine_updates(
        ENGINE_CATALOG,
        load_installed_engine_manifest(),
        engine_id=str(engine_id or ""),
    )

def check_node_versions(node_id=""):
    if not node_version_status:
        return {"success": False, "error": "Node version checker is unavailable"}
    return node_version_status(
        db.data.get("nodes", {}),
        APP_VERSION,
        APP_BUILD,
        node_id=str(node_id or ""),
    )

def install_engine_from_github(engine_type):
    if engine_type not in ENGINE_CATALOG:
        raise ValueError("Unknown engine")
    source_info = (check_all_engine_updates(engine_type).get("engines") or {}).get(engine_type, {})
    if source_info.get("source_type") != "github_release":
        raise ValueError("This engine is built-in or managed by the operating system")
    script_path = "/app/download_engines.py" if os.path.exists("/app/download_engines.py") else os.path.join(APP_ROOT, "download_engines.py")
    if not os.path.exists(script_path):
        raise RuntimeError("download_engines.py is not available in this image")
    persistent_dir = os.path.join(CONFIG_DIR, "engines")
    os.makedirs(persistent_dir, exist_ok=True)
    cmd = [
        sys.executable,
        script_path,
        "--engine",
        engine_type,
        "--output-dir",
        persistent_dir,
        "--no-archives",
    ]
    result = subprocess.run(cmd, cwd=APP_ROOT, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-3000:])
    installed = []
    for binary in ENGINE_CATALOG[engine_type].get("bins", []):
        source = os.path.join(persistent_dir, binary)
        if not os.path.isfile(source):
            continue
        target = os.path.join(ENGINES_DIR, binary)
        temporary = target + f".update-{os.getpid()}"
        shutil.copy2(source, temporary)
        os.chmod(temporary, os.stat(temporary).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(temporary, target)
        installed.append(binary)
    manifest_source = os.path.join(persistent_dir, "manifest.json")
    if os.path.isfile(manifest_source):
        shutil.copy2(manifest_source, os.path.join(ENGINES_DIR, "manifest.json"))
    if not installed:
        raise RuntimeError("GitHub download completed but no runtime binary was installed")
    invalidate_local_update_manifest()
    return {
        "success": True,
        "engine": engine_type,
        "installed": installed,
        "output": (result.stdout or "")[-2000:],
        "update_status": (check_all_engine_updates(engine_type).get("engines") or {}).get(engine_type, {}),
    }

def control_engine_process(engine_id, action):
    if core_control_engine_process:
        return core_control_engine_process(ENGINE_CATALOG, engine_id, action, ENGINES_DIR, os.getcwd())
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
    if core_check_engine_health:
        return core_check_engine_health(ENGINE_CATALOG, engine_id, ENGINES_DIR, os.getcwd())
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
    if core_install_engine_archive:
        return core_install_engine_archive(ENGINE_CATALOG, engine_id, filename, content, ENGINES_DIR)
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

def tcp_probe_host(host, ports=None, timeout=0.6):
    ports = ports or (22, 80, 443, 8080, 8443)
    results = []
    best_ms = None
    open_ports = []
    for port in ports:
        started = time.time()
        ok = False
        error = ""
        try:
            with socket.create_connection((str(host), int(port)), timeout=timeout):
                ok = True
        except Exception as e:
            error = str(e)[:120]
        elapsed = round((time.time() - started) * 1000, 1)
        if ok:
            open_ports.append(int(port))
            best_ms = elapsed if best_ms is None else min(best_ms, elapsed)
        results.append({"port": int(port), "open": ok, "ms": elapsed, "error": error})
    return {
        "host": host,
        "best_ms": best_ms,
        "open_ports": open_ports,
        "results": results
    }

def node_pressure_score(*nodes):
    worst = 0.0
    thread_pressure = 0
    for node in nodes:
        stats = node.get("stats", {}) if isinstance(node, dict) else {}
        try:
            worst = max(worst, float(stats.get("cpu", 0) or 0), float(stats.get("ram", 0) or 0))
        except Exception:
            pass
        try:
            thread_pressure = max(thread_pressure, int(stats.get("threads", 0) or 0))
        except Exception:
            pass
    score = max(0, min(100, int(worst)))
    if thread_pressure > 700:
        score = max(score, 85)
    elif thread_pressure > 350:
        score = max(score, 70)
    return score

def score_tunnel_profile(profile_id, profile, path_quality, objective="balanced"):
    metadata = profile_decision_metadata(profile_id, profile)
    scores = dict(metadata["rating_scores"])
    avg_ms = float(path_quality.get("avg_ms") or 999)
    loss = float(path_quality.get("loss") or 100)
    pressure = int(path_quality.get("pressure") or 0)
    engine = str(profile.get("engine", "builtin"))
    mode = str(profile.get("tunnel_mode", profile.get("transport", "tcp")))
    network = str(profile.get("network", "tcp"))
    throughput_mbps = float(path_quality.get("throughput_mbps") or 0)

    speed_penalty = 0
    stability_penalty = 0
    if avg_ms > 320:
        speed_penalty += 20
        stability_penalty += 14
    elif avg_ms > 180:
        speed_penalty += 10
        stability_penalty += 6
    if loss >= 30:
        speed_penalty += 16
        stability_penalty += 24
    elif loss >= 10:
        speed_penalty += 8
        stability_penalty += 10
    if pressure >= 80:
        speed_penalty += 18
        stability_penalty += 16
    elif pressure >= 65:
        speed_penalty += 8
        stability_penalty += 8
    if network == "udp" and (loss >= 10 or avg_ms > 220):
        stability_penalty += 12
    if engine in ("naiveproxy", "shadowtls", "singbox", "xray") and (loss >= 20 or avg_ms > 240):
        stability_penalty = max(0, stability_penalty - 6)
    if mode in ("reverse_tcp", "tcp") and loss < 5 and pressure < 65:
        speed_penalty = max(0, speed_penalty - 4)
    if throughput_mbps:
        if throughput_mbps < 10:
            speed_penalty += 18
        elif throughput_mbps < 40:
            speed_penalty += 8
        elif throughput_mbps >= 200:
            speed_penalty = max(0, speed_penalty - 6)

    scores["speed"] = max(10, min(100, scores["speed"] - speed_penalty))
    scores["stability"] = max(10, min(100, scores["stability"] - stability_penalty))
    scores["security"] = max(10, min(100, scores["security"]))
    weights = {
        "balanced": (0.34, 0.38, 0.28),
        "speed": (0.68, 0.22, 0.10),
        "stability": (0.18, 0.68, 0.14),
        "security": (0.14, 0.24, 0.62),
    }.get(objective, (0.34, 0.38, 0.28))
    total = round(scores["speed"] * weights[0] + scores["stability"] * weights[1] + scores["security"] * weights[2], 2)
    return {
        "profile_id": profile_id,
        "name": profile.get("name", profile_id),
        "engine": engine,
        "transport": profile.get("transport", profile.get("tunnel_mode", "tcp")),
        "tunnel_mode": mode,
        "network": network,
        "ratings": {k: rating_level(v) for k, v in scores.items()},
        "scores": scores,
        "total_score": total,
        "category": metadata["category"],
        "note": metadata["recommendation_note"],
        "objective": objective,
    }

def build_smart_tunnel_benchmark(internal_id, external_id, direction="external_to_internal", objective="balanced"):
    internal = db.data["nodes"].get(internal_id)
    external = db.data["nodes"].get(external_id)
    if not internal or not external:
        raise ValueError("Both nodes are required")
    if direction not in ("external_to_internal", "internal_to_external"):
        direction = "external_to_internal"
    if objective not in ("balanced", "speed", "stability", "security"):
        objective = "balanced"
    probe_ports = (22, 80, 443, 8080, 8443)
    internal_ping = safe_ping_host(internal.get("ip"), count=3, timeout=2)
    external_ping = safe_ping_host(external.get("ip"), count=3, timeout=2)
    internal_tcp = tcp_probe_host(internal.get("ip"), ports=probe_ports, timeout=0.8)
    external_tcp = tcp_probe_host(external.get("ip"), ports=probe_ports, timeout=0.8)
    now = time.time()
    internal_live = internal.get("status") == "online" and now - float(internal.get("last_seen", 0) or 0) <= 30
    external_live = external.get("status") == "online" and now - float(external.get("last_seen", 0) or 0) <= 30

    source_id = external_id if direction == "external_to_internal" else internal_id
    target_node = internal if direction == "external_to_internal" else external
    node_path_probe = {
        "success": False,
        "source_node_id": source_id,
        "target_host": target_node.get("ip"),
        "error": "Source or target node is not online.",
    }
    if internal_live and external_live and target_node.get("ip"):
        try:
            cmd_id = queue_smart_probe_command(source_id, target_node.get("ip"), ports=probe_ports)
            probe_result = wait_for_node_command_result(source_id, cmd_id, timeout=45)
            if probe_result:
                node_path_probe = probe_result.get("result", {}) or {}
                node_path_probe["source_node_id"] = source_id
            else:
                node_path_probe["error"] = "Timed out waiting for node-to-node probe result."
        except Exception as e:
            node_path_probe["error"] = str(e)

    directional_ping = (node_path_probe.get("ping") or {}) if node_path_probe.get("success") else {}
    directional_tcp = (node_path_probe.get("tcp") or {}) if node_path_probe.get("success") else {}
    # Prefer the real directional node-to-node path. Panel-to-node telemetry is
    # retained for diagnosis, but no longer dilutes a successful path probe.
    if directional_ping or directional_tcp:
        all_values = [
            value for value in (directional_ping.get("avg_ms"), directional_tcp.get("best_ms"))
            if value is not None
        ]
    else:
        avg_values = [x.get("avg_ms") for x in (internal_ping, external_ping) if x.get("avg_ms") is not None]
        tcp_values = [x.get("best_ms") for x in (internal_tcp, external_tcp) if x.get("best_ms") is not None]
        all_values = avg_values + tcp_values
    avg_ms = round(sum(all_values) / len(all_values), 1) if all_values else 999
    loss = float(directional_ping.get("loss", 100)) if directional_ping else max(
        float(internal_ping.get("loss", 100)), float(external_ping.get("loss", 100))
    )
    pressure = node_pressure_score(internal, external)
    throughput_probe = {
        "success": False,
        "error": "iperf3 throughput probe was not completed",
    }
    if internal_live and external_live:
        try:
            occupied_ports = set()
            for selected_node in (internal, external):
                occupied_ports.update(
                    int(port) for port in ((selected_node.get("stats") or {}).get("listening_tcp_ports") or [])
                    if valid_port(port)
                )
            preferred_port = 5201 + (int(hashlib.sha256(f"{internal_id}:{external_id}".encode()).hexdigest()[:4], 16) % 80)
            probe_port = next((port for port in range(preferred_port, 5301) if port not in occupied_ports), None)
            if probe_port is None:
                probe_port = next((port for port in range(5201, preferred_port) if port not in occupied_ports), 5299)
            throughput_probe = run_node_pair_iperf_test(
                source_id,
                internal_id if source_id == external_id else external_id,
                {
                    "duration": 4,
                    "parallel": 2,
                    "port": probe_port,
                    "protocol": "tcp",
                    "omit": 1,
                },
            )
        except Exception as exc:
            throughput_probe["error"] = str(exc)
    throughput_mbps = max(
        float(throughput_probe.get("upload_mbps") or 0),
        float(throughput_probe.get("download_mbps") or 0),
    )
    profiles, changed = ensure_tunnel_profiles()
    if changed:
        db.save()
    path_quality = {
        "avg_ms": avg_ms,
        "loss": loss,
        "pressure": pressure,
        "internal_live": internal_live,
        "external_live": external_live,
        "direction": direction,
        "node_path_probe": node_path_probe,
        "throughput_probe": throughput_probe,
        "throughput_mbps": round(throughput_mbps, 2),
    }
    internal_engines = set((internal.get("stats") or {}).get("transport_capabilities", {}).get("installed_engines") or [])
    external_engines = set((external.get("stats") or {}).get("transport_capabilities", {}).get("installed_engines") or [])
    common_engines = internal_engines & external_engines
    engine_aliases = {
        "singbox": "singbox", "sing-box": "singbox", "amneziawg": "amneziawg",
        "wireguard": "wireguard", "ssh": "builtin", "stunnel": "stunnel",
        "aead": "builtin", "rawsock": "builtin",
    }
    ranked = []
    excluded_profiles = []
    for pid, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        engine = engine_aliases.get(str(profile.get("engine", "builtin")), str(profile.get("engine", "builtin")))
        if common_engines and engine not in common_engines and engine not in ("builtin", "muxquantum"):
            excluded_profiles.append({"profile_id": pid, "name": profile.get("name", pid), "reason": f"engine unavailable on both nodes: {engine}"})
            continue
        ranked.append(score_tunnel_profile(pid, profile, path_quality, objective=objective))
    ranked.sort(key=lambda item: item["total_score"], reverse=True)
    by_speed = sorted(ranked, key=lambda item: item["scores"]["speed"], reverse=True)
    by_stability = sorted(ranked, key=lambda item: item["scores"]["stability"], reverse=True)
    by_security = sorted(ranked, key=lambda item: item["scores"]["security"], reverse=True)
    best = ranked[0] if ranked else {}
    xhttp_mode = "packet-up" if loss >= 10 or avg_ms >= 220 else ("stream-one" if loss < 2 and avg_ms < 100 else "stream-up")
    suggested_smux_max = 4 if pressure >= 80 else (6 if pressure >= 65 else 8)
    brutal_supported = bool(
        (internal.get("stats") or {}).get("transport_capabilities", {}).get("tcp_brutal")
        and (external.get("stats") or {}).get("transport_capabilities", {}).get("tcp_brutal")
    )
    reason = (
        f"Benchmark uses node liveness, panel-to-node ping/TCP probes, a directional node-to-node probe when both nodes are online, "
        f"CPU/RAM/thread pressure, a short iperf3 throughput probe, engine availability, and every compatible profile. "
        f"avg={avg_ms}ms loss={loss}% throughput={throughput_mbps}Mbps pressure={pressure}% "
        f"direction={direction} objective={objective} node_probe={bool(node_path_probe.get('success'))} "
        f"throughput_probe={bool(throughput_probe.get('success'))}."
    )
    return {
        "success": True,
        "direction": direction,
        "objective": objective,
        "path_quality": path_quality,
        "internal": {"id": internal_id, "name": internal.get("name"), "ping": internal_ping, "tcp": internal_tcp, "live": internal_live},
        "external": {"id": external_id, "name": external.get("name"), "ping": external_ping, "tcp": external_tcp, "live": external_live},
        "node_path_probe": node_path_probe,
        "throughput_probe": throughput_probe,
        "recommended_profile_id": best.get("profile_id"),
        "recommended_profile": profiles.get(best.get("profile_id"), {}) if best else {},
        "best_balanced": best,
        "best_by_speed": by_speed[0] if by_speed else {},
        "best_by_stability": by_stability[0] if by_stability else {},
        "best_by_security": by_security[0] if by_security else {},
        "ranked_profiles": ranked,
        "evaluated_profiles": len(ranked),
        "excluded_profiles": excluded_profiles,
        "adaptive_transport_settings": {
            "xhttp_mode": xhttp_mode,
            "smux_min_connections": 2,
            "smux_max_connections": suggested_smux_max,
            "smux_min_streams": 8 if pressure < 80 else 16,
            "tcp_brutal_recommended": bool(brutal_supported and loss >= 8),
            "tcp_brutal_supported_on_both_nodes": brutal_supported,
            "masque_mode": "connect-udp" if loss < 20 else "connect-ip",
        },
        "reason": reason
    }

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

def runtime_session_summary():
    by_link = {}
    total = 0
    with active_bridges_lock:
        for session in active_bridges.values():
            total += 1
            lid = str(getattr(session, "link_id", "") or "")
            if lid:
                by_link[lid] = by_link.get(lid, 0) + 1
    now = time.time()
    for node in db.data.get("nodes", {}).values():
        if now - node.get("last_seen", 0) > 30:
            continue
        for session in node.get("stats", {}).get("runtime_sessions", []) or []:
            if not isinstance(session, dict):
                continue
            total += 1
            lid = str(session.get("link_id") or "")
            if lid:
                by_link[lid] = by_link.get(lid, 0) + 1
    return {"total": total, "by_link": by_link}

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

def get_thread_snapshot(limit_processes=15, limit_threads=160):
    threads = []
    if not os.path.isdir("/proc"):
        return threads
    try:
        ticks = os.sysconf(os.sysconf_names.get("SC_CLK_TCK", "SC_CLK_TCK"))
    except Exception:
        ticks = 100
    for proc in get_process_snapshot(limit=limit_processes):
        pid = proc.get("pid")
        task_dir = f"/proc/{pid}/task"
        if not pid or not os.path.isdir(task_dir):
            continue
        try:
            tids = [tid for tid in os.listdir(task_dir) if tid.isdigit()]
        except Exception:
            continue
        for tid in tids[: max(1, min(256, limit_threads))]:
            try:
                with open(f"{task_dir}/{tid}/stat", "r") as f:
                    stat = f.read().split()
                cpu_seconds = 0.0
                if len(stat) > 15:
                    cpu_seconds = (int(stat[13]) + int(stat[14])) / ticks
                threads.append({
                    "tid": int(tid),
                    "pid": int(pid),
                    "name": stat[1].strip("()") if len(stat) > 1 else proc.get("name", str(tid)),
                    "process": proc.get("name", str(pid)),
                    "state": stat[2] if len(stat) > 2 else "?",
                    "rss_kb": proc.get("rss_kb", 0),
                    "cpu_seconds": round(cpu_seconds, 2),
                    "source": "panel",
                    "node_id": "",
                    "node_name": "Panel",
                    "kind": "thread",
                })
            except Exception:
                continue
    threads.sort(key=lambda item: (item.get("cpu_seconds", 0), item.get("rss_kb", 0)), reverse=True)
    return threads[:limit_threads]

def get_node_thread_snapshot(limit_per_node=12):
    threads = []
    now = time.time()
    for node_id, node in db.data.get("nodes", {}).items():
        if node.get("status") != "online" or now - node.get("last_seen", 0) > 30:
            continue
        node_name = node.get("name", node_id)
        for proc in (node.get("stats", {}).get("processes") or [])[:limit_per_node]:
            if not isinstance(proc, dict):
                continue
            try:
                thread_total = int(proc.get("threads") or 0)
            except Exception:
                thread_total = 0
            if thread_total <= 0:
                continue
            threads.append({
                "tid": "",
                "pid": proc.get("pid", ""),
                "name": f"{thread_total} threads",
                "process": proc.get("name", "process"),
                "state": proc.get("state", "?"),
                "rss_kb": proc.get("rss_kb", 0),
                "cpu_seconds": proc.get("cpu_seconds", 0),
                "source": "node",
                "node_id": node_id,
                "node_name": node_name,
                "kind": "process_group",
                "threads": thread_total,
            })
    threads.sort(key=lambda item: (int(item.get("threads") or 1), item.get("rss_kb", 0)), reverse=True)
    return threads

def get_all_thread_snapshot():
    return get_thread_snapshot() + get_node_thread_snapshot()

def close_runtime_session(session_id):
    try:
        sid = int(session_id)
    except Exception:
        return False
    with active_bridges_lock:
        session = active_bridges.pop(sid, None)
    if not session:
        return False
    session.close()
    return True

def queue_node_session_close(node_id, session_id):
    node = db.data.get("nodes", {}).get(node_id)
    if not node:
        return False, "Node not found"
    if node.get("status") != "online" or time.time() - node.get("last_seen", 0) > 30:
        return False, "Node is offline"
    commands = db.data.setdefault("node_commands", {})
    cmd_id = secrets.token_hex(8)
    commands.setdefault(node_id, []).append({
        "id": cmd_id,
        "type": "runtime_close_session",
        "session_id": str(session_id or ""),
        "created_at": time.time()
    })
    db.save()
    db.log("panel", "warning", f"Queued remote runtime session close for node={node_id}, session={session_id}.")
    return True, cmd_id

def queue_panel_handoff(new_panel_url):
    if not normalize_panel_url:
        raise RuntimeError("Panel migration module is unavailable")
    new_panel_url = normalize_panel_url(new_panel_url)
    now = time.time()
    commands = db.data.setdefault("node_commands", {})
    queued = []
    for node_id, node in db.data.get("nodes", {}).items():
        if node.get("status") != "online" or now - node.get("last_seen", 0) > 30:
            continue
        command_id = secrets.token_hex(8)
        commands.setdefault(node_id, []).append({
            "id": command_id,
            "type": "panel_handoff",
            "new_panel_url": new_panel_url,
            "created_at": now,
        })
        queued.append({
            "node_id": node_id,
            "name": node.get("name", node_id),
            "command_id": command_id,
        })
    if queued:
        db.save()
        db.log("panel", "warning", f"Queued panel endpoint handoff to {new_panel_url} for {len(queued)} node(s).")
    return queued

def wait_for_panel_handoff_results(queued, timeout=45):
    pending = {item["node_id"]: item["command_id"] for item in queued}
    results = {}
    deadline = time.time() + max(5, int(timeout))
    while pending and time.time() < deadline:
        for node_id, command_id in list(pending.items()):
            node = db.data.get("nodes", {}).get(node_id, {})
            report = node.get("last_command_result") or {}
            if report.get("id") != command_id:
                continue
            result = report.get("result") or {}
            results[node_id] = {
                "name": node.get("name", node_id),
                "success": bool(result.get("success")),
                "new_panel_url": result.get("new_panel_url"),
                "fallback_panel_url": result.get("fallback_panel_url"),
                "error": result.get("error", ""),
            }
            pending.pop(node_id, None)
        if pending:
            time.sleep(0.5)
    for node_id in pending:
        node = db.data.get("nodes", {}).get(node_id, {})
        results[node_id] = {
            "name": node.get("name", node_id),
            "success": False,
            "error": "Node did not acknowledge the new panel endpoint before timeout",
        }
    return results

def backup_path_for_id(backup_id):
    safe_id = "".join(ch for ch in str(backup_id or "") if ch.isalnum() or ch in ("-", "_"))[:80]
    if not safe_id:
        return ""
    root = os.path.realpath(os.path.join(CONFIG_DIR, "panel_backups"))
    path = os.path.realpath(os.path.join(root, f"p00rija-panel-backup-{safe_id}.tar.gz.enc"))
    if not path.startswith(root + os.sep) or not os.path.isfile(path):
        return ""
    return path

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

# RSS measurement is provided by p00rija_core.metrics.
def optimize_runtime_resources(action="idle", link_id=None):
    target_link_id = str(link_id or "")
    requested_action = action
    if action not in ("idle", "gc", "all", "pressure", "thread_guard"):
        raise ValueError("Invalid runtime optimization action")
    now = time.time()
    max_idle = clamp_int(db.data["settings"].get("max_idle_seconds", 300), 300, 30, 86400)
    threads_before = threading.active_count()
    rss_before = get_own_rss_kb()
    ram_percent = get_ram_percent()
    if (
        threads_before >= THREAD_PRESSURE_HARD
        or rss_before >= RSS_PRESSURE_HARD_KB
        or ram_percent >= 95
    ):
        pressure_level = "hard"
    elif (
        threads_before >= THREAD_PRESSURE_SOFT
        or rss_before >= RSS_PRESSURE_SOFT_KB
        or ram_percent >= 85
    ):
        pressure_level = "soft"
    else:
        pressure_level = "normal"
    closed_bridges = 0
    pruned_logins = 0
    pruned_node_commands = 0
    gc_collected = 0
    malloc_trimmed = False
    link_guardian_runs = 0
    link_idle_workers_reaped = 0

    should_close_idle = action in ("idle", "all") or (
        action == "pressure" and pressure_level in ("soft", "hard")
    )
    if should_close_idle:
        idle_threshold = max_idle
        if action == "pressure" and pressure_level == "hard":
            idle_threshold = min(max_idle, 120)
        with active_bridges_lock:
            stale = [
                (sid, session) for sid, session in list(active_bridges.items())
                if (not target_link_id or getattr(session, "link_id", "") == target_link_id)
                and now - getattr(session, "last_activity", now) > idle_threshold
            ]
            for sid, _session in stale[:256]:
                active_bridges.pop(sid, None)
        for _sid, session in stale[:256]:
            try:
                session.close()
                closed_bridges += 1
            except Exception:
                pass

    controller = runtime_controller
    if controller and action in ("all", "pressure", "thread_guard"):
        try:
            with controller.lock:
                items = list(controller.active_links.items())
            for active_link_id, link_data in items:
                if target_link_id and active_link_id != target_link_id:
                    continue
                before = int(link_data.get("idle_workers_reaped", 0) or 0)
                run_thread_guardian_for_link(active_link_id, link_data, force=True)
                after = int(link_data.get("idle_workers_reaped", 0) or 0)
                link_idle_workers_reaped += max(0, after - before)
                link_guardian_runs += 1
        except Exception as e:
            db.log("runtime", "warning", f"Thread guardian optimization failed: {e}")

    if action in ("idle", "all"):
        with active_sessions_lock:
            for session_token, login_time in list(active_sessions.items()):
                if now - login_time > 86400:
                    active_sessions.pop(session_token, None)
                    pruned_logins += 1

    if action == "all":
        commands = db.data.setdefault("node_commands", {})
        for nid, pending in list(commands.items()):
            fresh = [cmd for cmd in pending if now - float(cmd.get("created_at", now)) < 900]
            pruned_node_commands += len(pending) - len(fresh)
            commands[nid] = fresh
        if pruned_node_commands:
            db.save()

    if action in ("gc", "all", "pressure"):
        gc_collected = gc.collect()
        if action == "all" or pressure_level == "hard":
            gc_collected += gc.collect(2)
        try:
            libc = ctypes.CDLL("libc.so.6")
            malloc_trimmed = bool(libc.malloc_trim(0))
        except Exception:
            malloc_trimmed = False

    if action == "all" or (action == "pressure" and pressure_level == "hard"):
        prune_ssh_sessions(max_idle=300)

    rss_after = get_own_rss_kb()
    result = {
        "success": True,
        "action": action,
        "requested_action": requested_action,
        "link_id": target_link_id,
        "closed_idle_sessions": closed_bridges,
        "pruned_login_sessions": pruned_logins,
        "pruned_node_commands": pruned_node_commands,
        "gc_collected": gc_collected,
        "malloc_trimmed": malloc_trimmed,
        "pressure_level": pressure_level,
        "threads_before": threads_before,
        "rss_before_kb": rss_before,
        "rss_reclaimed_kb": max(0, rss_before - rss_after),
        "ram_percent": round(float(ram_percent or 0), 1),
        "link_guardian_runs": link_guardian_runs,
        "link_idle_workers_reaped": link_idle_workers_reaped,
        "threads": threading.active_count(),
        "active_tunnel_sessions": runtime_session_summary().get("total", 0),
        "rss_kb": rss_after,
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
        pending = commands.setdefault(nid, [])
        if any(cmd.get("type") == "node_update" for cmd in pending):
            continue
        duplicate = any(
            cmd.get("type") == "optimize"
            and cmd.get("action") == action
            and not cmd.get("link_id")
            and now - float(cmd.get("created_at", 0) or 0) < OPTIMIZE_COMMAND_DEDUP_SECONDS
            for cmd in pending
        )
        if duplicate:
            continue
        cmd_id = secrets.token_hex(8)
        pending.append({
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

def queue_node_link_guardian(link_id=None):
    now = time.time()
    commands = db.data.setdefault("node_commands", {})
    targets = set()
    for lid, link in db.data.get("links", {}).items():
        if link_id and lid != link_id:
            continue
        for key in ("internal_node_id", "external_node_id", "iran_node_id", "foreign_node_id"):
            if link.get(key):
                targets.add(link.get(key))
    queued = 0
    for nid in sorted(targets):
        node = db.data.get("nodes", {}).get(nid, {})
        if node.get("status") != "online" or now - node.get("last_seen", 0) > 30:
            continue
        pending = commands.setdefault(nid, [])
        if any(cmd.get("type") == "node_update" for cmd in pending):
            continue
        duplicate = any(
            cmd.get("type") == "optimize"
            and cmd.get("action") == "thread_guard"
            and str(cmd.get("link_id") or "") == str(link_id or "")
            and now - float(cmd.get("created_at", 0) or 0) < OPTIMIZE_COMMAND_DEDUP_SECONDS
            for cmd in pending
        )
        if duplicate:
            continue
        cmd_id = secrets.token_hex(8)
        pending.append({
            "id": cmd_id,
            "type": "optimize",
            "action": "thread_guard",
            "link_id": link_id or "",
            "created_at": now
        })
        queued += 1
    if queued:
        db.save()
        db.log("panel", "info", f"Queued link guardian command(s), link_id={link_id or 'all'}, nodes={queued}.")
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

def stop_temp_echo_server(command_id="", port=None):
    key = f"port:{int(port)}" if port is not None and valid_port(port) else str(command_id or "")
    with temp_echo_servers_lock:
        srv = temp_echo_servers.pop(key, None)
    if srv:
        try:
            srv.close()
        except Exception:
            pass
        return True
    return False


def ensure_iperf3():
    binary = shutil.which("iperf3")
    if binary:
        return binary
    with iperf_install_lock:
        binary = shutil.which("iperf3")
        if binary:
            return binary
        commands = []
        if shutil.which("apt-get"):
            commands = [
                ["apt-get", "-o", "Acquire::Check-Valid-Until=false", "update", "-y"],
                ["apt-get", "install", "-y", "--no-install-recommends", "iperf3"],
            ]
        elif shutil.which("dnf"):
            commands = [["dnf", "install", "-y", "iperf3"]]
        elif shutil.which("yum"):
            commands = [["yum", "install", "-y", "iperf3"]]
        elif shutil.which("apk"):
            commands = [["apk", "add", "iperf3"]]
        if not commands:
            raise RuntimeError("iperf3 is not installed and no supported package manager is available")
        for command in commands:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=600,
                check=False,
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
            )
            if completed.returncode != 0:
                raise RuntimeError((completed.stdout or "iperf3 installation failed")[-800:])
        binary = shutil.which("iperf3")
        if not binary:
            raise RuntimeError("iperf3 installation completed but the binary was not found")
        return binary


def iperf3_capabilities():
    try:
        binary = ensure_iperf3()
        version = subprocess.run(
            [binary, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=4,
            check=False,
        ).stdout.splitlines()[0]
        help_text = subprocess.run(
            [binary, "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=4,
            check=False,
        ).stdout
        return {
            "available": True,
            "version": version,
            "bidir": "--bidir" in help_text,
            "mptcp": "--mptcp" in help_text,
            "zerocopy": "--zerocopy" in help_text,
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def start_temp_iperf_server(port, timeout=45, command_id=""):
    port = int(port)
    if not valid_port(port):
        raise ValueError("Invalid iperf3 server port")
    binary = ensure_iperf3()
    key = str(command_id or f"port:{port}")
    with temp_iperf_servers_lock:
        previous = temp_iperf_servers.pop(key, None)
    if previous and previous.poll() is None:
        previous.terminate()
    process = subprocess.Popen(
        [binary, "--server", "--one-off", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    deadline = time.time() + 4
    ready = False
    while time.time() < deadline:
        if process.poll() is not None:
            break
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                ready = True
                break
        except Exception:
            time.sleep(0.1)
    # A TCP readiness probe consumes a one-off iperf server. Restart it after
    # the probe so the real client owns the single accepted test.
    if ready:
        try:
            process.wait(timeout=2)
        except Exception:
            process.terminate()
        process = subprocess.Popen(
            [binary, "--server", "--one-off", "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        time.sleep(0.2)
    if process.poll() is not None:
        raise RuntimeError("iperf3 server exited before becoming ready")
    with temp_iperf_servers_lock:
        temp_iperf_servers[key] = process

    def expire_server():
        time.sleep(max(10, min(180, int(timeout))))
        with temp_iperf_servers_lock:
            current = temp_iperf_servers.pop(key, None)
        if current and current.poll() is None:
            current.terminate()

    threading.Thread(target=expire_server, daemon=True).start()
    return {
        "success": True,
        "port": port,
        "pid": process.pid,
        "iperf3": iperf3_capabilities(),
        "network_mode": read_runtime_network_mode(),
        "server_id": key,
    }


def stop_temp_iperf_server(command_id="", port=0):
    keys = []
    if command_id:
        keys.append(str(command_id))
    if valid_port(port):
        keys.append(f"port:{int(port)}")
    stopped = False
    with temp_iperf_servers_lock:
        for key in keys:
            process = temp_iperf_servers.pop(key, None)
            if process and process.poll() is None:
                process.terminate()
                stopped = True
        if valid_port(port):
            for key, process in list(temp_iperf_servers.items()):
                if process and process.poll() is None:
                    try:
                        process_port = int(str(key).split("port:", 1)[1]) if str(key).startswith("port:") else 0
                    except Exception:
                        process_port = 0
                    if process_port == int(port):
                        temp_iperf_servers.pop(key, None)
                        process.terminate()
                        stopped = True
    return stopped


def _safe_iperf_host(value):
    host = str(value or "").strip()
    if not host or len(host) > 253 or not re.fullmatch(r"[A-Za-z0-9_.:-]+", host):
        raise ValueError("Invalid iperf3 host")
    return host


def run_iperf3_client(options):
    binary = ensure_iperf3()
    host = _safe_iperf_host(options.get("host"))
    port = clamp_int(options.get("port", 5201), 5201, 1, 65535)
    duration = clamp_int(options.get("duration", 8), 8, 1, 30)
    parallel = clamp_int(options.get("parallel", 2), 2, 1, 16)
    omit = clamp_int(options.get("omit", 1), 1, 0, 10)
    protocol = str(options.get("protocol") or "tcp").lower()
    command = [
        binary, "--client", host, "--port", str(port), "--time", str(duration),
        "--parallel", str(parallel), "--omit", str(omit), "--json",
        "--connect-timeout", str(clamp_int(options.get("connect_timeout_ms", 5000), 5000, 500, 20000)),
    ]
    if protocol == "udp":
        command.append("--udp")
        bitrate = str(options.get("bitrate") or "100M").strip()
        if not re.fullmatch(r"\d+(?:\.\d+)?[KMG]?", bitrate, re.I):
            raise ValueError("Invalid UDP bitrate")
        command += ["--bitrate", bitrate]
    if options.get("reverse"):
        command.append("--reverse")
    if options.get("bidir"):
        command.append("--bidir")
    if options.get("zerocopy") and protocol == "tcp":
        command.append("--zerocopy")
    if options.get("mptcp") and protocol == "tcp":
        command.append("--mptcp")
    block_length = int(options.get("block_length") or 0)
    if 16 <= block_length <= 1024 * 1024:
        command += ["--length", str(block_length)]
    window = str(options.get("window") or "").strip()
    if window:
        if not re.fullmatch(r"\d+(?:\.\d+)?[KMG]?", window, re.I):
            raise ValueError("Invalid TCP window")
        command += ["--window", window]
    congestion = str(options.get("congestion") or "").strip()
    if congestion:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", congestion):
            raise ValueError("Invalid congestion control name")
        command += ["--congestion", congestion]
    started = time.time()
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=duration + omit + 25,
        check=False,
    )
    try:
        raw = json.loads(completed.stdout or "{}")
    except Exception:
        raw = {}
    if completed.returncode != 0 or raw.get("error"):
        raise RuntimeError(str(raw.get("error") or completed.stderr or completed.stdout or "iperf3 failed")[-1000:])
    end = raw.get("end") or {}
    sent = end.get("sum_sent") or end.get("sum") or {}
    received = end.get("sum_received") or end.get("sum") or {}
    upstream_bps = float(sent.get("bits_per_second") or 0)
    downstream_bps = float(received.get("bits_per_second") or 0)
    streams = end.get("streams") or []
    if options.get("bidir") and streams:
        sender_rates = []
        receiver_rates = []
        for stream in streams:
            sender = stream.get("sender") or {}
            receiver = stream.get("receiver") or {}
            if sender.get("bits_per_second"):
                sender_rates.append(float(sender["bits_per_second"]))
            if receiver.get("bits_per_second"):
                receiver_rates.append(float(receiver["bits_per_second"]))
        if sender_rates:
            upstream_bps = sum(sender_rates)
        if receiver_rates:
            downstream_bps = sum(receiver_rates)
    cpu = end.get("cpu_utilization_percent") or {}
    return {
        "success": True,
        "host": host,
        "port": port,
        "protocol": protocol,
        "duration": duration,
        "parallel": parallel,
        "reverse": bool(options.get("reverse")),
        "bidir": bool(options.get("bidir")),
        "upload_mbps": round(upstream_bps / 1_000_000, 2),
        "download_mbps": round(downstream_bps / 1_000_000, 2),
        "jitter_ms": round(float(received.get("jitter_ms") or sent.get("jitter_ms") or 0), 3),
        "loss_percent": round(float(received.get("lost_percent") or sent.get("lost_percent") or 0), 3),
        "retransmits": int(sent.get("retransmits") or 0),
        "bytes_sent": int(sent.get("bytes") or 0),
        "bytes_received": int(received.get("bytes") or 0),
        "cpu_local": round(float(cpu.get("host_total") or 0), 2),
        "cpu_remote": round(float(cpu.get("remote_total") or 0), 2),
        "elapsed_seconds": round(time.time() - started, 3),
        "iperf3": iperf3_capabilities(),
    }


def apply_panel_handoff(new_panel_url, fallback_panel_url):
    if not normalize_panel_url:
        raise RuntimeError("Panel migration module is unavailable")
    new_panel_url = normalize_panel_url(new_panel_url)
    fallback_panel_url = normalize_panel_url(fallback_panel_url)
    with open(CONFIG_PATH, "r") as source:
        config = json.load(source)
    config["panel_url"] = new_panel_url
    config["panel_fallback_url"] = fallback_panel_url
    config["panel_handoff_at"] = time.time()
    temp_path = f"{CONFIG_PATH}.handoff.tmp"
    with open(temp_path, "w") as output:
        json.dump(config, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, CONFIG_PATH)
    return {
        "success": True,
        "new_panel_url": new_panel_url,
        "fallback_panel_url": fallback_panel_url,
        "restart_required": True,
    }

def execute_node_commands(panel_url, token, private_key, commands):
    for command in commands or []:
        command_type = command.get("type")
        cmd_id = command.get("id")
        should_restart_after_report = False
        if command_type == "optimize":
            action = command.get("action", "idle")
            try:
                result = optimize_runtime_resources(action, link_id=command.get("link_id") or None)
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
            result = {
                "success": stop_temp_echo_server(
                    command.get("target_id") or cmd_id,
                    port=command.get("port"),
                )
            }
            payload = {"id": cmd_id, "type": "payload_test_echo_stop", "action": action, "result": result}
        elif command_type == "smart_probe":
            action = "probe"
            target_host = str(command.get("target_host") or "").strip()
            ports = command.get("ports") or [22, 80, 443, 8080, 8443]
            try:
                safe_ports = [int(p) for p in ports if valid_port(p)][:8] or [22, 80, 443, 8080, 8443]
                ping = safe_ping_host(target_host, count=3, timeout=2)
                tcp = tcp_probe_host(target_host, ports=tuple(safe_ports), timeout=0.8)
                result = {
                    "success": bool(target_host) and (ping.get("ok") or bool(tcp.get("open_ports"))),
                    "target_host": target_host,
                    "ping": ping,
                    "tcp": tcp,
                }
            except Exception as e:
                result = {"success": False, "error": str(e), "target_host": target_host}
            payload = {"id": cmd_id, "type": "smart_probe", "action": action, "result": result}
        elif command_type == "speedtest_iperf_server":
            action = "listen"
            try:
                result = start_temp_iperf_server(
                    command.get("port", 5201),
                    timeout=command.get("timeout", 45),
                    command_id=cmd_id,
                )
            except Exception as e:
                result = {"success": False, "error": str(e), "port": command.get("port")}
            payload = {"id": cmd_id, "type": command_type, "action": action, "result": result}
        elif command_type == "speedtest_iperf_client":
            action = "measure"
            try:
                result = run_iperf3_client(command.get("options") or {})
            except Exception as e:
                result = {"success": False, "error": str(e)}
            payload = {"id": cmd_id, "type": command_type, "action": action, "result": result}
        elif command_type == "speedtest_iperf_stop":
            action = "stop"
            result = {
                "success": True,
                "stopped": stop_temp_iperf_server(
                    command.get("server_id") or command.get("target_id") or "",
                    command.get("port") or 0,
                ),
                "port": command.get("port"),
            }
            payload = {"id": cmd_id, "type": command_type, "action": action, "result": result}
        elif command_type == "speedtest_iperf_install":
            action = "install"
            try:
                result = {"success": True, "binary": ensure_iperf3(), "iperf3": iperf3_capabilities()}
            except Exception as e:
                result = {"success": False, "error": str(e)}
            payload = {"id": cmd_id, "type": command_type, "action": action, "result": result}
        elif command_type == "runtime_close_session":
            action = "close"
            session_id = str(command.get("session_id") or "")
            try:
                result = {
                    "success": close_runtime_session(session_id),
                    "session_id": session_id,
                }
            except Exception as e:
                result = {"success": False, "error": str(e), "session_id": session_id}
            payload = {"id": cmd_id, "type": "runtime_close_session", "action": action, "result": result}
        elif command_type == "node_update":
            action = "apply"
            restart_requested = bool(command.get("restart", True))
            package_path = ""
            try:
                package_path, digest = download_node_update_package(
                    panel_url,
                    token,
                    private_key,
                    command.get("package_id"),
                    command.get("sha256", ""),
                )
                result = apply_node_update_package(package_path, scope=command.get("scope", "app_engines"))
                result.update({
                    "download_sha256": digest,
                    "package_id": command.get("package_id"),
                    "version": command.get("version"),
                    "build": command.get("build"),
                    "restart_requested": restart_requested,
                    "package_size": command.get("package_size", 0),
                    "skipped_files": command.get("skipped_files", 0),
                })
                should_restart_after_report = bool(result.get("success")) and restart_requested and bool(result.get("restart_required"))
                if should_restart_after_report:
                    result["restart_scheduled"] = True
                    result["restart_method"] = "process_reexec"
            except Exception as e:
                result = {"success": False, "error": str(e), "package_id": command.get("package_id")}
            finally:
                if package_path:
                    try:
                        os.remove(package_path)
                    except Exception:
                        pass
            payload = {"id": cmd_id, "type": "node_update", "action": action, "result": result}
        elif command_type == "panel_handoff":
            action = "prepare"
            try:
                result = apply_panel_handoff(command.get("new_panel_url"), panel_url)
                should_restart_after_report = bool(result.get("success"))
                if should_restart_after_report:
                    result["restart_scheduled"] = True
                    result["restart_method"] = "process_reexec"
            except Exception as e:
                result = {
                    "success": False,
                    "error": str(e),
                    "new_panel_url": command.get("new_panel_url"),
                    "fallback_panel_url": panel_url,
                }
            payload = {"id": cmd_id, "type": "panel_handoff", "action": action, "result": result}
        else:
            continue
        try:
            make_panel_request(panel_url, "/api/node-command-result", token, payload, private_key=private_key)
            if should_restart_after_report:
                schedule_node_process_restart()
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

def queue_payload_echo_stop_command(node_id, target_port):
    cmd_id = secrets.token_hex(8)
    commands = db.data.setdefault("node_commands", {})
    commands.setdefault(node_id, []).append({
        "id": cmd_id,
        "type": "payload_test_echo_stop",
        "port": int(target_port),
        "created_at": time.time()
    })
    db.save()
    return cmd_id

def queue_smart_probe_command(node_id, target_host, ports=None):
    cmd_id = secrets.token_hex(8)
    safe_ports = [int(p) for p in (ports or (22, 80, 443, 8080, 8443)) if valid_port(p)][:8]
    commands = db.data.setdefault("node_commands", {})
    commands.setdefault(node_id, []).append({
        "id": cmd_id,
        "type": "smart_probe",
        "target_host": str(target_host or ""),
        "ports": safe_ports or [22, 80, 443, 8080, 8443],
        "created_at": time.time()
    })
    db.save()
    return cmd_id


def queue_speedtest_command(node_id, command_type, **payload):
    node = db.data.get("nodes", {}).get(node_id)
    if not node:
        raise ValueError("Node not found")
    if node.get("status") != "online" or time.time() - float(node.get("last_seen", 0) or 0) > 30:
        raise ValueError(f"Node is offline: {node.get('name', node_id)}")
    cmd_id = secrets.token_hex(8)
    command = {
        "id": cmd_id,
        "type": command_type,
        "created_at": time.time(),
        **payload,
    }
    db.data.setdefault("node_commands", {}).setdefault(node_id, []).append(command)
    db.save()
    return cmd_id


def ensure_speedtest_nodes_ready(node_ids, timeout=660):
    """Verify iperf3 before starting a timed test.

    A first-run package installation can legitimately take longer than the
    old 45-second server-start timeout. Queue all preflight commands together,
    then wait for their explicit results so installation time is not mistaken
    for a network or server-start failure.
    """
    pending = {}
    for node_id in dict.fromkeys(str(value) for value in node_ids if value):
        node = db.data.get("nodes", {}).get(node_id) or {}
        capability = ((node.get("stats") or {}).get("transport_capabilities") or {}).get("iperf3")
        # Still run a cheap verification command when the capability is
        # unknown; this also repairs old nodes that have not reported it yet.
        if capability is True:
            continue
        pending[node_id] = queue_speedtest_command(node_id, "speedtest_iperf_install")
    results = {}
    for node_id, command_id in pending.items():
        report = wait_for_node_command_result(node_id, command_id, timeout=timeout)
        node_name = db.data.get("nodes", {}).get(node_id, {}).get("name", node_id)
        if not report:
            raise RuntimeError(
                f"Timed out while installing/checking iperf3 on {node_name}; "
                "the node did not return a command result"
            )
        result = report.get("result") or {}
        if not result.get("success"):
            raise RuntimeError(
                f"iperf3 preflight failed on {node_name}: "
                f"{result.get('error') or 'unknown installation error'}"
            )
        results[node_id] = result
    return results


def run_node_pair_iperf_test(source_id, target_id, options):
    source = db.data.get("nodes", {}).get(source_id) or {}
    target = db.data.get("nodes", {}).get(target_id) or {}
    if not source or not target or source_id == target_id:
        raise ValueError("Two different nodes are required")
    target_ip = _safe_iperf_host(target.get("ip"))
    test_options = dict(options or {})
    preflight_done = bool(test_options.pop("_iperf_preflight_done", False))
    test_options["host"] = target_ip
    test_options["port"] = clamp_int(test_options.get("port", 5201), 5201, 1, 65535)
    occupied = {
        int(port) for port in ((target.get("stats") or {}).get("listening_tcp_ports") or [])
        if valid_port(port)
    }
    if test_options["port"] in occupied:
        replacement = next(
            (port for port in range(max(5201, test_options["port"] + 1), 5301) if port not in occupied),
            None,
        )
        if replacement is None:
            replacement = next((port for port in range(5201, test_options["port"]) if port not in occupied), None)
        if replacement is None:
            raise RuntimeError("No free iperf3 test port was found in 5201-5300")
        test_options["requested_port"] = test_options["port"]
        test_options["port"] = replacement
    if not preflight_done:
        ensure_speedtest_nodes_ready((source_id, target_id))
    server_id = ""
    server_result = {}
    try:
        server_id = queue_speedtest_command(
            target_id,
            "speedtest_iperf_server",
            port=test_options["port"],
            timeout=clamp_int(test_options.get("duration", 8), 8, 1, 30) + 90,
        )
        server_report = wait_for_node_command_result(target_id, server_id, timeout=75)
        server_result = (server_report or {}).get("result") or {}
        if not server_result.get("success"):
            detail = server_result.get("error") or (
                "the target did not return a server-start result within 75 seconds"
                if not server_report else "unknown server-start failure"
            )
            raise RuntimeError(f"Target node could not start iperf3: {detail}")
        client_id = queue_speedtest_command(
            source_id,
            "speedtest_iperf_client",
            options=test_options,
        )
        client_report = wait_for_node_command_result(
            source_id,
            client_id,
            timeout=clamp_int(test_options.get("duration", 8), 8, 1, 30) + 90,
        )
        result = (client_report or {}).get("result") or {}
        if not result:
            raise RuntimeError("Source node did not return an iperf3 result")
        if not result.get("success"):
            raise RuntimeError(result.get("error") or "iperf3 client test failed")
    finally:
        if server_id:
            try:
                queue_speedtest_command(
                    target_id,
                    "speedtest_iperf_stop",
                    server_id=server_id,
                    port=test_options["port"],
                )
            except Exception:
                pass
    result.update({
        "source_node_id": source_id,
        "source_name": source.get("name", source_id),
        "target_node_id": target_id,
        "target_name": target.get("name", target_id),
        "target_ip": target_ip,
        "server_network_mode": server_result.get("network_mode", "unknown"),
    })
    return result


def _speedtest_job_update(job_id, **changes):
    with speedtest_jobs_lock:
        job = speedtest_jobs.get(job_id)
        if not job:
            return
        job.update(changes)
        job["updated_at"] = time.time()


def _run_speedtest_job(job_id, request):
    mode = str(request.get("mode") or "pair")
    options = dict(request.get("options") or {})
    node_ids = [
        str(node_id) for node_id in (request.get("node_ids") or [])
        if str(node_id) in db.data.get("nodes", {})
    ]
    results = []
    errors = []
    try:
        if mode == "internet":
            host = _safe_iperf_host(request.get("internet_host"))
            total = len(node_ids)
            if not total:
                raise ValueError("Choose at least one node")
            _speedtest_job_update(job_id, total=total)
            _speedtest_job_update(job_id, phase="preflight")
            ensure_speedtest_nodes_ready(node_ids)
            _speedtest_job_update(job_id, phase="testing")
            for index, node_id in enumerate(node_ids, 1):
                node = db.data["nodes"][node_id]
                try:
                    command_options = {**options, "host": host}
                    command_id = queue_speedtest_command(
                        node_id, "speedtest_iperf_client", options=command_options
                    )
                    report = wait_for_node_command_result(
                        node_id, command_id,
                        timeout=clamp_int(options.get("duration", 8), 8, 1, 30) + 90,
                    )
                    result = (report or {}).get("result") or {}
                    if not report:
                        raise RuntimeError("Node did not return an iperf3 client result")
                    if not result.get("success"):
                        raise RuntimeError(result.get("error") or "Internet iperf3 test failed")
                    result.update({"node_id": node_id, "node_name": node.get("name", node_id), "scope": "internet"})
                    results.append(result)
                except Exception as exc:
                    errors.append({"node_id": node_id, "node_name": node.get("name", node_id), "error": str(exc)})
                _speedtest_job_update(job_id, completed=index, results=list(results), errors=list(errors))
        else:
            if mode == "mesh":
                pairs = [
                    (node_ids[left], node_ids[right])
                    for left in range(len(node_ids))
                    for right in range(left + 1, len(node_ids))
                ]
            else:
                if len(node_ids) != 2:
                    raise ValueError("Pair test requires exactly two nodes")
                pairs = [(node_ids[0], node_ids[1])]
            max_pairs = 28
            pairs = pairs[:max_pairs]
            _speedtest_job_update(job_id, total=len(pairs))
            _speedtest_job_update(job_id, phase="preflight")
            ensure_speedtest_nodes_ready(node_ids)
            options["_iperf_preflight_done"] = True
            _speedtest_job_update(job_id, phase="testing")
            for index, (source_id, target_id) in enumerate(pairs, 1):
                try:
                    results.append(run_node_pair_iperf_test(source_id, target_id, options))
                except Exception as exc:
                    errors.append({
                        "source_node_id": source_id,
                        "source_name": db.data["nodes"].get(source_id, {}).get("name", source_id),
                        "target_node_id": target_id,
                        "target_name": db.data["nodes"].get(target_id, {}).get("name", target_id),
                        "error": str(exc),
                    })
                _speedtest_job_update(job_id, completed=index, results=list(results), errors=list(errors))
        _speedtest_job_update(job_id, state="completed", phase="completed", completed=max(len(results) + len(errors), 0), finished_at=time.time())
    except Exception as exc:
        _speedtest_job_update(job_id, state="failed", phase="failed", error=str(exc), finished_at=time.time())


def start_speedtest_job(request):
    mode = str(request.get("mode") or "pair")
    if mode not in ("pair", "mesh", "internet"):
        raise ValueError("Invalid speed-test mode")
    options = dict(request.get("options") or {})
    options["duration"] = clamp_int(options.get("duration", 8), 8, 1, 30)
    options["parallel"] = clamp_int(options.get("parallel", 2), 2, 1, 16)
    options["port"] = clamp_int(options.get("port", 5201), 5201, 1, 65535)
    options["protocol"] = "udp" if str(options.get("protocol")).lower() == "udp" else "tcp"
    request = {**request, "mode": mode, "options": options}
    job_id = secrets.token_hex(12)
    with speedtest_jobs_lock:
        speedtest_jobs[job_id] = {
            "id": job_id,
            "state": "running",
            "phase": "queued",
            "mode": mode,
            "created_at": time.time(),
            "updated_at": time.time(),
            "completed": 0,
            "total": 0,
            "results": [],
            "errors": [],
            "request": request,
        }
        if len(speedtest_jobs) > 30:
            oldest = sorted(speedtest_jobs.values(), key=lambda item: item.get("created_at", 0))[:-20]
            for item in oldest:
                speedtest_jobs.pop(item["id"], None)
    threading.Thread(target=_run_speedtest_job, args=(job_id, request), daemon=True).start()
    return dict(speedtest_jobs[job_id])


def get_speedtest_job(job_id):
    with speedtest_jobs_lock:
        job = speedtest_jobs.get(str(job_id or ""))
        return dict(job) if job else None

def _add_path_to_tar(tf, source, arcname):
    if not source or not os.path.exists(source):
        return False
    tf.add(source, arcname=arcname, recursive=True)
    return True

def _sha256_file(path, chunk_size=1024 * 1024):
    stat_info = os.stat(path)
    cache_key = os.path.realpath(path)
    signature = (stat_info.st_size, stat_info.st_mtime_ns)
    with update_manifest_lock:
        cached = update_hash_cache.get(cache_key)
        if cached and cached.get("signature") == signature:
            return cached["sha256"], stat_info.st_size
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    value = digest.hexdigest()
    with update_manifest_lock:
        update_hash_cache[cache_key] = {"signature": signature, "sha256": value}
    return value, stat_info.st_size

def _app_update_sources():
    sources = {}
    for name in ("P00RIJA.py", "download_engines.py"):
        path = os.path.join(APP_ROOT, name)
        if os.path.isfile(path):
            sources[name] = path
    core_dir = os.path.join(APP_ROOT, "p00rija_core")
    if os.path.isdir(core_dir):
        for name in sorted(os.listdir(core_dir)):
            if name.endswith(".py"):
                sources[f"p00rija_core/{name}"] = os.path.join(core_dir, name)
    return sources

def _engine_update_sources():
    sources = {}
    source_dir = _find_update_engines_dir()
    if not source_dir:
        return sources
    binary_names = {
        str(binary)
        for info in ENGINE_CATALOG.values()
        for binary in info.get("bins", [])
        if binary
    }
    for name in sorted(binary_names | {"manifest.json"}):
        path = os.path.join(source_dir, name)
        if os.path.isfile(path) and not os.path.islink(path):
            sources[f"engines/{name}"] = path
    return sources

def _node_installed_update_sources():
    sources = _app_update_sources()
    binary_names = {
        str(binary)
        for info in ENGINE_CATALOG.values()
        for binary in info.get("bins", [])
        if binary
    }
    for name in sorted(binary_names | {"manifest.json"}):
        path = os.path.join(ENGINES_DIR, name)
        if os.path.isfile(path) and not os.path.islink(path):
            sources[f"engines/{name}"] = path
    return sources

def build_local_update_manifest(max_age=60):
    now = time.time()
    with update_manifest_lock:
        if update_manifest_cache["files"] and now - update_manifest_cache["created_at"] < max_age:
            return dict(update_manifest_cache["files"])
    files = {}
    for relative_path, source in _node_installed_update_sources().items():
        try:
            digest, size = _sha256_file(source)
            files[relative_path] = {"sha256": digest, "size": size}
        except Exception:
            continue
    with update_manifest_lock:
        update_manifest_cache["created_at"] = now
        update_manifest_cache["files"] = files
    return dict(files)

def invalidate_local_update_manifest():
    with update_manifest_lock:
        update_manifest_cache["created_at"] = 0.0
        update_manifest_cache["files"] = {}

def _find_update_engines_dir():
    for candidate in (
        os.path.join(CONFIG_DIR, "engines"),
        os.path.join(APP_ROOT, "engines"),
        os.path.join(os.getcwd(), "engines"),
        "/app/engines",
    ):
        if os.path.isdir(candidate):
            return candidate
    return ""

def cleanup_node_update_packages(max_age=21600):
    try:
        now = time.time()
        os.makedirs(NODE_UPDATE_DIR, exist_ok=True)
        for name in os.listdir(NODE_UPDATE_DIR):
            path = os.path.join(NODE_UPDATE_DIR, name)
            try:
                if os.path.isfile(path) and now - os.path.getmtime(path) > max_age:
                    os.remove(path)
            except Exception:
                pass
    except Exception:
        pass

def build_node_update_package(include_app=True, include_engines=True, node_manifest=None):
    cleanup_node_update_packages()
    os.makedirs(NODE_UPDATE_DIR, exist_ok=True)
    package_id = secrets.token_hex(12)
    package_path = os.path.join(NODE_UPDATE_DIR, f"{package_id}.tar.gz")
    sources = {}
    if include_app:
        sources.update(_app_update_sources())
    if include_engines:
        sources.update(_engine_update_sources())
    remote_files = node_manifest if isinstance(node_manifest, dict) else {}
    changed = {}
    skipped_bytes = 0
    for relative_path, source in sources.items():
        digest, size = _sha256_file(source)
        remote = remote_files.get(relative_path) or {}
        if remote.get("sha256") == digest and int(remote.get("size") or -1) == size:
            skipped_bytes += size
            continue
        changed[relative_path] = {
            "source": source,
            "sha256": digest,
            "size": size,
        }
    manifest = {
        "app": "P00RIJA TUNNEL",
        "version": APP_VERSION,
        "build": APP_BUILD,
        "created_at": time.time(),
        "include_app": bool(include_app),
        "include_engines": bool(include_engines),
        "delta": True,
        "files": {
            relative_path: {"sha256": item["sha256"], "size": item["size"]}
            for relative_path, item in changed.items()
        },
        "changed_files": len(changed),
        "skipped_files": len(sources) - len(changed),
        "skipped_bytes": skipped_bytes,
    }
    with tarfile.open(package_path, "w:gz", compresslevel=3) as tf:
        for relative_path, item in changed.items():
            tf.add(item["source"], arcname=relative_path, recursive=False)
        info = json.dumps(manifest, indent=2).encode("utf-8")
        tar_info = tarfile.TarInfo("update_manifest.json")
        tar_info.size = len(info)
        tar_info.mtime = int(time.time())
        tf.addfile(tar_info, io.BytesIO(info))
    digest, package_size = _sha256_file(package_path)
    manifest["package_size"] = package_size
    return {"package_id": package_id, "path": package_path, "sha256": digest, "size": package_size, "manifest": manifest}

def queue_node_update(node_id=None, scope="app_engines", restart=True):
    include_engines = scope in ("app_engines", "engines")
    include_app = scope in ("app", "app_engines")
    if not include_engines and not include_app:
        raise ValueError("Invalid update scope")
    now = time.time()
    commands = db.data.setdefault("node_commands", {})
    queued = []
    for nid, node in db.data.get("nodes", {}).items():
        if node_id and nid != node_id:
            continue
        if node.get("status") != "online" or now - node.get("last_seen", 0) > 30:
            continue
        existing_update = next(
            (
                command for command in commands.get(nid, [])
                if command.get("type") == "node_update"
                and now - float(command.get("created_at", now)) < 1800
            ),
            None,
        )
        if existing_update:
            pending = commands.setdefault(nid, [])
            pending[:] = [existing_update] + [cmd for cmd in pending if cmd is not existing_update]
            queued.append({
                "node_id": nid,
                "name": node.get("name", nid),
                "command_id": existing_update.get("id"),
                "changed_files": existing_update.get("changed_files", 0),
                "package_size": existing_update.get("package_size", 0),
                "already_pending": True,
            })
            continue
        node_manifest = (node.get("stats") or {}).get("update_manifest") or {}
        package = build_node_update_package(
            include_app=include_app,
            include_engines=include_engines,
            node_manifest=node_manifest,
        )
        cmd_id = secrets.token_hex(8)
        command = {
            "id": cmd_id,
            "type": "node_update",
            "action": "apply",
            "scope": scope,
            "include_app": include_app,
            "include_engines": include_engines,
            "restart": bool(restart),
            "package_id": package["package_id"],
            "sha256": package["sha256"],
            "version": APP_VERSION,
            "build": APP_BUILD,
            "delta": True,
            "changed_files": package["manifest"].get("changed_files", 0),
            "skipped_files": package["manifest"].get("skipped_files", 0),
            "package_size": package.get("size", 0),
            "created_at": now,
        }
        # Updates are control-plane critical and must not be starved behind
        # periodic optimizer/guardian work. Node config polling intentionally
        # returns a bounded command window, so keep the update at the front.
        commands.setdefault(nid, []).insert(0, command)
        node["last_update_queued_at"] = now
        queued.append({
            "node_id": nid,
            "name": node.get("name", nid),
            "command_id": cmd_id,
            "changed_files": package["manifest"].get("changed_files", 0),
            "package_size": package.get("size", 0),
        })
    if queued:
        db.save()
        db.log("panel", "info", f"Queued remote node update for {len(queued)} node(s), scope={scope}, restart={restart}.")
    return {"success": True, "queued": queued, "queued_count": len(queued), "version": APP_VERSION, "scope": scope, "delta": True}

def node_can_download_update_package(node_token, package_id):
    token = normalize_node_token(node_token)
    if not token or not package_id:
        return False
    for nid, node in db.data.get("nodes", {}).items():
        if node.get("token") != token:
            continue
        for command in db.data.setdefault("node_commands", {}).get(nid, []):
            if command.get("type") == "node_update" and command.get("package_id") == package_id:
                return True
    return False

def node_for_update_package_download(node_token, package_id):
    token = normalize_node_token(node_token)
    if not token or not package_id:
        return "", {}
    for nid, node in db.data.get("nodes", {}).items():
        if node.get("token") != token:
            continue
        for command in db.data.setdefault("node_commands", {}).get(nid, []):
            if command.get("type") == "node_update" and command.get("package_id") == package_id:
                return nid, node
    return "", {}

def node_update_package_path(package_id):
    safe_id = "".join(ch for ch in str(package_id or "") if ch.isalnum())[:32]
    if not safe_id:
        return None
    path = os.path.join(NODE_UPDATE_DIR, f"{safe_id}.tar.gz")
    if not os.path.isfile(path):
        return ""
    return path

def _safe_extract_tar(tf, dest):
    dest_real = os.path.realpath(dest)
    for member in tf.getmembers():
        target = os.path.realpath(os.path.join(dest, member.name))
        if not target.startswith(dest_real + os.sep) and target != dest_real:
            raise ValueError(f"Unsafe path in update package: {member.name}")
    tf.extractall(dest)

def _replace_path(src, dst, backup_root):
    if not os.path.exists(src):
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        backup_dst = os.path.join(backup_root, dst.strip("/").replace("/", "__"))
        if os.path.isdir(dst) and not os.path.islink(dst):
            shutil.copytree(dst, backup_dst, dirs_exist_ok=True)
            shutil.rmtree(dst)
        else:
            os.makedirs(os.path.dirname(backup_dst), exist_ok=True)
            shutil.copy2(dst, backup_dst)
            os.remove(dst)
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)
        try:
            os.chmod(dst, 0o755)
        except Exception:
            pass
    return True

def download_node_update_package(panel_url, token, private_key, package_id, expected_sha):
    import urllib.request
    import urllib.error
    path = f"/api/node-update-package?package_id={package_id}"
    url = f"{panel_url.rstrip('/')}{path}"
    base_headers = {"X-Node-Token": normalize_node_token(token)}
    if private_key:
        base_headers["X-Node-Signature"] = hmac.new(private_key.encode(), f"{path}\n".encode(), hashlib.sha256).hexdigest()
    ctx = ssl._create_unverified_context()
    download_dir = os.path.join(CONFIG_DIR, "updates")
    os.makedirs(download_dir, exist_ok=True)
    destination = os.path.join(download_dir, f"{package_id}.tar.gz.part")
    last_error = None
    for attempt in range(NODE_UPDATE_DOWNLOAD_RETRIES):
        offset = os.path.getsize(destination) if os.path.exists(destination) else 0
        headers = dict(base_headers)
        if offset:
            headers["Range"] = f"bytes={offset}-"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=NODE_UPDATE_DOWNLOAD_TIMEOUT, context=ctx) as response:
                resumed = offset > 0 and response.getcode() == 206
                mode = "ab" if resumed else "wb"
                with open(destination, mode) as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            if attempt + 1 < NODE_UPDATE_DOWNLOAD_RETRIES:
                time.sleep(min(10, 2 ** attempt))
    if last_error is not None:
        raise RuntimeError(f"Update download failed after {NODE_UPDATE_DOWNLOAD_RETRIES} attempts: {last_error}")
    digest, _download_size = _sha256_file(destination)
    if expected_sha and digest != expected_sha:
        try:
            os.remove(destination)
        except Exception:
            pass
        raise ValueError("Downloaded update package sha256 mismatch")
    final_path = destination[:-5]
    os.replace(destination, final_path)
    return final_path, digest

def apply_node_update_package(package, scope="app_engines"):
    include_app = scope in ("app", "app_engines")
    include_engines = scope in ("engines", "app_engines")
    backup_root = os.path.join(CONFIG_DIR, "backups", f"node-update-{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(backup_root, exist_ok=True)
    applied = []
    with tempfile.TemporaryDirectory() as td:
        archive = package if isinstance(package, str) else os.path.join(td, "node-update.tar.gz")
        if not isinstance(package, str):
            with open(archive, "wb") as f:
                f.write(package)
        extract_dir = os.path.join(td, "extract")
        os.makedirs(extract_dir, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tf:
            _safe_extract_tar(tf, extract_dir)
        manifest_path = os.path.join(extract_dir, "update_manifest.json")
        manifest = json.load(open(manifest_path, encoding="utf-8")) if os.path.isfile(manifest_path) else {}
        for relative_path, expected in (manifest.get("files") or {}).items():
            src = os.path.join(extract_dir, relative_path)
            if not os.path.isfile(src):
                raise ValueError(f"Update payload is missing {relative_path}")
            digest, size = _sha256_file(src)
            if digest != expected.get("sha256") or size != int(expected.get("size") or -1):
                raise ValueError(f"Update payload verification failed for {relative_path}")
            destinations = []
            if relative_path.startswith("engines/"):
                if not include_engines:
                    continue
                engine_name = relative_path.split("/", 1)[1]
                destinations.append(os.path.join(ENGINES_DIR, engine_name))
                destinations.append(os.path.join(CONFIG_DIR, "engines", engine_name))
            else:
                if not include_app:
                    continue
                destinations.append(os.path.join(APP_ROOT, relative_path))
                destinations.append(os.path.join(CONFIG_DIR, relative_path))
            replaced = False
            for dst in dict.fromkeys(os.path.realpath(path) for path in destinations):
                if _replace_path(src, dst, backup_root):
                    replaced = True
                    try:
                        os.chmod(dst, 0o755 if relative_path.startswith("engines/") or not relative_path.startswith("p00rija_core/") else 0o644)
                    except Exception:
                        pass
            if replaced:
                applied.append(relative_path)
    invalidate_local_update_manifest()
    return {
        "success": True,
        "applied": applied,
        "backup": backup_root,
        "scope": scope,
        "delta": True,
        "changed_files": len(applied),
        "restart_required": include_app and bool(applied),
    }

def schedule_node_process_restart(delay=1.5):
    def _restart():
        time.sleep(delay)
        try:
            db.log("node", "info", "Re-executing node process after remote update.")
        except Exception:
            pass
        terminate_orphaned_native_engines()
        argv = [sys.executable] + sys.argv
        try:
            os.execv(sys.executable, argv)
        except Exception:
            os._exit(1)
    threading.Thread(target=_restart, daemon=True).start()

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

def wait_for_node_command_result(node_id, cmd_id, timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            node = db.data.get("nodes", {}).get(node_id, {})
            result = (node.get("command_results") or {}).get(cmd_id) or node.get("last_command_result", {})
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

def wrap_socket_client_tls(sock, sni_hostname=None, ca_content=""):
    try:
        if ca_content:
            context = ssl.create_default_context(cadata=ca_content)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_REQUIRED
            # The panel distributes the exact tunnel certificate as the pin.
            # Public CA leaf certificates are not themselves CA certificates,
            # so OpenSSL rejects them as trust anchors unless partial-chain
            # verification is enabled. This keeps certificate verification
            # mandatory while allowing the pinned leaf (or a private CA) to
            # terminate the verified chain.
            partial_chain = getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)
            if partial_chain:
                context.verify_flags |= partial_chain
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            db.log("tls", "warning", "Tunnel TLS certificate pin is unavailable; using compatibility mode.")
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

def make_websocket_header(length: int) -> bytes:
    if length <= 125:
        return bytes((0x82, length))
    if length <= 65535:
        return bytes((0x82, 126)) + struct.pack("!H", length)
    return bytes((0x82, 127)) + struct.pack("!Q", length)

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
        self.mode = "tcp" if self.requested_mode == "reverse_tcp" else (self.requested_mode if self.requested_mode in ("tcp", "websocket", "http_obfs") else "tcp")
        self.config = config or {}
        self.handshake_done = False
        self.ws_parser = None
        self.read_buf = b""
        self.write_closed = False
        try:
            keepalive = clamp_int(self.config.get("keepalive_interval", 25), 25, 5, 300)
            if hasattr(socket, "TCP_KEEPIDLE"):
                self.raw_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, keepalive)
            if hasattr(socket, "TCP_KEEPINTVL"):
                self.raw_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, max(5, keepalive // 3))
        except Exception:
            pass

    def obfuscation_padding_header(self):
        minimum = clamp_int(self.config.get("padding_min", 0), 0, 0, 1024)
        maximum = clamp_int(self.config.get("padding_max", minimum), minimum, minimum, 1024)
        if maximum <= 0:
            return ""
        size = minimum if maximum == minimum else minimum + secrets.randbelow(maximum - minimum + 1)
        if size <= 0:
            return ""
        return "X-Padding: " + base64.urlsafe_b64encode(secrets.token_bytes(size)).decode().rstrip("=") + "\r\n"

    def validate_obfuscation_request(self, request, method):
        lines = request.split("\r\n")
        if not lines:
            return False
        request_parts = lines[0].split()
        if len(request_parts) < 2 or request_parts[0].upper() != method:
            return False
        expected_path = str(self.config.get("obfs_path") or "/tunnel")
        if request_parts[1] != expected_path:
            return False
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        expected_host = str(self.config.get("obfs_host") or "localhost").lower()
        received_host = headers.get("host", "").split(":", 1)[0].lower()
        return received_host == expected_host

    def perform_handshake(self):
        if self.handshake_done:
            return True
        try:
            if self.mode == "websocket":
                if self.role in ("iran", "internal"):
                    req = self.read_http_headers()
                    if not req or "upgrade: websocket" not in req.lower() or not self.validate_obfuscation_request(req, "GET"):
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
                        "Sec-WebSocket-Version: 13\r\n"
                        f"{self.obfuscation_padding_header()}\r\n"
                    )
                    self.raw_sock.sendall(req.encode())
                    resp = self.read_http_headers()
                    expected_accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
                    if not resp or "101 Switching Protocols" not in resp or f"Sec-WebSocket-Accept: {expected_accept}".lower() not in resp.lower():
                        return False
                    self.ws_parser = WSFrameParser(self.raw_sock)
            elif self.mode == "http_obfs":
                if self.role in ("iran", "internal"):
                    req = self.read_http_headers()
                    if not req or not self.validate_obfuscation_request(req, "POST"):
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
                        "Connection: keep-alive\r\n"
                        f"{self.obfuscation_padding_header()}\r\n"
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
            is_client = self.role in ("foreign", "external")
            if is_client and WEBSOCKET_MASK_CLIENT_FRAMES:
                self.raw_sock.sendall(make_websocket_frame(data, is_client=True))
            else:
                # Private node-to-node fast path: the peer parser accepts
                # unmasked binary frames. Sending header and payload
                # separately avoids a full payload copy and expensive Python
                # masking for every large chunk.
                self.raw_sock.sendall(make_websocket_header(len(data)))
                if data:
                    self.raw_sock.sendall(data)
        else:  # http_obfs
            self.raw_sock.sendall(f"{len(data):x}\r\n".encode())
            if data:
                self.raw_sock.sendall(data)
            self.raw_sock.sendall(b"\r\n")

    def close(self):
        self.raw_sock.close()

    def shutdown(self, how):
        if how == socket.SHUT_WR and not self.write_closed:
            self.write_closed = True
            try:
                if self.mode == "websocket":
                    # Protocol-level EOF; safe through TLS and framing.
                    self.raw_sock.sendall(b"\x88\x00")
                    return
                if self.mode == "http_obfs":
                    self.raw_sock.sendall(b"0\r\n\r\n")
                    return
                if isinstance(self.raw_sock, ssl.SSLSocket):
                    # Raw TCP half-close would bypass TLS state.
                    return
            except Exception:
                return
        try:
            self.raw_sock.shutdown(how)
        except Exception:
            pass

# --------- Core Tunnel Logic ----------
def init_link_lifecycle(link_data):
    link_data.setdefault("stop_event", threading.Event())
    link_data.setdefault("lifecycle_lock", threading.Lock())
    link_data.setdefault("guardian_lock", threading.Lock())
    link_data.setdefault("threads", set())
    link_data.setdefault("worker_threads", set())
    link_data.setdefault("sockets", set())
    return link_data

def link_is_running(link_data):
    stop_event = link_data.get("stop_event")
    return bool(link_data.get("running", False)) and not (stop_event and stop_event.is_set())

def track_link_socket(link_data, sock):
    if sock is None:
        return sock
    with link_data["lifecycle_lock"]:
        if not link_is_running(link_data):
            try:
                sock.close()
            except Exception:
                pass
            raise OSError("link is stopping")
        link_data["sockets"].add(sock)
    return sock

def untrack_link_socket(link_data, sock):
    if sock is None:
        return
    with link_data["lifecycle_lock"]:
        link_data.get("sockets", set()).discard(sock)

def start_link_thread(link_data, target, *, name, args=(), worker=False):
    init_link_lifecycle(link_data)

    def runner():
        try:
            target(*args)
        finally:
            current = threading.current_thread()
            with link_data["lifecycle_lock"]:
                link_data["threads"].discard(current)
                link_data["worker_threads"].discard(current)
                link_data["worker_threads_alive"] = len(link_data["worker_threads"])

    thread = threading.Thread(target=runner, name=name[:63], daemon=True)
    with link_data["lifecycle_lock"]:
        if not link_is_running(link_data):
            return None
        link_data["threads"].add(thread)
        if worker:
            link_data["worker_threads"].add(thread)
            link_data["worker_threads_alive"] = len(link_data["worker_threads"])
    try:
        thread.start()
    except Exception:
        with link_data["lifecycle_lock"]:
            link_data["threads"].discard(thread)
            link_data["worker_threads"].discard(thread)
            link_data["worker_threads_alive"] = len(link_data["worker_threads"])
        raise
    return thread

def link_ports_signature(link):
    result = []
    for mapping in link.get("ports", []) or []:
        try:
            result.append((
                int(mapping.get("user_port")),
                int(mapping.get("target_port")),
                str(mapping.get("target_host") or ""),
            ))
        except Exception:
            continue
    return tuple(sorted(result))

def native_hysteria2_enabled(link):
    return link.get("engine") == "hysteria2" and bool(link.get("native_engine_enabled", False))

def hysteria2_binary():
    for name in ("hysteria2", "hysteria"):
        path = engine_binary_path(name)
        if path and os.path.isfile(path):
            try:
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception:
                pass
            return path
    return ""

def write_runtime_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)

def write_link_certificate_material(link):
    link_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(link.get("id") or "link"))
    cert_content = str(link.get("cert_content") or "")
    key_content = str(link.get("key_content") or "")
    cert_path = os.path.join(CONFIG_DIR, "certs", f"hysteria2-{link_id}.crt")
    key_path = os.path.join(CONFIG_DIR, "certs", f"hysteria2-{link_id}.key")
    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
    if cert_content:
        with open(cert_path, "w", encoding="utf-8") as output:
            output.write(cert_content)
        os.chmod(cert_path, 0o644)
    if key_content:
        with open(key_path, "w", encoding="utf-8") as output:
            output.write(key_content)
        os.chmod(key_path, 0o600)
    return cert_path, key_path

def terminate_engine_link_process(link_data, timeout=3.0):
    process = link_data.get("engine_process")
    if not process:
        return
    try:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except Exception:
            pass
    except Exception:
        pass
    link_data["engine_process"] = None

def terminate_orphaned_native_engines(timeout=1.5):
    marker = os.path.join(CONFIG_DIR, "engine_runtime", "hysteria2-")
    pids = []
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit() or int(entry) == os.getpid():
                continue
            try:
                with open(f"/proc/{entry}/cmdline", "rb") as source:
                    command = source.read().replace(b"\0", b" ").decode("utf-8", errors="ignore")
                if marker in command and ("hysteria2" in command or "hysteria" in command):
                    os.kill(int(entry), signal.SIGTERM)
                    pids.append(int(entry))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
        deadline = time.time() + max(0.1, float(timeout))
        while pids and time.time() < deadline:
            pids = [pid for pid in pids if os.path.exists(f"/proc/{pid}")]
            if pids:
                time.sleep(0.05)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    except Exception:
        pass

def start_hysteria2_link(link):
    binary = hysteria2_binary()
    if not binary:
        raise RuntimeError("Bundled Hysteria2 binary is unavailable")
    link_id = str(link["id"])
    safe_link_id = re.sub(r"[^A-Za-z0-9_.-]", "_", link_id)
    local_role = str(link.get("local_tunnel_role") or "")
    runtime_dir = os.path.join(CONFIG_DIR, "engine_runtime")
    config_path = os.path.join(runtime_dir, f"hysteria2-{safe_link_id}-{local_role}.json")
    log_path = os.path.join(runtime_dir, f"hysteria2-{safe_link_id}-{local_role}.log")
    auth_secret = str(link.get("xray_uuid") or link_id)
    bridge_port = int(link.get("bridge_port"))
    cert_path, key_path = write_link_certificate_material(link)

    if local_role == "client":
        if not os.path.isfile(cert_path) or not os.path.isfile(key_path):
            raise RuntimeError("Hysteria2 server certificate/key is unavailable")
        mode = "server"
        config = {
            "listen": f":{bridge_port}",
            "tls": {
                "cert": cert_path,
                "key": key_path,
                "sniGuard": "disable",
            },
            "auth": {
                "type": "password",
                "password": auth_secret,
            },
            "speedTest": True,
            "disableUDP": False,
            "congestion": {
                "type": "bbr",
                "bbrProfile": "aggressive",
            },
        }
        role_label = "server"
    else:
        mode = "client"
        peer_ip = str(link.get("peer_ip") or link.get("client_ip") or "").strip()
        if not peer_ip:
            raise RuntimeError("Hysteria2 peer IP is unavailable")
        mappings = []
        for mapping in link.get("ports", []) or []:
            try:
                user_port = int(mapping.get("user_port"))
                target_port = int(mapping.get("target_port"))
            except Exception:
                continue
            if not valid_port(user_port) or not valid_port(target_port):
                continue
            target_host = str(mapping.get("target_host") or "127.0.0.1")
            mappings.append({
                "listen": f"0.0.0.0:{user_port}",
                "remote": f"{target_host}:{target_port}",
            })
        config = {
            "server": f"{peer_ip}:{bridge_port}",
            "auth": auth_secret,
            "bandwidth": {
                "up": f"{clamp_int(link.get('hysteria_up_mbps'), HYSTERIA2_DEFAULT_UP_MBPS, 1, 1000)} mbps",
                "down": f"{clamp_int(link.get('hysteria_down_mbps'), HYSTERIA2_DEFAULT_DOWN_MBPS, 1, 1000)} mbps",
            },
            "tls": {
                "sni": str(link.get("cert_sni") or link.get("tls_sni") or "localhost"),
                "insecure": False,
            },
            "tcpForwarding": mappings,
            "quic": {
                "maxIdleTimeout": "60s",
                "keepAlivePeriod": "10s",
            },
        }
        role_label = "client"

    write_runtime_json(config_path, config)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log_file = open(log_path, "ab", buffering=0)
    env = dict(os.environ)
    env["HYSTERIA_DISABLE_UPDATE_CHECK"] = "1"
    process = subprocess.Popen(
        [binary, mode, "-c", config_path, "-l", "warn"],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
        close_fds=True,
    )
    log_file.close()
    time.sleep(0.8)
    if process.poll() is not None:
        detail = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as source:
                detail = source.read()[-1200:]
        except Exception:
            pass
        raise RuntimeError(f"Hysteria2 {role_label} exited during startup: {detail}")
    link_data = {
        "running": True,
        "local_tunnel_role": local_role,
        "engine_managed": True,
        "engine": "hysteria2",
        "engine_role": role_label,
        "engine_process": process,
        "engine_config_path": config_path,
        "engine_log_path": log_path,
        "engine_started_at": time.time(),
        "engine_restart_count": 0,
        "ports": {
            int(mapping.get("user_port")): {
                "target_port": int(mapping.get("target_port")),
                "engine_managed": True,
            }
            for mapping in (link.get("ports", []) or [])
            if valid_port(mapping.get("user_port")) and valid_port(mapping.get("target_port"))
        } if local_role == "server" else {},
        "_raw_config": link,
    }
    init_link_lifecycle(link_data)
    db.log("node", "info", f"Started native Hysteria2 {role_label} for {link_id} on UDP {bridge_port}.")
    return link_data

def engine_link_status(link_data):
    process = link_data.get("engine_process")
    running = bool(link_is_running(link_data) and process and process.poll() is None)
    port_status = {}
    for user_port, mapping in (link_data.get("ports") or {}).items():
        port_status[str(user_port)] = {
            "user_port": int(user_port),
            "target_port": int(mapping.get("target_port")),
            "listening": running and is_local_tcp_listening(int(user_port)),
        }
    return {
        "running": running,
        "role": link_data.get("engine_role"),
        "engine": link_data.get("engine"),
        "engine_managed": True,
        "engine_pid": process.pid if running else 0,
        "bridge_listening": running and link_data.get("engine_role") == "server",
        "ready_workers": 1 if running and link_data.get("engine_role") == "client" else 0,
        "desired_workers": 1,
        "max_workers": 1,
        "worker_threads_alive": 0,
        "worker_errors": 0 if running else 1,
        "last_worker_error": "" if running else "Native Hysteria2 process is not running",
        "pool_available": 1 if running else 0,
        "ports": port_status,
        "network_mode": read_runtime_network_mode(),
    }

def close_link_bridge_sessions(link_id):
    stale = []
    with active_bridges_lock:
        for sid, session in list(active_bridges.items()):
            if getattr(session, "link_id", None) == link_id:
                stale.append(session)
                active_bridges.pop(sid, None)
    for session in stale:
        session.close()
    return len(stale)

def stop_link_lifecycle(link_id, link_data, join_timeout=2.0):
    init_link_lifecycle(link_data)
    link_data["running"] = False
    link_data["stop_event"].set()
    terminate_engine_link_process(link_data)
    close_link_bridge_sessions(link_id)
    mux_pool = link_data.get("mux_pool")
    if mux_pool:
        mux_pool.close()

    listeners = (
        link_data.get("bridge_sock"),
        link_data.get("sync_sock"),
        link_data.get("direct_bridge_sock"),
    )
    for sock in listeners:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    pool = link_data.get("pool")
    if pool:
        while True:
            try:
                close_tunnel_quietly(pool.get_nowait())
            except Empty:
                break

    with link_data["lifecycle_lock"]:
        sockets = list(link_data["sockets"])
    for sock in sockets:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass

    deadline = time.time() + max(0.1, float(join_timeout))
    current = threading.current_thread()
    with link_data["lifecycle_lock"]:
        threads = list(link_data["threads"])
    for thread in threads:
        if thread is current:
            continue
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        thread.join(timeout=min(0.35, remaining))
    with link_data["lifecycle_lock"]:
        link_data["sockets"].clear()
        link_data["worker_threads_alive"] = sum(1 for thread in link_data["worker_threads"] if thread.is_alive())

def link_runtime_healthy(link_data):
    if not link_is_running(link_data):
        return False
    if link_data.get("engine_managed"):
        process = link_data.get("engine_process")
        return bool(process and process.poll() is None)
    if link_data.get("local_tunnel_role") == "client" or "direct_bridge_sock" in link_data:
        with link_data["lifecycle_lock"]:
            workers = sum(1 for thread in link_data.get("worker_threads", ()) if thread.is_alive())
        return workers > 0
    bridge_sock = link_data.get("bridge_sock")
    sync_sock = link_data.get("sync_sock")
    return bool(
        bridge_sock and bridge_sock.fileno() >= 0
        and (
            not link_data.get("auto_sync_enabled")
            or (sync_sock and sync_sock.fileno() >= 0)
        )
    )

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

class BondBridgeSession:
    def __init__(self, endpoint, lanes, link_id, target_port):
        self.endpoint = endpoint
        self.lanes = list(lanes)
        self.link_id = link_id
        self.target_port = target_port
        self.last_activity = time.time()
        self.created_at = time.time()
        self.lock = threading.Lock()

    def update_activity(self):
        with self.lock:
            self.last_activity = time.time()

    def close(self):
        try:
            self.endpoint.close()
        except Exception:
            pass
        for lane in self.lanes:
            close_tunnel_quietly(lane)

class PendingBondGroup:
    def __init__(self, link_id, group_id, target_port, total_lanes):
        self.link_id = link_id
        self.group_id = group_id
        self.target_port = target_port
        self.total_lanes = total_lanes
        self.lanes = {}
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.done = threading.Event()
        self.leader_claimed = False
        self.error = ""
        self.created_at = time.time()

    def add_lane(self, lane_index, lane):
        with self.lock:
            if lane_index in self.lanes:
                raise RuntimeError("Duplicate bonding lane")
            self.lanes[lane_index] = lane
            if len(self.lanes) == self.total_lanes:
                self.ready.set()

    def claim_leader(self):
        with self.lock:
            if self.leader_claimed:
                return False
            self.leader_claimed = True
            return True

    def ordered_lanes(self):
        with self.lock:
            return [self.lanes[index] for index in range(self.total_lanes)]

    def close(self):
        with self.lock:
            lanes = list(self.lanes.values())
        for lane in lanes:
            close_tunnel_quietly(lane)
        self.done.set()

def adaptive_bond_lane_count(link_data, requested):
    requested = clamp_int(requested, 2, 2, BONDING_MAX_LANES)
    pool = link_data.get("pool")
    available = pool.qsize() if pool else 0
    active = count_active_bridge_sessions(link_data.get("_link_id"))
    with link_data["lifecycle_lock"]:
        in_use = int(link_data.get("bonded_lanes_in_use", 0) or 0)
        budget = max(1, int(link_data.get("max_workers", MAX_REVERSE_WORKERS_PER_LINK) or 1))
    free_budget = max(0, budget - in_use)
    if threading.active_count() >= THREAD_PRESSURE_SOFT or active >= budget:
        return 1
    # Existing sessions already own their lanes. Divide the remaining worker
    # budget by current demand so new users cannot multiply connections
    # without bound. A single user on an idle link can still receive the full
    # selected ceiling (up to 16 lanes).
    fair_share = max(1, budget // max(1, active + 1))
    capacity = min(requested, available, free_budget, fair_share)
    for lane_count in BONDING_LANE_STEPS:
        if lane_count <= capacity:
            return lane_count
    return 1

def reserve_bond_lanes(link_data, requested):
    lanes = []
    deadline = time.time() + POOL_WAIT
    while len(lanes) < requested and time.time() < deadline:
        try:
            candidate = link_data["pool"].get(timeout=max(0.05, deadline - time.time()))
        except Empty:
            break
        try:
            if not is_socket_alive(candidate.raw_sock):
                close_tunnel_quietly(candidate)
                continue
        except Exception:
            close_tunnel_quietly(candidate)
            continue
        untrack_link_socket(link_data, getattr(candidate, "raw_sock", None))
        lanes.append(candidate)
    return lanes

def send_bond_join(lane, group_id, lane_index, lane_count, target_port):
    lane.sendall(struct.pack("!H", BOND_TARGET_SENTINEL))
    lane.sendall(BOND_JOIN_HEADER.pack(BOND_MAGIC, group_id, lane_index, lane_count, target_port))

def receive_bond_join(lane):
    raw = recv_exact(lane, BOND_JOIN_HEADER.size)
    if not raw:
        raise RuntimeError("Bonding join header was not received")
    magic, group_id, lane_index, lane_count, target_port = BOND_JOIN_HEADER.unpack(raw)
    if magic != BOND_MAGIC or lane_count < 2 or lane_index >= lane_count or not valid_port(target_port):
        raise RuntimeError("Invalid bonding join header")
    return group_id, lane_index, lane_count, target_port

def join_pending_bond_group(link_id, lane, group_id, lane_index, lane_count, target_port):
    key = (str(link_id), int(group_id))
    with bond_groups_lock:
        group = bond_groups.get(key)
        if group is None:
            group = PendingBondGroup(link_id, group_id, target_port, lane_count)
            bond_groups[key] = group
        elif group.total_lanes != lane_count or group.target_port != target_port:
            raise RuntimeError("Bonding group metadata mismatch")
    group.add_lane(lane_index, lane)
    return key, group

def remove_pending_bond_group(key, group):
    with bond_groups_lock:
        if bond_groups.get(key) is group:
            bond_groups.pop(key, None)

def bonded_bridge(endpoint, lanes, link_id, target_port):
    lanes = list(lanes)
    session = BondBridgeSession(endpoint, lanes, link_id, target_port)
    session_id = id(session)
    stop_event = threading.Event()
    error_box = []
    with active_bridges_lock:
        active_bridges[session_id] = session

    lane_queues = [Queue(maxsize=8) for _ in lanes]
    lane_senders = []

    def lane_sender(index, lane):
        try:
            while not stop_event.is_set():
                item = lane_queues[index].get()
                if item is None:
                    lane.sendall(BOND_FRAME_HEADER.pack(send_sequence[0], 0, 0))
                    return
                sequence, payload, checksum = item
                lane.sendall(BOND_FRAME_HEADER.pack(sequence, len(payload), checksum) + payload)
        except Exception as exc:
            error_box.append(str(exc))
            stop_event.set()

    send_sequence = [0]
    for index, lane in enumerate(lanes):
        thread = threading.Thread(
            target=lane_sender,
            args=(index, lane),
            name=f"p00rija-bond-lane-send-{link_id}-{index}"[:63],
            daemon=True,
        )
        thread.start()
        lane_senders.append(thread)

    def send_direction():
        sequence = 0
        lane_cursor = 0

        def enqueue(lane_queue, item):
            while not stop_event.is_set():
                try:
                    lane_queue.put(item, timeout=0.25)
                    return True
                except Full:
                    continue
            return False

        try:
            while not stop_event.is_set():
                payload = endpoint.recv(BONDING_FRAME_SIZE)
                if not payload:
                    send_sequence[0] = sequence
                    for lane_queue in lane_queues:
                        enqueue(lane_queue, None)
                    return
                checksum = zlib.crc32(payload) & 0xFFFFFFFF
                candidates = sorted(
                    range(len(lanes)),
                    key=lambda index: (
                        lane_queues[index].qsize(),
                        (index - lane_cursor) % len(lanes),
                    ),
                )
                selected = candidates[0]
                lane_cursor = (selected + 1) % len(lanes)
                if not enqueue(lane_queues[selected], (sequence, payload, checksum)):
                    return
                sequence += 1
                session.update_activity()
        except Exception as exc:
            error_box.append(str(exc))
            stop_event.set()

    send_thread = threading.Thread(
        target=send_direction,
        name=f"p00rija-bond-send-{link_id}"[:63],
        daemon=True,
    )
    send_thread.start()
    pending = {}
    expected = 0
    eof_sequence = None
    eof_lanes = set()
    reader_lock = threading.Lock()
    reader_condition = threading.Condition(reader_lock)

    def read_lane(index, lane):
        nonlocal eof_sequence
        try:
            while not stop_event.is_set():
                header = recv_exact(lane, BOND_FRAME_HEADER.size)
                if not header:
                    raise RuntimeError(f"Bonding lane {index} closed")
                sequence, payload_size, checksum = BOND_FRAME_HEADER.unpack(header)
                if payload_size == 0:
                    with reader_condition:
                        eof_lanes.add(index)
                        eof_sequence = sequence if eof_sequence is None else min(eof_sequence, sequence)
                        reader_condition.notify_all()
                    return
                if payload_size > BONDING_FRAME_SIZE:
                    raise RuntimeError("Bonding frame exceeds configured limit")
                payload = recv_exact(lane, payload_size)
                if not payload or (zlib.crc32(payload) & 0xFFFFFFFF) != checksum:
                    raise RuntimeError(f"Bonding integrity check failed on lane {index}")
                with reader_condition:
                    while len(pending) >= 256 and sequence != expected and not stop_event.is_set():
                        reader_condition.wait(0.1)
                    pending[sequence] = payload
                    reader_condition.notify_all()
        except Exception as exc:
            error_box.append(str(exc))
            stop_event.set()
            with reader_condition:
                reader_condition.notify_all()

    readers = [
        threading.Thread(
            target=read_lane,
            args=(index, lane),
            name=f"p00rija-bond-recv-{link_id}-{index}"[:63],
            daemon=True,
        )
        for index, lane in enumerate(lanes)
    ]
    for thread in readers:
        thread.start()
    receive_complete = False
    try:
        while not stop_event.is_set():
            with reader_condition:
                while expected not in pending and not stop_event.is_set():
                    if eof_sequence is not None and expected >= eof_sequence and len(eof_lanes) == len(lanes):
                        try:
                            endpoint.shutdown(socket.SHUT_WR)
                        except Exception:
                            pass
                        receive_complete = True
                        break
                    reader_condition.wait(0.25)
                if receive_complete:
                    break
                payload = pending.pop(expected, None)
                reader_condition.notify_all()
            if payload is None:
                continue
            endpoint.sendall(payload)
            expected += 1
            session.update_activity()
        while receive_complete and send_thread.is_alive() and not stop_event.is_set():
            send_thread.join(timeout=0.5)
    finally:
        # On the successful path each lane sender already has an EOF frame in
        # its queue. Let those frames reach the peer before stop_event makes
        # sender loops exit and before session.close() tears down the sockets.
        # Closing first caused intermittent "Bonding lane closed" failures
        # during otherwise complete transfers.
        if receive_complete and not error_box:
            send_thread.join(timeout=2.0)
            for thread in lane_senders:
                thread.join(timeout=2.0)
        stop_event.set()
        with reader_condition:
            reader_condition.notify_all()
        send_thread.join(timeout=0.5)
        if not receive_complete or error_box:
            for lane_queue in lane_queues:
                try:
                    lane_queue.put_nowait(None)
                except Full:
                    pass
        session.close()
        for thread in lane_senders:
            thread.join(timeout=0.5)
        for thread in readers:
            thread.join(timeout=0.2)
        with active_bridges_lock:
            active_bridges.pop(session_id, None)
    if error_box:
        raise OSError(error_box[0])

def link_data_plane_architecture(link):
    architecture = str(link.get("data_plane_architecture") or "").strip().lower()
    if architecture in ("per_user", "adaptive_bonding", "shared_mux", "smart_hybrid"):
        return architecture
    return "adaptive_bonding" if bool(link.get("bonding_enabled", False)) else "per_user"

class MuxStreamSession:
    def __init__(self, carrier, stream_id, local_sock, link_id, target_port):
        self.carrier = carrier
        self.stream_id = int(stream_id)
        self.local_sock = local_sock
        self.link_id = link_id
        self.target_port = int(target_port)
        self.last_activity = time.time()
        self.created_at = time.time()
        self.local_eof = False
        self.remote_eof = False
        self.remote_drained = False
        self.closed = False
        self.lock = threading.Lock()
        self.done = threading.Event()
        # Bound each stream independently: slow clients are reset without
        # blocking the shared carrier or retaining unbounded payload data.
        self.remote_queue = Queue(maxsize=8)
        self.remote_writer_started = False

    def update_activity(self):
        with self.lock:
            self.last_activity = time.time()

    def mark_local_eof(self):
        with self.lock:
            self.local_eof = True
            return self.remote_drained

    def mark_remote_eof(self):
        with self.lock:
            self.remote_eof = True
            return self.local_eof

    def close(self, notify=False):
        with self.lock:
            if self.closed:
                return
            self.closed = True
        try:
            self.remote_queue.put_nowait(None)
        except Full:
            pass
        if notify and self.carrier.running:
            try:
                self.carrier.send_frame(MUX_FRAME_RST, self.stream_id)
            except Exception:
                pass
        try:
            self.local_sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.local_sock.close()
        except Exception:
            pass
        untrack_link_socket(self.carrier.link_data, self.local_sock)
        self.carrier.remove_stream(self.stream_id, close=False)
        with self.carrier.link_data["lifecycle_lock"]:
            self.carrier.link_data["mux_streams"] = max(
                0,
                int(self.carrier.link_data.get("mux_streams", 0) or 0) - 1,
            )
        with active_bridges_lock:
            active_bridges.pop(id(self), None)
        self.done.set()

    def start_remote_writer(self):
        with self.lock:
            if self.remote_writer_started:
                return
            self.remote_writer_started = True

        def writer():
            try:
                while self.carrier.running and not self.closed:
                    payload = self.remote_queue.get()
                    if payload is None:
                        try:
                            self.local_sock.shutdown(socket.SHUT_WR)
                        except Exception:
                            pass
                        with self.lock:
                            self.remote_drained = True
                            local_eof = self.local_eof
                        if local_eof:
                            self.close()
                        return
                    self.local_sock.sendall(payload)
                    self.update_activity()
            except Exception:
                self.close(notify=True)

        start_link_thread(
            self.carrier.link_data,
            writer,
            name=f"p00rija-mux-deliver-{self.link_id}-{self.stream_id}",
        )

    def queue_remote_data(self, payload):
        try:
            self.remote_queue.put_nowait(payload)
            return True
        except Full:
            return False

    def queue_remote_eof(self):
        try:
            self.remote_queue.put_nowait(None)
            return True
        except Full:
            return False

class SharedMuxCarrier:
    def __init__(self, endpoint, link_data, link_id, carrier_id, *, on_open=None, on_close=None):
        self.endpoint = endpoint
        self.link_data = link_data
        self.link_id = link_id
        self.carrier_id = int(carrier_id)
        self.on_open = on_open
        self.on_close = on_close
        self.streams = {}
        self.streams_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.running = True
        self.created_at = time.time()
        self.bytes_sent = 0
        self.bytes_received = 0
        self.streams_total = 0
        self.last_error = ""
        self.last_received_at = time.monotonic()
        self.last_pong_at = self.last_received_at

    @property
    def active_streams(self):
        with self.streams_lock:
            return len(self.streams)

    def send_frame(self, frame_type, stream_id, payload=b""):
        if not self.running:
            raise OSError("Mux carrier is closed")
        payload = payload or b""
        checksum = zlib.crc32(payload) & 0xFFFFFFFF
        frame = MUX_FRAME_HEADER.pack(int(frame_type), int(stream_id), len(payload), checksum) + payload
        with self.write_lock:
            self.endpoint.sendall(frame)
            self.bytes_sent += len(payload)

    def register_stream(self, stream_id, local_sock, target_port):
        tune_tcp(local_sock)
        track_link_socket(self.link_data, local_sock)
        session = MuxStreamSession(self, stream_id, local_sock, self.link_id, target_port)
        with self.streams_lock:
            if stream_id in self.streams or len(self.streams) >= MUX_MAX_STREAMS_PER_CARRIER:
                untrack_link_socket(self.link_data, local_sock)
                local_sock.close()
                raise RuntimeError("Mux carrier stream limit reached")
            self.streams[stream_id] = session
            self.streams_total += 1
        session.start_remote_writer()
        with self.link_data["lifecycle_lock"]:
            self.link_data["mux_streams"] = int(self.link_data.get("mux_streams", 0) or 0) + 1
            self.link_data["mux_streams_total"] = int(self.link_data.get("mux_streams_total", 0) or 0) + 1
        with active_bridges_lock:
            active_bridges[id(session)] = session
        return session

    def remove_stream(self, stream_id, close=True):
        with self.streams_lock:
            session = self.streams.pop(int(stream_id), None)
        if session and close:
            session.close()
        return session

    def allocate_stream_id(self):
        for _ in range(32):
            stream_id = secrets.randbits(31) + 1
            with self.streams_lock:
                if stream_id not in self.streams:
                    return stream_id
        raise RuntimeError("Unable to allocate mux stream id")

    def start_local_stream(self, local_sock, target_port):
        stream_id = self.allocate_stream_id()
        session = self.register_stream(stream_id, local_sock, target_port)
        self.send_frame(MUX_FRAME_OPEN, stream_id, struct.pack("!H", int(target_port)))
        self.start_pump(session)
        return session

    def start_pump(self, session):
        def pump():
            try:
                while self.running and not session.closed:
                    payload = session.local_sock.recv(MUX_MAX_FRAME_SIZE)
                    if not payload:
                        self.send_frame(MUX_FRAME_FIN, session.stream_id)
                        if session.mark_local_eof():
                            session.close()
                        return
                    self.send_frame(MUX_FRAME_DATA, session.stream_id, payload)
                    session.update_activity()
            except Exception:
                try:
                    self.send_frame(MUX_FRAME_RST, session.stream_id)
                except Exception:
                    pass
                session.close()
        start_link_thread(
            self.link_data,
            pump,
            name=f"p00rija-mux-stream-{self.link_id}-{session.stream_id}",
        )

    def handle_open(self, stream_id, payload):
        if not self.on_open or len(payload) != 2:
            self.send_frame(MUX_FRAME_RST, stream_id)
            return
        (target_port,) = struct.unpack("!H", payload)
        if not valid_port(target_port):
            self.send_frame(MUX_FRAME_RST, stream_id)
            return
        try:
            local_sock = self.on_open(target_port)
            session = self.register_stream(stream_id, local_sock, target_port)
            self.start_pump(session)
        except Exception:
            self.send_frame(MUX_FRAME_RST, stream_id)

    def handle_frame(self, frame_type, stream_id, payload):
        if frame_type == MUX_FRAME_OPEN:
            self.handle_open(stream_id, payload)
            return
        if frame_type == MUX_FRAME_PING:
            self.send_frame(MUX_FRAME_PONG, stream_id, payload)
            return
        if frame_type == MUX_FRAME_PONG:
            self.last_pong_at = time.monotonic()
            return
        with self.streams_lock:
            session = self.streams.get(int(stream_id))
        if not session:
            if frame_type not in (MUX_FRAME_FIN, MUX_FRAME_RST):
                self.send_frame(MUX_FRAME_RST, stream_id)
            return
        if frame_type == MUX_FRAME_DATA:
            if not session.queue_remote_data(payload):
                self.send_frame(MUX_FRAME_RST, stream_id)
                session.close()
        elif frame_type == MUX_FRAME_FIN:
            session.mark_remote_eof()
            if not session.queue_remote_eof():
                self.send_frame(MUX_FRAME_RST, stream_id)
                session.close()
        elif frame_type == MUX_FRAME_RST:
            session.close()

    def run(self):
        def heartbeat():
            while self.running and link_is_running(self.link_data):
                time.sleep(MUX_KEEPALIVE_INTERVAL)
                if not self.running:
                    return
                try:
                    self.send_frame(MUX_FRAME_PING, 0, struct.pack("!d", time.monotonic()))
                except Exception:
                    self.close()
                    return
                if time.monotonic() - self.last_received_at > MUX_DEAD_TIMEOUT:
                    self.last_error = "Mux carrier keepalive timed out"
                    self.close()
                    return

        start_link_thread(
            self.link_data,
            heartbeat,
            name=f"p00rija-mux-heartbeat-{self.link_id}-{self.carrier_id}",
        )
        try:
            while link_is_running(self.link_data) and self.running:
                header = recv_exact(self.endpoint, MUX_FRAME_HEADER.size)
                if not header:
                    raise OSError("Mux carrier closed")
                frame_type, stream_id, payload_size, checksum = MUX_FRAME_HEADER.unpack(header)
                if payload_size > MUX_MAX_FRAME_SIZE:
                    raise OSError("Mux frame exceeds configured limit")
                payload = recv_exact(self.endpoint, payload_size) if payload_size else b""
                if payload_size and (not payload or (zlib.crc32(payload) & 0xFFFFFFFF) != checksum):
                    raise OSError("Mux frame integrity check failed")
                self.last_received_at = time.monotonic()
                self.bytes_received += len(payload)
                self.handle_frame(frame_type, stream_id, payload)
        except Exception as exc:
            if self.running and link_is_running(self.link_data):
                self.last_error = str(exc)[:180]
        finally:
            self.close()

    def close(self):
        if not self.running:
            return
        self.running = False
        with self.streams_lock:
            sessions = list(self.streams.values())
            self.streams.clear()
        for session in sessions:
            session.close()
        close_tunnel_quietly(self.endpoint)
        if self.on_close:
            try:
                self.on_close(self)
            except Exception:
                pass

class SharedMuxPool:
    def __init__(self, link_data, link_id, desired_carriers, *, adaptive=False, min_carriers=2, max_carriers=None, min_streams=8):
        self.link_data = link_data
        self.link_id = link_id
        self.desired_carriers = clamp_int(desired_carriers, 4, 2, MUX_MAX_CARRIERS)
        self.adaptive = bool(adaptive)
        self.min_carriers = clamp_int(min_carriers, 2, 1, MUX_MAX_CARRIERS)
        self.max_carriers = clamp_int(
            max_carriers if max_carriers is not None else desired_carriers,
            self.desired_carriers,
            self.min_carriers,
            MUX_MAX_CARRIERS,
        )
        self.min_streams = clamp_int(min_streams, 8, 1, MUX_MAX_STREAMS_PER_CARRIER)
        self.carriers = {}
        self.lock = threading.Lock()
        self.carriers_total = 0
        self.fallbacks = 0

    def add_carrier(self, carrier):
        with self.lock:
            self.carriers[carrier.carrier_id] = carrier
            self.carriers_total += 1
            count = len(self.carriers)
        self.link_data["mux_carriers"] = count

    def remove_carrier(self, carrier):
        with self.lock:
            if self.carriers.get(carrier.carrier_id) is carrier:
                self.carriers.pop(carrier.carrier_id, None)
            count = len(self.carriers)
        self.link_data["mux_carriers"] = count

    def live_carriers(self):
        with self.lock:
            return [carrier for carrier in self.carriers.values() if carrier.running]

    def rebalance(self):
        if not self.adaptive:
            return self.desired_carriers
        active_streams = self.active_streams
        ram = float(get_ram_percent() or 0)
        pressure_cap = self.max_carriers
        if ram >= 90 or threading.active_count() >= 900:
            pressure_cap = self.min_carriers
        elif ram >= 80 or threading.active_count() >= 700:
            pressure_cap = max(self.min_carriers, self.max_carriers // 2)
        stream_target = self.min_carriers + max(0, active_streams - 1) // self.min_streams
        target = max(self.min_carriers, min(pressure_cap, stream_target))
        self.desired_carriers = target
        live = sorted(
            self.live_carriers(),
            key=lambda carrier: (carrier.active_streams, carrier.created_at),
            reverse=True,
        )
        idle_excess = len(live) - target
        if idle_excess > 0:
            for carrier in sorted(live, key=lambda item: (item.active_streams, item.created_at)):
                if idle_excess <= 0:
                    break
                if carrier.active_streams == 0 and time.time() - carrier.created_at >= 15:
                    carrier.close()
                    idle_excess -= 1
        self.link_data["mux_desired_carriers"] = target
        self.link_data["mux_adaptive"] = True
        return target

    @property
    def active_streams(self):
        return sum(carrier.active_streams for carrier in self.live_carriers())

    def open_stream(self, local_sock, target_port):
        carriers = [
            carrier
            for carrier in self.live_carriers()
            if carrier.active_streams < MUX_MAX_STREAMS_PER_CARRIER
        ]
        if not carriers:
            self.fallbacks += 1
            return None
        carrier = min(
            carriers,
            key=lambda item: (
                item.active_streams,
                (item.bytes_sent + item.bytes_received) // max(1, item.streams_total),
                item.carrier_id,
            ),
        )
        return carrier.start_local_stream(local_sock, target_port)

    def close(self):
        for carrier in self.live_carriers():
            carrier.close()

def send_mux_join(lane, carrier_id, carrier_count):
    lane.sendall(struct.pack("!H", MUX_TARGET_SENTINEL))
    lane.sendall(MUX_JOIN_HEADER.pack(MUX_MAGIC, int(carrier_id), int(carrier_count)))

def receive_mux_join(lane):
    raw = recv_exact(lane, MUX_JOIN_HEADER.size)
    if not raw:
        raise RuntimeError("Mux join header was not received")
    magic, carrier_id, carrier_count = MUX_JOIN_HEADER.unpack(raw)
    if magic != MUX_MAGIC or carrier_count < 2 or carrier_count > MUX_MAX_CARRIERS or carrier_id >= carrier_count:
        raise RuntimeError("Invalid mux join header")
    return carrier_id, carrier_count

def bridge_select_socket(endpoint):
    return getattr(endpoint, "raw_sock", endpoint)

def endpoint_has_buffered_data(endpoint):
    return bool(getattr(endpoint, "read_buf", b""))

def endpoint_supports_half_close(endpoint):
    # A TunnelSocket may be framed and/or backed by TLS. Calling shutdown()
    # on its raw socket bypasses the framing/TLS state machine and can corrupt
    # the response (notably WSS latency probes). Local service/user sockets can
    # safely receive a TCP half-close.
    if isinstance(endpoint, TunnelSocket):
        return endpoint.mode in ("websocket", "http_obfs") or not isinstance(endpoint.raw_sock, ssl.SSLSocket)
    return True

def bridge(a, b, link_id: str, target_port: int):
    session = BridgeSession(a, b, link_id, target_port)
    session_id = id(session)
    with active_bridges_lock:
        active_bridges[session_id] = session
    try:
        # One bidirectional selector loop replaces the previous extra pipe
        # thread per session. Besides halving active-session thread usage, this
        # preserves the response side after a client half-closes its request —
        # a common pattern in latency and "real delay" probes.
        directions = {a: b, b: a}
        half_closed_at = None
        while directions:
            buffered = [src for src in directions if endpoint_has_buffered_data(src)]
            if buffered:
                readable_endpoints = buffered
            else:
                raw_to_endpoint = {
                    bridge_select_socket(src): src
                    for src in directions
                }
                try:
                    readable_raw, _, exceptional_raw = select.select(
                        list(raw_to_endpoint),
                        [],
                        list(raw_to_endpoint),
                        1.0,
                    )
                except Exception:
                    break
                if exceptional_raw:
                    break
                readable_endpoints = [raw_to_endpoint[raw] for raw in readable_raw]
                if not readable_endpoints:
                    if half_closed_at and time.time() - half_closed_at >= BRIDGE_HALF_CLOSE_GRACE:
                        break
                    continue

            for src in readable_endpoints:
                dst = directions.get(src)
                if dst is None:
                    continue
                try:
                    data = src.recv(BUF_COPY)
                except Exception:
                    data = b""
                if not data:
                    directions.pop(src, None)
                    half_closed_at = half_closed_at or time.time()
                    if endpoint_supports_half_close(dst):
                        try:
                            dst.shutdown(socket.SHUT_WR)
                        except Exception:
                            pass
                    continue
                try:
                    dst.sendall(data)
                except Exception:
                    directions.clear()
                    break
                session.update_activity()
    finally:
        with active_bridges_lock:
            active_bridges.pop(session_id, None)
        session.close()

def start_bridge_monitor(max_idle_seconds: float):
    def monitor_loop():
        while True:
            time.sleep(THREAD_GUARD_INTERVAL)
            now = time.time()
            stale = []
            with active_bridges_lock:
                for sid, session in list(active_bridges.items()):
                    if now - session.last_activity > max_idle_seconds:
                        stale.append((sid, session))
                        active_bridges.pop(sid, None)
            for _sid, s in stale:
                s.close()
    threading.Thread(target=monitor_loop, daemon=True).start()

def start_runtime_maintenance():
    def maintenance_loop():
        while True:
            time.sleep(60)
            now = time.time()
            changed = False
            with active_sessions_lock:
                for session_token, last_seen in list(active_sessions.items()):
                    if now - last_seen > 86400:
                        active_sessions.pop(session_token, None)
            prune_ssh_sessions(max_idle=300)
            commands = db.data.setdefault("node_commands", {})
            for node_id, pending in list(commands.items()):
                fresh = [
                    command for command in pending
                    if now - float(command.get("created_at", now)) < 1800
                ]
                if len(fresh) != len(pending):
                    commands[node_id] = fresh
                    changed = True
            if changed:
                db.save()
            cleanup_node_update_packages()
    threading.Thread(target=maintenance_loop, name="p00rija-maintenance", daemon=True).start()

def count_active_bridge_sessions(link_id=None):
    with active_bridges_lock:
        if link_id is None:
            return len(active_bridges)
        return sum(1 for session in active_bridges.values() if getattr(session, "link_id", None) == link_id)

def desired_reverse_workers(max_workers, active_sessions=0, min_ready=None):
    max_workers = max(1, int(max_workers or 1))
    if not SMART_THREAD_GUARD_ENABLED:
        return max_workers
    min_ready = clamp_int(
        MIN_READY_WORKERS_PER_LINK if min_ready is None else min_ready,
        MIN_READY_WORKERS_PER_LINK,
        1,
        max_workers,
    )
    active_sessions = max(0, int(active_sessions or 0))
    reserve = min(max_workers, active_sessions + min_ready)
    pressure = threading.active_count()
    if pressure >= THREAD_PRESSURE_HARD:
        # Never retire workers that are carrying active sessions. Under hard
        # pressure retain one warm reserve so a new flow is not forced to wait
        # for a full reconnect.
        return min(max_workers, active_sessions + 1)
    if pressure >= THREAD_PRESSURE_SOFT:
        return min(reserve, min(max_workers, active_sessions + max(1, min_ready // 2)))
    return max(1, reserve)

def should_retire_reverse_worker(link_data):
    if not SMART_THREAD_GUARD_ENABLED:
        return False
    try:
        with link_data["lifecycle_lock"]:
            alive = len(link_data.get("worker_threads", ()))
        return alive > int(link_data.get("desired_workers", 1) or 1)
    except Exception:
        return False

def close_tunnel_quietly(tunnel):
    try:
        tunnel.close()
    except Exception:
        try:
            tunnel.raw_sock.close()
        except Exception:
            pass

def reap_idle_reserve_pool(link_id, link_data, desired_keep=None, ttl=None):
    pool = link_data.get("pool")
    if not pool:
        return 0
    now = time.time()
    ttl = IDLE_RESERVE_TTL if ttl is None else float(ttl)
    desired_keep = desired_reverse_workers(
        link_data.get("max_workers", MAX_REVERSE_WORKERS_PER_LINK),
        count_active_bridge_sessions(link_id),
        link_data.get("min_ready_workers"),
    ) if desired_keep is None else max(0, int(desired_keep))
    drained = []
    reaped = 0
    while True:
        try:
            drained.append(pool.get_nowait())
        except Empty:
            break
    kept = []
    for tunnel in drained:
        alive = False
        try:
            alive = is_socket_alive(tunnel.raw_sock)
        except Exception:
            alive = False
        # A healthy reserve tunnel is useful regardless of age. TCP keepalive
        # detects dead peers; rotating live tunnels on a timer only creates
        # reconnect churn and transient V2Ray failures.
        if alive and len(kept) < desired_keep:
            kept.append(tunnel)
            continue
        close_tunnel_quietly(tunnel)
        reaped += 1
    for tunnel in kept:
        try:
            pool.put(tunnel, block=False)
        except Full:
            close_tunnel_quietly(tunnel)
            reaped += 1
    link_data["idle_workers_reaped"] = int(link_data.get("idle_workers_reaped", 0) or 0) + reaped
    return reaped

def run_thread_guardian_for_link(link_id, link_data, force=False):
    init_link_lifecycle(link_data)
    if link_data.get("engine_managed"):
        process = link_data.get("engine_process")
        running = bool(process and process.poll() is None)
        return {
            "enabled": True,
            "engine_managed": True,
            "engine": link_data.get("engine"),
            "role": link_data.get("engine_role"),
            "pid": process.pid if running else 0,
            "healthy": running,
            "action": "observe" if running else "watchdog_restart",
            "checked_at": time.time(),
            "reaped": 0,
        }
    if not SMART_THREAD_GUARD_ENABLED or not link_is_running(link_data):
        return {"enabled": bool(SMART_THREAD_GUARD_ENABLED), "reaped": 0}
    with link_data["guardian_lock"]:
        if not link_is_running(link_data):
            return {"enabled": True, "reaped": 0}
        now = time.time()
        previous = link_data.get("thread_guardian") or {}
        last_run = float(link_data.get("last_guardian_at", 0) or 0)
        if not force and previous and now - last_run < GUARDIAN_SCAN_INTERVAL:
            cached = dict(previous)
            cached["cached"] = True
            return cached
        active = count_active_bridge_sessions(link_id)
        max_workers = int(link_data.get("max_workers", MAX_REVERSE_WORKERS_PER_LINK) or MAX_REVERSE_WORKERS_PER_LINK)
        desired = desired_reverse_workers(max_workers, active, link_data.get("min_ready_workers"))
        link_data["desired_workers"] = desired
        reaped = 0
        if link_data.get("pool"):
            reaped = reap_idle_reserve_pool(link_id, link_data, desired_keep=desired)
        spawner = link_data.get("spawn_reverse_worker")
        with link_data["lifecycle_lock"]:
            alive = len(link_data.get("worker_threads", ()))
        if spawner and alive < desired:
            for _ in range(desired - alive):
                try:
                    if not spawner():
                        break
                except Exception as e:
                    link_data["last_worker_error"] = f"Worker spawn failed: {e}"[:180]
                    break
        with link_data["lifecycle_lock"]:
            alive = len(link_data.get("worker_threads", ()))
            link_data["worker_threads_alive"] = alive
        guardian = {
            "enabled": True,
            "desired_workers": desired,
            "max_workers": max_workers,
            "worker_threads_alive": alive,
            "active_sessions": active,
            "thread_pressure": threading.active_count(),
            "idle_ttl": IDLE_RESERVE_TTL,
            "reaped": reaped,
            "reaped_total": int(link_data.get("idle_workers_reaped", 0) or 0),
            "pressure_level": (
                "hard" if threading.active_count() >= THREAD_PRESSURE_HARD
                else "soft" if threading.active_count() >= THREAD_PRESSURE_SOFT
                else "normal"
            ),
            "checked_at": now,
            "cached": False,
        }
        link_data["last_guardian_at"] = now
        link_data["thread_guardian"] = guardian
        return guardian

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

def normalize_node_panel_url(value):
    """Return the panel origin even when a browser management URL was pasted."""
    raw = str(value or "").strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return raw
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return raw
    return f"{parsed.scheme}://{parsed.netloc}"

class PanelEndpointFailoverMixin:
    """Keep the migrated panel primary while using the old panel temporarily."""

    def init_panel_endpoints(self, panel_url, fallback_panel_url=""):
        self.primary_panel_url = normalize_node_panel_url(panel_url)
        self.fallback_panel_url = normalize_node_panel_url(fallback_panel_url)
        self.panel_url = self.primary_panel_url
        self.active_panel_url = self.primary_panel_url
        self.primary_panel_failures = 0
        self.primary_panel_retry_at = 0.0
        self.panel_endpoint_lock = threading.Lock()

    def panel_endpoint_status(self):
        with self.panel_endpoint_lock:
            return {
                "primary": self.primary_panel_url,
                "active": self.active_panel_url,
                "using_fallback": bool(
                    self.fallback_panel_url
                    and self.active_panel_url == self.fallback_panel_url
                ),
                "primary_failures": self.primary_panel_failures,
                "primary_retry_at": self.primary_panel_retry_at,
            }

    def _panel_candidates(self):
        now = time.monotonic()
        with self.panel_endpoint_lock:
            primary = self.primary_panel_url
            fallback = self.fallback_panel_url
            active = self.active_panel_url or primary
            retry_at = self.primary_panel_retry_at
        if active != primary and fallback:
            if now >= retry_at:
                candidates = [primary, fallback]
            else:
                # Keep the healthy fallback cheap, but immediately try primary
                # if the fallback itself stops responding.
                candidates = [fallback, primary]
        else:
            candidates = [primary, fallback]
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))

    def _record_panel_failure(self, candidate):
        if candidate != self.primary_panel_url:
            return
        now = time.monotonic()
        with self.panel_endpoint_lock:
            self.primary_panel_failures += 1
            delay = min(60.0, 5.0 * (2 ** min(self.primary_panel_failures - 1, 4)))
            self.primary_panel_retry_at = now + delay

    def _record_panel_success(self, candidate):
        with self.panel_endpoint_lock:
            previous = self.active_panel_url
            if (
                candidate == self.fallback_panel_url
                and previous == self.primary_panel_url
                and self.primary_panel_failures == 0
            ):
                # A fallback request may have started in another thread before
                # a newer primary request recovered. Never let that stale
                # fallback response overwrite the confirmed primary endpoint.
                return
            self.active_panel_url = candidate
            self.panel_url = candidate
            if candidate == self.primary_panel_url:
                self.primary_panel_failures = 0
                self.primary_panel_retry_at = 0.0
        if candidate != previous:
            source = "primary" if candidate == self.primary_panel_url else "fallback"
            db.log("node", "warning", f"Panel endpoint switched to {source}: {candidate}")

    def panel_request(self, path, payload=None, timeout=5):
        last_error = None
        for candidate in self._panel_candidates():
            try:
                response = make_panel_request(
                    candidate, path, self.token, payload,
                    timeout=timeout, private_key=self.private_key,
                )
                self._record_panel_success(candidate)
                return response
            except Exception as exc:
                last_error = exc
                self._record_panel_failure(candidate)
        raise last_error or RuntimeError("No panel endpoint is configured")


# --------- Iran Node Daemon Controller ----------
class IranNodeController(PanelEndpointFailoverMixin):
    def __init__(self, panel_url, token, private_key="", fallback_panel_url=""):
        self.init_panel_endpoints(panel_url, fallback_panel_url)
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
                res = self.panel_request("/api/node-config")
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
                    current["_raw_config"] = link
                    current["signature"] = signature
                    if not current.get("engine_managed") and (current.get("local_tunnel_role") == "server" or "pool" in current):
                        self.update_link_ports(link_id, link)

            for lid in list(self.active_links.keys()):
                if lid not in active_link_ids:
                    self.stop_link(lid)

    def link_signature(self, link):
        keys = ("direction", "local_tunnel_role", "server_ip", "peer_ip", "bridge_port", "sync_port", "pool_size", "max_reverse_workers", "min_ready_workers", "data_plane_architecture", "mux_carriers", "adaptive_smux_enabled", "smux_min_connections", "smux_max_connections", "smux_min_streams", "smux_padding", "bonding_enabled", "bonding_max_lanes", "engine", "transport", "network", "tls_enabled", "tls_sni", "cert_content", "tunnel_mode", "obfs_host", "obfs_path", "profile_id", "padding_min", "padding_max", "jitter_ms", "keepalive_interval", "awg_mtu", "awg_jc", "awg_jmin", "awg_jmax", "awg_s1", "awg_s2", "awg_s3", "awg_s4", "awg_h1", "awg_h2", "awg_h3", "awg_h4", "awg_i1", "awg_i2", "awg_i3", "awg_i4", "awg_i5", "wg_address", "wg_client_address", "wg_mtu", "wg_allowed_ips", "wg_interface")
        # Port mappings are hot-reloaded below. Treating them as a process
        # signature forced both endpoints to restart for every add/remove,
        # dropping active VPN sessions and the temporary payload-test echo.
        signature = tuple(link.get(k) for k in keys)
        if native_hysteria2_enabled(link):
            signature += (
                link_ports_signature(link),
                link.get("key_content"),
                link.get("cert_sni"),
                link.get("hysteria_up_mbps"),
                link.get("hysteria_down_mbps"),
            )
        return signature
                    
    def engine_watchdog_loop(self):
        last_restart = time.time()
        while self.running:
            try:
                # Engine restart interval logic
                interval_minutes = getattr(self, "engine_restart_interval", 0)
                if interval_minutes > 0 and time.time() - last_restart > interval_minutes * 60:
                    restarted = 0
                    with self.lock:
                        for lid, link_data in list(self.active_links.items()):
                            link = link_data.get("_raw_config")
                            if link and not link_runtime_healthy(link_data):
                                self.stop_link(lid)
                                self.start_link(link)
                                restarted += 1
                    db.log("iran-node", "info", f"Watchdog maintenance checked links; restarted unhealthy={restarted}.")
                    last_restart = time.time()
                    
                # Engine health check logic
                with self.lock:
                    for lid, link_data in list(self.active_links.items()):
                        if link_data.get("engine_managed") and not link_runtime_healthy(link_data):
                            if time.time() - float(link_data.get("engine_started_at", 0) or 0) >= HYSTERIA2_PROCESS_RESTART_DELAY:
                                link = link_data.get("_raw_config")
                                self.stop_link(lid)
                                if link:
                                    self.start_link(link)
                                continue
                        run_thread_guardian_for_link(lid, link_data)
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
            time.sleep(THREAD_GUARD_INTERVAL)

    def start_link(self, link):
        if native_hysteria2_enabled(link):
            try:
                self.active_links[link["id"]] = start_hysteria2_link(link)
            except Exception as e:
                db.log("iran-node", "error", f"Native Hysteria2 start failed for {link.get('id')}: {e}")
            return
        if link.get("local_tunnel_role") == "client":
            return ForeignNodeController.start_link(self, link)
        link_id = link["id"]
        bridge_port = link["bridge_port"]
        sync_port = link["sync_port"]
        auto_sync_enabled = bool(link.get("auto_sync_ports"))
        tls_enabled = link.get("tls_enabled", False)
        max_workers = clamp_int(
            link.get("max_reverse_workers", MAX_REVERSE_WORKERS_PER_LINK),
            MAX_REVERSE_WORKERS_PER_LINK,
            1,
            32,
        )
        max_workers = min(max_workers, clamp_int(link.get("pool_size", 24), 24, 1, 256))
        min_ready_workers = clamp_int(
            link.get("min_ready_workers", MIN_READY_WORKERS_PER_LINK),
            MIN_READY_WORKERS_PER_LINK,
            1,
            max_workers,
        )
        pool = Queue(maxsize=max(4, MAX_POOL_SIZE_PER_LINK * 2))

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
            if not cert_path or not key_path:
                db.log("iran-node", "error", f"TLS is enabled for link {link_id}, but certificate/key material is unavailable.")
                return

        bridge_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tune_listener_socket(bridge_srv)
        try:
            bridge_srv.bind(("0.0.0.0", bridge_port))
            bridge_srv.listen(16384)
        except Exception as e:
            db.log("iran-node", "error", f"Failed binding bridge port {bridge_port}: {e}")
            return

        sync_srv = None
        if auto_sync_enabled:
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
            "_link_id": link_id,
            "bridge_port": bridge_port,
            "sync_port": sync_port,
            "bridge_sock": bridge_srv,
            "sync_sock": sync_srv,
            "auto_sync_enabled": auto_sync_enabled,
            "pool": pool,
            "max_workers": max_workers,
            "min_ready_workers": min_ready_workers,
            "desired_workers": desired_reverse_workers(max_workers, 0, min_ready_workers),
            "ports": {},
            "local_tunnel_role": "server",
            "running": True,
            "_raw_config": link,
            "idle_workers_reaped": 0,
            "direct_fallbacks": 0,
            "last_direct_error": "",
            "bonded_lanes_in_use": 0,
            "bonded_sessions": 0,
            "bonded_sessions_total": 0,
            "bonding_fallbacks": 0,
            "mux_pool": None,
            "mux_carriers": 0,
            "mux_streams": 0,
            "mux_streams_total": 0,
        }
        init_link_lifecycle(link_data)
        self.active_links[link_id] = link_data
        architecture = link_data_plane_architecture(link)
        mux_enabled = architecture in ("shared_mux", "smart_hybrid")
        mux_carrier_count = clamp_int(link.get("mux_carriers", 4), 4, 2, MUX_MAX_CARRIERS)
        if mux_enabled:
            adaptive_mux = bool(link.get("adaptive_smux_enabled", True))
            link_data["mux_pool"] = SharedMuxPool(
                link_data,
                link_id,
                mux_carrier_count,
                adaptive=adaptive_mux,
                min_carriers=link.get("smux_min_connections", 2),
                max_carriers=link.get("smux_max_connections", mux_carrier_count),
                min_streams=link.get("smux_min_streams", 8),
            )

        def accept_bridge():
            db.log("iran-node", "info", f"[DEBUG] accept_bridge started listening on {bridge_port}")
            while link_data["running"]:
                try:
                    c, addr = bridge_srv.accept()
                    track_link_socket(link_data, c)
                    db.log("iran-node", "info", f"[DEBUG] accept_bridge accepted connection from {addr}")
                    tune_tcp(c)
                    if tls_enabled and cert_path and key_path:
                        try:
                            raw_c = c
                            c = wrap_socket_server_tls(c, cert_path, key_path)
                            untrack_link_socket(link_data, raw_c)
                            track_link_socket(link_data, c)
                        except Exception as e:
                            db.log("iran-node", "error", f"[DEBUG] TLS wrap failed: {e}")
                            c.close()
                            untrack_link_socket(link_data, c)
                            continue
                    
                    mode = link.get("tunnel_mode", "tcp")
                    ts = TunnelSocket(c, role="internal", mode=mode, config=link)
                    if not ts.perform_handshake():
                        db.log("iran-node", "error", f"[DEBUG] Handshake failed from {addr}")
                        ts.close()
                        untrack_link_socket(link_data, c)
                        continue
                    ts._p00rija_pool_since = time.time()
                    ts._p00rija_link_id = link_id
                    try:
                        pool.put(ts, block=False)
                    except Full:
                        db.log("iran-node", "error", f"[DEBUG] Pool full from {addr}")
                        ts.close()
                        untrack_link_socket(link_data, c)
                except OSError:
                    if not link_data["running"]:
                        break
                    time.sleep(0.1)
                except Exception:
                    time.sleep(0.1)

        def accept_sync():
            if sync_srv is None:
                return
            while link_data["running"]:
                try:
                    c, _ = sync_srv.accept()
                    track_link_socket(link_data, c)
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
                        finally:
                            untrack_link_socket(link_data, conn)
                            conn.close()
                    start_link_thread(
                        link_data,
                        handle_sync,
                        name=f"p00rija-sync-{link_id}",
                        args=(c,),
                    )
                except OSError:
                    if not link_data["running"]:
                        break
                    time.sleep(0.1)
                except Exception:
                    time.sleep(0.1)

        def maintain_mux_carriers():
            mux_pool = link_data.get("mux_pool")
            if not mux_pool:
                return
            while link_is_running(link_data):
                mux_pool.rebalance()
                live_ids = {carrier.carrier_id for carrier in mux_pool.live_carriers()}
                missing = [index for index in range(mux_pool.desired_carriers) if index not in live_ids]
                if not missing:
                    time.sleep(0.5)
                    continue
                try:
                    candidate = pool.get(timeout=1.0)
                except Empty:
                    continue
                try:
                    if not is_socket_alive(candidate.raw_sock):
                        close_tunnel_quietly(candidate)
                        continue
                    untrack_link_socket(link_data, getattr(candidate, "raw_sock", None))
                    carrier_id = missing[0]
                    send_mux_join(candidate, carrier_id, mux_pool.desired_carriers)
                    carrier = SharedMuxCarrier(
                        candidate,
                        link_data,
                        link_id,
                        carrier_id,
                        on_close=mux_pool.remove_carrier,
                    )
                    mux_pool.add_carrier(carrier)
                    start_link_thread(
                        link_data,
                        carrier.run,
                        name=f"p00rija-mux-carrier-{link_id}-{carrier_id}",
                    )
                    db.log("iran-node", "info", f"Shared Mux carrier {carrier_id + 1}/{mux_pool.desired_carriers} is ready for {link_id}.")
                except Exception as e:
                    close_tunnel_quietly(candidate)
                    db.log("iran-node", "warning", f"Shared Mux carrier setup failed for {link_id}: {e}")
                    time.sleep(0.5)

        start_link_thread(link_data, accept_bridge, name=f"p00rija-accept-bridge-{link_id}")
        if auto_sync_enabled:
            start_link_thread(link_data, accept_sync, name=f"p00rija-accept-sync-{link_id}")
        if mux_enabled:
            start_link_thread(link_data, maintain_mux_carriers, name=f"p00rija-mux-maintain-{link_id}")
        db.log("iran-node", "info", f"Started link {link_id} (Bridge: {bridge_port}, Sync: {'enabled' if auto_sync_enabled else 'disabled'})")
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
        port_stop_event = threading.Event()
        tune_listener_socket(srv)
        try:
            srv.bind(("0.0.0.0", user_port))
            srv.listen(16384)
            # A bounded accept lets temporary/hot-reloaded port listeners
            # observe link shutdown even on kernels where close() from a
            # different thread does not immediately wake accept().
            srv.settimeout(1.0)
        except Exception as e:
            db.log("iran-node", "error", f"Failed binding user port {user_port} for link {link_id}: {e}")
            return

        def handle_user(u, p):
            tune_tcp(u)
            link = link_data.get("_raw_config") or {}
            architecture = link_data_plane_architecture(link)
            mux_pool = link_data.get("mux_pool")
            use_mux = architecture == "shared_mux"
            if architecture == "smart_hybrid" and (
                count_active_bridge_sessions(link_id) > 0
                or (mux_pool and mux_pool.active_streams > 0)
            ):
                use_mux = True
            if use_mux and mux_pool:
                deadline = time.time() + POOL_WAIT
                session = None
                while time.time() < deadline and not session:
                    try:
                        session = mux_pool.open_stream(u, target_port)
                    except Exception:
                        session = None
                    if not session:
                        time.sleep(0.05)
                if session:
                    session.done.wait()
                    return
                db.log("iran-node", "warning", f"Shared Mux unavailable for {link_id}; falling back to a per-user tunnel.")

            bonding_enabled = architecture in ("adaptive_bonding", "smart_hybrid")
            requested_lanes = clamp_int(link.get("bonding_max_lanes", 4), 4, 2, BONDING_MAX_LANES)
            desired_lanes = adaptive_bond_lane_count(link_data, requested_lanes) if bonding_enabled else 1
            reserved_lanes = reserve_bond_lanes(link_data, desired_lanes)
            if len(reserved_lanes) >= 2:
                group_id = secrets.randbits(64)
                lanes = reserved_lanes
                with link_data["lifecycle_lock"]:
                    link_data["bonded_lanes_in_use"] = int(link_data.get("bonded_lanes_in_use", 0) or 0) + len(lanes)
                    link_data["bonded_sessions"] = int(link_data.get("bonded_sessions", 0) or 0) + 1
                    link_data["bonded_sessions_total"] = int(link_data.get("bonded_sessions_total", 0) or 0) + 1
                try:
                    for lane_index, lane in enumerate(lanes):
                        send_bond_join(lane, group_id, lane_index, len(lanes), target_port)
                    db.log(
                        "iran-node",
                        "info",
                        f"Adaptive Bonding opened {len(lanes)} lanes for user port {user_port} -> {target_port}.",
                    )
                    bonded_bridge(u, lanes, link_id, target_port)
                except Exception as e:
                    db.log("iran-node", "error", f"Adaptive Bonding failed on user port {user_port}: {e}")
                    for lane in lanes:
                        close_tunnel_quietly(lane)
                    try:
                        u.close()
                    except Exception:
                        pass
                finally:
                    with link_data["lifecycle_lock"]:
                        link_data["bonded_lanes_in_use"] = max(
                            0,
                            int(link_data.get("bonded_lanes_in_use", 0) or 0) - len(lanes),
                        )
                        link_data["bonded_sessions"] = max(
                            0,
                            int(link_data.get("bonded_sessions", 0) or 0) - 1,
                        )
                return
            if bonding_enabled:
                link_data["bonding_fallbacks"] = int(link_data.get("bonding_fallbacks", 0) or 0) + 1

            deadline = time.time() + POOL_WAIT
            europe = reserved_lanes[0] if reserved_lanes else None
            while time.time() < deadline:
                if europe is not None:
                    break
                try:
                    cand = link_data["pool"].get(timeout=max(0.1, deadline - time.time()))
                except Empty:
                    break
                try:
                    if not is_socket_alive(cand.raw_sock):
                        cand.close()
                        untrack_link_socket(link_data, getattr(cand, "raw_sock", None))
                        continue
                except Exception:
                    cand.close()
                    untrack_link_socket(link_data, getattr(cand, "raw_sock", None))
                    continue
                europe = cand
                untrack_link_socket(link_data, getattr(cand, "raw_sock", None))
                break

            if not europe:
                peer_ip = str(link.get("peer_ip") or link.get("external_ip") or "").strip()
                if DIRECT_BRIDGE_FALLBACK_ENABLED and peer_ip:
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
            while link_data["running"] and not port_stop_event.is_set():
                try:
                    u, _ = srv.accept()
                    track_link_socket(link_data, u)
                    def handle_user_tracked(client, port):
                        try:
                            handle_user(client, port)
                        finally:
                            untrack_link_socket(link_data, client)
                    start_link_thread(
                        link_data,
                        handle_user_tracked,
                        name=f"p00rija-user-{link_id}-{user_port}",
                        args=(u, target_port),
                    )
                except socket.timeout:
                    if port_stop_event.is_set():
                        break
                    continue
                except OSError:
                    if not link_data["running"] or port_stop_event.is_set():
                        break
                    time.sleep(0.1)
                except Exception:
                    time.sleep(0.1)

        t = start_link_thread(link_data, accept_users, name=f"p00rija-user-listener-{link_id}-{user_port}")
        link_data["ports"][user_port] = {
            "sock": srv,
            "thread": t,
            "stop_event": port_stop_event,
            "target_port": target_port
        }
        db.log("iran-node", "info", f"Opened user port {user_port} -> Foreign:{target_port}")

    def close_user_port(self, link_data, user_port):
        pdata = link_data["ports"].pop(user_port, None)
        if pdata:
            stop_event = pdata.get("stop_event")
            if stop_event:
                stop_event.set()
            try: pdata["sock"].shutdown(socket.SHUT_RDWR)
            except Exception: pass
            try: pdata["sock"].close()
            except Exception: pass
            db.log("iran-node", "info", f"Closed user port {user_port}")

    def collect_link_statuses(self):
        statuses = {}
        with self.lock:
            items = list(self.active_links.items())
        for link_id, link_data in items:
            if link_data.get("engine_managed"):
                statuses[link_id] = engine_link_status(link_data)
                continue
            if link_data.get("local_tunnel_role") == "client" or "direct_bridge_sock" in link_data:
                statuses[link_id] = {
                    "running": bool(link_data.get("running")),
                    "role": "client",
                    "direct_bridge_listening": bool(link_data.get("direct_bridge_listening")),
                    "direct_bridges": int(link_data.get("direct_bridges", 0) or 0),
                    "ready_workers": int(link_data.get("ready_workers", 0) or 0),
                    "desired_workers": int(link_data.get("desired_workers", 0) or 0),
                    "max_workers": int(link_data.get("max_workers", 0) or 0),
                    "worker_threads_alive": int(link_data.get("worker_threads_alive", 0) or 0),
                    "worker_threads_started": int(link_data.get("worker_threads_started", 0) or 0),
                    "idle_workers_reaped": int(link_data.get("idle_workers_reaped", 0) or 0),
                    "thread_guardian": link_data.get("thread_guardian", {}),
                    "successful_bridges": int(link_data.get("successful_bridges", 0) or 0),
                    "worker_errors": int(link_data.get("worker_errors", 0) or 0),
                    "last_worker_error": link_data.get("last_worker_error", ""),
                    "bonded_sessions": int(link_data.get("bonded_sessions", 0) or 0),
                    "bonded_sessions_total": int(link_data.get("bonded_sessions_total", 0) or 0),
                    "bonded_lanes_in_use": int(link_data.get("bonded_lanes_in_use", 0) or 0),
                    "bonding_join_failures": int(link_data.get("bonding_join_failures", 0) or 0),
                    "mux_carriers": int(link_data.get("mux_carriers", 0) or 0),
                    "mux_streams": int(link_data.get("mux_streams", 0) or 0),
                    "mux_streams_total": int(link_data.get("mux_streams_total", 0) or 0),
                    "mux_carrier_failures": int(link_data.get("mux_carrier_failures", 0) or 0),
                    "network_mode": read_runtime_network_mode()
                }
                continue
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
                "sync_enabled": bool(link_data.get("auto_sync_enabled")),
                "sync_listening": bool(
                    not link_data.get("auto_sync_enabled")
                    or (link_data.get("sync_sock") and link_data["sync_sock"].fileno() != -1)
                ),
                "pool_available": pool.qsize() if pool else 0,
                "desired_workers": int(link_data.get("desired_workers", 0) or 0),
                "max_workers": int(link_data.get("max_workers", 0) or 0),
                "idle_workers_reaped": int(link_data.get("idle_workers_reaped", 0) or 0),
                "thread_guardian": link_data.get("thread_guardian", {}),
                "direct_fallbacks": int(link_data.get("direct_fallbacks", 0) or 0),
                "last_direct_error": link_data.get("last_direct_error", ""),
                "bonded_sessions": int(link_data.get("bonded_sessions", 0) or 0),
                "bonded_sessions_total": int(link_data.get("bonded_sessions_total", 0) or 0),
                "bonded_lanes_in_use": int(link_data.get("bonded_lanes_in_use", 0) or 0),
                "bonding_fallbacks": int(link_data.get("bonding_fallbacks", 0) or 0),
                "mux_carriers": int(link_data.get("mux_carriers", 0) or 0),
                "mux_desired_carriers": int(link_data.get("mux_desired_carriers", 0) or 0),
                "mux_adaptive": bool(link_data.get("mux_adaptive", False)),
                "mux_streams": int(link_data.get("mux_streams", 0) or 0),
                "mux_streams_total": int(link_data.get("mux_streams_total", 0) or 0),
                "mux_fallbacks": int(getattr(link_data.get("mux_pool"), "fallbacks", 0) or 0),
                "ports": port_status,
                "network_mode": read_runtime_network_mode()
            }
        return statuses

    def stop_link(self, link_id):
        link_data = self.active_links.pop(link_id, None)
        if link_data:
            for up in list(link_data.get("ports", {}).keys()):
                self.close_user_port(link_data, up)
            stop_link_lifecycle(link_id, link_data)
            db.log("iran-node", "info", f"Stopped link {link_id}")

    def get_local_listen_ports(self, exclude_bridge, exclude_sync, allowed_ports=None):
        return ForeignNodeController.get_local_listen_ports(self, exclude_bridge, exclude_sync, allowed_ports)

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
                "app_version": APP_VERSION,
                "app_build": APP_BUILD,
                "cpu": round(cpu_pct, 1),
                "ram": round(ram_pct, 1),
                "rx_speed": round(rx, 1),
                "tx_speed": round(tx, 1),
                "threads": threading.active_count(),
                "connections": connections,
                "link_statuses": self.collect_link_statuses(),
                "runtime_sessions": list_runtime_sessions(),
                "processes": get_process_snapshot(limit=10)
                ,"update_manifest": build_local_update_manifest()
                ,"listening_tcp_ports": get_local_listening_tcp_ports()
                ,"network_mode": read_runtime_network_mode()
                ,"published_port_ranges": read_published_port_ranges()
                ,"docker_host_gateway": read_docker_host_gateway()
                ,"panel_endpoint": self.panel_endpoint_status()
                ,"transport_capabilities": runtime_transport_capabilities()
            }

            try:
                self.panel_request("/api/report", payload)
            except Exception:
                pass

# --------- Foreign Node Daemon Controller ----------
class ForeignNodeController(PanelEndpointFailoverMixin):
    def __init__(self, panel_url, token, private_key="", fallback_panel_url=""):
        self.init_panel_endpoints(panel_url, fallback_panel_url)
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
                res = self.panel_request("/api/node-config")
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
                    if link_id in self.active_links:
                        self.active_links[link_id]["signature"] = signature
                elif current.get("signature") != signature:
                    self.stop_link(link_id)
                    self.start_link(link)
                    if link_id in self.active_links:
                        self.active_links[link_id]["signature"] = signature
                else:
                    current["_raw_config"] = link
                    current["signature"] = signature
                    if not current.get("engine_managed") and (current.get("local_tunnel_role") == "server" or "pool" in current):
                        self.update_link_ports(link_id, link)

            for lid in list(self.active_links.keys()):
                if lid not in active_link_ids:
                    self.stop_link(lid)

    def engine_watchdog_loop(self):
        last_restart = time.time()
        while self.running:
            try:
                interval_minutes = getattr(self, "engine_restart_interval", 0)
                if interval_minutes > 0 and time.time() - last_restart > interval_minutes * 60:
                    restarted = 0
                    with self.lock:
                        for lid, link_data in list(self.active_links.items()):
                            link = link_data.get("_raw_config")
                            if link and not link_runtime_healthy(link_data):
                                self.stop_link(lid)
                                self.start_link(link)
                                restarted += 1
                    db.log("foreign-node", "info", f"Watchdog maintenance checked links; restarted unhealthy={restarted}.")
                    last_restart = time.time()
                    
                # No central socket check here since pool relies on TunnelSocket which handles its own reconnection.
                with self.lock:
                    for lid, link_data in list(self.active_links.items()):
                        if link_data.get("engine_managed") and not link_runtime_healthy(link_data):
                            if time.time() - float(link_data.get("engine_started_at", 0) or 0) >= HYSTERIA2_PROCESS_RESTART_DELAY:
                                link = link_data.get("_raw_config")
                                self.stop_link(lid)
                                if link:
                                    self.start_link(link)
                                continue
                        run_thread_guardian_for_link(lid, link_data)
            except Exception as e:
                db.log("foreign-node", "error", f"Watchdog error: {e}")
            time.sleep(10)

    def link_signature(self, link):
        keys = ("direction", "local_tunnel_role", "iran_ip", "server_ip", "peer_ip", "bridge_port", "sync_port", "pool_size", "max_reverse_workers", "min_ready_workers", "data_plane_architecture", "mux_carriers", "adaptive_smux_enabled", "smux_min_connections", "smux_max_connections", "smux_min_streams", "smux_padding", "bonding_enabled", "bonding_max_lanes", "engine", "transport", "network", "tls_enabled", "tls_sni", "cert_content", "tunnel_mode", "obfs_host", "obfs_path", "profile_id", "padding_min", "padding_max", "jitter_ms", "keepalive_interval", "awg_mtu", "awg_jc", "awg_jmin", "awg_jmax", "awg_s1", "awg_s2", "awg_s3", "awg_s4", "awg_h1", "awg_h2", "awg_h3", "awg_h4", "awg_i1", "awg_i2", "awg_i3", "awg_i4", "awg_i5", "wg_address", "wg_client_address", "wg_mtu", "wg_allowed_ips", "wg_interface")
        signature = tuple(link.get(k) for k in keys)
        if native_hysteria2_enabled(link):
            signature += (
                link_ports_signature(link),
                link.get("key_content"),
                link.get("cert_sni"),
                link.get("hysteria_up_mbps"),
                link.get("hysteria_down_mbps"),
            )
        return signature

    def start_link(self, link):
        if native_hysteria2_enabled(link):
            try:
                self.active_links[link["id"]] = start_hysteria2_link(link)
            except Exception as e:
                db.log("foreign-node", "error", f"Native Hysteria2 start failed for {link.get('id')}: {e}")
            return
        if link.get("local_tunnel_role") == "server":
            return IranNodeController.start_link(self, link)
        link_id = link["id"]
        iran_ip = link["iran_ip"]
        bridge_port = link["bridge_port"]
        sync_port = link["sync_port"]
        auto_sync_enabled = bool(link.get("auto_sync_ports"))
        pool_size = clamp_int(link.get("pool_size", 24), 24, 1, 256)
        worker_count = min(
            pool_size,
            clamp_int(
                link.get("max_reverse_workers", MAX_REVERSE_WORKERS_PER_LINK),
                MAX_REVERSE_WORKERS_PER_LINK,
                1,
                32,
            ),
        )
        min_ready_workers = clamp_int(
            link.get("min_ready_workers", MIN_READY_WORKERS_PER_LINK),
            MIN_READY_WORKERS_PER_LINK,
            1,
            worker_count,
        )
        initial_workers = desired_reverse_workers(worker_count, 0, min_ready_workers)
        tls_enabled = link.get("tls_enabled", False)

        link_data = {
            "_link_id": link_id,
            "iran_ip": iran_ip,
            "bridge_port": bridge_port,
            "sync_port": sync_port,
            "signature": self.link_signature(link),
            "local_tunnel_role": "client",
            "running": True,
            "_raw_config": link,
            "direct_bridge_sock": None,
            "direct_bridge_listening": False,
            "direct_bridges": 0,
            "ready_workers": 0,
            "max_workers": worker_count,
            "min_ready_workers": min_ready_workers,
            "desired_workers": initial_workers,
            "worker_threads_alive": 0,
            "worker_threads_started": 0,
            "idle_workers_reaped": 0,
            "successful_bridges": 0,
            "worker_errors": 0,
            "last_worker_error": "",
            "bonded_lanes_in_use": 0,
            "bonded_sessions": 0,
            "bonded_sessions_total": 0,
            "bonding_join_failures": 0,
            "mux_carriers": 0,
            "mux_streams": 0,
            "mux_streams_total": 0,
            "mux_carrier_failures": 0,
        }
        init_link_lifecycle(link_data)
        self.active_links[link_id] = link_data

        direct_srv = None
        if DIRECT_BRIDGE_FALLBACK_ENABLED:
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
                direct_srv = None
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
                    track_link_socket(link_data, conn)
                    tune_tcp(conn)
                    def handle_direct(c, peer):
                        try:
                            hdr = recv_exact(c, 2)
                            if not hdr:
                                c.close()
                                return
                            (target_port,) = struct.unpack("!H", hdr)
                            db.log("external-node", "info", f"[DEBUG] Direct fallback from {peer} dialing target_port: {target_port}")
                            local, target_host = dial_target_service(link, target_port)
                            track_link_socket(link_data, local)
                            link_data["direct_bridges"] = link_data.get("direct_bridges", 0) + 1
                            link_data["last_target_host"] = target_host
                            bridge(local, c, link_id, target_port)
                        except Exception as e:
                            link_data["worker_errors"] = link_data.get("worker_errors", 0) + 1
                            link_data["last_worker_error"] = f"Direct fallback failed: {e}"[:180]
                            db.log("external-node", "error", f"[DEBUG] direct fallback error: {e}")
                            try:
                                c.close()
                            except Exception:
                                pass
                        finally:
                            untrack_link_socket(link_data, c)
                            untrack_link_socket(link_data, locals().get("local"))
                    start_link_thread(
                        link_data,
                        handle_direct,
                        name=f"p00rija-direct-{link_id}",
                        args=(conn, addr),
                    )
                except OSError:
                    if not link_data["running"]:
                        break
                    time.sleep(0.1)
                except Exception as e:
                    link_data["last_worker_error"] = f"Direct accept error: {e}"[:180]
                    time.sleep(0.1)

        def port_sync_loop():
            if not auto_sync_enabled:
                return
            allowed_auto_ports = set()
            for value in link.get("auto_sync_ports", []):
                try:
                    port = int(value)
                    if valid_port(port):
                        allowed_auto_ports.add(port)
                except Exception:
                    pass
            while link_data["running"]:
                c = None
                try:
                    c = dial_tcp(iran_ip, sync_port)
                    track_link_socket(link_data, c)
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
                    time.sleep(SYNC_INTERVAL)
                finally:
                    untrack_link_socket(link_data, c)
                    try:
                        c.close()
                    except Exception:
                        pass

        def reverse_link_worker(worker_id=0):
            delay = 0.2
            conn = None
            ts = None
            local = None
            try:
                while link_is_running(link_data):
                    if should_retire_reverse_worker(link_data):
                        break
                    conn = None
                    ts = None
                    local = None
                    try:
                        jitter_ms = clamp_int(link.get("jitter_ms", 0), 0, 0, 5000)
                        if jitter_ms:
                            time.sleep(secrets.randbelow(jitter_ms + 1) / 1000.0)
                        conn = dial_tcp(iran_ip, bridge_port)
                        track_link_socket(link_data, conn)
                        
                        # Wrap TLS client
                        if tls_enabled:
                            try:
                                raw_conn = conn
                                conn = wrap_socket_client_tls(
                                    conn,
                                    sni_hostname=link.get("tls_sni"),
                                    ca_content=link.get("cert_content", ""),
                                )
                                untrack_link_socket(link_data, raw_conn)
                                track_link_socket(link_data, conn)
                            except Exception as e:
                                db.log("external-node", "error", f"[DEBUG] External TLS wrap failed: {e}")
                                conn.close()
                                untrack_link_socket(link_data, conn)
                                if should_retire_reverse_worker(link_data):
                                    break
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
                            untrack_link_socket(link_data, getattr(ts, "raw_sock", conn))
                            if should_retire_reverse_worker(link_data):
                                break
                            time.sleep(delay)
                            delay = min(delay * 2, 5.0)
                            continue
                        
                        link_data["ready_workers"] = link_data.get("ready_workers", 0) + 1
                        try:
                            hdr = recv_exact(ts, 2)
                        finally:
                            link_data["ready_workers"] = max(0, link_data.get("ready_workers", 0) - 1)
                        if not hdr:
                            if should_retire_reverse_worker(link_data):
                                try:
                                    ts.close()
                                except Exception:
                                    pass
                                untrack_link_socket(link_data, getattr(ts, "raw_sock", conn))
                                break
                            db.log("external-node", "error", "[DEBUG] External recv_exact failed to get target_port header")
                            link_data["worker_errors"] = link_data.get("worker_errors", 0) + 1
                            link_data["last_worker_error"] = "External tunnel did not receive target port"
                            ts.close()
                            untrack_link_socket(link_data, getattr(ts, "raw_sock", conn))
                            time.sleep(delay)
                            delay = min(delay * 2, 5.0)
                            continue
                        (target_port,) = struct.unpack("!H", hdr)

                        # Replace a consumed reserve connection immediately.
                        # This lets bursts of short V2Ray latency/speed-test
                        # connections scale within one RTT instead of waiting
                        # for the 5-10 second guardian interval.
                        active_now = count_active_bridge_sessions(link_id)
                        with link_data["lifecycle_lock"]:
                            current_desired = int(link_data.get("desired_workers", 1) or 1)
                            min_ready = int(
                                link_data.get("min_ready_workers", MIN_READY_WORKERS_PER_LINK)
                                or MIN_READY_WORKERS_PER_LINK
                            )
                            link_data["desired_workers"] = min(
                                link_data["max_workers"],
                                max(
                                    current_desired + 1,
                                    active_now + min_ready + 1,
                                ),
                            )
                        spawn_reverse_worker()

                        if target_port == MUX_TARGET_SENTINEL:
                            carrier = None
                            try:
                                carrier_id, carrier_count = receive_mux_join(ts)

                                def mux_open_target(mux_target_port):
                                    target_sock, target_host = dial_target_service(link, mux_target_port)
                                    link_data["last_target_host"] = target_host
                                    return target_sock

                                def mux_carrier_closed(closed_carrier):
                                    # Keep the carrier's raw socket lifecycle-tracked while
                                    # carrier.run() owns it. Pause/delete then closes the
                                    # blocking recv immediately instead of leaving an old
                                    # carrier thread alive until the remote peer notices.
                                    untrack_link_socket(
                                        link_data,
                                        getattr(closed_carrier.endpoint, "raw_sock", conn),
                                    )
                                    with link_data["lifecycle_lock"]:
                                        link_data["mux_carriers"] = max(
                                            0,
                                            int(link_data.get("mux_carriers", 0) or 0) - 1,
                                        )

                                carrier = SharedMuxCarrier(
                                    ts,
                                    link_data,
                                    link_id,
                                    carrier_id,
                                    on_open=mux_open_target,
                                    on_close=mux_carrier_closed,
                                )
                                with link_data["lifecycle_lock"]:
                                    link_data["mux_carriers"] = int(link_data.get("mux_carriers", 0) or 0) + 1
                                db.log(
                                    "external-node",
                                    "info",
                                    f"Shared Mux carrier {carrier_id + 1}/{carrier_count} joined for {link_id}.",
                                )
                                carrier.run()
                                if carrier.last_error:
                                    link_data["mux_carrier_failures"] = int(link_data.get("mux_carrier_failures", 0) or 0) + 1
                                    link_data["last_worker_error"] = f"Shared Mux carrier closed: {carrier.last_error}"[:180]
                                ts = None
                                conn = None
                                delay = 0.2
                                continue
                            except Exception as e:
                                link_data["mux_carrier_failures"] = int(link_data.get("mux_carrier_failures", 0) or 0) + 1
                                link_data["last_worker_error"] = f"Shared Mux carrier failed: {e}"[:180]
                                db.log("external-node", "error", link_data["last_worker_error"])
                                if carrier:
                                    carrier.close()
                                elif ts is not None:
                                    untrack_link_socket(link_data, getattr(ts, "raw_sock", conn))
                                    close_tunnel_quietly(ts)
                                ts = None
                                conn = None
                                time.sleep(delay)
                                delay = min(delay * 2, 5.0)
                                continue

                        if target_port == BOND_TARGET_SENTINEL:
                            key = None
                            group = None
                            try:
                                group_id, lane_index, lane_count, target_port = receive_bond_join(ts)
                                untrack_link_socket(link_data, getattr(ts, "raw_sock", conn))
                                key, group = join_pending_bond_group(
                                    link_id,
                                    ts,
                                    group_id,
                                    lane_index,
                                    lane_count,
                                    target_port,
                                )
                                if not group.ready.wait(BONDING_JOIN_TIMEOUT):
                                    raise RuntimeError("Timed out waiting for all bonding lanes")
                                if group.claim_leader():
                                    local, target_host = dial_target_service(link, target_port)
                                    track_link_socket(link_data, local)
                                    link_data["last_target_host"] = target_host
                                    with link_data["lifecycle_lock"]:
                                        link_data["bonded_lanes_in_use"] = int(link_data.get("bonded_lanes_in_use", 0) or 0) + lane_count
                                        link_data["bonded_sessions"] = int(link_data.get("bonded_sessions", 0) or 0) + 1
                                        link_data["bonded_sessions_total"] = int(link_data.get("bonded_sessions_total", 0) or 0) + 1
                                    db.log(
                                        "external-node",
                                        "info",
                                        f"Adaptive Bonding joined {lane_count} lanes for target port {target_port}.",
                                    )
                                    try:
                                        bonded_bridge(local, group.ordered_lanes(), link_id, target_port)
                                    finally:
                                        untrack_link_socket(link_data, local)
                                        with link_data["lifecycle_lock"]:
                                            link_data["bonded_lanes_in_use"] = max(
                                                0,
                                                int(link_data.get("bonded_lanes_in_use", 0) or 0) - lane_count,
                                            )
                                            link_data["bonded_sessions"] = max(
                                                0,
                                                int(link_data.get("bonded_sessions", 0) or 0) - 1,
                                            )
                                        group.done.set()
                                        remove_pending_bond_group(key, group)
                                else:
                                    group.done.wait()
                                ts = None
                                conn = None
                                local = None
                                delay = 0.2
                                continue
                            except Exception as e:
                                link_data["bonding_join_failures"] = int(link_data.get("bonding_join_failures", 0) or 0) + 1
                                link_data["last_worker_error"] = f"Adaptive Bonding join failed: {e}"[:180]
                                db.log("external-node", "error", link_data["last_worker_error"])
                                if group is not None:
                                    group.error = str(e)
                                    group.close()
                                if key is not None and group is not None:
                                    remove_pending_bond_group(key, group)
                                if local is not None:
                                    untrack_link_socket(link_data, local)
                                    try:
                                        local.close()
                                    except Exception:
                                        pass
                                if ts is not None:
                                    untrack_link_socket(link_data, getattr(ts, "raw_sock", conn))
                                    close_tunnel_quietly(ts)
                                ts = None
                                conn = None
                                local = None
                                time.sleep(delay)
                                delay = min(delay * 2, 5.0)
                                continue
                        
                        db.log("external-node", "info", f"[DEBUG] External dialing target_port: {target_port}")
                        local, target_host = dial_target_service(link, target_port)
                        track_link_socket(link_data, local)
                        link_data["last_target_host"] = target_host
                    except Exception as e:
                        db.log("external-node", "error", f"[DEBUG] reverse_link_worker error connecting to {iran_ip}:{bridge_port} -> {e}")
                        link_data["worker_errors"] = link_data.get("worker_errors", 0) + 1
                        link_data["last_worker_error"] = str(e)[:180]
                        if local is not None:
                            untrack_link_socket(link_data, local)
                            try:
                                local.close()
                            except Exception:
                                pass
                            local = None
                        if ts is not None:
                            untrack_link_socket(link_data, getattr(ts, "raw_sock", conn))
                            close_tunnel_quietly(ts)
                            ts = None
                            conn = None
                        elif conn is not None:
                            untrack_link_socket(link_data, conn)
                            try:
                                conn.close()
                            except Exception:
                                pass
                            conn = None
                        if should_retire_reverse_worker(link_data):
                            break
                        time.sleep(delay)
                        delay = min(delay * 2, 5.0)
                        continue

                    db.log("external-node", "info", f"[DEBUG] External successfully bridged to target_port {target_port}")
                    link_data["successful_bridges"] = link_data.get("successful_bridges", 0) + 1
                    delay = 0.2
                    try:
                        bridge(local, ts, link_id, target_port)
                    finally:
                        untrack_link_socket(link_data, local)
                        untrack_link_socket(link_data, getattr(ts, "raw_sock", conn))
            finally:
                if local is not None:
                    untrack_link_socket(link_data, local)
                    try:
                        local.close()
                    except Exception:
                        pass
                if ts is not None:
                    untrack_link_socket(link_data, getattr(ts, "raw_sock", conn))
                    close_tunnel_quietly(ts)
                elif conn is not None:
                    untrack_link_socket(link_data, conn)
                    try:
                        conn.close()
                    except Exception:
                        pass

        def spawn_reverse_worker():
            with link_data["lifecycle_lock"]:
                if not link_is_running(link_data):
                    return False
                desired = int(link_data.get("desired_workers", 1) or 1)
                if len(link_data["worker_threads"]) >= desired:
                    return False
                link_data["worker_threads_started"] = int(link_data.get("worker_threads_started", 0) or 0) + 1
                worker_id = link_data["worker_threads_started"]
            thread = start_link_thread(
                link_data,
                reverse_link_worker,
                name=f"p00rija-reverse-{link_id}-{worker_id}",
                args=(worker_id,),
                worker=True,
            )
            return thread is not None

        link_data["spawn_reverse_worker"] = spawn_reverse_worker

        if auto_sync_enabled:
            start_link_thread(link_data, port_sync_loop, name=f"p00rija-port-sync-{link_id}")
        if direct_srv is not None:
            start_link_thread(link_data, accept_direct_bridge, name=f"p00rija-direct-listener-{link_id}")
        for _ in range(initial_workers):
            spawn_reverse_worker()

        db.log("foreign-node", "info", f"Started Link {link_id} (Iran IP: {iran_ip}, pool size: {pool_size}, workers: {initial_workers}/{worker_count}, smart_thread_guard={SMART_THREAD_GUARD_ENABLED})")

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
            for up in list(link_data.get("ports", {}).keys()):
                self.close_user_port(link_data, up)
            stop_link_lifecycle(link_id, link_data)
            db.log("foreign-node", "info", f"Stopped link {link_id}")

    def sync_auto_ports(self, link_id, active_ports):
        return IranNodeController.sync_auto_ports(self, link_id, active_ports)

    def update_link_ports(self, link_id, link):
        return IranNodeController.update_link_ports(self, link_id, link)

    def reconcile_combined_ports(self, link_id, link_data):
        return IranNodeController.reconcile_combined_ports(self, link_id, link_data)

    def reconcile_ports(self, link_id, link_data, configured_ports):
        return IranNodeController.reconcile_ports(self, link_id, link_data, configured_ports)

    def open_user_port(self, link_id, link_data, user_port, target_port):
        return IranNodeController.open_user_port(self, link_id, link_data, user_port, target_port)

    def close_user_port(self, link_data, user_port):
        return IranNodeController.close_user_port(self, link_data, user_port)

    def collect_target_port_statuses(self):
        checks = {}
        with self.lock:
            items = list(self.active_links.items())
        for link_id, link_data in items:
            if link_data.get("engine_managed"):
                continue
            if link_data.get("local_tunnel_role") == "server" or "pool" in link_data:
                continue
            link = link_data.get("_raw_config") or {}
            link_checks = {}
            for pm in link.get("ports", []) or []:
                try:
                    user_port = int(pm.get("user_port"))
                    target_port = int(pm.get("target_port"))
                    if not valid_port(user_port) or not valid_port(target_port):
                        continue
                    candidates = target_service_candidates(link, target_port)
                    reachable_host = next((host for host in candidates if is_tcp_port_open(host, target_port)), "")
                    link_checks[str(user_port)] = {
                        "user_port": user_port,
                        "target_port": target_port,
                        "target_open": bool(reachable_host),
                        "target_host": reachable_host,
                        "candidate_hosts": candidates,
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
            if link_data.get("engine_managed"):
                statuses[link_id] = engine_link_status(link_data)
                continue
            if link_data.get("local_tunnel_role") == "server" or "pool" in link_data:
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
                    "role": "server",
                    "bridge_listening": bool(link_data.get("bridge_sock") and link_data["bridge_sock"].fileno() != -1),
                    "sync_enabled": bool(link_data.get("auto_sync_enabled")),
                    "sync_listening": bool(
                        not link_data.get("auto_sync_enabled")
                        or (link_data.get("sync_sock") and link_data["sync_sock"].fileno() != -1)
                    ),
                    "pool_available": pool.qsize() if pool else 0,
                    "desired_workers": int(link_data.get("desired_workers", 0) or 0),
                    "max_workers": int(link_data.get("max_workers", 0) or 0),
                    "idle_workers_reaped": int(link_data.get("idle_workers_reaped", 0) or 0),
                    "thread_guardian": link_data.get("thread_guardian", {}),
                    "direct_fallbacks": int(link_data.get("direct_fallbacks", 0) or 0),
                    "last_direct_error": link_data.get("last_direct_error", ""),
                    "bonded_sessions": int(link_data.get("bonded_sessions", 0) or 0),
                    "bonded_sessions_total": int(link_data.get("bonded_sessions_total", 0) or 0),
                    "bonded_lanes_in_use": int(link_data.get("bonded_lanes_in_use", 0) or 0),
                    "bonding_fallbacks": int(link_data.get("bonding_fallbacks", 0) or 0),
                    "mux_carriers": int(link_data.get("mux_carriers", 0) or 0),
                    "mux_streams": int(link_data.get("mux_streams", 0) or 0),
                    "mux_streams_total": int(link_data.get("mux_streams_total", 0) or 0),
                    "mux_fallbacks": int(getattr(link_data.get("mux_pool"), "fallbacks", 0) or 0),
                    "ports": port_status,
                    "network_mode": read_runtime_network_mode()
                }
                continue
            statuses[link_id] = {
                "running": bool(link_data.get("running")),
                "role": "client",
                "direct_bridge_listening": bool(link_data.get("direct_bridge_listening")),
                "direct_bridges": int(link_data.get("direct_bridges", 0) or 0),
                "ready_workers": int(link_data.get("ready_workers", 0) or 0),
                "desired_workers": int(link_data.get("desired_workers", 0) or 0),
                "max_workers": int(link_data.get("max_workers", 0) or 0),
                "worker_threads_alive": int(link_data.get("worker_threads_alive", 0) or 0),
                "worker_threads_started": int(link_data.get("worker_threads_started", 0) or 0),
                "idle_workers_reaped": int(link_data.get("idle_workers_reaped", 0) or 0),
                "thread_guardian": link_data.get("thread_guardian", {}),
                "successful_bridges": int(link_data.get("successful_bridges", 0) or 0),
                "worker_errors": int(link_data.get("worker_errors", 0) or 0),
                "last_worker_error": link_data.get("last_worker_error", ""),
                "last_target_host": link_data.get("last_target_host", ""),
                "bonded_sessions": int(link_data.get("bonded_sessions", 0) or 0),
                "bonded_sessions_total": int(link_data.get("bonded_sessions_total", 0) or 0),
                "bonded_lanes_in_use": int(link_data.get("bonded_lanes_in_use", 0) or 0),
                "bonding_join_failures": int(link_data.get("bonding_join_failures", 0) or 0),
                "mux_carriers": int(link_data.get("mux_carriers", 0) or 0),
                "mux_desired_carriers": int(link_data.get("mux_desired_carriers", 0) or 0),
                "mux_adaptive": bool(link_data.get("mux_adaptive", False)),
                "mux_streams": int(link_data.get("mux_streams", 0) or 0),
                "mux_streams_total": int(link_data.get("mux_streams_total", 0) or 0),
                "mux_carrier_failures": int(link_data.get("mux_carrier_failures", 0) or 0),
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
                "app_version": APP_VERSION,
                "app_build": APP_BUILD,
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
                ,"update_manifest": build_local_update_manifest()
                ,"listening_tcp_ports": get_local_listening_tcp_ports()
                ,"network_mode": read_runtime_network_mode()
                ,"published_port_ranges": read_published_port_ranges()
                ,"docker_host_gateway": read_docker_host_gateway()
                ,"panel_endpoint": self.panel_endpoint_status()
                ,"transport_capabilities": runtime_transport_capabilities()
            }

            try:
                self.panel_request("/api/report", payload)
            except Exception:
                pass

# Embedded panel UI template is provided by p00rija_core.ui.


# --------- REST HTTP Panel Server (Threading Interface) ----------
class P00RIJAThreadingHTTPServer(ThreadingHTTPServer):
    request_queue_size = 256
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        self.request_slots = threading.BoundedSemaphore(MAX_PANEL_REQUEST_THREADS)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            try:
                request.close()
            except Exception:
                pass
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()

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

from p00rija_core.handler_runtime import bind_runtime as bind_http_handler_runtime
P00RIJAHTTPHandler = bind_http_handler_runtime(globals())

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
    global runtime_controller
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
        start_runtime_maintenance()
        
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
        panel_url = normalize_node_panel_url(config.get("panel_url"))
        fallback_panel_url = normalize_node_panel_url(config.get("panel_fallback_url", ""))
        token = config.get("token")
        private_key = config.get("private_key", "")
        terminate_orphaned_native_engines()
        
        max_idle_seconds = float(os.environ.get("P00RIJA_MAX_IDLE", "300"))
        start_bridge_monitor(max_idle_seconds)
        start_runtime_maintenance()
        
        controller = IranNodeController(panel_url, token, private_key, fallback_panel_url)
        runtime_controller = controller
        controller.start()
        print(f"[IR-NODE] Node daemon started. Polling panel: {panel_url}")
        
        while True:
            try: time.sleep(3600)
            except KeyboardInterrupt: break

    elif role in ("eu", "foreign", "external"):
        panel_url = normalize_node_panel_url(config.get("panel_url"))
        fallback_panel_url = normalize_node_panel_url(config.get("panel_fallback_url", ""))
        token = config.get("token")
        private_key = config.get("private_key", "")
        terminate_orphaned_native_engines()
        
        max_idle_seconds = float(os.environ.get("P00RIJA_MAX_IDLE", "300"))
        start_bridge_monitor(max_idle_seconds)
        start_runtime_maintenance()
        
        controller = ForeignNodeController(panel_url, token, private_key, fallback_panel_url)
        runtime_controller = controller
        controller.start()
        print(f"[EXTERNAL-NODE] Node daemon started. Polling panel: {panel_url}")
        
        while True:
            try: time.sleep(3600)
            except KeyboardInterrupt: break

if __name__ == "__main__":
    main()
