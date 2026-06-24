"""Tunnel link API dispatchers for P00RIJA TUNNEL."""

from __future__ import annotations

import os
import secrets
import subprocess
import time
import uuid
from collections.abc import Callable
from typing import Any
import re


def dispatch_links_get(
    path: str,
    query: dict[str, list[str]],
    *,
    db_data: dict[str, Any],
    save_db: Callable[[], Any],
    log_event: Callable[[str, str, str], Any],
    list_runtime_sessions: Callable[[], list[dict[str, Any]]],
    hysteria2_config_for_link: Callable[[dict[str, Any], str], dict[str, Any]],
    muxquantum_config_for_link: Callable[[str, dict[str, Any], str, str], dict[str, Any]],
    xray_config_for_link: Callable[[dict[str, Any], str], dict[str, Any]],
    singbox_config_for_link: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
    masque_config_for_link: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
    amneziawg_config_for_link: Callable[[str, dict[str, Any], str, str], dict[str, Any]] | None = None,
    wireguard_config_for_link: Callable[[str, dict[str, Any], str, str], dict[str, Any]] | None = None,
    ssh_config_for_link: Callable[[str, dict[str, Any], str, str], dict[str, Any]] | None = None,
    stunnel_config_for_link: Callable[[str, dict[str, Any], str, str], dict[str, Any]] | None = None,
    raw_socket_config_for_link: Callable[[str, dict[str, Any], str, str], dict[str, Any]] | None = None,
    aead_config_for_link: Callable[[str, dict[str, Any], str, str], dict[str, Any]] | None = None,
) -> tuple[bool, dict[str, Any], int]:
    if path == "/api/links/toggle-pause":
        link_id = query.get("id", [None])[0]
        if not link_id or link_id not in db_data.get("links", {}):
            return True, {"error": "Link not found"}, 404
        link = db_data["links"][link_id]
        link["paused"] = not link.get("paused", False)
        save_db()
        log_event("panel", "info", f"Tunnel link '{link.get('name', link_id)}' {'paused' if link['paused'] else 'resumed'}.")
        return True, {"success": True, "paused": link["paused"]}, 200

    if path == "/api/links/test":
        link_id = query.get("id", [""])[0]
        link = db_data.get("links", {}).get(link_id)
        if not link:
            return True, {"error": "Link not found"}, 404
        now = time.time()
        internal_node = db_data.get("nodes", {}).get(link.get("internal_node_id", link.get("iran_node_id")), {})
        external_node = db_data.get("nodes", {}).get(link.get("external_node_id", link.get("foreign_node_id")), {})
        internal_live = internal_node.get("status") == "online" and now - internal_node.get("last_seen", 0) <= 30
        external_live = external_node.get("status") == "online" and now - external_node.get("last_seen", 0) <= 30
        return True, {
            "success": internal_live and external_live,
            "internal_live": internal_live,
            "external_live": external_live,
            "engine": link.get("engine", "builtin"),
            "active_sessions": [s for s in list_runtime_sessions() if s.get("link_id") == link_id],
        }, 200

    if path == "/api/links/engine-config":
        link_id = query.get("id", [""])[0]
        link = db_data.get("links", {}).get(link_id)
        if not link:
            return True, {"error": "Link not found"}, 404
        engine = link.get("engine")
        external_id = link.get("external_node_id", link.get("foreign_node_id"))
        external_node = db_data.get("nodes", {}).get(external_id, {})
        external_ip = external_node.get("ip") or link.get("external_ip", link.get("iran_ip", "127.0.0.1"))
        if engine == "hysteria2":
            return True, {
                "internal": hysteria2_config_for_link(link, "internal"),
                "external": hysteria2_config_for_link(link, "external"),
            }, 200
        if engine == "muxquantum":
            other_ip = link.get("external_ip", link.get("iran_ip", "127.0.0.1"))
            return True, {
                "internal": muxquantum_config_for_link(link_id, link, "internal", other_ip),
                "external": muxquantum_config_for_link(link_id, link, "external", other_ip),
            }, 200
        if engine == "singbox" and singbox_config_for_link:
            return True, {
                "internal": singbox_config_for_link(link, "internal"),
                "external": singbox_config_for_link(link, "external"),
            }, 200
        if engine == "masque" and masque_config_for_link:
            return True, {
                "internal": masque_config_for_link(link, "internal"),
                "external": masque_config_for_link(link, "external"),
            }, 200
        if engine == "amneziawg" and amneziawg_config_for_link:
            return True, {
                "internal": amneziawg_config_for_link(link_id, link, "internal", external_ip),
                "external": amneziawg_config_for_link(link_id, link, "external", external_ip),
            }, 200
        if engine == "wireguard" and wireguard_config_for_link:
            return True, {
                "internal": wireguard_config_for_link(link_id, link, "internal", external_ip),
                "external": wireguard_config_for_link(link_id, link, "external", external_ip),
            }, 200
        if engine == "ssh" and ssh_config_for_link:
            return True, {
                "internal": ssh_config_for_link(link_id, link, "internal", external_ip),
                "external": ssh_config_for_link(link_id, link, "external", external_ip),
            }, 200
        if engine == "stunnel" and stunnel_config_for_link:
            return True, {
                "internal": stunnel_config_for_link(link_id, link, "internal", external_ip),
                "external": stunnel_config_for_link(link_id, link, "external", external_ip),
            }, 200
        if engine == "rawsock" and raw_socket_config_for_link:
            return True, {
                "internal": raw_socket_config_for_link(link_id, link, "internal", external_ip),
                "external": raw_socket_config_for_link(link_id, link, "external", external_ip),
            }, 200
        if engine == "aead" and aead_config_for_link:
            return True, {
                "internal": aead_config_for_link(link_id, link, "internal", external_ip),
                "external": aead_config_for_link(link_id, link, "external", external_ip),
            }, 200
        if engine == "xray":
            return True, {
                "internal": xray_config_for_link(link, "internal"),
                "external": xray_config_for_link(link, "external"),
            }, 200
        runtime_summary = {
            "engine": engine or "builtin",
            "runtime": "p00rija-builtin-compatible",
            "data_plane_architecture": link.get("data_plane_architecture", "per_user"),
            "transport": link.get("transport", "tcp"),
            "tunnel_mode": link.get("tunnel_mode", "tcp"),
            "bridge_port": link.get("bridge_port"),
            "sync_port": link.get("sync_port"),
        }
        return True, {
            "internal": {**runtime_summary, "role": "internal"},
            "external": {**runtime_summary, "role": "external"},
        }, 200

    return False, {}, 404


def _parse_port_range(port_text: str) -> tuple[int | None, int | None]:
    if "-" in port_text:
        parts = port_text.split("-", 1)
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])
    if port_text.isdigit():
        value = int(port_text)
        return value, value
    return None, None


def _xray_key_pair(engine_binary: str | None = None) -> tuple[str, str]:
    fallback_key = "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM="
    candidates = [engine_binary] if engine_binary else []
    candidates.extend(("engines/xray", "/usr/local/bin/xray"))
    for candidate in candidates:
        if not candidate or not os.path.exists(candidate):
            continue
        try:
            output = subprocess.run([candidate, "x25519"], capture_output=True, text=True, timeout=5).stdout
            private_key = ""
            public_key = ""
            for line in output.splitlines():
                if "Private key:" in line:
                    private_key = line.split("Private key:", 1)[1].strip()
                if "Public key:" in line:
                    public_key = line.split("Public key:", 1)[1].strip()
            if private_key and public_key:
                return private_key, public_key
        except Exception:
            continue
    return fallback_key, fallback_key


_HOST_RE = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def _link_node_ids(link: dict[str, Any]) -> set[str]:
    return {
        str(value)
        for value in (
            link.get("internal_node_id", link.get("iran_node_id")),
            link.get("external_node_id", link.get("foreign_node_id")),
        )
        if value
    }


def _used_ports_for_nodes(
    db_data: dict[str, Any],
    node_ids: set[str],
    *,
    exclude_link_id: str = "",
    ignore_runtime_ports_by_node: dict[str, set[int]] | None = None,
) -> set[int]:
    used: set[int] = set()
    ignored_runtime = ignore_runtime_ports_by_node or {}
    for node_id in node_ids:
        node = db_data.get("nodes", {}).get(node_id, {})
        stats = node.get("stats") or {}
        node_ignored = ignored_runtime.get(str(node_id), set())
        for value in stats.get("listening_tcp_ports", []) or []:
            try:
                port = int(value)
                if 1 <= port <= 65535 and port not in node_ignored:
                    used.add(port)
            except Exception:
                pass
    for existing_id, link in db_data.get("links", {}).items():
        if exclude_link_id and existing_id == exclude_link_id:
            continue
        if not (_link_node_ids(link) & node_ids):
            continue
        for value in (link.get("bridge_port"), link.get("sync_port")):
            try:
                port = int(value)
                if 1 <= port <= 65535:
                    used.add(port)
            except Exception:
                pass
        for mapping in link.get("ports", []) or []:
            try:
                port = int(mapping.get("user_port"))
                if 1 <= port <= 65535:
                    used.add(port)
            except Exception:
                pass
    return used


def _edit_owned_runtime_ports(
    db_data: dict[str, Any],
    link_id: str,
    selected_node_ids: set[str],
) -> dict[str, set[int]]:
    """Return only runtime listener ports that the edited link already owns.

    Node reports include the active link's Bridge/Sync listeners. During an
    edit those listeners must not collide with themselves, but they may only
    be ignored on nodes that already belong to the same link. Database-backed
    reservations from every other link are still checked independently.
    """
    link = db_data.get("links", {}).get(str(link_id), {})
    if not link:
        return {}
    current_nodes = _link_node_ids(link)
    owned_ports: set[int] = set()
    for value in (link.get("bridge_port"), link.get("sync_port")):
        try:
            port = int(value)
            if 1 <= port <= 65535:
                owned_ports.add(port)
        except Exception:
            pass
    return {
        node_id: set(owned_ports)
        for node_id in current_nodes & {str(value) for value in selected_node_ids}
    }


def _next_port_pair(
    db_data: dict[str, Any],
    internal_node_id: str,
    external_node_id: str,
    *,
    exclude_link_id: str = "",
    start: int = 7000,
) -> tuple[int, int]:
    used = _used_ports_for_nodes(
        db_data,
        {str(internal_node_id), str(external_node_id)},
        exclude_link_id=exclude_link_id,
        ignore_runtime_ports_by_node=_edit_owned_runtime_ports(
            db_data,
            exclude_link_id,
            {str(internal_node_id), str(external_node_id)},
        ) if exclude_link_id else None,
    )
    candidate = max(1024, int(start or 7000))
    if candidate % 2:
        candidate += 1
    while candidate <= 65533:
        if candidate not in used and candidate + 1 not in used:
            return candidate, candidate + 1
        candidate += 2
    raise ValueError("No free Bridge/Sync port pair is available")


def _valid_obfuscation_host(value: Any) -> bool:
    host = str(value or "").strip()
    return bool(host) and (_HOST_RE.fullmatch(host) is not None)


def dispatch_links_post(
    path: str,
    query: dict[str, list[str]],
    body: dict[str, Any],
    *,
    db_data: dict[str, Any],
    save_db: Callable[[], Any],
    log_event: Callable[[str, str, str], Any],
    default_tunnel_profiles: Callable[[], dict[str, dict[str, Any]]],
    normalize_tags: Callable[[Any], list[str]],
    clamp_int: Callable[[Any, int, int, int], int],
    valid_port: Callable[[Any], bool],
    role_matches: Callable[[str, str], bool],
    valid_engines: set[str],
    valid_modes: set[str],
    valid_transports: set[str],
    max_pool_size_per_link: int,
    xray_binary: str | None = None,
) -> tuple[bool, dict[str, Any], int]:
    if path == "/api/links/next-ports":
        internal_node_id = str(body.get("internal_node_id") or body.get("iran_node_id") or "")
        external_node_id = str(body.get("external_node_id") or body.get("foreign_node_id") or "")
        if internal_node_id not in db_data.get("nodes", {}) or external_node_id not in db_data.get("nodes", {}):
            return True, {"error": "Valid internal and external nodes are required"}, 400
        try:
            bridge_port, sync_port = _next_port_pair(
                db_data,
                internal_node_id,
                external_node_id,
                exclude_link_id=str(body.get("exclude_link_id") or ""),
                start=int(body.get("start") or 7000),
            )
        except Exception as exc:
            return True, {"error": str(exc)}, 409
        return True, {
            "success": True,
            "bridge_port": bridge_port,
            "sync_port": sync_port,
            "checked_node_ids": [internal_node_id, external_node_id],
        }, 200

    if path in ("/api/links", "/api/links/edit"):
        edit_mode = path == "/api/links/edit"
        link_id = body.get("id") if edit_mode else f"link_{str(uuid.uuid4())[:8]}"
        existing_link = db_data.get("links", {}).get(link_id, {}) if edit_mode else {}
        if edit_mode and not existing_link:
            return True, {"error": "Link not found"}, 404

        name = body.get("name")
        internal_node_id = body.get("internal_node_id") or body.get("iran_node_id")
        external_node_id = body.get("external_node_id") or body.get("foreign_node_id")
        profile_id = body.get("profile_id", "custom")
        profiles = db_data.get("settings", {}).get("tunnel_profiles", default_tunnel_profiles())
        profile = profiles.get(profile_id, {}) if profile_id != "custom" else {}

        easy_mode = bool(body.get("easy_mode", False))
        auto_allocate_ports = bool(body.get("auto_allocate_ports", easy_mode))
        bridge_port = int(body.get("bridge_port", profile.get("bridge_port", 7000)))
        sync_port = int(body.get("sync_port", profile.get("sync_port", 7001)))
        pool_default = 4 if easy_mode else 24
        requested_pool_size = body.get(
            "pool_size",
            profile.get("pool_size", existing_link.get("pool_size", pool_default)),
        )
        pool_size = clamp_int(requested_pool_size, pool_default, 1, max_pool_size_per_link)
        if edit_mode and "pool_size" in existing_link:
            try:
                existing_pool_size = int(existing_link["pool_size"])
                submitted_pool_size = int(requested_pool_size)
                # Old releases allowed larger pools. Keeping the unchanged
                # legacy value is safe because that link already runs with it;
                # silently shrinking it during an unrelated edit is not.
                if submitted_pool_size == existing_pool_size and existing_pool_size > max_pool_size_per_link:
                    pool_size = existing_pool_size
            except Exception:
                pass
        direction = body.get("direction") or profile.get("direction") or existing_link.get("direction", "external_to_internal")
        if direction not in ("external_to_internal", "internal_to_external"):
            return True, {"error": "Invalid tunnel direction"}, 400

        engine = body.get("engine") or profile.get("engine", "builtin")
        transport = body.get("transport") or profile.get("transport", profile.get("tunnel_mode", "tcp"))
        network = body.get("network") or profile.get("network", "tcp")
        tunnel_mode = body.get("tunnel_mode") or profile.get("tunnel_mode", "tcp")
        tls_enabled = bool(body.get("tls_enabled", profile.get("tls_enabled", False)))
        tls_sni = body.get("tls_sni") or profile.get("tls_sni", profile.get("obfs_host", "speedtest.net"))
        obfs_host = body.get("obfs_host") or profile.get("obfs_host", "speedtest.net")
        obfs_path = body.get("obfs_path") or profile.get("obfs_path", "/tunnel")
        tags = normalize_tags(body.get("tags", existing_link.get("tags", [])))
        category = str(
            body.get("category")
            or existing_link.get("category")
            or profile.get("category")
            or f"{engine} / {tunnel_mode}"
        ).strip()[:80]
        default_display_order = max(
            [int(item.get("display_order", 0) or 0) for item in db_data.get("links", {}).values()] or [-1]
        ) + 1
        display_order = int(existing_link.get("display_order", default_display_order) or default_display_order)
        padding_min = clamp_int(body.get("padding_min", profile.get("padding_min", 0)), 0, 0, 4096)
        padding_max = clamp_int(body.get("padding_max", profile.get("padding_max", 0)), 0, 0, 4096)
        jitter_ms = clamp_int(body.get("jitter_ms", profile.get("jitter_ms", 0)), 0, 0, 5000)
        keepalive_interval = clamp_int(body.get("keepalive_interval", profile.get("keepalive_interval", 25)), 25, 5, 300)
        architecture = str(
            body.get("data_plane_architecture")
            or profile.get("data_plane_architecture")
            or existing_link.get("data_plane_architecture")
            or ""
        ).strip().lower()
        if not architecture:
            legacy_bonding = bool(body.get("bonding_enabled", profile.get("bonding_enabled", existing_link.get("bonding_enabled", False))))
            architecture = "adaptive_bonding" if legacy_bonding else "per_user"
        if architecture not in ("per_user", "adaptive_bonding", "shared_mux", "smart_hybrid"):
            return True, {"error": "Invalid data-plane architecture"}, 400
        bonding_enabled = architecture in ("adaptive_bonding", "smart_hybrid")
        mux_carriers = clamp_int(
            body.get("mux_carriers", profile.get("mux_carriers", existing_link.get("mux_carriers", 2))),
            4,
            2,
            8,
        )
        adaptive_smux_enabled = bool(
            body.get("adaptive_smux_enabled", profile.get("adaptive_smux_enabled", existing_link.get("adaptive_smux_enabled", False)))
        )
        smux_min_connections = clamp_int(
            body.get("smux_min_connections", profile.get("smux_min_connections", existing_link.get("smux_min_connections", 2))),
            2, 1, 16,
        )
        smux_max_connections = clamp_int(
            body.get("smux_max_connections", profile.get("smux_max_connections", existing_link.get("smux_max_connections", max(4, mux_carriers)))),
            max(4, mux_carriers), smux_min_connections, 16,
        )
        smux_min_streams = clamp_int(
            body.get("smux_min_streams", profile.get("smux_min_streams", existing_link.get("smux_min_streams", 8))),
            8, 1, 1024,
        )
        bonding_max_lanes = clamp_int(
            body.get("bonding_max_lanes", profile.get("bonding_max_lanes", existing_link.get("bonding_max_lanes", 4))),
            4,
            2,
            16,
        )
        if bonding_max_lanes not in (2, 4, 6, 8, 10, 12, 16):
            return True, {"error": "Adaptive Bonding lanes must be one of 2, 4, 6, 8, 10, 12, or 16"}, 400
        if bonding_enabled and bonding_max_lanes > max_pool_size_per_link:
            return True, {"error": f"Adaptive Bonding lanes exceed this node pool limit ({max_pool_size_per_link})"}, 400
        requested_max_workers = clamp_int(
            body.get("max_reverse_workers", profile.get("max_reverse_workers", existing_link.get("max_reverse_workers", 16))),
            16,
            1,
            max_pool_size_per_link,
        )
        requested_min_ready = clamp_int(
            body.get("min_ready_workers", profile.get("min_ready_workers", existing_link.get("min_ready_workers", 2))),
            2,
            1,
            requested_max_workers,
        )
        if architecture == "adaptive_bonding":
            # The selected lane value is a real idle-path ceiling, so keep
            # enough reverse workers warm to satisfy it for the first flow.
            pool_size = bonding_max_lanes
            requested_max_workers = max(requested_max_workers, bonding_max_lanes)
            requested_min_ready = max(requested_min_ready, bonding_max_lanes)
        elif architecture == "shared_mux":
            pool_size = smux_max_connections if adaptive_smux_enabled else mux_carriers
            requested_max_workers = pool_size
            requested_min_ready = smux_min_connections if adaptive_smux_enabled else mux_carriers
        elif architecture == "smart_hybrid":
            hybrid_mux_workers = smux_max_connections if adaptive_smux_enabled else mux_carriers
            hybrid_workers = bonding_max_lanes + hybrid_mux_workers
            if hybrid_workers > max_pool_size_per_link:
                return True, {"error": f"Hybrid worker demand exceeds this node pool limit ({max_pool_size_per_link})"}, 400
            pool_size = hybrid_workers
            requested_max_workers = hybrid_workers
            requested_min_ready = bonding_max_lanes + (
                smux_min_connections if adaptive_smux_enabled else mux_carriers
            )
        xray_protocol = body.get("xray_protocol") or profile.get("xray_protocol", "vless")
        xray_security = body.get("xray_security") or profile.get("xray_security", "reality")
        xray_flow = body.get("xray_flow") or profile.get("xray_flow", "xtls-rprx-vision")
        xray_uuid = body.get("xray_uuid") or str(uuid.uuid4())
        xray_sni = body.get("xray_sni") or profile.get("xray_sni", "www.microsoft.com")
        xray_shortid = body.get("xray_shortid") or profile.get("xray_shortid", secrets.token_hex(8))
        xray_private_key = body.get("xray_private_key") or profile.get("xray_private_key", "")
        xray_public_key = body.get("xray_public_key") or profile.get("xray_public_key", "")
        if not xray_private_key or not xray_public_key:
            xray_private_key, xray_public_key = _xray_key_pair(xray_binary)
        ech_enabled = bool(body.get("ech_enabled", profile.get("ech_enabled", existing_link.get("ech_enabled", False))))
        ech_config = str(body.get("ech_config") or existing_link.get("ech_config") or "").strip()
        ech_key_path = str(body.get("ech_key_path") or existing_link.get("ech_key_path") or "/opt/p00rija/certs/ech-key.pem").strip()
        ech_query_server_name = str(body.get("ech_query_server_name") or existing_link.get("ech_query_server_name") or tls_sni).strip()
        xhttp_auto_select = bool(body.get("xhttp_auto_select", profile.get("xhttp_auto_select", existing_link.get("xhttp_auto_select", True))))
        xhttp_mode = str(body.get("xhttp_mode") or profile.get("xhttp_mode") or existing_link.get("xhttp_mode") or "auto").strip()
        if xhttp_mode not in ("auto", "packet-up", "stream-up", "stream-one"):
            return True, {"error": "Invalid XHTTP mode"}, 400
        masque_mode = str(body.get("masque_mode") or existing_link.get("masque_mode") or "connect-udp").strip()
        if masque_mode not in ("connect-udp", "connect-ip"):
            return True, {"error": "Invalid MASQUE mode"}, 400
        masque_token = str(body.get("masque_token") or existing_link.get("masque_token") or secrets.token_urlsafe(24))[:256]
        tcp_brutal_enabled = bool(body.get("tcp_brutal_enabled", existing_link.get("tcp_brutal_enabled", False)))
        tcp_brutal_up_mbps = clamp_int(body.get("tcp_brutal_up_mbps", existing_link.get("tcp_brutal_up_mbps", 50)), 50, 1, 10000)
        tcp_brutal_down_mbps = clamp_int(body.get("tcp_brutal_down_mbps", existing_link.get("tcp_brutal_down_mbps", 100)), 100, 1, 10000)

        if easy_mode:
            engine = "builtin"
            transport = "websocket"
            network = "tcp"
            tunnel_mode = "websocket"
            tls_enabled = True
            pool_size = min(16, max_pool_size_per_link)
            tls_sni = str(tls_sni or "speedtest.net").strip()
            obfs_host = str(obfs_host or tls_sni or "speedtest.net").strip()
            obfs_path = str(obfs_path or "/assets/ws").strip()
            padding_min = max(8, padding_min)
            padding_max = max(padding_min, min(96, padding_max or 48))
            jitter_ms = min(25, max(0, jitter_ms))
            keepalive_interval = min(45, max(15, keepalive_interval))

        nodes = db_data.get("nodes", {})
        if not name or internal_node_id not in nodes or external_node_id not in nodes:
            return True, {"error": "Invalid nodes chosen"}, 400
        internal_role = nodes[internal_node_id].get("type", nodes[internal_node_id].get("role", "unknown"))
        external_role = nodes[external_node_id].get("type", nodes[external_node_id].get("role", "unknown"))
        if not role_matches(internal_role, "internal") or not role_matches(external_role, "external"):
            return True, {"error": "Internal and external node roles are required"}, 400
        if auto_allocate_ports:
            bridge_port, sync_port = _next_port_pair(
                db_data,
                str(internal_node_id),
                str(external_node_id),
                exclude_link_id=str(link_id) if edit_mode else "",
                start=bridge_port,
            )
        if not valid_port(bridge_port) or not valid_port(sync_port) or bridge_port == sync_port:
            return True, {"error": "Invalid bridge or sync port"}, 400
        if engine not in valid_engines:
            return True, {"error": "Invalid tunnel engine"}, 400
        if tunnel_mode not in valid_modes:
            return True, {"error": "Invalid tunnel mode"}, 400
        if transport not in valid_transports:
            return True, {"error": "Invalid transport"}, 400
        if network not in ("tcp", "udp", "tcp_udp"):
            return True, {"error": "Invalid network"}, 400
        if ech_enabled and engine != "singbox":
            return True, {"error": "ECH requires the sing-box engine and compatible DNS/client support"}, 400
        if ech_enabled and not (ech_config or ech_query_server_name):
            return True, {"error": "ECH config or DNS query server name is required"}, 400
        if tunnel_mode == "xhttp" and engine != "xray":
            return True, {"error": "XHTTP + REALITY requires the Xray engine"}, 400
        if engine == "masque" and not tls_enabled:
            return True, {"error": "MASQUE requires TLS/HTTP3"}, 400
        if tcp_brutal_enabled and engine != "singbox":
            return True, {"error": "TCP Brutal requires sing-box"}, 400
        if architecture != "per_user" and bool(body.get("native_engine_enabled", profile.get("native_engine_enabled", False))):
            return True, {"error": "Shared Mux and Adaptive Bonding require the built-in compatible data plane, not native engine mode"}, 400
        if len(str(name)) > 100 or len(str(obfs_host)) > 255 or not str(obfs_path).startswith("/") or len(str(obfs_path)) > 255:
            return True, {"error": "Invalid tunnel metadata"}, 400
        if any(ch in str(obfs_path) for ch in ("\r", "\n", " ", "\t")):
            return True, {"error": "Obfuscation path must be a clean absolute URL path"}, 400
        if (tls_enabled or tunnel_mode in ("websocket", "http_obfs")) and not _valid_obfuscation_host(obfs_host):
            return True, {"error": "A valid obfuscation Host is required"}, 400
        if tls_enabled and not _valid_obfuscation_host(tls_sni):
            return True, {"error": "A valid TLS SNI hostname is required"}, 400

        used_ports = _used_ports_for_nodes(
            db_data,
            {str(internal_node_id), str(external_node_id)},
            exclude_link_id=str(link_id) if edit_mode else "",
            ignore_runtime_ports_by_node=_edit_owned_runtime_ports(
                db_data,
                str(link_id),
                {str(internal_node_id), str(external_node_id)},
            ) if edit_mode else None,
        )
        if bridge_port in used_ports or sync_port in used_ports:
            return True, {"error": "Bridge or Sync port is already occupied on one of the selected nodes"}, 409

        link_payload = {
            "name": name,
            "internal_node_id": internal_node_id,
            "external_node_id": external_node_id,
            "iran_node_id": internal_node_id,
            "foreign_node_id": external_node_id,
            "direction": direction,
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
            "easy_mode": easy_mode,
            "tags": tags,
            "category": category,
            "display_order": display_order,
            "padding_min": padding_min,
            "padding_max": max(padding_min, padding_max),
            "jitter_ms": jitter_ms,
            "keepalive_interval": keepalive_interval,
            "bonding_enabled": bonding_enabled,
            "bonding_max_lanes": bonding_max_lanes,
            "data_plane_architecture": architecture,
            "mux_carriers": mux_carriers,
            "adaptive_smux_enabled": adaptive_smux_enabled,
            "smux_min_connections": smux_min_connections,
            "smux_max_connections": smux_max_connections,
            "smux_min_streams": smux_min_streams,
            "smux_padding": bool(body.get("smux_padding", existing_link.get("smux_padding", True))),
            "max_reverse_workers": requested_max_workers,
            "min_ready_workers": requested_min_ready,
            "xray_protocol": xray_protocol,
            "xray_security": xray_security,
            "xray_flow": xray_flow,
            "xray_uuid": xray_uuid,
            "xray_sni": xray_sni,
            "xray_shortid": xray_shortid,
            "xray_public_key": xray_public_key,
            "xray_private_key": xray_private_key,
            "ech_enabled": ech_enabled,
            "ech_config": ech_config,
            "ech_key_path": ech_key_path,
            "ech_query_server_name": ech_query_server_name,
            "xhttp_auto_select": xhttp_auto_select,
            "xhttp_mode": xhttp_mode,
            "masque_mode": masque_mode,
            "masque_token": masque_token,
            "tcp_brutal_enabled": tcp_brutal_enabled,
            "tcp_brutal_up_mbps": tcp_brutal_up_mbps,
            "tcp_brutal_down_mbps": tcp_brutal_down_mbps,
            "paused": bool(existing_link.get("paused", False)),
            "ports": existing_link.get("ports", []),
        }
        for key in (
            "awg_address", "awg_client_address", "awg_mtu", "awg_jc", "awg_jmin", "awg_jmax",
            "awg_s1", "awg_s2", "awg_s3", "awg_s4", "awg_h1", "awg_h2", "awg_h3", "awg_h4",
            "awg_i1", "awg_i2", "awg_i3", "awg_i4", "awg_i5", "awg_interface",
            "awg_server_private_key", "awg_server_public_key", "awg_client_private_key", "awg_client_public_key",
            "wg_address", "wg_client_address", "wg_mtu", "wg_allowed_ips", "wg_interface",
            "wg_server_private_key", "wg_server_public_key", "wg_client_private_key", "wg_client_public_key",
            "ssh_user", "ssh_port", "ssh_host", "ssh_bind_host", "ssh_identity_file", "ssh_jump_hosts",
            "ssh_target_host", "ssh_target_port", "stunnel_cert_path", "stunnel_key_path", "stunnel_verify",
            "raw_protocol", "raw_mtu", "raw_packet_mark", "aead_cipher", "aead_key", "aead_nonce_mode",
            "egress_mode", "socks5_username", "socks5_password",
            "hysteria_up_mbps", "hysteria_down_mbps",
            "native_engine_enabled",
        ):
            if key in body:
                link_payload[key] = body.get(key)
            elif key in profile:
                link_payload[key] = profile.get(key)
            elif key in existing_link:
                link_payload[key] = existing_link.get(key)

        db_data.setdefault("links", {})[link_id] = link_payload
        save_db()
        log_event("panel", "info", f"{'Updated' if edit_mode else 'Created'} tunnel link '{name}' (Mode: {tunnel_mode}, TLS: {tls_enabled}).")
        return True, {
            "success": True,
            "link_id": link_id,
            "bridge_port": bridge_port,
            "sync_port": sync_port,
            "easy_mode": easy_mode,
            "tls_enabled": tls_enabled,
        }, 200

    if path == "/api/links/reorder":
        order = body.get("order")
        if not isinstance(order, list):
            return True, {"error": "Tunnel order must be a list"}, 400
        known = db_data.get("links", {})
        clean = [str(link_id) for link_id in order if str(link_id) in known]
        clean.extend(link_id for link_id in known if link_id not in clean)
        for index, link_id in enumerate(clean):
            known[link_id]["display_order"] = index
        save_db()
        log_event("panel", "info", f"Updated tunnel display order for {len(clean)} link(s).")
        return True, {"success": True, "order": clean}, 200

    if path == "/api/links/categories/reorder":
        order = body.get("order")
        if not isinstance(order, list):
            return True, {"error": "Category order must be a list"}, 400
        clean = []
        for value in order:
            category_name = str(value or "").strip()[:80]
            if category_name and category_name not in clean:
                clean.append(category_name)
        db_data.setdefault("settings", {})["link_category_order"] = clean
        save_db()
        log_event("panel", "info", f"Updated tunnel category order for {len(clean)} category item(s).")
        return True, {"success": True, "order": clean}, 200

    if path == "/api/links/ports/edit":
        link_id = query.get("id", [""])[0]
        index = int(body.get("index", -1))
        user_port = int(str(body.get("user_port", "")).strip())
        target_port = int(str(body.get("target_port", "")).strip())
        if link_id not in db_data.get("links", {}):
            return True, {"error": "Link not found"}, 404
        if not valid_port(user_port) or not valid_port(target_port):
            return True, {"error": "Invalid port value"}, 400
        link = db_data["links"][link_id]
        if not (0 <= index < len(link.get("ports", []))):
            return True, {"error": "Invalid mapping index"}, 400
        duplicate = any(int(port.get("user_port", 0)) == user_port and port_index != index for port_index, port in enumerate(link.get("ports", [])))
        if duplicate:
            return True, {"error": "Internal input port is already mapped in this tunnel"}, 400
        old = dict(link["ports"][index])
        link["ports"][index] = {"user_port": user_port, "target_port": target_port}
        save_db()
        log_event("panel", "info", f"Edited port mapping {old.get('user_port')} -> {old.get('target_port')} to {user_port} -> {target_port} in tunnel '{link['name']}'.")
        return True, {"success": True, "mapping": link["ports"][index]}, 200

    if path == "/api/links/ports":
        link_id = query.get("id", [""])[0]
        user_port_text = str(body.get("user_port")).strip()
        target_port_text = str(body.get("target_port")).strip()
        if link_id not in db_data.get("links", {}):
            return True, {"error": "Link not found"}, 404
        link = db_data["links"][link_id]
        user_start, user_end = _parse_port_range(user_port_text)
        target_start, target_end = _parse_port_range(target_port_text)
        if None in (user_start, user_end, target_start, target_end) or not (
            valid_port(user_start) and valid_port(user_end) and valid_port(target_start) and valid_port(target_end)
        ):
            return True, {"error": "Invalid port value or range"}, 400
        if (user_end - user_start) != (target_end - target_start):
            return True, {"error": "Port ranges must be of equal length"}, 400
        if (user_end - user_start) > 200:
            return True, {"error": "Range too large. Max 200 ports at once."}, 400

        existing_ports = {port["user_port"] for port in link.setdefault("ports", [])}
        added = 0
        for offset in range((user_end - user_start) + 1):
            current_user_port = user_start + offset
            current_target_port = target_start + offset
            if current_user_port not in existing_ports:
                link["ports"].append({"user_port": current_user_port, "target_port": current_target_port})
                added += 1
        save_db()
        log_event("panel", "info", f"Mapped {added} ports from range {user_port_text} -> {target_port_text} in tunnel '{link['name']}'.")
        return True, {"success": True, "added": added}, 200

    return False, {}, 404


def dispatch_links_delete(
    path: str,
    query: dict[str, list[str]],
    *,
    db_data: dict[str, Any],
    save_db: Callable[[], Any],
    log_event: Callable[[str, str, str], Any],
) -> tuple[bool, dict[str, Any], int]:
    if path == "/api/links":
        link_id = query.get("id", [""])[0]
        if link_id not in db_data.get("links", {}):
            return True, {"error": "Link not found"}, 404
        link = db_data["links"].pop(link_id)
        save_db()
        log_event("panel", "info", f"Deleted tunnel link '{link['name']}'.")
        return True, {"success": True}, 200

    if path == "/api/links/ports":
        link_id = query.get("id", [""])[0]
        try:
            index = int(query.get("index", ["-1"])[0])
        except Exception:
            index = -1
        if link_id not in db_data.get("links", {}):
            return True, {"error": "Link not found"}, 404
        link = db_data["links"][link_id]
        if not (0 <= index < len(link.get("ports", []))):
            return True, {"error": "Invalid mapping index"}, 400
        removed = link["ports"].pop(index)
        save_db()
        log_event("panel", "info", f"Removed port mapping {removed['user_port']} -> {removed['target_port']} from tunnel '{link['name']}'.")
        return True, {"success": True}, 200

    return False, {}, 404
