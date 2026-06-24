"""Runtime monitoring API dispatchers for P00RIJA TUNNEL."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


TARGET_NODE_VERSION = "1.9.95"


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except Exception:
        return default


def _node_reported_version(node: dict[str, Any]) -> str:
    stats = node.get("stats") or {}
    direct = str(stats.get("app_version") or stats.get("version") or "").strip()
    if direct:
        return direct
    last = node.get("last_command_result") or {}
    if last.get("type") == "node_update":
        result = last.get("result") or {}
        return str(result.get("version") or "").strip()
    return ""


def _score_level(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 55:
        return "normal"
    return "poor"


def _build_runtime_intelligence(
    *,
    node_resources: list[dict[str, Any]],
    link_resources: list[dict[str, Any]],
    threads: int,
    sessions: int,
    rss_kb: int,
) -> dict[str, Any]:
    online_nodes = [n for n in node_resources if n.get("status") == "online"]
    version_unknown = [n for n in node_resources if not n.get("app_version")]
    version_drift = [
        n for n in node_resources
        if n.get("app_version") and n.get("app_version") != TARGET_NODE_VERSION
    ]
    version_ok = [
        n for n in node_resources
        if n.get("app_version") == TARGET_NODE_VERSION
    ]

    link_scores: list[dict[str, Any]] = []
    for link in link_resources:
        score = 100
        reasons: list[str] = []
        if link.get("paused"):
            score -= 20
            reasons.append("paused")
        if not link.get("running"):
            score -= 45
            reasons.append("not_running")
        if int(link.get("sessions") or 0) == 0:
            score -= 8
            reasons.append("no_active_session")
        if int(link.get("ready_workers") or 0) < max(1, int(link.get("desired_workers") or 1)):
            score -= 12
            reasons.append("low_ready_workers")
        if int(link.get("thread_pressure") or 0) >= 160:
            score -= 18
            reasons.append("thread_pressure")
        if link.get("action") not in ("ok", ""):
            score -= 8
            reasons.append(str(link.get("action")))
        score = max(0, min(100, score))
        link_scores.append({
            "id": link.get("id"),
            "name": link.get("name"),
            "score": score,
            "level": _score_level(score),
            "reasons": reasons[:4],
        })

    avg_sla = round(sum(item["score"] for item in link_scores) / len(link_scores), 1) if link_scores else 100.0
    max_cpu = max([_num(n.get("cpu")) for n in online_nodes] or [0.0])
    max_ram = max([_num(n.get("ram")) for n in online_nodes] or [0.0])
    max_node_threads = max([_num(n.get("threads")) for n in online_nodes] or [0.0])
    rss_mb = round((rss_kb or 0) / 1024, 1)
    risk_score = int(min(100, max(max_cpu, max_ram, threads / 4, max_node_threads / 2, rss_mb / 4)))
    risk_level = _score_level(100 - risk_score)

    recommendations: list[dict[str, Any]] = []
    if version_drift or version_unknown:
        recommendations.append({
            "id": "sync_node_versions",
            "label": "Sync node versions",
            "label_fa": "هماهنگ‌سازی نسخه نودها",
            "action": "node_update",
            "severity": "poor" if version_drift else "normal",
            "detail": f"{len(version_drift)} drift, {len(version_unknown)} unknown",
        })
    if risk_score >= 65:
        recommendations.append({
            "id": "reduce_runtime_pressure",
            "label": "Reduce runtime pressure",
            "label_fa": "کاهش فشار Runtime",
            "action": "pressure",
            "severity": "poor",
            "detail": f"risk={risk_score}",
        })
    idle_links = [l for l in link_resources if l.get("action") == "reap_idle_reserve"]
    if idle_links:
        recommendations.append({
            "id": "reap_idle_reserves",
            "label": "Reap idle reserves",
            "label_fa": "پاک‌سازی رزروهای idle",
            "action": "thread_guard",
            "severity": "normal",
            "detail": f"{len(idle_links)} tunnel(s)",
        })
    unhealthy = [item for item in link_scores if item["score"] < 80]
    if unhealthy:
        recommendations.append({
            "id": "check_tunnel_sla",
            "label": "Review tunnel SLA",
            "label_fa": "بررسی SLA تانل‌ها",
            "action": "inspect",
            "severity": "normal",
            "detail": f"{len(unhealthy)} below 80",
        })
    if not recommendations:
        recommendations.append({
            "id": "all_clear",
            "label": "Everything is aligned",
            "label_fa": "همه چیز هماهنگ است",
            "action": "none",
            "severity": "good",
            "detail": "no immediate action",
        })

    transport_radar = [
        {
            "id": "masque_connect_udp",
            "name": "MASQUE / CONNECT-UDP",
            "level": "research",
            "why": "HTTP/3 UDP/IP tunneling path for QUIC-like transport profiles.",
        },
        {
            "id": "quic_reverse_mux",
            "name": "QUIC reverse multiplexing",
            "level": "candidate",
            "why": "Low-latency bidirectional reverse tunnels with stream multiplexing.",
        },
        {
            "id": "wireguard_quic_wrap",
            "name": "WireGuard over QUIC/MASQUE",
            "level": "candidate",
            "why": "UDP tunnel wrapping for networks that interfere with raw WireGuard.",
        },
        {
            "id": "yamux_smart_pool",
            "name": "Yamux/smux adaptive pool",
            "level": "candidate",
            "why": "Fewer idle workers by multiplexing many streams on fewer connections.",
        },
        {
            "id": "http3_loadbalanced_reverse",
            "name": "HTTP/3 load-balanced reverse tunnel",
            "level": "research",
            "why": "Multiple edge nodes behind the same reverse tunnel identity.",
        },
    ]

    return {
        "target_version": TARGET_NODE_VERSION,
        "version_sync": {
            "ok": len(version_ok),
            "drift": len(version_drift),
            "unknown": len(version_unknown),
            "online": len(online_nodes),
            "nodes": [
                {
                    "id": n.get("id"),
                    "name": n.get("name"),
                    "status": n.get("status"),
                    "version": n.get("app_version") or "unknown",
                    "aligned": n.get("app_version") == TARGET_NODE_VERSION,
                }
                for n in node_resources
            ],
        },
        "sla": {
            "score": avg_sla,
            "level": _score_level(int(avg_sla)),
            "links": sorted(link_scores, key=lambda item: item["score"])[:6],
        },
        "resource_risk": {
            "score": risk_score,
            "level": risk_level,
            "threads": threads,
            "sessions": sessions,
            "rss_mb": rss_mb,
            "max_cpu": round(max_cpu, 1),
            "max_ram": round(max_ram, 1),
        },
        "recommendations": recommendations[:5],
        "transport_radar": transport_radar,
    }


def dispatch_runtime_get(
    path: str,
    *,
    db_data: dict[str, Any],
    get_all_process_snapshot: Callable[[], list[dict[str, Any]]],
    get_all_thread_snapshot: Callable[[], list[dict[str, Any]]] | None,
    list_all_runtime_sessions: Callable[[], list[dict[str, Any]]],
    runtime_session_summary: Callable[[], dict[str, Any]] | None,
    thread_count: Callable[[], int],
    get_own_rss_kb: Callable[[], int],
) -> tuple[bool, dict[str, Any], int]:
    if path == "/api/runtime/processes":
        return True, {"processes": get_all_process_snapshot()}, 200

    if path == "/api/runtime/threads":
        threads = get_all_thread_snapshot() if get_all_thread_snapshot else []
        return True, {"threads": threads, "count": len(threads)}, 200

    if path == "/api/runtime/sessions":
        return True, {"sessions": list_all_runtime_sessions(), "threads": thread_count()}, 200

    if path == "/api/runtime/resources":
        session_summary = runtime_session_summary() if runtime_session_summary else {}
        sessions_by_link: dict[str, int] = dict(session_summary.get("by_link") or {})
        active_sessions = int(session_summary.get("total") or 0)
        if not runtime_session_summary:
            all_sessions = list_all_runtime_sessions()
            active_sessions = len(all_sessions)
            for session in all_sessions:
                lid = str(session.get("link_id") or "")
                if lid:
                    sessions_by_link[lid] = sessions_by_link.get(lid, 0) + 1
        now = time.time()
        node_resources: list[dict[str, Any]] = []
        node_threads = 0
        nodes = db_data.get("nodes", {})
        for node_id, node in db_data.get("nodes", {}).items():
            online = node.get("status") == "online" and now - node.get("last_seen", 0) <= 30
            stats = node.get("stats") or {}
            if online:
                try:
                    node_threads += int(stats.get("threads") or 0)
                except Exception:
                    pass
            node_resources.append({
                "id": node_id,
                "name": node.get("name", node_id),
                "role": node.get("role", node.get("type", "")),
                "status": "online" if online else "offline",
                "app_version": _node_reported_version(node),
                "app_build": str(stats.get("app_build") or ""),
                "cpu": stats.get("cpu", 0),
                "ram": stats.get("ram", 0),
                "rx_speed": stats.get("rx_speed", 0),
                "tx_speed": stats.get("tx_speed", 0),
                "threads": stats.get("threads", 0),
                "connections": stats.get("connections", 0),
                "last_command_result": node.get("last_command_result"),
            })
        link_resources: list[dict[str, Any]] = []
        for link_id, link in db_data.get("links", {}).items():
            internal_id = link.get("internal_node_id", link.get("iran_node_id", ""))
            external_id = link.get("external_node_id", link.get("foreign_node_id", ""))
            direction = link.get("direction", "external_to_internal")
            server_id = internal_id if direction == "external_to_internal" else external_id
            client_id = external_id if direction == "external_to_internal" else internal_id
            server = nodes.get(server_id, {})
            client = nodes.get(client_id, {})
            server_status = ((server.get("stats") or {}).get("link_statuses") or {}).get(link_id, {})
            client_status = ((client.get("stats") or {}).get("link_statuses") or {}).get(link_id, {})
            server_guard = server_status.get("thread_guardian") or {}
            client_guard = client_status.get("thread_guardian") or {}
            desired = client_status.get("desired_workers", server_status.get("desired_workers", 0)) or 0
            max_workers = client_status.get("max_workers", server_status.get("max_workers", 0)) or 0
            ready = client_status.get("ready_workers", server_status.get("pool_available", 0)) or 0
            alive = client_status.get("worker_threads_alive", 0) or 0
            reaped = (client_status.get("idle_workers_reaped", 0) or 0) + (server_status.get("idle_workers_reaped", 0) or 0)
            pressure = client_guard.get("thread_pressure", server_guard.get("thread_pressure", 0)) or 0
            running = bool(server_status.get("running")) or bool(client_status.get("running"))
            action = "ok"
            if link.get("paused"):
                action = "paused"
            elif not running:
                action = "start_or_check_nodes"
            elif sessions_by_link.get(link_id, 0) == 0 and int(ready or 0) > int(desired or 0):
                action = "reap_idle_reserve"
            elif int(pressure or 0) >= 160:
                action = "reduce_thread_pressure"
            elif link.get("engine", "builtin") != "builtin":
                action = "engine_process_watch"
            link_resources.append({
                "id": link_id,
                "name": link.get("name", link_id),
                "engine": link.get("engine", "builtin"),
                "mode": link.get("tunnel_mode", link.get("transport", "tcp")),
                "direction": direction,
                "paused": bool(link.get("paused")),
                "server_node": server.get("name", server_id),
                "client_node": client.get("name", client_id),
                "running": running,
                "sessions": sessions_by_link.get(link_id, 0),
                "desired_workers": desired,
                "max_workers": max_workers,
                "ready_workers": ready,
                "worker_threads_alive": alive,
                "idle_workers_reaped": reaped,
                "thread_pressure": pressure,
                "action": action,
            })
        total_threads = thread_count() + node_threads
        rss_kb = get_own_rss_kb()
        return True, {
            "threads": total_threads,
            "active_tunnel_sessions": active_sessions,
            "rss_kb": rss_kb,
            "nodes": node_resources,
            "links": link_resources,
            "intelligence": _build_runtime_intelligence(
                node_resources=node_resources,
                link_resources=link_resources,
                threads=total_threads,
                sessions=active_sessions,
                rss_kb=rss_kb,
            ),
        }, 200

    return False, {}, 404
