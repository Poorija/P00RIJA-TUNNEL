"""Tunnel method and engine definitions for P00RIJA TUNNEL."""

from __future__ import annotations

import hashlib
import ipaddress
import base64
import secrets
import os
import shlex
import shutil
import socket
import subprocess
import uuid
from typing import Any, Callable

try:
    from .security import normalize_role
except Exception:
    def normalize_role(role):
        if role in ("iran", "internal"):
            return "internal"
        if role in ("eu", "foreign", "external"):
            return "external"
        return role

CONFIG_DIR = os.environ.get("P00RIJA_CONFIG_DIR", "/opt/p00rija")

EXTRA_ENGINE_CATALOG = {
    "amneziawg": {
        "bins": ["amneziawg-go", "awg", "awg-quick"],
        "repo": "amnezia-vpn/amneziawg-go + amnezia-vpn/amneziawg-tools",
    },
    "wireguard": {
        "bins": ["wg", "wg-quick"],
        "repo": "WireGuard tools",
    },
    "ssh": {
        "bins": ["ssh", "sshpass"],
        "repo": "OpenSSH client",
    },
    "stunnel": {
        "bins": ["stunnel", "stunnel4"],
        "repo": "stunnel/stunnel",
    },
    "aead": {
        "bins": ["python3", "openssl"],
        "repo": "builtin AEAD envelope",
    },
    "rawsock": {
        "bins": ["python3"],
        "repo": "builtin raw socket helper",
    },
    "phormal": {
        "bins": ["phormal"],
        "repo": "Schmi7zz/Phormal",
        "license": "GPL-3.0",
        "native_manager": True,
        "requires_systemd": True,
        "requires_host_network": True,
        "notes": "Phormal is exposed as an opt-in native host manager. GRE/Echo/Raw modes require CAP_NET_ADMIN/CAP_NET_RAW and must not be auto-started inside restricted containers.",
    },
    "hedioum": {
        "bins": ["hedioum-tunnel"],
        "repo": "hedioum/Hedioum-Pool-Tunnel",
        "native_manager": True,
        "requires_systemd": True,
        "redistribution": "upstream-license-not-declared; bundled only when operator supplies the binary",
        "notes": "Dynamic SSH-mimic Yamux pool. P00RIJA uses conservative pool defaults and never moves OpenSSH ports automatically.",
    },
    "cloak": {
        "bins": ["ck-client", "ck-server"],
        "repo": "cbeuw/Cloak",
        "license": "GPL-3.0",
        "native_manager": True,
        "requires_systemd": True,
        "notes": "Cloak is an opt-in pluggable transport for HTTPS-looking camouflage. It is not a standalone proxy and should wrap an explicit upstream proxy/service.",
    }
}

EXTRA_TUNNEL_ENGINES = {"amneziawg", "wireguard", "ssh", "stunnel", "aead", "rawsock", "phormal", "hedioum", "cloak"}
EXTRA_TUNNEL_MODES = {
    "reverse_tcp", "amneziawg_v2", "wireguard_kernel",
    "ssh_socks5", "ssh_local_forward", "ssh_remote_forward", "ssh_jump",
    "stunnel_tls_wrap", "raw_socket", "aead_port_forward", "aead_socks5",
    "client_port_forward", "client_socks5",
    "phormal_bridge", "phormal_relay", "phormal_reverse", "phormal_gre",
    "phormal_echo", "phormal_raw", "hedioum_pool", "hedioum_egress",
    "httpupgrade", "cloak_shadowsocks", "cloak_tcp_bridge",
}
EXTRA_TRANSPORTS = {
    "reverse_tcp", "amneziawg_udp", "wireguard_udp",
    "ssh_dynamic", "ssh_local", "ssh_remote", "ssh_jump",
    "stunnel_tls", "raw_ip", "aead_tcp", "port_forward", "socks5",
    "phormal_sit", "phormal_relay_quic", "phormal_reverse_tcp",
    "phormal_gre", "phormal_echo_icmp", "phormal_raw_udp2raw",
    "ssh_mimic_yamux", "ssh_mimic_tcp", "httpupgrade",
    "cloak_https", "cloak_mux",
}

EXTRA_TUNNEL_PROFILES = {
    "reverse_tcp_builtin": {
        "name": "Reverse TCP Tunnel",
        "engine": "builtin",
        "tunnel_mode": "reverse_tcp",
        "transport": "reverse_tcp",
        "network": "tcp",
        "tls_enabled": False,
        "pool_size": 96,
        "obfs_host": "direct",
        "obfs_path": "/",
        "padding_min": 0,
        "padding_max": 0,
        "jitter_ms": 0,
        "keepalive_interval": 20,
        "description": "Plain reverse TCP bridge using the built-in P00RIJA worker pool.",
    },
    "amneziawg_v2_balanced": {
        "name": "AmneziaWG v2 Balanced",
        "engine": "amneziawg",
        "tunnel_mode": "amneziawg_v2",
        "transport": "amneziawg_udp",
        "network": "udp",
        "tls_enabled": False,
        "pool_size": 64,
        "obfs_host": "quic-like",
        "obfs_path": "/",
        "padding_min": 8,
        "padding_max": 96,
        "jitter_ms": 12,
        "keepalive_interval": 25,
        "awg_address": "10.66.0.1/24",
        "awg_client_address": "10.66.0.2/32",
        "awg_mtu": 1280,
        "awg_jc": 6,
        "awg_jmin": 32,
        "awg_jmax": 768,
        "awg_s1": 96,
        "awg_s2": 128,
        "awg_s3": 64,
        "awg_s4": 96,
        "awg_h1": "1234567-2234567",
        "awg_h2": "2234568-3234568",
        "awg_h3": "3234569-4234569",
        "awg_h4": "4234570-5234570",
        "awg_i1": "<r 16>",
        "awg_i2": "",
        "awg_i3": "",
        "awg_i4": "",
        "awg_i5": "",
        "description": "AmneziaWG 2.0 UDP profile with dynamic headers and padding-ready defaults.",
    },
    "wireguard_fastest_kernel": {
        "name": "WireGuard Fastest Raw Throughput",
        "engine": "wireguard",
        "tunnel_mode": "wireguard_kernel",
        "transport": "wireguard_udp",
        "network": "udp",
        "tls_enabled": False,
        "pool_size": 32,
        "bridge_port": 51820,
        "sync_port": 7001,
        "wg_address": "10.77.0.1/24",
        "wg_client_address": "10.77.0.2/32",
        "wg_mtu": 1420,
        "wg_allowed_ips": "0.0.0.0/0, ::/0",
        "keepalive_interval": 25,
        "description": "Fastest general-purpose profile for clean UDP paths. Uses WireGuard kernel/tools with low overhead and high throughput.",
        "ratings": {"speed": "good", "security": "good", "stability": "good"},
    },
    "ssh_socks5_dynamic": {
        "name": "SSH SOCKS5 Dynamic (-D)",
        "engine": "ssh",
        "tunnel_mode": "ssh_socks5",
        "transport": "ssh_dynamic",
        "network": "tcp",
        "tls_enabled": False,
        "pool_size": 32,
        "bridge_port": 1080,
        "sync_port": 7001,
        "ssh_user": "root",
        "ssh_port": 22,
        "ssh_bind_host": "127.0.0.1",
        "ssh_identity_file": "/opt/p00rija/ssh/id_ed25519",
        "keepalive_interval": 20,
        "description": "OpenSSH dynamic SOCKS5 proxy using -D for client egress through the selected peer.",
        "ratings": {"speed": "normal", "security": "good", "stability": "good"},
    },
    "ssh_local_port_forward": {
        "name": "SSH Local Forward (-L)",
        "engine": "ssh",
        "tunnel_mode": "ssh_local_forward",
        "transport": "ssh_local",
        "network": "tcp",
        "tls_enabled": False,
        "pool_size": 24,
        "bridge_port": 8443,
        "sync_port": 7001,
        "ssh_user": "root",
        "ssh_port": 22,
        "ssh_bind_host": "127.0.0.1",
        "ssh_target_host": "127.0.0.1",
        "ssh_target_port": 443,
        "ssh_identity_file": "/opt/p00rija/ssh/id_ed25519",
        "keepalive_interval": 20,
        "description": "OpenSSH local port forward using -L from a local listener to a service reachable by the peer.",
        "ratings": {"speed": "good", "security": "good", "stability": "good"},
    },
    "ssh_remote_reverse_forward": {
        "name": "SSH Remote/Reverse Forward (-R)",
        "engine": "ssh",
        "tunnel_mode": "ssh_remote_forward",
        "transport": "ssh_remote",
        "network": "tcp",
        "tls_enabled": False,
        "pool_size": 24,
        "bridge_port": 8443,
        "sync_port": 7001,
        "ssh_user": "root",
        "ssh_port": 22,
        "ssh_bind_host": "127.0.0.1",
        "ssh_target_host": "127.0.0.1",
        "ssh_target_port": 443,
        "ssh_identity_file": "/opt/p00rija/ssh/id_ed25519",
        "keepalive_interval": 20,
        "description": "OpenSSH reverse forwarding using -R for NAT and firewall friendly inbound service exposure.",
        "ratings": {"speed": "normal", "security": "good", "stability": "good"},
    },
    "ssh_jump_multihop": {
        "name": "SSH Jump Hosts / Multi-Hop (-J)",
        "engine": "ssh",
        "tunnel_mode": "ssh_jump",
        "transport": "ssh_jump",
        "network": "tcp",
        "tls_enabled": False,
        "pool_size": 20,
        "bridge_port": 8443,
        "sync_port": 7001,
        "ssh_user": "root",
        "ssh_port": 22,
        "ssh_bind_host": "127.0.0.1",
        "ssh_target_host": "127.0.0.1",
        "ssh_target_port": 443,
        "ssh_jump_hosts": "bastion1.example.com,bastion2.example.com",
        "ssh_identity_file": "/opt/p00rija/ssh/id_ed25519",
        "keepalive_interval": 20,
        "description": "OpenSSH ProxyJump chain using -J plus a local forward to reach an otherwise indirect target.",
        "ratings": {"speed": "normal", "security": "good", "stability": "normal"},
    },
    "stunnel_tls_wrapped_ssh": {
        "name": "Stunnel TLS Wrapped SSH",
        "engine": "stunnel",
        "tunnel_mode": "stunnel_tls_wrap",
        "transport": "stunnel_tls",
        "network": "tcp",
        "tls_enabled": True,
        "pool_size": 32,
        "bridge_port": 443,
        "sync_port": 2222,
        "stunnel_cert_path": "/opt/p00rija/certs/stunnel.crt",
        "stunnel_key_path": "/opt/p00rija/certs/stunnel.key",
        "stunnel_verify": False,
        "ssh_target_host": "127.0.0.1",
        "ssh_target_port": 22,
        "obfs_host": "www.cloudflare.com",
        "tls_sni": "www.cloudflare.com",
        "description": "Stunnel wraps SSH or another TCP service inside a regular TLS listener, usually on port 443.",
        "ratings": {"speed": "normal", "security": "good", "stability": "good"},
    },
    "kcp_udp_loss_rescue": {
        "name": "KCP UDP Loss Rescue",
        "engine": "frp",
        "tunnel_mode": "kcp",
        "transport": "kcp",
        "network": "udp",
        "tls_enabled": False,
        "pool_size": 64,
        "obfs_host": "udp-kcp",
        "obfs_path": "/",
        "padding_min": 8,
        "padding_max": 128,
        "jitter_ms": 10,
        "keepalive_interval": 12,
        "description": "KCP profile for high-loss UDP paths that need fast retransmission and flow control.",
        "ratings": {"speed": "good", "security": "normal", "stability": "normal"},
    },
    "raw_socket_controlled_lab": {
        "name": "Raw Socket Controlled Lab",
        "engine": "rawsock",
        "tunnel_mode": "raw_socket",
        "transport": "raw_ip",
        "network": "tcp_udp",
        "tls_enabled": False,
        "pool_size": 8,
        "bridge_port": 7000,
        "sync_port": 7001,
        "raw_protocol": 253,
        "raw_mtu": 1200,
        "description": "Low-level raw socket profile for controlled lab networks. Requires root or CAP_NET_RAW and strict firewall scoping.",
        "ratings": {"speed": "normal", "security": "normal", "stability": "poor"},
        "experimental": True,
    },
    "aead_aes128gcm_port_forward": {
        "name": "AEAD AES-128-GCM Port Forward",
        "engine": "aead",
        "tunnel_mode": "aead_port_forward",
        "transport": "aead_tcp",
        "network": "tcp",
        "tls_enabled": False,
        "pool_size": 48,
        "bridge_port": 7443,
        "sync_port": 7001,
        "aead_cipher": "aes-128-gcm",
        "egress_mode": "port_forward",
        "ssh_target_host": "127.0.0.1",
        "ssh_target_port": 443,
        "description": "Authenticated encryption envelope for TCP port forwarding with AES-128-GCM style settings.",
        "ratings": {"speed": "normal", "security": "good", "stability": "normal"},
    },
    "client_port_forward_egress": {
        "name": "Client Egress Port Forward",
        "engine": "builtin",
        "tunnel_mode": "client_port_forward",
        "transport": "port_forward",
        "network": "tcp",
        "tls_enabled": False,
        "pool_size": 48,
        "bridge_port": 7443,
        "sync_port": 7001,
        "egress_mode": "port_forward",
        "ssh_target_host": "127.0.0.1",
        "ssh_target_port": 443,
        "description": "Final client-side egress profile for blind TCP port forwarding to a target service.",
        "ratings": {"speed": "good", "security": "normal", "stability": "good"},
    },
    "client_socks5_egress": {
        "name": "Client Egress SOCKS5 Proxy",
        "engine": "aead",
        "tunnel_mode": "aead_socks5",
        "transport": "socks5",
        "network": "tcp",
        "tls_enabled": False,
        "pool_size": 48,
        "bridge_port": 1080,
        "sync_port": 7001,
        "aead_cipher": "aes-128-gcm",
        "egress_mode": "socks5",
        "socks5_username": "",
        "socks5_password": "",
        "description": "Final client-side egress profile that exposes a SOCKS5 listener on a chosen port.",
        "ratings": {"speed": "normal", "security": "good", "stability": "normal"},
    },
    "phormal_bridge_stable": {
        "name": "Phormal Bridge Stable",
        "engine": "phormal",
        "tunnel_mode": "phormal_bridge",
        "transport": "phormal_sit",
        "network": "tcp_udp",
        "tls_enabled": False,
        "native_engine_enabled": True,
        "host_native_required": True,
        "requires_systemd": True,
        "requires_capabilities": ["CAP_NET_ADMIN"],
        "pool_size": 24,
        "bridge_port": 7000,
        "sync_port": 7001,
        "keepalive_interval": 15,
        "description": "Phormal point-to-point bridge profile for stable paths. Uses host networking and should be launched only on nodes where native tunnel privileges are explicitly allowed.",
        "ratings": {"speed": "good", "security": "normal", "stability": "good"},
    },
    "phormal_relay_throughput": {
        "name": "Phormal Relay Throughput",
        "engine": "phormal",
        "tunnel_mode": "phormal_relay",
        "transport": "phormal_relay_quic",
        "network": "tcp_udp",
        "tls_enabled": True,
        "native_engine_enabled": True,
        "host_native_required": True,
        "requires_systemd": True,
        "pool_size": 32,
        "bridge_port": 443,
        "sync_port": 7001,
        "padding_min": 8,
        "padding_max": 96,
        "jitter_ms": 8,
        "keepalive_interval": 15,
        "description": "Phormal Relay profile for open paths that need high throughput plus obfuscated relaying and port-hopping behavior.",
        "ratings": {"speed": "good", "security": "good", "stability": "normal"},
    },
    "phormal_reverse_nat_safe": {
        "name": "Phormal Reverse NAT Safe",
        "engine": "phormal",
        "tunnel_mode": "phormal_reverse",
        "transport": "phormal_reverse_tcp",
        "network": "tcp",
        "tls_enabled": False,
        "native_engine_enabled": True,
        "host_native_required": True,
        "requires_systemd": True,
        "pool_size": 24,
        "bridge_port": 7443,
        "sync_port": 7001,
        "description": "Phormal Reverse profile for environments where only outbound TCP from the private node survives.",
        "ratings": {"speed": "normal", "security": "normal", "stability": "good"},
    },
    "phormal_gre_low_latency": {
        "name": "Phormal GRE Low Latency",
        "engine": "phormal",
        "tunnel_mode": "phormal_gre",
        "transport": "phormal_gre",
        "network": "tcp_udp",
        "tls_enabled": False,
        "native_engine_enabled": True,
        "host_native_required": True,
        "requires_systemd": True,
        "requires_capabilities": ["CAP_NET_ADMIN"],
        "pool_size": 12,
        "bridge_port": 7000,
        "sync_port": 7001,
        "description": "Phormal GRE/IPIP profile for low-overhead friendly paths. Requires explicit host tunnel privileges.",
        "ratings": {"speed": "good", "security": "poor", "stability": "normal"},
        "experimental": True,
    },
    "phormal_echo_restricted": {
        "name": "Phormal Echo Restricted Path",
        "engine": "phormal",
        "tunnel_mode": "phormal_echo",
        "transport": "phormal_echo_icmp",
        "network": "tcp_udp",
        "tls_enabled": False,
        "native_engine_enabled": True,
        "host_native_required": True,
        "requires_systemd": True,
        "requires_capabilities": ["CAP_NET_ADMIN", "CAP_NET_RAW"],
        "pool_size": 8,
        "bridge_port": 7000,
        "sync_port": 7001,
        "description": "Phormal Echo profile for very restricted paths. It may touch ICMP host behavior, so P00RIJA keeps it experimental and opt-in.",
        "ratings": {"speed": "poor", "security": "normal", "stability": "normal"},
        "experimental": True,
    },
    "phormal_raw_udp_hostile": {
        "name": "Phormal Raw UDP-Hostile",
        "engine": "phormal",
        "tunnel_mode": "phormal_raw",
        "transport": "phormal_raw_udp2raw",
        "network": "tcp_udp",
        "tls_enabled": False,
        "native_engine_enabled": True,
        "host_native_required": True,
        "requires_systemd": True,
        "requires_capabilities": ["CAP_NET_ADMIN", "CAP_NET_RAW"],
        "pool_size": 10,
        "bridge_port": 4096,
        "sync_port": 7001,
        "description": "Phormal Raw/udp2raw-style profile for UDP-hostile filtering. Requires raw socket capability and careful firewall scoping.",
        "ratings": {"speed": "normal", "security": "normal", "stability": "normal"},
        "experimental": True,
    },
    "hedioum_dynamic_pool_socks5": {
        "name": "Hedioum Dynamic Pool SOCKS5 Hub",
        "engine": "hedioum",
        "tunnel_mode": "hedioum_pool",
        "transport": "ssh_mimic_yamux",
        "network": "tcp",
        "tls_enabled": False,
        "native_engine_enabled": True,
        "host_native_required": True,
        "requires_systemd": True,
        "pool_size": 16,
        "bridge_port": 40001,
        "sync_port": 7001,
        "hedioum_role": "iran",
        "hedioum_min_connections": 3,
        "hedioum_max_connections": 12,
        "hedioum_bandwidth_limit_mbps": 8,
        "hedioum_jitter_mbps": 2,
        "hedioum_scale_down_idle_sec": 90,
        "description": "Hedioum hub profile with a local SOCKS5 bridge and adaptive SSH-mimic Yamux pools. Defaults are intentionally conservative to avoid connection storms on busy nodes.",
        "ratings": {"speed": "good", "security": "good", "stability": "good"},
    },
    "hedioum_foreign_egress": {
        "name": "Hedioum Foreign Egress",
        "engine": "hedioum",
        "tunnel_mode": "hedioum_egress",
        "transport": "ssh_mimic_tcp",
        "network": "tcp",
        "tls_enabled": False,
        "native_engine_enabled": True,
        "host_native_required": True,
        "requires_systemd": True,
        "pool_size": 16,
        "bridge_port": 22,
        "sync_port": 7001,
        "hedioum_role": "foreign",
        "hedioum_decoy_target": "127.0.0.1:2022",
        "hedioum_move_ssh_port": False,
        "description": "Hedioum foreign egress listener with SSH-mimic handshake and decoy forwarding. P00RIJA never changes the real SSH daemon port unless the operator does it manually.",
        "ratings": {"speed": "good", "security": "good", "stability": "good"},
    },
    "xray_httpupgrade_reality": {
        "name": "Xray VLESS HTTPUpgrade + REALITY",
        "engine": "xray",
        "tunnel_mode": "httpupgrade",
        "transport": "httpupgrade",
        "network": "tcp",
        "tls_enabled": True,
        "xray_protocol": "vless",
        "xray_security": "reality",
        "pool_size": 16,
        "bridge_port": 443,
        "sync_port": 7001,
        "obfs_host": "www.microsoft.com",
        "tls_sni": "www.microsoft.com",
        "obfs_path": "/cdn-cgi/p00rija-upgrade",
        "padding_min": 8,
        "padding_max": 96,
        "jitter_ms": 8,
        "keepalive_interval": 18,
        "description": "Xray HTTPUpgrade uses an HTTP/1.1 Upgrade style transport without WebSocket framing. It is useful behind TLS/reverse proxies and is lighter than classic WebSocket for compatible Xray clients.",
        "ratings": {"speed": "good", "security": "good", "stability": "good"},
    },
    "cloak_https_camouflage": {
        "name": "Cloak HTTPS Camouflage",
        "engine": "cloak",
        "tunnel_mode": "cloak_tcp_bridge",
        "transport": "cloak_https",
        "network": "tcp",
        "tls_enabled": True,
        "native_engine_enabled": True,
        "host_native_required": True,
        "requires_systemd": True,
        "pool_size": 16,
        "bridge_port": 443,
        "sync_port": 7001,
        "cloak_proxy_method": "shadowsocks",
        "cloak_num_conn": 4,
        "cloak_browser_sig": "chrome",
        "obfs_host": "www.cloudflare.com",
        "tls_sni": "www.cloudflare.com",
        "obfs_path": "/",
        "padding_min": 16,
        "padding_max": 160,
        "jitter_ms": 12,
        "keepalive_interval": 20,
        "description": "Opt-in Cloak pluggable transport profile for HTTPS-looking traffic camouflage. It should wrap an explicit upstream proxy/service and is intentionally bounded to avoid connection storms.",
        "ratings": {"speed": "normal", "security": "good", "stability": "good"},
    },
}

TUNNEL_OPTION_MATRIX_EXTRA = {
    "amneziawg": {
        "transports": [["amneziawg_udp", "AmneziaWG UDP"]],
        "modes": [["amneziawg_v2", "AmneziaWG v2"]],
        "networks": [["udp", "UDP"]],
    },
    "wireguard": {
        "transports": [["wireguard_udp", "WireGuard UDP"]],
        "modes": [["wireguard_kernel", "WireGuard Kernel / wg-quick"]],
        "networks": [["udp", "UDP"]],
    },
    "ssh": {
        "transports": [["ssh_dynamic", "SSH Dynamic SOCKS5"], ["ssh_local", "SSH Local -L"], ["ssh_remote", "SSH Remote -R"], ["ssh_jump", "SSH Jump -J"]],
        "modes": [["ssh_socks5", "SOCKS5 Dynamic (-D)"], ["ssh_local_forward", "Local Port Forward (-L)"], ["ssh_remote_forward", "Remote/Reverse Forward (-R)"], ["ssh_jump", "Jump Hosts / Multi-Hop (-J)"]],
        "networks": [["tcp", "TCP"]],
    },
    "stunnel": {
        "transports": [["stunnel_tls", "Stunnel TLS"]],
        "modes": [["stunnel_tls_wrap", "TLS Wrapping"]],
        "networks": [["tcp", "TCP"]],
    },
    "aead": {
        "transports": [["aead_tcp", "AEAD TCP"], ["socks5", "SOCKS5"], ["port_forward", "Port Forward"]],
        "modes": [["aead_port_forward", "AEAD Port Forward"], ["aead_socks5", "AEAD SOCKS5 Proxy"], ["client_port_forward", "Client Port Forward"], ["client_socks5", "Client SOCKS5 Proxy"]],
        "networks": [["tcp", "TCP"]],
    },
    "rawsock": {
        "transports": [["raw_ip", "Raw IP Socket"]],
        "modes": [["raw_socket", "Raw Socket"]],
        "networks": [["tcp_udp", "TCP + UDP"]],
    },
    "phormal": {
        "transports": [
            ["phormal_sit", "Phormal Bridge / SIT"],
            ["phormal_relay_quic", "Phormal Relay"],
            ["phormal_reverse_tcp", "Phormal Reverse TCP"],
            ["phormal_gre", "Phormal GRE"],
            ["phormal_echo_icmp", "Phormal Echo / ICMP"],
            ["phormal_raw_udp2raw", "Phormal Raw / udp2raw"],
        ],
        "modes": [
            ["phormal_bridge", "Phormal Bridge"],
            ["phormal_relay", "Phormal Relay"],
            ["phormal_reverse", "Phormal Reverse"],
            ["phormal_gre", "Phormal GRE"],
            ["phormal_echo", "Phormal Echo"],
            ["phormal_raw", "Phormal Raw"],
        ],
        "networks": [["tcp", "TCP"], ["udp", "UDP"], ["tcp_udp", "TCP + UDP"]],
    },
    "hedioum": {
        "transports": [["ssh_mimic_yamux", "SSH-mimic Yamux Pool"], ["ssh_mimic_tcp", "SSH-mimic TCP Egress"]],
        "modes": [["hedioum_pool", "Dynamic Pool Hub"], ["hedioum_egress", "Foreign Egress"]],
        "networks": [["tcp", "TCP"]],
    },
    "xray": {
        "transports": [["tcp", "TCP"], ["grpc", "gRPC TLS"], ["h2", "HTTP/2 TLS"], ["ws", "WebSocket"], ["wss", "WebSocket TLS"], ["httpupgrade", "HTTPUpgrade"]],
        "modes": [["vless_reality", "Xray VLESS Reality"], ["reality_grpc", "REALITY gRPC"], ["reality_h2", "REALITY HTTP/2"], ["reality_ws", "REALITY WebSocket"], ["httpupgrade", "HTTPUpgrade + REALITY"]],
        "networks": [["tcp", "TCP"]],
    },
    "cloak": {
        "transports": [["cloak_https", "Cloak HTTPS Camouflage"], ["cloak_mux", "Cloak Multiplexed TCP"]],
        "modes": [["cloak_tcp_bridge", "Cloak TCP Bridge"], ["cloak_shadowsocks", "Cloak Shadowsocks Plugin"]],
        "networks": [["tcp", "TCP"]],
    }
}


def merge_defaults(base: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in EXTRA_TUNNEL_PROFILES.items():
        merged.setdefault(key, value)
    return merged


def amneziawg_obfuscation_from_link(link: dict[str, Any]) -> dict[str, Any]:
    return {
        "Jc": int(link.get("awg_jc", link.get("jitter_ms", 6) or 6)),
        "Jmin": int(link.get("awg_jmin", link.get("padding_min", 32) or 32)),
        "Jmax": int(link.get("awg_jmax", link.get("padding_max", 768) or 768)),
        "S1": int(link.get("awg_s1", 96)),
        "S2": int(link.get("awg_s2", 128)),
        "S3": int(link.get("awg_s3", 64)),
        "S4": int(link.get("awg_s4", 96)),
        "H1": str(link.get("awg_h1", "1234567-2234567")),
        "H2": str(link.get("awg_h2", "2234568-3234568")),
        "H3": str(link.get("awg_h3", "3234569-4234569")),
        "H4": str(link.get("awg_h4", "4234570-5234570")),
        "I1": str(link.get("awg_i1", "<r 16>")),
        "I2": str(link.get("awg_i2", "")),
        "I3": str(link.get("awg_i3", "")),
        "I4": str(link.get("awg_i4", "")),
        "I5": str(link.get("awg_i5", "")),
    }


def _engine_binary_candidates(binary: str) -> list[str]:
    """Locations of a bundled engine binary, mirroring engine_binary_path."""
    bases = [
        os.path.join(os.getcwd(), "engines"),
        "/app/engines",
        "/usr/local/bin",
        os.path.join(CONFIG_DIR, "engines"),
    ]
    candidates = [os.path.join(base, binary) for base in bases]
    which = shutil.which(binary)
    if which:
        candidates.append(which)
    return candidates


def _run_engine_tool(binary: str, args: list[str], stdin_text: str | None = None) -> str:
    for path in _engine_binary_candidates(binary):
        if not (os.path.isfile(path) and os.access(path, os.X_OK)):
            continue
        try:
            proc = subprocess.run(
                [path, *args],
                input=stdin_text,
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = (proc.stdout or "").strip()
            if output:
                return output
        except Exception:
            continue
    return ""


def _x25519_keypair_from_cryptography() -> tuple[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

    private_key = X25519PrivateKey.generate()
    private_raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(private_raw).decode("ascii"), base64.b64encode(public_raw).decode("ascii")


def _x25519_public_from_private_cryptography(private_key: str) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

    private_raw = base64.b64decode(private_key.strip(), validate=True)
    if len(private_raw) != 32:
        raise ValueError("WireGuard private key must decode to 32 bytes")
    public_raw = (
        X25519PrivateKey.from_private_bytes(private_raw)
        .public_key()
        .public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )
    return base64.b64encode(public_raw).decode("ascii")


def _wg_generate_keypair(tools: tuple[str, ...] = ("awg", "wg")) -> tuple[str, str]:
    """Generate a real WireGuard/AmneziaWG key pair.

    Prefers the bundled ``genkey``/``pubkey`` tools (awg first, wg fallback);
    falls back to the Python ``cryptography`` x25519 implementation; raises a
    clear error when neither is available.
    """
    for tool in tools:
        private_key = _run_engine_tool(tool, ["genkey"])
        if not private_key:
            continue
        public_key = _run_engine_tool(tool, ["pubkey"], stdin_text=private_key + "\n")
        if public_key:
            return private_key, public_key
    try:
        return _x25519_keypair_from_cryptography()
    except Exception as exc:
        raise RuntimeError(
            "Unable to generate WireGuard/AmneziaWG keys: no bundled awg/wg binary "
            f"and the 'cryptography' package is unavailable ({exc}). "
            "Install the engines or `pip install cryptography`."
        ) from exc


def _wg_public_from_private(private_key: str, tools: tuple[str, ...] = ("awg", "wg")) -> str:
    for tool in tools:
        public_key = _run_engine_tool(tool, ["pubkey"], stdin_text=private_key.strip() + "\n")
        if public_key:
            return public_key
    try:
        return _x25519_public_from_private_cryptography(private_key)
    except Exception:
        return ""


def _resolve_wg_keypair(
    link: dict[str, Any],
    private_field: str,
    public_field: str,
    tools: tuple[str, ...],
    persist: Callable[[dict[str, Any]], None] | None,
) -> tuple[str, str]:
    """Return (private, public) for a WG/AWG side, generating and persisting once."""
    private_key = str(link.get(private_field) or "").strip()
    public_key = str(link.get(public_field) or "").strip()
    if private_key and public_key:
        return private_key, public_key
    generated: dict[str, Any] = {}
    if private_key and not public_key:
        public_key = _wg_public_from_private(private_key, tools)
        if not public_key:
            raise RuntimeError(
                "Unable to derive the WireGuard public key for this link: no bundled "
                "awg/wg binary and the 'cryptography' package is unavailable. "
                "Install the engines or `pip install cryptography`."
            )
        generated[public_field] = public_key
    if not private_key:
        private_key, public_key = _wg_generate_keypair(tools)
        generated[private_field] = private_key
        generated[public_field] = public_key
    if generated and persist:
        try:
            persist(generated)
        except Exception:
            pass
    return private_key, public_key


def _persist_fields_once(
    persist: Callable[[dict[str, Any]], None] | None,
    fields: dict[str, Any],
) -> None:
    if persist and fields:
        try:
            persist(fields)
        except Exception:
            pass


def _xray_x25519_keypair() -> tuple[str, str] | None:
    """REALITY key pair from the bundled xray binary ('xray x25519'), or None."""
    output = _run_engine_tool("xray", ["x25519"])
    if not output:
        return None
    private_key = ""
    public_key = ""
    for line in output.splitlines():
        if "Private key:" in line:
            private_key = line.split("Private key:", 1)[1].strip()
        elif "Public key:" in line:
            public_key = line.split("Public key:", 1)[1].strip()
    if private_key and public_key:
        return private_key, public_key
    return None


def _normalize_ip_network(value: str, fallback: str) -> str:
    try:
        return str(ipaddress.ip_interface(value))
    except Exception:
        return fallback


def _peer_host_route(address_cidr: str) -> str:
    """Single-host route for a peer address: strip the prefix and use /32 (IPv4) or /128 (IPv6)."""
    try:
        interface = ipaddress.ip_interface(str(address_cidr))
        return f"{interface.ip}/{interface.max_prefixlen}"
    except Exception:
        return str(address_cidr)


def amneziawg_config_for_link(
    link_id: str,
    link: dict[str, Any],
    role: str,
    peer_ip: str,
    persist: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    listen_port = int(link.get("bridge_port", 7000))
    mtu = int(link.get("awg_mtu", 1280))
    obfs = amneziawg_obfuscation_from_link(link)
    server_private, server_public = _resolve_wg_keypair(
        link, "awg_server_private_key", "awg_server_public_key", ("awg", "wg"), persist
    )
    client_private, client_public = _resolve_wg_keypair(
        link, "awg_client_private_key", "awg_client_public_key", ("awg", "wg"), persist
    )
    server_address = _normalize_ip_network(str(link.get("awg_address", "10.66.0.1/24")), "10.66.0.1/24")
    client_address = _normalize_ip_network(str(link.get("awg_client_address", "10.66.0.2/32")), "10.66.0.2/32")
    client_allowed = _peer_host_route(client_address)
    interface_name = str(link.get("awg_interface", f"awg{str(link_id)[-4:]}")).replace("-", "")[:15] or "awg0"

    def render_interface(private_key: str, address: str, listen: bool) -> str:
        lines = [
            "[Interface]",
            f"PrivateKey = {private_key}",
            f"Address = {address}",
            f"MTU = {mtu}",
        ]
        if listen:
            lines.append(f"ListenPort = {listen_port}")
        for key, value in obfs.items():
            if value not in ("", None):
                lines.append(f"{key} = {value}")
        return "\n".join(lines)

    if role in ("external", "foreign", "eu"):
        config = "\n".join([
            render_interface(server_private, server_address, True),
            "",
            "[Peer]",
            f"PublicKey = {client_public}",
            f"AllowedIPs = {client_allowed}",
            "PersistentKeepalive = 25",
            "",
        ])
        return {
            "engine": "amneziawg",
            "version": "2",
            "role": "server",
            "interface": interface_name,
            "binary": "amneziawg-go",
            "tools": ["awg", "awg-quick"],
            "listen_port": listen_port,
            "config": config,
            "commands": [
                f"install -m 600 /path/to/{interface_name}.conf /etc/amnezia/amneziawg/{interface_name}.conf",
                f"amneziawg-go -f {interface_name}",
                f"awg setconf {interface_name} /etc/amnezia/amneziawg/{interface_name}.conf",
            ],
            "obfuscation": obfs,
        }

    endpoint = f"{peer_ip}:{listen_port}"
    config = "\n".join([
        render_interface(client_private, client_address, False),
        "",
        "[Peer]",
        f"PublicKey = {server_public}",
        "AllowedIPs = 0.0.0.0/0, ::/0",
        f"Endpoint = {endpoint}",
        "PersistentKeepalive = 25",
        "",
    ])
    return {
        "engine": "amneziawg",
        "version": "2",
        "role": "client",
        "interface": interface_name,
        "binary": "amneziawg-go",
        "tools": ["awg", "awg-quick"],
        "endpoint": endpoint,
        "config": config,
        "commands": [
            f"install -m 600 /path/to/{interface_name}.conf /etc/amnezia/amneziawg/{interface_name}.conf",
            f"amneziawg-go -f {interface_name}",
            f"awg setconf {interface_name} /etc/amnezia/amneziawg/{interface_name}.conf",
        ],
        "obfuscation": obfs,
    }

def wireguard_config_for_link(
    link_id: str,
    link: dict[str, Any],
    role: str,
    peer_ip: str,
    persist: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    listen_port = int(link.get("bridge_port", 51820))
    mtu = int(link.get("wg_mtu", 1420))
    server_private, server_public = _resolve_wg_keypair(
        link, "wg_server_private_key", "wg_server_public_key", ("wg", "awg"), persist
    )
    client_private, client_public = _resolve_wg_keypair(
        link, "wg_client_private_key", "wg_client_public_key", ("wg", "awg"), persist
    )
    server_address = _normalize_ip_network(str(link.get("wg_address", "10.77.0.1/24")), "10.77.0.1/24")
    client_address = _normalize_ip_network(str(link.get("wg_client_address", "10.77.0.2/32")), "10.77.0.2/32")
    client_allowed = _peer_host_route(client_address)
    allowed_ips = str(link.get("wg_allowed_ips") or "0.0.0.0/0, ::/0")
    keepalive = int(link.get("keepalive_interval", 25) or 25)
    interface_name = str(link.get("wg_interface", f"wg{str(link_id)[-4:]}")).replace("-", "")[:15] or "wg0"

    def render_interface(private_key: str, address: str, listen: bool) -> str:
        lines = [
            "[Interface]",
            f"PrivateKey = {private_key}",
            f"Address = {address}",
            f"MTU = {mtu}",
        ]
        if listen:
            lines.append(f"ListenPort = {listen_port}")
        return "\n".join(lines)

    if normalize_role(role) == "external":
        config = "\n".join([
            render_interface(server_private, server_address, True),
            "",
            "[Peer]",
            f"PublicKey = {client_public}",
            f"AllowedIPs = {client_allowed}",
            f"PersistentKeepalive = {keepalive}",
            "",
        ])
        return {
            "engine": "wireguard",
            "role": "server",
            "interface": interface_name,
            "binary": "wg-quick",
            "listen_port": listen_port,
            "config_path": f"/etc/wireguard/{interface_name}.conf",
            "config": config,
            "commands": [
                f"install -m 600 /path/to/{interface_name}.conf /etc/wireguard/{interface_name}.conf",
                f"wg-quick up {interface_name}",
                f"wg show {interface_name}",
            ],
            "notes": ["Requires NET_ADMIN and /dev/net/tun in containers.", "Best raw speed on clean UDP paths; use Hysteria2/TUIC/AmneziaWG when UDP is lossy or filtered."],
        }

    endpoint = f"{peer_ip}:{listen_port}"
    config = "\n".join([
        render_interface(client_private, client_address, False),
        "",
        "[Peer]",
        f"PublicKey = {server_public}",
        f"AllowedIPs = {allowed_ips}",
        f"Endpoint = {endpoint}",
        f"PersistentKeepalive = {keepalive}",
        "",
    ])
    return {
        "engine": "wireguard",
        "role": "client",
        "interface": interface_name,
        "binary": "wg-quick",
        "endpoint": endpoint,
        "config_path": f"/etc/wireguard/{interface_name}.conf",
        "config": config,
        "commands": [
            f"install -m 600 /path/to/{interface_name}.conf /etc/wireguard/{interface_name}.conf",
            f"wg-quick up {interface_name}",
            f"wg show {interface_name}",
        ],
        "notes": ["Set a real generated key pair before production use.", "Use iperf3/smart test to compare against Hysteria2 on the same route."],
    }


# --------- Built-in tunnel profile catalog and scoring ---------
def default_tunnel_profiles():
    profiles = {
        "easy": {
            "name": "Easy",
            "engine": "builtin",
            "tunnel_mode": "websocket",
            "transport": "websocket",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 16,
            "obfs_host": "speedtest.net",
            "obfs_path": "/assets/ws",
            "padding_min": 0,
            "padding_max": 32,
            "jitter_ms": 0,
            "keepalive_interval": 25
        },
        "adaptive_bonding": {
            "name": "Adaptive Bonding Smart",
            "engine": "builtin",
            "tunnel_mode": "websocket",
            "transport": "websocket",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 16,
            "max_reverse_workers": 16,
            "min_ready_workers": 16,
            "data_plane_architecture": "adaptive_bonding",
            "bonding_enabled": True,
            "bonding_max_lanes": 8,
            "obfs_host": "speedtest.net",
            "obfs_path": "/assets/ws",
            "padding_min": 8,
            "padding_max": 64,
            "jitter_ms": 4,
            "keepalive_interval": 20,
            "description": "Optional 2-16 lane per-flow striping with sequence ordering, CRC32 integrity checks, and adaptive fallback under concurrent-user load.",
        },
        "shared_mux_pool": {
            "name": "Shared Mux Pool",
            "engine": "builtin",
            "tunnel_mode": "websocket",
            "transport": "websocket",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 4,
            "max_reverse_workers": 4,
            "min_ready_workers": 4,
            "data_plane_architecture": "shared_mux",
            "mux_carriers": 4,
            "bonding_enabled": False,
            "bonding_max_lanes": 4,
            "obfs_host": "speedtest.net",
            "obfs_path": "/assets/ws",
            "padding_min": 8,
            "padding_max": 48,
            "jitter_ms": 4,
            "keepalive_interval": 20,
            "description": "Many isolated user streams share 2-8 persistent server-to-server carriers with CRC32 framing, keepalive recovery, and load-aware carrier selection.",
        },
        "smart_hybrid_mux_bonding": {
            "name": "Smart Hybrid Mux + Bonding",
            "engine": "builtin",
            "tunnel_mode": "websocket",
            "transport": "websocket",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 14,
            "max_reverse_workers": 14,
            "min_ready_workers": 14,
            "data_plane_architecture": "smart_hybrid",
            "mux_carriers": 6,
            "bonding_enabled": True,
            "bonding_max_lanes": 8,
            "obfs_host": "speedtest.net",
            "obfs_path": "/assets/ws",
            "padding_min": 8,
            "padding_max": 64,
            "jitter_ms": 4,
            "keepalive_interval": 20,
            "description": "Recommended hybrid: an idle heavy flow may use up to 8 bonded lanes while concurrent users share a resilient 6-carrier Mux pool.",
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
            "stealth_profile": "ech_h2",
            "ech_enabled": True,
            "ech_query_server_name": "www.cloudflare.com"
        },
        "masque_connect_udp_h3": {
            "name": "MASQUE CONNECT-UDP HTTP/3",
            "engine": "masque",
            "tunnel_mode": "masque_connect_udp",
            "transport": "masque_h3",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 72,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/.well-known/masque/udp",
            "padding_min": 8,
            "padding_max": 128,
            "jitter_ms": 10,
            "keepalive_interval": 18,
            "experimental": True,
            "stealth_profile": "http3_connect_udp",
            "masque_mode": "connect-udp"
        },
        "masque_quic_aware_proxy": {
            "name": "MASQUE QUIC-aware Proxy",
            "engine": "masque",
            "tunnel_mode": "masque_quic_proxy",
            "transport": "connect_udp",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 64,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/masque/quic",
            "padding_min": 12,
            "padding_max": 160,
            "jitter_ms": 12,
            "keepalive_interval": 16,
            "experimental": True,
            "stealth_profile": "quic_aware_masque",
            "masque_mode": "connect-ip"
        },
        "singbox_xhttp_reality": {
            "name": "Xray XHTTP + REALITY Adaptive",
            "engine": "xray",
            "tunnel_mode": "xhttp",
            "transport": "xhttp",
            "network": "tcp",
            "tls_enabled": True,
            "pool_size": 72,
            "obfs_host": "www.microsoft.com",
            "obfs_path": "/xhttp",
            "xray_protocol": "vless",
            "xray_security": "reality",
            "xray_flow": "",
            "padding_min": 0,
            "padding_max": 96,
            "jitter_ms": 8,
            "keepalive_interval": 24,
            "experimental": True,
            "stealth_profile": "xhttp_reality",
            "xhttp_auto_select": True,
            "xhttp_mode": "auto"
        },
        "tuic_udp_over_stream": {
            "name": "TUIC UDP over Stream",
            "engine": "tuic",
            "tunnel_mode": "tuic_udp_over_stream",
            "transport": "udp_over_stream",
            "network": "udp",
            "tls_enabled": True,
            "pool_size": 70,
            "obfs_host": "www.apple.com",
            "obfs_path": "/",
            "padding_min": 8,
            "padding_max": 128,
            "jitter_ms": 8,
            "keepalive_interval": 16,
            "stealth_profile": "tuic_stream_udp"
        },
        "turn_tls_relay": {
            "name": "TURN-like TLS Relay",
            "engine": "singbox",
            "tunnel_mode": "turn_tls",
            "transport": "turn_tls",
            "network": "tcp_udp",
            "tls_enabled": True,
            "pool_size": 48,
            "obfs_host": "www.cloudflare.com",
            "obfs_path": "/turn",
            "padding_min": 8,
            "padding_max": 96,
            "jitter_ms": 10,
            "keepalive_interval": 20,
            "experimental": True,
            "stealth_profile": "turn_tls_relay"
        }
    }
    profiles.update(EXTRA_TUNNEL_PROFILES)
    for profile_id, profile in profiles.items():
        if isinstance(profile, dict):
            try:
                configured_pool = int(profile.get("pool_size", 4) or 4)
            except Exception:
                configured_pool = 4
            profile["pool_size"] = 16 if profile_id == "easy" else min(16, max(1, configured_pool))
            profile.setdefault("adaptive_smux_enabled", True)
            profile.setdefault("smux_min_connections", 2)
            profile.setdefault("smux_max_connections", 8)
            profile.setdefault("smux_min_streams", 8)
            profile.setdefault("smux_padding", True)
    return profiles

def ensure_tunnel_profiles(settings: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    profiles = settings.setdefault("tunnel_profiles", {})
    defaults = default_tunnel_profiles()
    changed = False
    for profile_id, profile in defaults.items():
        if profile_id not in profiles:
            profiles[profile_id] = profile
            changed = True
    for profile_id, profile in list(profiles.items()):
        if not isinstance(profile, dict):
            continue
        if profile_id in ("adaptive_bonding", "shared_mux_pool", "smart_hybrid_mux_bonding"):
            adaptive_defaults = defaults[profile_id]
            for key in (
                "name", "description", "data_plane_architecture", "mux_carriers",
                "bonding_enabled", "bonding_max_lanes", "pool_size",
                "max_reverse_workers", "min_ready_workers",
            ):
                if profile.get(key) != adaptive_defaults.get(key):
                    profile[key] = adaptive_defaults.get(key)
                    changed = True
        try:
            configured_pool = int(profile.get("pool_size", 4) or 4)
        except Exception:
            configured_pool = 4
        bounded_pool = 16 if profile_id == "easy" else min(16, max(1, configured_pool))
        if profile.get("pool_size") != bounded_pool:
            profile["pool_size"] = bounded_pool
            changed = True
        metadata = profile_decision_metadata(profile_id, profile)
        for key, value in metadata.items():
            if profile.get(key) != value:
                profile[key] = value
                changed = True
    return profiles, changed

def _link_int(link: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(link.get(key, default))
    except Exception:
        return default

def _first_port_map(link: dict[str, Any]) -> dict[str, Any]:
    ports = link.get("ports") or []
    if ports and isinstance(ports[0], dict):
        return ports[0]
    return {}

def _peer_host(peer_ip: str) -> str:
    peer_ip = str(peer_ip or "127.0.0.1")
    return f"[{peer_ip}]" if ":" in peer_ip and not peer_ip.startswith("[") else peer_ip

def _secret_hex(seed: str, length: int = 16) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[: length * 2]

def _ssh_base_args(link: dict[str, Any], peer_ip: str) -> list[str]:
    user = str(link.get("ssh_user") or "root").strip() or "root"
    host = str(link.get("ssh_host") or peer_ip or "127.0.0.1").strip()
    port = str(_link_int(link, "ssh_port", 22))
    identity = str(link.get("ssh_identity_file") or "/opt/p00rija/ssh/id_ed25519").strip()
    args = [
        "ssh", "-N",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=20",
        "-o", "ServerAliveCountMax=3",
        "-p", port,
    ]
    if identity:
        args.extend(["-i", identity])
    jump_hosts = str(link.get("ssh_jump_hosts") or "").replace("\n", ",")
    jump_hosts = ",".join([part.strip() for part in jump_hosts.split(",") if part.strip()])
    if jump_hosts:
        args.extend(["-J", jump_hosts])
    args.append(f"{user}@{host}")
    return args

def _command_text(args: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in args)

def ssh_config_for_link(link_id: str, link: dict[str, Any], role: str, peer_ip: str) -> dict[str, Any]:
    mode = str(link.get("tunnel_mode") or "ssh_socks5")
    # Default to loopback so forwarded listeners are never exposed publicly by
    # accident. A non-loopback bind requires the explicit ssh_expose_public opt-in.
    bind_host = "127.0.0.1"
    configured_bind = str(link.get("ssh_bind_host") or "").strip()
    if configured_bind:
        try:
            bind_is_loopback = ipaddress.ip_address(configured_bind).is_loopback
        except ValueError:
            bind_is_loopback = False
        if bind_is_loopback:
            bind_host = configured_bind
        elif bool(link.get("ssh_expose_public", False)):
            bind_host = configured_bind
    bridge_port = _link_int(link, "bridge_port", 1080 if mode == "ssh_socks5" else 8443)
    port_map = _first_port_map(link)
    target_host = str(link.get("ssh_target_host") or "127.0.0.1")
    target_port = int(link.get("ssh_target_port") or port_map.get("target_port") or 443)
    args = _ssh_base_args(link, peer_ip)
    if mode == "ssh_socks5":
        args[2:2] = ["-D", f"{bind_host}:{bridge_port}"]
        purpose = "dynamic_socks5"
    elif mode == "ssh_remote_forward":
        args[2:2] = ["-R", f"{bind_host}:{bridge_port}:{target_host}:{target_port}"]
        purpose = "remote_reverse_forward"
    else:
        args[2:2] = ["-L", f"{bind_host}:{bridge_port}:{target_host}:{target_port}"]
        purpose = "local_forward_with_jump_hosts" if mode == "ssh_jump" else "local_forward"
    return {
        "engine": "ssh",
        "role": normalize_role(role),
        "purpose": purpose,
        "mode": mode,
        "peer": {"host": peer_ip, "port": _link_int(link, "ssh_port", 22)},
        "listen": {"host": bind_host, "port": bridge_port},
        "target": {"host": target_host, "port": target_port},
        "jump_hosts": [part.strip() for part in str(link.get("ssh_jump_hosts") or "").replace("\n", ",").split(",") if part.strip()],
        "command": _command_text(args),
        "systemd": {
            "unit": f"p00rija-ssh-{link_id}.service",
            "restart": "always",
            "exec_start": _command_text(args),
        },
        "notes": [
            "Use key-based auth for unattended node operation.",
            "Remote forwarding requires GatewayPorts on the SSH server when binding outside localhost.",
        ],
    }

def stunnel_config_for_link(link_id: str, link: dict[str, Any], role: str, peer_ip: str) -> dict[str, Any]:
    normalized_role = normalize_role(role)
    bridge_port = _link_int(link, "bridge_port", 443)
    sync_port = _link_int(link, "sync_port", 2222)
    target_host = str(link.get("ssh_target_host") or "127.0.0.1")
    target_port = _link_int(link, "ssh_target_port", 22)
    cert_path = str(link.get("stunnel_cert_path") or f"{CONFIG_DIR}/certs/stunnel.crt")
    key_path = str(link.get("stunnel_key_path") or f"{CONFIG_DIR}/certs/stunnel.key")
    sni = str(link.get("tls_sni") or link.get("obfs_host") or "localhost")
    verify = "2" if bool(link.get("stunnel_verify", False)) else "0"
    if normalized_role == "external":
        conf = f"""foreground = no
pid = /var/run/p00rija-stunnel-{link_id}.pid
[p00rija-{link_id}]
client = no
accept = 0.0.0.0:{bridge_port}
connect = {target_host}:{target_port}
cert = {cert_path}
key = {key_path}
"""
    else:
        conf = f"""foreground = no
pid = /var/run/p00rija-stunnel-{link_id}.pid
[p00rija-{link_id}]
client = yes
accept = 127.0.0.1:{sync_port}
connect = {_peer_host(peer_ip)}:{bridge_port}
sni = {sni}
verify = {verify}
CAfile = {cert_path}
"""
    return {
        "engine": "stunnel",
        "role": normalized_role,
        "mode": "stunnel_tls_wrap",
        "listen_port": bridge_port if normalized_role == "external" else sync_port,
        "peer": {"host": peer_ip, "port": bridge_port, "sni": sni},
        "target": {"host": target_host, "port": target_port},
        "config_path": f"{CONFIG_DIR}/stunnel/{link_id}-{normalized_role}.conf",
        "config": conf,
        "command": f"stunnel {CONFIG_DIR}/stunnel/{link_id}-{normalized_role}.conf",
        "notes": ["Generate cert/key before enabling the listener.", "Use port 443 only when no web server already binds it."],
    }

def raw_socket_config_for_link(link_id: str, link: dict[str, Any], role: str, peer_ip: str) -> dict[str, Any]:
    protocol = _link_int(link, "raw_protocol", 253)
    mtu = _link_int(link, "raw_mtu", 1200)
    return {
        "engine": "rawsock",
        "role": normalize_role(role),
        "mode": "raw_socket",
        "protocol_number": protocol,
        "mtu": mtu,
        "peer": {"host": peer_ip},
        "requires": ["root or CAP_NET_RAW", "explicit firewall allow-list", "controlled lab validation before production"],
        "capability_command": "setcap cap_net_raw+ep /usr/bin/python3",
        "worker_spec": {
            "listen": f"0.0.0.0:{_link_int(link, 'bridge_port', 7000)}",
            "peer": peer_ip,
            "packet_mark": str(link.get("raw_packet_mark") or f"p00rija-{link_id}"),
            "anti_loop_guard": True,
        },
        "notes": [
            "Raw sockets bypass normal TCP/UDP socket semantics and can be blocked by container or host policy.",
            "Prefer KCP, QUIC, WireGuard-family, or Stunnel for production unless raw IP is explicitly permitted.",
        ],
    }

def aead_config_for_link(
    link_id: str,
    link: dict[str, Any],
    role: str,
    peer_ip: str,
    persist: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    cipher = str(link.get("aead_cipher") or "aes-128-gcm").lower()
    key_hex = str(link.get("aead_key") or "").strip()
    if not key_hex:
        # Prefer the per-link secret; generate once per call and persist so both
        # sides of the tunnel observe the same key.
        key_hex = str(link.get("tunnel_secret") or "").strip()
        if not key_hex:
            key_hex = secrets.token_urlsafe(32)
            _persist_fields_once(persist, {"tunnel_secret": key_hex})
    mode = str(link.get("tunnel_mode") or "aead_port_forward")
    egress_mode = str(link.get("egress_mode") or ("socks5" if "socks5" in mode else "port_forward"))
    bridge_port = _link_int(link, "bridge_port", 7443 if egress_mode == "port_forward" else 1080)
    target_host = str(link.get("ssh_target_host") or "127.0.0.1")
    target_port = _link_int(link, "ssh_target_port", 443)
    return {
        "engine": "aead",
        "role": normalize_role(role),
        "mode": mode,
        "egress_mode": egress_mode,
        "cipher": cipher,
        "key_hex": key_hex,
        "nonce": {"size": 12, "mode": str(link.get("aead_nonce_mode") or "counter-random-prefix")},
        "listen": {"host": "0.0.0.0", "port": bridge_port},
        "peer": {"host": peer_ip, "port": bridge_port},
        "target": {"host": target_host, "port": target_port},
        "socks5": {
            "enabled": egress_mode == "socks5",
            "username": str(link.get("socks5_username") or ""),
            "password_set": bool(link.get("socks5_password")),
        },
        "worker_spec": {
            "frame": "length-prefix + nonce + ciphertext + tag",
            "tag_size": 16,
            "replay_window": 4096,
            "keepalive_interval": _link_int(link, "keepalive_interval", 25),
        },
        "notes": ["Rotate aead_key per tunnel for production.", "Use TLS or SSH family methods when a standards-based transport is required."],
    }

def rating_level(score):
    if score >= 75:
        return "good"
    if score >= 50:
        return "normal"
    return "poor"

def profile_decision_metadata(profile_id, profile):
    engine = str(profile.get("engine", "builtin"))
    mode = str(profile.get("tunnel_mode", profile.get("transport", "tcp")))
    transport = str(profile.get("transport", mode))
    network = str(profile.get("network", "tcp"))
    tls = bool(profile.get("tls_enabled", False))
    padding = int(profile.get("padding_max", 0) or 0)
    jitter = int(profile.get("jitter_ms", 0) or 0)
    experimental = bool(profile.get("experimental", False))

    speed = 58
    security = 45
    stability = 58

    if engine in ("rathole", "backhaul", "frp", "builtin", "amneziawg", "wireguard"):
        speed += 14
        stability += 10
    if engine == "hedioum":
        speed += 12
        security += 12
        stability += 14
        if mode == "hedioum_pool":
            stability += 8
            speed += 4
    if engine == "cloak":
        security += 24
        stability += 10
        speed -= 4
        if transport == "cloak_mux":
            speed += 8
            stability += 4
    if engine == "phormal":
        speed += 8
        stability += 6
        if mode == "phormal_relay":
            speed += 14
            security += 8
        elif mode == "phormal_bridge":
            stability += 10
        elif mode == "phormal_reverse":
            stability += 12
            speed -= 2
        elif mode in ("phormal_gre", "phormal_raw"):
            speed += 10
            security -= 8
        elif mode == "phormal_echo":
            speed -= 10
            stability += 4
    if engine == "wireguard" or transport == "wireguard_udp":
        speed += 12
        security += 8
    if engine in ("hysteria2", "tuic") or network == "udp" or transport in ("quic", "h3", "tuic", "amneziawg_udp", "wireguard_udp", "masque_h3", "connect_udp", "udp_over_stream"):
        speed += 18
        stability -= 4
    if engine in ("singbox", "xray", "naiveproxy", "shadowtls", "mieru", "brook", "masque"):
        security += 18
    if tls or "reality" in mode or "shadowtls" in mode or "anytls" in mode or "naive" in mode:
        security += 22
        stability += 4
    if mode in ("tcp", "reverse_tcp") and not tls:
        security -= 18
        speed += 8
    if mode in ("grpc", "reality_grpc", "mux_grpc", "http2_tls", "h2", "ech_h2", "xhttp", "httpupgrade") or transport == "httpupgrade":
        stability += 10
        security += 6
        speed += 4
    if mode in ("masque_connect_udp", "masque_quic_proxy"):
        security += 14
        speed += 8
    if mode == "tuic_udp_over_stream" or transport == "udp_over_stream":
        stability += 10
        speed -= 4
    if mode == "turn_tls" or transport == "turn_tls":
        security += 8
        stability += 6
        speed -= 6
    if padding > 128 or jitter > 25:
        security += 8
        speed -= 8
    if experimental:
        stability -= 14

    speed = max(20, min(95, speed))
    security = max(20, min(95, security))
    stability = max(20, min(95, stability))

    if profile_id in ("easy", "hard", "resilient"):
        category = "recommended"
    elif engine in ("hysteria2", "tuic", "singbox", "xray", "naiveproxy", "shadowtls", "mieru", "brook", "masque", "hedioum", "cloak"):
        category = "stealth"
    elif engine in ("rathole", "backhaul", "frp", "chisel", "gost", "phormal"):
        category = "classic"
    elif engine in ("amneziawg", "wireguard", "muxquantum"):
        category = "advanced"
    else:
        category = "other"

    notes = {
        "recommended": "Fast preset for common deployments.",
        "stealth": "Designed for stricter filtering and camouflage.",
        "classic": "Stable reverse-tunnel family with mature behavior.",
        "advanced": "Advanced profile for custom transport/core tuning.",
        "other": "General custom tunnel profile."
    }
    return {
        "ratings": {
            "speed": rating_level(speed),
            "security": rating_level(security),
            "stability": rating_level(stability)
        },
        "rating_scores": {
            "speed": speed,
            "security": security,
            "stability": stability
        },
        "category": category,
        "recommendation_note": notes.get(category, notes["other"])
    }


# --------- External engine config builders ---------
def phormal_config_for_link(link_id: str, link: dict[str, Any], role: str, peer_ip: str) -> dict[str, Any]:
    mode = str(link.get("tunnel_mode") or "phormal_bridge").replace("phormal_", "")
    product = {
        "bridge": "Bridge",
        "relay": "Relay",
        "reverse": "Reverse",
        "gre": "GRE",
        "echo": "Echo",
        "raw": "Raw",
    }.get(mode, "Bridge")
    listen_port = int(link.get("bridge_port", 7000) or 7000)
    sync_port = int(link.get("sync_port", 7001) or 7001)
    local_role = normalize_role(role)
    host_requirements = ["systemd", "iproute2", "CAP_NET_ADMIN"]
    if mode in {"echo", "raw"}:
        host_requirements.append("CAP_NET_RAW")
    if mode == "echo":
        host_requirements.append("ICMP echo policy review")
    return {
        "engine": "phormal",
        "product": product,
        "mode": mode,
        "role": local_role,
        "peer": peer_ip,
        "ports": {
            "bridge": listen_port,
            "sync": sync_port,
        },
        "native_manager": True,
        "safe_launch_policy": "manual-opt-in",
        "host_requirements": host_requirements,
        "risk_controls": [
            "P00RIJA does not run the Phormal installer automatically.",
            "Review generated Phormal settings on both nodes before starting host-level services.",
            "Avoid GRE/Echo/Raw inside restricted Docker containers unless the required capabilities are explicitly granted.",
        ],
        "recommended_runtime": {
            "unit_prefix": f"phormal-{mode}",
            "max_nofile": min(65535, int(link.get("phormal_nofile_limit", 65535) or 65535)),
            "restart_sec": max(5, int(link.get("phormal_restart_sec", 5) or 5)),
            "keepalive_sec": max(10, int(link.get("keepalive_interval", 15) or 15)),
        },
    }


def hedioum_config_for_link(
    link_id: str,
    link: dict[str, Any],
    role: str,
    peer_ip: str,
    persist: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    local_role = normalize_role(role)
    tunnel_mode = str(link.get("tunnel_mode") or "hedioum_pool")
    token = str(link.get("hedioum_auth_token") or "").strip()
    if not token:
        # Never derive the pool token from the link id; use the per-link secret
        # or generate once and persist so both sides share it.
        token = str(link.get("tunnel_secret") or "").strip()
        if not token:
            token = secrets.token_urlsafe(32)
            _persist_fields_once(persist, {"tunnel_secret": token})
    min_conn = max(1, min(8, int(link.get("hedioum_min_connections", 3) or 3)))
    max_conn = max(min_conn, min(32, int(link.get("hedioum_max_connections", 12) or 12)))
    cap_mbps = max(1, min(1000, int(link.get("hedioum_bandwidth_limit_mbps", 8) or 8)))
    jitter_mbps = max(0, min(cap_mbps, int(link.get("hedioum_jitter_mbps", 2) or 2)))
    listen_port = int(link.get("bridge_port", 22) or 22)
    socks_port = int(link.get("hedioum_local_socks_port", link.get("bridge_port", 40001)) or 40001)
    target_port = int(link.get("hedioum_target_port", listen_port) or listen_port)
    if tunnel_mode == "hedioum_egress" or local_role == "external":
        return {
            "engine": "hedioum",
            "role": "foreign",
            "foreign_listen_port": listen_port,
            "auth_token": token,
            "decoy_target": str(link.get("hedioum_decoy_target") or "127.0.0.1:2022"),
            "move_ssh_port": False,
            "safe_launch_policy": "manual-opt-in",
            "risk_controls": [
                "P00RIJA does not move OpenSSH to another port automatically.",
                "Use a firewall window and out-of-band console before binding Hedioum to port 22.",
                "Keep systemd restart limits conservative to avoid tight crash loops.",
            ],
        }
    return {
        "engine": "hedioum",
        "role": "iran",
        "local_socks_port": socks_port,
        "foreign_nodes": [
            {
                "alias": str(link.get("hedioum_foreign_alias") or "foreign-1"),
                "target_ip": peer_ip,
                "target_port": target_port,
                "local_socks_port": socks_port,
                "min_connections": min_conn,
                "max_connections": max_conn,
                "bandwidth_limit_mbps": cap_mbps,
                "bandwidth_jitter_mbps": jitter_mbps,
                "auth_token": token,
            }
        ],
        "safe_launch_policy": "manual-opt-in",
        "risk_controls": [
            "Pool defaults are capped to avoid connection storms.",
            "Scale-up should be tied to real throughput and server pressure.",
            "Use one hub pool per remote egress and route client streams through the pool instead of creating unbounded per-user TCP sessions.",
        ],
    }


def _link_credential_uuid(
    link: dict[str, Any],
    persist: Callable[[dict[str, Any]], None] | None,
    field: str = "xray_uuid",
) -> str:
    """Return the link's credential value, generating and persisting it once.

    Without a persist callback a missing credential is a hard error instead of a
    silent per-call uuid4 rotation that desynchronizes the two tunnel sides.
    """
    value = str(link.get(field) or "").strip()
    if value:
        return value
    if persist is None:
        raise ValueError(f"{field} missing on link and no persist callback provided — regenerate link")
    value = str(uuid.uuid4())
    _persist_fields_once(persist, {field: value})
    return value


def hysteria2_config_for_link(
    link,
    role,
    peer_ip: str = "127.0.0.1",
    persist: Callable[[dict[str, Any]], None] | None = None,
):
    psk = _link_credential_uuid(link, persist)
    listen_port = int(link.get("bridge_port", 7000))
    sni = link.get("tls_sni", "speedtest.net")
    tunnel_mode = str(link.get("tunnel_mode") or "")

    def bandwidth_text(value: Any) -> str:
        try:
            return f"{int(value)} mbps"
        except (TypeError, ValueError):
            return "1000 mbps"

    bandwidth = {
        "up": bandwidth_text(link.get("hysteria_up_mbps")),
        "down": bandwidth_text(link.get("hysteria_down_mbps")),
    }
    # Hysteria2 salamander obfuscation must be identical on both sides; the
    # correct type key is "salamander" (upstream also accepts "salamoder").
    salamander = tunnel_mode == "hysteria2_salamander" or str(link.get("obfs_layer")) == "salamander"
    obfs_password = ""
    if salamander:
        obfs_password = str(link.get("tunnel_secret") or "").strip()
        if not obfs_password:
            obfs_password = secrets.token_urlsafe(32)
            _persist_fields_once(persist, {"tunnel_secret": obfs_password})

    if normalize_role(role) == "external":
        server_config = {
            "listen": f":{listen_port}",
            "tls": {
                "cert": f"{CONFIG_DIR}/certs/cert.pem",
                "key": f"{CONFIG_DIR}/certs/key.pem"
            },
            "auth": {
                "type": "password",
                "password": psk
            },
            "bandwidth": bandwidth
        }
        if salamander:
            server_config["obfs"] = {"type": "salamander", "password": obfs_password}
        if tunnel_mode == "http3_masquerade":
            server_config["masquerade"] = {
                "type": "proxy",
                "url": "https://news.ycombinator.com/",
                "rewriteHost": True,
            }
        return server_config

    tcp_fw = []
    for p in link.get("ports", []):
        tcp_fw.append({
            "listen": f"0.0.0.0:{p.get('user_port', p.get('target_port'))}",
            "remote": f"{p.get('target_host') or '127.0.0.1'}:{p.get('target_port', 443)}"
        })

    other_ip = str(peer_ip or "127.0.0.1")
    if ":" in other_ip:
        other_ip = f"[{other_ip}]"

    client_config = {
        "server": f"{other_ip}:{listen_port}",
        "auth": psk,
        "tls": {
            "sni": sni,
            "insecure": bool(link.get("tls_insecure", False))
        },
        "bandwidth": bandwidth,
        "tcpForwarding": tcp_fw
    }
    if salamander:
        client_config["obfs"] = {"type": "salamander", "password": obfs_password}
    return client_config

def _local_port_free(port: int) -> bool:
    """True when both a TCP and a UDP socket can bind 0.0.0.0:<port> locally."""
    for sock_type in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        probe = socket.socket(socket.AF_INET, sock_type)
        try:
            probe.bind(("0.0.0.0", port))
        except OSError:
            return False
        finally:
            probe.close()
    return True


def muxquantum_config_for_link(
    lid,
    link,
    role,
    other_ip,
    persist: Callable[[dict[str, Any]], None] | None = None,
):
    psk = str(link.get("tunnel_secret") or "").strip()
    if not psk:
        # Never use the link id as the pre-shared key; generate once per call
        # and persist so both sides reuse the same secret.
        psk = secrets.token_urlsafe(32)
        _persist_fields_once(persist, {"tunnel_secret": psk})
    transport = link.get("transport", link.get("tunnel_mode", "httpsmux"))
    bridge_port = int(link.get("bridge_port", 7000))
    sync_port = int(link.get("sync_port", 7001))
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
        # Never fall back to bridge_port+1: the sync listener sits right next to
        # the bridge port, so bridge_port+1 collides with it. Prefer sync_port+1,
        # then bridge_port+2, and skip the fallback mapping if neither is free.
        for candidate in (sync_port + 1, bridge_port + 2):
            if (
                1 <= candidate <= 65535
                and candidate not in (bridge_port, sync_port)
                and _local_port_free(candidate)
            ):
                maps.append({"type": "tcp", "bind": f"0.0.0.0:{candidate}", "target": "127.0.0.1:443"})
                break

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

def xray_config_for_link(
    link,
    role,
    peer_ip: str = "127.0.0.1",
    persist: Callable[[dict[str, Any]], None] | None = None,
):
    protocol = link.get("xray_protocol", "vless")
    security = link.get("xray_security", "reality")
    listen_port = int(link.get("bridge_port", 7000))

    server_names = [s.strip() for s in link.get("xray_sni", "www.microsoft.com").split(",") if s.strip()]
    if not server_names:
        server_names = ["www.microsoft.com"]

    private_key = str(link.get("xray_private_key") or "").strip()
    public_key = str(link.get("xray_public_key") or "").strip()
    if security == "reality" and (not private_key or not public_key):
        # Silent "M"*43 placeholder keys produced a handshake that could never
        # succeed; fail loudly instead so the operator regenerates the link.
        raise ValueError("REALITY keys missing — regenerate link")
    short_id = link.get("xray_shortid", "0123456789abcdef")
    flow = link.get("xray_flow", "xtls-rprx-vision")
    uuid_val = _link_credential_uuid(link, persist)
    # REALITY borrows a real TLS handshake: default the target to the first
    # serverName on 443 unless the link explicitly overrides it.
    reality_target = str(link.get("xray_reality_target") or f"{server_names[0]}:443")

    transport = str(link.get("transport") or link.get("tunnel_mode") or "tcp")
    xhttp_enabled = transport == "xhttp" or link.get("tunnel_mode") == "xhttp"
    httpupgrade_enabled = transport == "httpupgrade" or link.get("tunnel_mode") == "httpupgrade"
    network_name = "xhttp" if xhttp_enabled else ("httpupgrade" if httpupgrade_enabled else "raw")
    xhttp_settings = {
        "path": str(link.get("obfs_path") or "/xhttp"),
        "mode": str(link.get("xhttp_mode") or "auto"),
    }
    if link.get("xhttp_auto_select", True):
        xhttp_settings["mode"] = "auto"
    httpupgrade_settings = {
        "path": str(link.get("obfs_path") or "/cdn-cgi/p00rija-upgrade"),
        "host": str(link.get("obfs_host") or link.get("tls_sni") or server_names[0]),
    }

    if normalize_role(role) == "external":
        client = {"id": uuid_val}
        if flow and not xhttp_enabled and not httpupgrade_enabled:
            client["flow"] = flow
        stream_settings = {
            "network": network_name,
            "security": security,
            "realitySettings": {
                "show": False,
                "target": reality_target,
                "xver": 0,
                "serverNames": server_names,
                "privateKey": private_key,
                "shortIds": [short_id]
            }
        }
        if xhttp_enabled:
            stream_settings["xhttpSettings"] = xhttp_settings
        if httpupgrade_enabled:
            stream_settings["httpupgradeSettings"] = httpupgrade_settings
        return {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "tag": "p00rija-xray-in",
                "port": listen_port,
                "protocol": protocol,
                "settings": {
                    "clients": [client],
                    "decryption": "none"
                },
                "streamSettings": stream_settings
            }],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}]
        }
    user = {"id": uuid_val, "encryption": "none"}
    if flow and not xhttp_enabled and not httpupgrade_enabled:
        user["flow"] = flow
    stream_settings = {
        "network": network_name,
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
    if xhttp_enabled:
        stream_settings["xhttpSettings"] = xhttp_settings
    if httpupgrade_enabled:
        stream_settings["httpupgradeSettings"] = httpupgrade_settings
    # The client-side SOCKS inbound is a local listener: use the link's local
    # port, never the remote target port.
    local_inbound_port = int(link.get("local_port") or link.get("user_port") or 1080)
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{"tag": "p00rija-socks-in", "port": local_inbound_port, "listen": "127.0.0.1", "protocol": "socks"}],
        "outbounds": [{
            "tag": "p00rija-xray-out",
            "protocol": protocol,
            "settings": {
                "vnext": [{
                    "address": str(peer_ip or "127.0.0.1"),
                    "port": listen_port,
                    "users": [user]
                }]
            },
            "streamSettings": stream_settings
        }]
    }


def singbox_config_for_link(
    link,
    role,
    peer_ip: str = "127.0.0.1",
    persist: Callable[[dict[str, Any]], None] | None = None,
):
    listen_port = int(link.get("bridge_port", 7000))
    uuid_val = _link_credential_uuid(link, persist)
    server_name = str(link.get("tls_sni") or link.get("obfs_host") or "www.cloudflare.com")
    profile_name = " ".join(
        str(link.get(key) or "")
        for key in ("profile_id", "tunnel_mode", "name")
    ).lower()
    is_reality = "reality" in profile_name

    if is_reality:
        short_id = str(link.get("xray_shortid") or "").strip()
        private_key = str(link.get("xray_private_key") or "").strip()
        public_key = str(link.get("xray_public_key") or "").strip()
        generated: dict[str, Any] = {}
        if not short_id:
            short_id = secrets.token_hex(8)
            generated["xray_shortid"] = short_id
        if not (private_key and public_key):
            pair = _xray_x25519_keypair()
            if pair is None:
                raise ValueError(
                    "REALITY keys missing and the bundled xray binary is unavailable — regenerate link"
                )
            if not private_key:
                private_key = pair[0]
                generated["xray_private_key"] = private_key
            if not public_key:
                public_key = pair[1]
                generated["xray_public_key"] = public_key
        _persist_fields_once(persist, generated)
        flow = str(link.get("xray_flow") or "xtls-rprx-vision")
        # xtls-rprx-vision is incompatible with multiplexing.
        multiplex = {"enabled": False}
        if normalize_role(role) == "external":
            return {
                "log": {"level": "warn"},
                "inbounds": [{
                    "type": "vless",
                    "tag": "p00rija-in",
                    "listen": "::",
                    "listen_port": listen_port,
                    "users": [{"uuid": uuid_val, "flow": flow}],
                    "tls": {
                        "enabled": True,
                        "server_name": server_name,
                        "reality": {
                            "enabled": True,
                            "handshake": {"server": server_name, "server_port": 443},
                            "private_key": private_key,
                            "short_id": short_id,
                        },
                    },
                    "multiplex": multiplex,
                }],
                "outbounds": [{"type": "direct", "tag": "direct"}],
            }
        local_inbound_port = int(link.get("local_port") or link.get("user_port") or 1080)
        return {
            "log": {"level": "warn"},
            "inbounds": [{
                "type": "socks",
                "tag": "p00rija-socks",
                "listen": "127.0.0.1",
                "listen_port": local_inbound_port,
            }],
            "outbounds": [{
                "type": "vless",
                "tag": "p00rija-out",
                "server": str(peer_ip or "127.0.0.1"),
                "server_port": listen_port,
                "uuid": uuid_val,
                "tls": {
                    "enabled": True,
                    "server_name": server_name,
                    "utls": {"enabled": True, "fingerprint": "chrome"},
                    "reality": {
                        "enabled": True,
                        "public_key": public_key,
                        "short_id": short_id,
                    },
                },
                "multiplex": multiplex,
            }],
        }

    multiplex = {
        "enabled": True,
        "protocol": "smux",
        "max_connections": int(link.get("smux_max_connections", link.get("mux_carriers", 4)) or 4),
        "min_streams": int(link.get("smux_min_streams", 4) or 4),
        "padding": bool(link.get("smux_padding", True)),
    }
    if link.get("tcp_brutal_enabled"):
        multiplex["brutal"] = {
            "enabled": True,
            "up_mbps": int(link.get("tcp_brutal_up_mbps", 50) or 50),
            "down_mbps": int(link.get("tcp_brutal_down_mbps", 100) or 100),
        }
    tls = {
        "enabled": True,
        "server_name": server_name,
        "min_version": "1.3",
    }
    if link.get("ech_enabled"):
        ech = {"enabled": True}
        if normalize_role(role) == "external":
            ech["key_path"] = str(link.get("ech_key_path") or "/opt/p00rija/certs/ech-key.pem")
        else:
            configs = [value.strip() for value in str(link.get("ech_config") or "").splitlines() if value.strip()]
            if configs:
                ech["config"] = configs
            ech["query_server_name"] = str(link.get("ech_query_server_name") or server_name)
        tls["ech"] = ech
    cert_content = str(link.get("cert_content") or "").strip()
    certs_dir = "/opt/p00rija/certs"
    if normalize_role(role) == "external":
        tls.update({
            "certificate_path": os.path.join(certs_dir, "cert.pem"),
            "key_path": os.path.join(certs_dir, "key.pem"),
        })
        if cert_content:
            tls["certificate"] = [cert_content]
        return {
            "log": {"level": "warn"},
            "inbounds": [{
                "type": "vless",
                "tag": "p00rija-in",
                "listen": "::",
                "listen_port": listen_port,
                "users": [{"uuid": uuid_val}],
                "tls": tls,
                "multiplex": multiplex,
            }],
            "outbounds": [{"type": "direct", "tag": "direct"}],
        }
    # Client TLS verification: trust the panel-managed cert when it is synced
    # onto the link, otherwise skip verification only on explicit opt-in.
    if cert_content:
        tls["certificate"] = [cert_content]
    elif bool(link.get("tls_insecure", False)):
        tls["insecure"] = True
    local_inbound_port = int(link.get("local_port") or link.get("user_port") or 1080)
    return {
        "log": {"level": "warn"},
        "inbounds": [{
            "type": "socks",
            "tag": "p00rija-socks",
            "listen": "127.0.0.1",
            "listen_port": local_inbound_port,
        }],
        "outbounds": [{
            "type": "vless",
            "tag": "p00rija-out",
            "server": str(peer_ip or "127.0.0.1"),
            "server_port": listen_port,
            "uuid": uuid_val,
            "tls": tls,
            "multiplex": multiplex,
        }],
    }


def masque_config_for_link(link, role, peer_ip: str = "127.0.0.1"):
    listen_port = int(link.get("bridge_port", 443))
    target_port = int((link.get("ports") or [{"target_port": 51820}])[0].get("target_port", 51820))
    mode = str(link.get("masque_mode") or "connect-udp")
    common = {
        "protocol": "CONNECT-IP" if mode == "connect-ip" else "CONNECT-UDP",
        "http_version": "h3",
        "path": str(link.get("obfs_path") or "/.well-known/masque/udp"),
        "server_name": str(link.get("tls_sni") or link.get("obfs_host") or ""),
        "bearer_token": str(link.get("masque_token") or link.get("xray_uuid") or ""),
    }
    cert_dir = "/opt/p00rija/certs"
    if normalize_role(role) == "external":
        return {
            **common,
            "mode": "server",
            "listen": f"0.0.0.0:{listen_port}",
            "target": f"127.0.0.1:{target_port}",
            "certificate": os.path.join(cert_dir, "cert.pem"),
            "private_key": os.path.join(cert_dir, "key.pem"),
        }
    # The client listens locally on the link's local port, not the remote target port.
    local_inbound_port = int(link.get("local_port") or link.get("user_port") or 1080)
    return {
        **common,
        "mode": "client",
        "server": f"{str(peer_ip or '127.0.0.1')}:{listen_port}",
        "listen": f"127.0.0.1:{local_inbound_port}",
        "connect_ip": mode == "connect-ip",
        "auto_reconnect": True,
    }
