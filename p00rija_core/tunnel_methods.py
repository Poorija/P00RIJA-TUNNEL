"""Tunnel method and engine definitions for P00RIJA TUNNEL."""

from __future__ import annotations

import hashlib
import ipaddress
import base64
import secrets
import os
import shlex
import uuid
from typing import Any

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
    }
}

EXTRA_TUNNEL_ENGINES = {"amneziawg", "wireguard", "ssh", "stunnel", "aead", "rawsock"}
EXTRA_TUNNEL_MODES = {
    "reverse_tcp", "amneziawg_v2", "wireguard_kernel",
    "ssh_socks5", "ssh_local_forward", "ssh_remote_forward", "ssh_jump",
    "stunnel_tls_wrap", "raw_socket", "aead_port_forward", "aead_socks5",
    "client_port_forward", "client_socks5",
}
EXTRA_TRANSPORTS = {
    "reverse_tcp", "amneziawg_udp", "wireguard_udp",
    "ssh_dynamic", "ssh_local", "ssh_remote", "ssh_jump",
    "stunnel_tls", "raw_ip", "aead_tcp", "port_forward", "socks5",
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
        "ssh_bind_host": "0.0.0.0",
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
        "ssh_bind_host": "0.0.0.0",
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
        "ssh_bind_host": "0.0.0.0",
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


def _stable_awg_private(seed: str) -> str:
    # This is a deterministic placeholder for preview/export. Real deployment
    # should replace it with `awg genkey` output.
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def _stable_awg_public(seed: str) -> str:
    digest = hashlib.sha256(("public:" + seed).encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def _normalize_ip_network(value: str, fallback: str) -> str:
    try:
        return str(ipaddress.ip_interface(value))
    except Exception:
        return fallback


def amneziawg_config_for_link(link_id: str, link: dict[str, Any], role: str, peer_ip: str) -> dict[str, Any]:
    listen_port = int(link.get("bridge_port", 7000))
    mtu = int(link.get("awg_mtu", 1280))
    obfs = amneziawg_obfuscation_from_link(link)
    server_private = link.get("awg_server_private_key") or _stable_awg_private(f"{link_id}:server")
    client_private = link.get("awg_client_private_key") or _stable_awg_private(f"{link_id}:client")
    server_public = link.get("awg_server_public_key") or _stable_awg_public(f"{link_id}:server")
    client_public = link.get("awg_client_public_key") or _stable_awg_public(f"{link_id}:client")
    server_address = _normalize_ip_network(str(link.get("awg_address", "10.66.0.1/24")), "10.66.0.1/24")
    client_address = _normalize_ip_network(str(link.get("awg_client_address", "10.66.0.2/32")), "10.66.0.2/32")
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
            "AllowedIPs = 10.66.0.2/32",
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

def wireguard_config_for_link(link_id: str, link: dict[str, Any], role: str, peer_ip: str) -> dict[str, Any]:
    listen_port = int(link.get("bridge_port", 51820))
    mtu = int(link.get("wg_mtu", 1420))
    server_private = link.get("wg_server_private_key") or _stable_awg_private(f"{link_id}:wg:server")
    client_private = link.get("wg_client_private_key") or _stable_awg_private(f"{link_id}:wg:client")
    server_public = link.get("wg_server_public_key") or _stable_awg_public(f"{link_id}:wg:server")
    client_public = link.get("wg_client_public_key") or _stable_awg_public(f"{link_id}:wg:client")
    server_address = _normalize_ip_network(str(link.get("wg_address", "10.77.0.1/24")), "10.77.0.1/24")
    client_address = _normalize_ip_network(str(link.get("wg_client_address", "10.77.0.2/32")), "10.77.0.2/32")
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
            "AllowedIPs = 10.77.0.2/32",
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
    bind_host = str(link.get("ssh_bind_host") or ("0.0.0.0" if mode != "ssh_jump" else "127.0.0.1"))
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

def aead_config_for_link(link_id: str, link: dict[str, Any], role: str, peer_ip: str) -> dict[str, Any]:
    cipher = str(link.get("aead_cipher") or "aes-128-gcm").lower()
    key_hex = str(link.get("aead_key") or _secret_hex(f"{link_id}:{cipher}", 16))
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
    if mode in ("grpc", "reality_grpc", "mux_grpc", "http2_tls", "h2", "ech_h2", "xhttp"):
        stability += 10
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
    elif engine in ("hysteria2", "tuic", "singbox", "naiveproxy", "shadowtls", "mieru", "brook", "masque"):
        category = "stealth"
    elif engine in ("rathole", "backhaul", "frp", "chisel", "gost"):
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
            "remote": f"{p.get('target_host') or '127.0.0.1'}:{p.get('target_port', 443)}"
        })
        
    other_ip = link.get("external_ip") or link.get("peer_ip") or link.get("client_ip") or "127.0.0.1"
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

    transport = str(link.get("transport") or link.get("tunnel_mode") or "tcp")
    xhttp_enabled = transport == "xhttp" or link.get("tunnel_mode") == "xhttp"
    network_name = "xhttp" if xhttp_enabled else "raw"
    xhttp_settings = {
        "path": str(link.get("obfs_path") or "/xhttp"),
        "mode": str(link.get("xhttp_mode") or "auto"),
    }
    if link.get("xhttp_auto_select", True):
        xhttp_settings["mode"] = "auto"

    if normalize_role(role) == "external":
        client = {"id": uuid_val}
        if flow and not xhttp_enabled:
            client["flow"] = flow
        stream_settings = {
            "network": network_name,
            "security": security,
            "realitySettings": {
                "show": False,
                "target": "1.1.1.1:443",
                "xver": 0,
                "serverNames": server_names,
                "privateKey": private_key,
                "shortIds": [short_id]
            }
        }
        if xhttp_enabled:
            stream_settings["xhttpSettings"] = xhttp_settings
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
    if flow and not xhttp_enabled:
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
                    "users": [user]
                }]
            },
            "streamSettings": stream_settings
        }]
    }


def singbox_config_for_link(link, role):
    listen_port = int(link.get("bridge_port", 7000))
    target_port = int((link.get("ports") or [{"target_port": 443}])[0].get("target_port", 443))
    uuid_val = link.get("xray_uuid") or str(uuid.uuid4())
    server_name = str(link.get("tls_sni") or link.get("obfs_host") or "www.cloudflare.com")
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
    if normalize_role(role) == "external":
        tls.update({
            "certificate_path": "/opt/p00rija/certs/cert.pem",
            "key_path": "/opt/p00rija/certs/key.pem",
        })
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
    return {
        "log": {"level": "warn"},
        "inbounds": [{
            "type": "socks",
            "tag": "p00rija-socks",
            "listen": "127.0.0.1",
            "listen_port": target_port,
        }],
        "outbounds": [{
            "type": "vless",
            "tag": "p00rija-out",
            "server": str(link.get("external_ip") or link.get("iran_ip") or "127.0.0.1"),
            "server_port": listen_port,
            "uuid": uuid_val,
            "tls": tls,
            "multiplex": multiplex,
        }],
    }


def masque_config_for_link(link, role):
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
    if normalize_role(role) == "external":
        return {
            **common,
            "mode": "server",
            "listen": f"0.0.0.0:{listen_port}",
            "target": f"127.0.0.1:{target_port}",
            "certificate": "/opt/p00rija/certs/cert.pem",
            "private_key": "/opt/p00rija/certs/key.pem",
        }
    return {
        **common,
        "mode": "client",
        "server": f"{link.get('external_ip', link.get('iran_ip', '127.0.0.1'))}:{listen_port}",
        "listen": f"127.0.0.1:{target_port}",
        "connect_ip": mode == "connect-ip",
        "auto_reconnect": True,
    }
