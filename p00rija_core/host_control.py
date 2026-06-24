"""Filesystem request bridge to the privileged P00RIJA host agent."""

from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any


def _root(config_dir: str) -> str:
    return os.path.join(config_dir, "host_control")


def host_control_available(config_dir: str) -> bool:
    root = _root(config_dir)
    heartbeat = os.path.join(root, "agent-heartbeat.json")
    try:
        data = json.loads(Path(heartbeat).read_text(encoding="utf-8"))
        return time.time() - float(data.get("timestamp", 0)) <= 10
    except Exception:
        return False


def host_control_status(config_dir: str, request_id: str) -> dict[str, Any]:
    safe_id = "".join(ch for ch in str(request_id or "") if ch.isalnum() or ch in "-_")[:80]
    if not safe_id:
        return {"success": False, "error": "Invalid host-control request ID"}
    path = os.path.join(_root(config_dir), "results", f"{safe_id}.json")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"success": True, "pending": True, "request_id": safe_id}
    except Exception as exc:
        return {"success": False, "error": f"Could not read host-control result: {exc}"}


def submit_host_control(
    config_dir: str,
    action: str,
    payload: dict[str, Any],
    *,
    wait_timeout: float = 0,
    delay_seconds: float = 0,
) -> dict[str, Any]:
    if action not in ("certificate", "panel_ports", "panel_node"):
        raise ValueError("Unsupported host-control action")
    if not host_control_available(config_dir):
        raise RuntimeError("P00RIJA host agent is not installed or not running")
    root = _root(config_dir)
    requests = os.path.join(root, "requests")
    results = os.path.join(root, "results")
    os.makedirs(requests, mode=0o700, exist_ok=True)
    os.makedirs(results, mode=0o700, exist_ok=True)
    request_id = f"{int(time.time())}-{secrets.token_hex(6)}"
    request = {
        "id": request_id,
        "action": action,
        "payload": payload,
        "created_at": time.time(),
        "not_before": time.time() + max(0, float(delay_seconds or 0)),
    }
    final_path = os.path.join(requests, f"{request_id}.json")
    temp_path = final_path + ".tmp"
    Path(temp_path).write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, final_path)
    if wait_timeout <= 0:
        return {"success": True, "queued": True, "pending": True, "request_id": request_id}
    deadline = time.time() + max(1, float(wait_timeout))
    while time.time() < deadline:
        result = host_control_status(config_dir, request_id)
        if not result.get("pending"):
            return result
        time.sleep(0.5)
    return {
        "success": False,
        "pending": True,
        "request_id": request_id,
        "error": "Host operation is still running; check its status again shortly",
    }
