"""Panel/node semantic-version compatibility helpers."""

from __future__ import annotations

import re
import time
from typing import Any


def version_tuple(value: str) -> tuple[int, int, int]:
    parts = [int(item) for item in re.findall(r"\d+", str(value or ""))[:3]]
    return tuple((parts + [0, 0, 0])[:3])


def node_version_status(
    nodes: dict[str, dict[str, Any]],
    panel_version: str,
    panel_build: str,
    *,
    node_id: str = "",
    online_window: float = 45.0,
) -> dict[str, Any]:
    panel_tuple = version_tuple(panel_version)
    now = time.time()
    items: dict[str, dict[str, Any]] = {}
    for current_id, node in nodes.items():
        if node_id and current_id != node_id:
            continue
        stats = node.get("stats") or {}
        version = str(stats.get("app_version") or "")
        build = str(stats.get("app_build") or "")
        current_tuple = version_tuple(version)
        online = node.get("status") == "online" and now - float(node.get("last_seen") or 0) <= online_window
        same_release = current_tuple == panel_tuple
        same_build = same_release and build == panel_build
        compatible = bool(version) and current_tuple[:2] == panel_tuple[:2]
        if not version:
            state = "unknown"
            reason = "Node has not reported an application version."
        elif current_tuple > panel_tuple:
            state = "ahead"
            reason = "Node is newer than the panel."
        elif not compatible:
            state = "incompatible"
            reason = "Node major/minor release differs from the panel."
        elif not same_release:
            state = "outdated"
            reason = "Node patch version is older than the panel."
        elif not same_build:
            state = "build_mismatch"
            reason = "Version matches but the runtime build differs."
        else:
            state = "current"
            reason = "Node version and build match the panel."
        items[current_id] = {
            "node_id": current_id,
            "name": node.get("name", current_id),
            "online": online,
            "node_version": version,
            "node_build": build,
            "panel_version": panel_version,
            "panel_build": panel_build,
            "compatible": compatible,
            "up_to_date": same_build,
            "state": state,
            "reason": reason,
        }
    return {
        "success": True,
        "checked_at": now,
        "panel_version": panel_version,
        "panel_build": panel_build,
        "summary": {
            "total": len(items),
            "online": sum(1 for item in items.values() if item["online"]),
            "current": sum(1 for item in items.values() if item["state"] == "current"),
            "outdated": sum(1 for item in items.values() if item["state"] in {"outdated", "build_mismatch"}),
            "incompatible": sum(1 for item in items.values() if item["state"] in {"incompatible", "ahead", "unknown"}),
        },
        "nodes": items,
    }
