"""API route registry for the P00RIJA TUNNEL panel.

This module is intentionally declarative for now. It gives the monolithic HTTP
handler a stable contract to migrate toward without changing existing routes.
"""

from __future__ import annotations

import csv
import hmac
import io
import re
import secrets
import subprocess
import time
import uuid
from collections.abc import Callable
from typing import Any


API_ROUTE_GROUPS: dict[str, dict[str, Any]] = {
    "public": {
        "description": "Unauthenticated browser bootstrap and login metadata.",
        "routes": {
            "GET": ["/api/public-settings"],
            "POST": ["/api/login"],
        },
    },
    "node": {
        "description": "Node enrollment, polling, command reports, runtime config, and remote update packages.",
        "routes": {
            "GET": ["/api/node-config", "/api/node-update-package"],
            "POST": ["/api/report", "/api/node-command-result", "/api/nodes/register"],
        },
    },
    "dashboard": {
        "description": "Authenticated panel state, logs, and operational snapshots.",
        "routes": {
            "GET": ["/api/status", "/api/logs", "/api/logs/csv"],
        },
    },
    "nodes": {
        "description": "Node management, SSH access, health checks, pause/resume, and secrets.",
        "routes": {
            "GET": ["/api/nodes/secrets", "/api/nodes/test", "/api/nodes/toggle-pause", "/api/nodes/version-check"],
            "POST": [
                "/api/nodes",
                "/api/nodes/edit",
                "/api/nodes/auto",
                "/api/nodes/reorder",
                "/api/nodes/panel-local",
                "/api/nodes/ssh/save",
                "/api/nodes/ssh/start",
                "/api/nodes/ssh/write",
                "/api/nodes/ssh/read",
                "/api/nodes/ssh/close",
                "/api/nodes/ssh/run",
                "/api/nodes/update",
            ],
            "DELETE": ["/api/nodes"],
        },
    },
    "links": {
        "description": "Tunnel creation, live tests, payload tests, ports, and engine config previews.",
        "routes": {
            "GET": [
                "/api/links/test",
                "/api/links/payload-test",
                "/api/links/engine-config",
                "/api/links/toggle-pause",
            ],
            "POST": [
                "/api/links",
                "/api/links/next-ports",
                "/api/links/smart-test",
                "/api/links/payload-test",
                "/api/links/reorder",
                "/api/links/categories/reorder",
                "/api/ports",
                "/api/ports/range",
                "/api/sync-xui",
            ],
            "DELETE": ["/api/links", "/api/ports"],
        },
    },
    "profiles_engines": {
        "description": "Tunnel profiles, engine health, engine process control, and binary upload.",
        "routes": {
            "GET": ["/api/engines/health", "/api/engines/check-updates"],
            "POST": [
                "/api/profiles",
                "/api/profiles/import",
                "/api/engines/health",
                "/api/engines/control",
                "/api/engines/upload",
                "/api/engine/update",
                "/api/engines/check-updates",
            ],
        },
    },
    "runtime_system": {
        "description": "Runtime sessions, process/resource monitor, optimization, settings, certificates, and audits.",
        "routes": {
            "GET": [
                "/api/runtime/processes",
                "/api/runtime/threads",
                "/api/runtime/sessions",
                "/api/runtime/resources",
                "/api/system/audit",
                "/api/system/routes",
                "/api/speedtest/status",
            ],
            "POST": [
                "/api/runtime/optimize",
                "/api/settings",
                "/api/security",
                "/api/certificates/local",
                "/api/certificates/generate",
                "/api/settings/restart",
                "/api/settings/panel-ports",
                "/api/settings/panel-path",
                "/api/speedtest/start",
                "/api/speedtest/install",
            ],
            "DELETE": ["/api/runtime/sessions", "/api/runtime/processes"],
        },
    },
    "backup_migration": {
        "description": "Encrypted backup creation, download, restore, and staged host migration.",
        "routes": {
            "GET": ["/api/backup/list", "/api/backup/download"],
            "POST": [
                "/api/backup/create",
                "/api/backup/restore",
                "/api/backup/restore-upload",
                "/api/migration/start",
            ],
        },
    },
    "host_control": {
        "description": "Privileged host operations bridged through the local filesystem agent.",
        "routes": {
            "GET": ["/api/host-control/status"],
            "POST": [],
        },
    },
}


def iter_routes() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for group_id, group in API_ROUTE_GROUPS.items():
        for method, routes in group.get("routes", {}).items():
            for route in routes:
                rows.append({
                    "group": group_id,
                    "method": method,
                    "path": route,
                    "description": group.get("description", ""),
                })
    return rows


def describe_api_surface() -> dict[str, Any]:
    routes = iter_routes()
    methods: dict[str, int] = {}
    for item in routes:
        methods[item["method"]] = methods.get(item["method"], 0) + 1
    return {
        "groups": API_ROUTE_GROUPS,
        "routes": routes,
        "route_count": len(routes),
        "methods": methods,
        "migration_status": "link_lifecycle_runtime_dispatch_ready",
        "next_step": "Move runtime optimization and settings route groups out of P00RIJAHTTPHandler.",
    }


def is_registered_route(method: str, path: str) -> bool:
    method = method.upper()
    return any(item["method"] == method and item["path"] == path for item in iter_routes())


def build_public_settings(settings: dict[str, Any], *, app_version: str, app_license: str) -> dict[str, Any]:
    return {
        "version": app_version,
        "license": app_license,
        "two_factor_enabled": settings.get("two_factor_enabled", False),
        "biometric_enabled": settings.get("biometric_enabled", False),
        "panel_tls": True,
        "https_required": True,
    }


def build_system_audit_response(
    *,
    audit_builder: Callable[..., dict[str, Any]] | None,
    root: str,
    config_dir: str,
    engines_dir: str,
    db_data: dict[str, Any],
    engine_catalog: dict[str, dict[str, Any]],
    app_version: str,
) -> dict[str, Any]:
    if audit_builder:
        payload = audit_builder(
            root=root,
            config_dir=config_dir,
            engines_dir=engines_dir,
            db_data=db_data,
            engine_catalog=engine_catalog,
            app_version=app_version,
        )
    else:
        payload = {
            "version": app_version,
            "score": 40,
            "root": root,
            "recommendations": ["p00rija_core.system_audit is not available in this installation."],
            "capabilities": [{"id": "system_audit", "ready": False, "label": "Modularity and readiness audit"}],
        }
    payload["api_surface"] = describe_api_surface()
    return payload


def dispatch_public_system_get(
    path: str,
    *,
    settings: dict[str, Any],
    app_version: str,
    app_license: str,
    root: str,
    config_dir: str,
    engines_dir: str,
    db_data: dict[str, Any],
    engine_catalog: dict[str, dict[str, Any]],
    audit_builder: Callable[..., dict[str, Any]] | None,
) -> tuple[bool, dict[str, Any], int]:
    if path == "/api/public-settings":
        return True, build_public_settings(settings, app_version=app_version, app_license=app_license), 200
    if path == "/api/system/routes":
        return True, describe_api_surface(), 200
    if path == "/api/system/audit":
        return True, build_system_audit_response(
            audit_builder=audit_builder,
            root=root,
            config_dir=config_dir,
            engines_dir=engines_dir,
            db_data=db_data,
            engine_catalog=engine_catalog,
            app_version=app_version,
        ), 200
    return False, {}, 404


def refresh_dashboard_nodes(
    db_data: dict[str, Any],
    *,
    ensure_tunnel_profiles: Callable[[], tuple[dict[str, Any], bool]],
    refresh_node_ping_async: Callable[[str, dict[str, Any]], Any],
    save_db: Callable[[], Any],
) -> dict[str, Any]:
    now = time.time()
    tunnel_profiles, profiles_changed = ensure_tunnel_profiles()
    structure_changed = False
    for index, (node_id, node) in enumerate(db_data.get("nodes", {}).items()):
        if "display_order" not in node:
            node["display_order"] = index
            structure_changed = True
        if not node.get("category"):
            node["category"] = "Panel" if node.get("is_panel_node") else str(node.get("role") or "Nodes").title()
            structure_changed = True
        tags = list(node.get("tags") or [])
        for tag in (str(node.get("role") or ""), "node"):
            if tag and tag not in tags:
                tags.append(tag)
                structure_changed = True
        node["tags"] = tags[:8]
        if node.get("status") == "online" and now - node.get("last_seen", 0) > 30:
            node["status"] = "offline"
        if not node.get("paused") and node.get("ip"):
            refresh_node_ping_async(node_id, node)
    if profiles_changed or structure_changed:
        save_db()
    return tunnel_profiles


def build_dashboard_status(
    db_data: dict[str, Any],
    *,
    app_version: str,
    app_build: str,
    app_license: str,
    author_github: str,
    author_email: str,
    sanitize_nodes_for_status: Callable[[dict[str, Any]], dict[str, Any]],
    list_engine_status: Callable[[], dict[str, Any]],
    load_ssh_vault: Callable[[], dict[str, Any]],
    sanitize_ssh_credential: Callable[[dict[str, Any]], dict[str, Any]],
    list_all_runtime_sessions: Callable[[], list[dict[str, Any]]],
    get_host_info: Callable[[], dict[str, Any]],
    ensure_tunnel_profiles: Callable[[], tuple[dict[str, Any], bool]],
    refresh_node_ping_async: Callable[[str, dict[str, Any]], Any],
    save_db: Callable[[], Any],
) -> dict[str, Any]:
    settings = db_data.get("settings", {})
    tunnel_profiles = refresh_dashboard_nodes(
        db_data,
        ensure_tunnel_profiles=ensure_tunnel_profiles,
        refresh_node_ping_async=refresh_node_ping_async,
        save_db=save_db,
    )
    links_changed = False
    for index, link in enumerate(db_data.get("links", {}).values()):
        if "display_order" not in link:
            link["display_order"] = index
            links_changed = True
        if not link.get("category"):
            link["category"] = f"{link.get('engine', 'builtin')} / {link.get('tunnel_mode', 'tcp')}"
            links_changed = True
    if links_changed:
        save_db()
    return {
        "nodes": sanitize_nodes_for_status(db_data.get("nodes", {})),
        "links": db_data.get("links", {}),
        "logs": db_data.get("logs", []),
        "admin_username": db_data.get("admin", {}).get("username", "admin"),
        "panel_tls": True,
        "cert_path": settings.get("cert_path", ""),
        "key_path": settings.get("key_path", ""),
        "panel_host": settings.get("panel_host", ""),
        "panel_port": settings.get("port", 8080),
        "api_port": settings.get("api_port", 8000),
        "hidden_panel_path_enabled": bool(settings.get("hidden_panel_path_enabled", False)),
        "hidden_panel_path": settings.get("hidden_panel_path", ""),
        "version": app_version,
        "build": app_build,
        "capabilities": {
            "payload_test": True,
            "payload_test_client": True,
            "direct_bridge_fallback": True,
            "link_runtime_health": True,
            "remote_node_update": True,
            "smart_thread_guardian": True,
            "idle_reserve_reaper": True,
            "per_link_worker_telemetry": True,
            "runtime_intelligence": True,
            "node_version_drift_detection": True,
            "tunnel_sla_scoring": True,
            "auto_guardian_scheduler": True,
            "transport_radar_2026": True,
            "host_control_agent": True,
            "panel_port_management": True,
            "local_panel_node": True,
            "dns01_wildcard_acme": True,
            "ech_config_export": True,
            "masque_connect_udp": True,
            "masque_connect_ip_config": True,
            "masque_connect_ip_runtime": "capability-gated",
            "xhttp_reality_adaptive": True,
            "adaptive_smux": True,
            "tcp_brutal_capability_detection": True,
            "node_link_ordering": True,
        },
        "license": app_license,
        "author_github": author_github,
        "author_email": author_email,
        "two_factor_enabled": settings.get("two_factor_enabled", False),
        "biometric_enabled": settings.get("biometric_enabled", False),
        "disable_ipv6": settings.get("disable_ipv6", False),
        "engine_restart_interval": settings.get("engine_restart_interval", 0),
        "tunnel_profiles": tunnel_profiles,
        "link_category_order": settings.get("link_category_order", []),
        "engines": list_engine_status(),
        "ssh_saved_nodes": {
            node_id: sanitize_ssh_credential(credential)
            for node_id, credential in load_ssh_vault().get("nodes", {}).items()
        },
        "runtime_sessions": list_all_runtime_sessions(),
        "host_info": get_host_info(),
    }


def build_logs_csv(logs: list[dict[str, Any]]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Source", "Level", "Message"])
    for entry in logs:
        writer.writerow([
            entry.get("timestamp", ""),
            entry.get("source", ""),
            entry.get("level", ""),
            entry.get("message", ""),
        ])
    return output.getvalue().encode("utf-8")


def dispatch_dashboard_get(
    path: str,
    *,
    db_data: dict[str, Any],
    app_version: str,
    app_build: str,
    app_license: str,
    author_github: str,
    author_email: str,
    sanitize_nodes_for_status: Callable[[dict[str, Any]], dict[str, Any]],
    list_engine_status: Callable[[], dict[str, Any]],
    load_ssh_vault: Callable[[], dict[str, Any]],
    sanitize_ssh_credential: Callable[[dict[str, Any]], dict[str, Any]],
    list_all_runtime_sessions: Callable[[], list[dict[str, Any]]],
    get_host_info: Callable[[], dict[str, Any]],
    ensure_tunnel_profiles: Callable[[], tuple[dict[str, Any], bool]],
    refresh_node_ping_async: Callable[[str, dict[str, Any]], Any],
    save_db: Callable[[], Any],
) -> tuple[bool, Any, int, dict[str, str]]:
    if path == "/api/status":
        return True, build_dashboard_status(
            db_data,
            app_version=app_version,
            app_build=app_build,
            app_license=app_license,
            author_github=author_github,
            author_email=author_email,
            sanitize_nodes_for_status=sanitize_nodes_for_status,
            list_engine_status=list_engine_status,
            load_ssh_vault=load_ssh_vault,
            sanitize_ssh_credential=sanitize_ssh_credential,
            list_all_runtime_sessions=list_all_runtime_sessions,
            get_host_info=get_host_info,
            ensure_tunnel_profiles=ensure_tunnel_profiles,
            refresh_node_ping_async=refresh_node_ping_async,
            save_db=save_db,
        ), 200, {}
    if path == "/api/logs":
        return True, db_data.get("logs", []), 200, {}
    if path == "/api/logs/csv":
        return True, build_logs_csv(db_data.get("logs", [])), 200, {
            "Content-Type": "text/csv",
            "Content-Disposition": 'attachment; filename="p00rija_logs.csv"',
        }
    return False, None, 404, {}


def build_node_secrets(db_data: dict[str, Any], node_id: str) -> tuple[dict[str, Any], int]:
    node = db_data.get("nodes", {}).get(node_id)
    if not node:
        return {"error": "Node not found"}, 404
    return {
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
        ]),
    }, 200


def toggle_node_pause(db_data: dict[str, Any], node_id: str, *, save_db: Callable[[], Any]) -> tuple[dict[str, Any], int]:
    if not node_id or node_id not in db_data.get("nodes", {}):
        return {"error": "Node not found"}, 404
    node = db_data["nodes"][node_id]
    node["paused"] = not node.get("paused", False)
    save_db()
    return {"success": True, "paused": node["paused"]}, 200


def test_node_connectivity(db_data: dict[str, Any], node_id: str, *, save_db: Callable[[], Any]) -> tuple[dict[str, Any], int]:
    if not node_id or node_id not in db_data.get("nodes", {}):
        return {"error": "Node not found"}, 404
    node = db_data["nodes"][node_id]
    ip = node.get("ip")
    if not ip:
        return {"error": "No IP assigned to node"}, 400
    try:
        cmd1 = ["ping", "-c", "3", "-W", "2", ip]
        res1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=8)
        out = f"==== Node Connection ({ip}) ====\n{res1.stdout}{res1.stderr}\n"

        if res1.returncode == 0:
            lines = [line for line in res1.stdout.split("\n") if "time=" in line or "avg" in line]
            if lines:
                ms_match = re.search(r"time=([\d.]+)", lines[0])
                if ms_match:
                    node.setdefault("stats", {})["ping_ms"] = float(ms_match.group(1))
                    save_db()

        cmd2 = ["ping", "-c", "3", "-W", "2", "1.1.1.1"]
        res2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=8)
        out += f"\n==== Internet Connection (1.1.1.1) ====\n{res2.stdout}{res2.stderr}"
        return {"success": True, "result": out.strip()}, 200
    except FileNotFoundError:
        return {"error": "Ping command not found on server"}, 500
    except Exception as exc:
        return {"error": f"Ping error: {exc}"}, 500


def dispatch_nodes_get(
    path: str,
    query: dict[str, list[str]],
    *,
    db_data: dict[str, Any],
    save_db: Callable[[], Any],
) -> tuple[bool, dict[str, Any], int]:
    node_id = query.get("id", [""])[0]
    if path == "/api/nodes/secrets":
        payload, status = build_node_secrets(db_data, node_id)
        return True, payload, status
    if path == "/api/nodes/toggle-pause":
        payload, status = toggle_node_pause(db_data, node_id, save_db=save_db)
        return True, payload, status
    if path == "/api/nodes/test":
        payload, status = test_node_connectivity(db_data, node_id, save_db=save_db)
        return True, payload, status
    return False, {}, 404


def _clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(value)
    except Exception:
        return default
    return max(minimum, min(maximum, value))


def dispatch_node_ssh_request(
    path: str,
    body: dict[str, Any],
    *,
    db_data: dict[str, Any],
    load_ssh_vault: Callable[[], dict[str, Any]],
    save_ssh_vault: Callable[[dict[str, Any]], Any],
    sanitize_ssh_credential: Callable[[dict[str, Any]], dict[str, Any]],
    prune_ssh_sessions: Callable[[], Any],
    start_ssh_session: Callable[[str, dict[str, Any]], tuple[str, str, bool, dict[str, Any]]],
    write_ssh_session: Callable[[str, str], Any],
    read_ssh_session_output: Callable[..., tuple[str, bool]],
    cleanup_ssh_session: Callable[[str], Any],
    execute_ssh_command: Callable[[dict[str, Any], str], dict[str, Any]],
    log_event: Callable[[str, str, str], Any],
) -> tuple[bool, dict[str, Any], int]:
    if path == "/api/nodes/ssh/save":
        try:
            node_id = body.get("node_id")
            if node_id not in db_data.get("nodes", {}):
                return True, {"error": "Node not found"}, 404
            vault = load_ssh_vault()
            vault.setdefault("nodes", {})[node_id] = {
                "host": str(body.get("host") or db_data["nodes"][node_id].get("ip", ""))[:255],
                "port": _clamp_int(body.get("port", 22), 22, 1, 65535),
                "username": str(body.get("username") or "root")[:80],
                "auth_method": body.get("auth_method", "password") if body.get("auth_method") in ("password", "key") else "password",
                "password": str(body.get("password") or "")[:1000],
                "private_key": str(body.get("private_key") or "")[:20000],
                "timeout": _clamp_int(body.get("timeout", 15), 15, 3, 120),
                "saved_at": time.time(),
            }
            save_ssh_vault(vault)
            log_event("panel", "info", f"Saved encrypted SSH profile for node '{db_data['nodes'][node_id].get('name', node_id)}'.")
            return True, {"success": True, "credential": sanitize_ssh_credential(vault["nodes"][node_id])}, 200
        except Exception as exc:
            return True, {"error": f"SSH save failed: {exc}"}, 400

    if path == "/api/nodes/ssh/start":
        try:
            prune_ssh_sessions()
            node_id = body.get("node_id")
            if node_id not in db_data.get("nodes", {}):
                return True, {"error": "Node not found"}, 404
            session_id, output, alive, credential = start_ssh_session(node_id, body)
            log_event("panel", "info", f"Started interactive SSH terminal for node '{db_data['nodes'][node_id].get('name', node_id)}'.")
            return True, {"success": True, "session_id": session_id, "output": output, "alive": alive, "credential": credential}, 200
        except Exception as exc:
            return True, {"error": f"SSH terminal start failed: {exc}"}, 400

    if path == "/api/nodes/ssh/write":
        try:
            session_id = body.get("session_id")
            write_ssh_session(session_id, body.get("data", ""))
            output, alive = read_ssh_session_output(session_id)
            return True, {"success": True, "output": output, "alive": alive}, 200
        except Exception as exc:
            return True, {"error": f"SSH terminal write failed: {exc}"}, 400

    if path == "/api/nodes/ssh/read":
        try:
            output, alive = read_ssh_session_output(body.get("session_id"))
            return True, {"success": True, "output": output, "alive": alive}, 200
        except Exception as exc:
            return True, {"error": f"SSH terminal read failed: {exc}"}, 400

    if path == "/api/nodes/ssh/close":
        try:
            cleanup_ssh_session(body.get("session_id"))
            return True, {"success": True}, 200
        except Exception as exc:
            return True, {"error": f"SSH terminal close failed: {exc}"}, 400

    if path == "/api/nodes/ssh/run":
        try:
            node_id = body.get("node_id")
            if node_id not in db_data.get("nodes", {}):
                return True, {"error": "Node not found"}, 404
            vault = load_ssh_vault()
            saved = vault.get("nodes", {}).get(node_id, {})
            cred = dict(saved)
            for key in ("host", "port", "username", "auth_method", "password", "private_key", "timeout"):
                if body.get(key) not in (None, ""):
                    cred[key] = body.get(key)
            if not cred.get("host"):
                cred["host"] = db_data["nodes"][node_id].get("ip", "")
            if body.get("save"):
                vault.setdefault("nodes", {})[node_id] = dict(cred, saved_at=time.time())
                save_ssh_vault(vault)
            result = execute_ssh_command(cred, body.get("command", "uname -a && uptime"))
            return True, {"success": result["success"], "result": result, "credential": sanitize_ssh_credential(cred)}, 200
        except Exception as exc:
            return True, {"error": f"SSH command failed: {exc}"}, 400

    return False, {}, 404


def _new_node_id() -> str:
    return f"node_{str(uuid.uuid4())[:8]}"


def _new_node_token() -> str:
    return f"tok_{secrets.token_hex(8)}"


def _store_node(
    db_data: dict[str, Any],
    *,
    node_id: str,
    name: str,
    role: str,
    ip: str,
    token: str,
    public_key: str,
    private_key: str,
    tags: list[str],
    category: str = "",
    display_order: int = 0,
) -> None:
    effective_tags = list(tags or [])
    for default_tag in (role, "node"):
        if default_tag and default_tag not in effective_tags:
            effective_tags.append(default_tag)
    db_data.setdefault("nodes", {})[node_id] = {
        "name": name,
        "role": role,
        "ip": ip,
        "token": token,
        "public_key": public_key,
        "private_key": private_key,
        "status": "offline",
        "last_seen": 0,
        "tags": effective_tags[:8],
        "category": str(category or "").strip()[:60],
        "display_order": int(display_order or 0),
        "stats": {},
    }


def dispatch_nodes_post(
    path: str,
    body: dict[str, Any],
    *,
    db_data: dict[str, Any],
    node_api_key: str,
    client_ip: str,
    normalize_role: Callable[[Any], str],
    normalize_tags: Callable[[Any], list[str]],
    make_node_keypair: Callable[[], tuple[str, str]],
    save_db: Callable[[], Any],
    log_event: Callable[[str, str, str], Any],
) -> tuple[bool, dict[str, Any], int]:
    if path == "/api/nodes":
        try:
            name = body.get("name")
            role = normalize_role(body.get("role"))
            ip = body.get("ip")
            tags = normalize_tags(body.get("tags"))
            category = str(body.get("category") or role or "").strip()[:60]
            display_order = max(
                [int(node.get("display_order", 0) or 0) for node in db_data.get("nodes", {}).values()] or [-1]
            ) + 1
            if not name or role not in ("internal", "external") or not ip:
                return True, {"error": "Missing parameters"}, 400
            if len(str(name)) > 80 or len(str(ip)) > 255:
                return True, {"error": "Invalid node name or IP"}, 400
            node_id = _new_node_id()
            node_token = _new_node_token()
            private_key, public_key = make_node_keypair()
            _store_node(
                db_data,
                node_id=node_id,
                name=name,
                role=role,
                ip=ip,
                token=node_token,
                public_key=public_key,
                private_key=private_key,
                tags=tags,
                category=category,
                display_order=display_order,
            )
            save_db()
            log_event("panel", "info", f"Registered new node '{name}' ({role.upper()}) at IP {ip}.")
            return True, {"success": True, "node_id": node_id, "token": node_token, "private_key": private_key, "public_key": public_key}, 200
        except Exception:
            return True, {"error": "Bad request"}, 400

    if path == "/api/nodes/edit":
        try:
            node_id = body.get("id")
            name = body.get("name")
            role = normalize_role(body.get("role"))
            ip = body.get("ip")
            tags = normalize_tags(body.get("tags"))
            if not node_id or node_id not in db_data.get("nodes", {}):
                return True, {"error": "Node not found"}, 404
            if not name or role not in ("internal", "external") or not ip:
                return True, {"error": "Missing parameters"}, 400
            node = db_data["nodes"][node_id]
            node["name"] = name
            node["role"] = role
            node["ip"] = ip
            node["tags"] = list(dict.fromkeys([*tags, role, "node"]))[:8]
            node["category"] = str(body.get("category") or node.get("category") or role).strip()[:60]
            save_db()
            log_event("panel", "info", f"Edited node '{name}' ({role.upper()}) at IP {ip}.")
            return True, {"success": True}, 200
        except Exception:
            return True, {"error": "Bad request"}, 400

    if path == "/api/nodes/register":
        try:
            api_key = body.get("api_key")
            expected_key = db_data.get("settings", {}).get("node_api_key") or node_api_key
            if not expected_key or not hmac.compare_digest(str(api_key or ""), str(expected_key)):
                return True, {"error": "Invalid node API key"}, 401
            name = body.get("name") or f"node-{str(uuid.uuid4())[:8]}"
            role = normalize_role(body.get("role"))
            ip = body.get("ip") or client_ip
            tags = normalize_tags(body.get("tags"))
            if role not in ("internal", "external"):
                return True, {"error": "Invalid node role"}, 400
            node_id = _new_node_id()
            node_token = _new_node_token()
            private_key, public_key = make_node_keypair()
            _store_node(
                db_data,
                node_id=node_id,
                name=str(name)[:80],
                role=role,
                ip=str(ip)[:255],
                token=node_token,
                public_key=public_key,
                private_key=private_key,
                tags=tags,
                category=str(body.get("category") or role).strip()[:60],
                display_order=max(
                    [int(node.get("display_order", 0) or 0) for node in db_data.get("nodes", {}).values()] or [-1]
                ) + 1,
            )
            save_db()
            log_event("panel", "info", f"Node self-registered as '{name}' ({role}).")
            return True, {"success": True, "node_id": node_id, "token": node_token, "private_key": private_key, "public_key": public_key}, 200
        except Exception as exc:
            return True, {"error": f"Bad request: {exc}"}, 400

    if path == "/api/nodes/auto":
        try:
            created = []
            existing_names = {node.get("name") for node in db_data.get("nodes", {}).values()}
            internal_idx = 1
            while f"INTERNAL-Node-{internal_idx}" in existing_names:
                internal_idx += 1
            external_idx = 1
            while f"EXTERNAL-Node-{external_idx}" in existing_names:
                external_idx += 1
            presets = [
                (f"INTERNAL-Node-{internal_idx}", "internal", "10.10.10.10"),
                (f"EXTERNAL-Node-{external_idx}", "external", "20.20.20.20"),
            ]
            for name, role, ip in presets:
                node_id = _new_node_id()
                node_token = _new_node_token()
                private_key, public_key = make_node_keypair()
                _store_node(
                    db_data,
                    node_id=node_id,
                    name=name,
                    role=role,
                    ip=ip,
                    token=node_token,
                    public_key=public_key,
                    private_key=private_key,
                    tags=[],
                    category=role,
                    display_order=max(
                        [int(node.get("display_order", 0) or 0) for node in db_data.get("nodes", {}).values()] or [-1]
                    ) + 1,
                )
                created.append({"node_id": node_id, "name": name, "role": role, "ip": ip, "token": node_token, "private_key": private_key, "public_key": public_key})
            save_db()
            log_event("panel", "info", f"Auto-registered {len(created)} starter nodes.")
            return True, {"success": True, "created": created}, 200
        except Exception as exc:
            return True, {"error": f"Bad request: {exc}"}, 400

    if path == "/api/nodes/reorder":
        order = body.get("order")
        if not isinstance(order, list):
            return True, {"error": "Node order must be a list"}, 400
        known = db_data.get("nodes", {})
        clean = [str(node_id) for node_id in order if str(node_id) in known]
        clean.extend(node_id for node_id in known if node_id not in clean)
        for index, node_id in enumerate(clean):
            known[node_id]["display_order"] = index
        save_db()
        log_event("panel", "info", f"Updated server display order for {len(clean)} node(s).")
        return True, {"success": True, "order": clean}, 200

    return False, {}, 404
