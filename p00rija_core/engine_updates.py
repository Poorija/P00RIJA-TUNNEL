"""GitHub release and installed-version checks for tunnel engines."""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


GITHUB_API = "https://api.github.com"
USER_AGENT = "P00RIJA-TUNNEL-engine-update-checker"
_CACHE: dict[str, Any] = {"created_at": 0.0, "result": {}}
_CACHE_LOCK = threading.Lock()

RELEASE_SOURCES: dict[str, dict[str, Any]] = {
    "xray": {"repo": "XTLS/Xray-core"},
    "gost": {"repo": "go-gost/gost"},
    "backhaul": {"repo": "Musixal/Backhaul"},
    "rathole": {"repo": "rathole-org/rathole"},
    "chisel": {"repo": "jpillora/chisel"},
    "frp": {"repo": "fatedier/frp"},
    "hysteria2": {"repo": "apernet/hysteria"},
    "singbox": {"repo": "SagerNet/sing-box"},
    "masque": {"repo": "ferneast/masque-tunnel"},
    "naiveproxy": {"repo": "klzgrad/naiveproxy"},
    "shadowtls": {"repo": "ihciah/shadow-tls"},
    "brook": {"repo": "txthinking/brook"},
    "mieru": {"repo": "enfein/mieru"},
    "amneziawg": {"repo": "amnezia-vpn/amneziawg-tools"},
    "tuic": {
        "repo": "tuic-protocol/tuic",
        "release_prefixes": ("tuic-server-", "tuic-client-"),
    },
}

SYSTEM_SOURCES: dict[str, dict[str, str]] = {
    "wireguard": {"repo": "WireGuard/wireguard-tools", "manager": "apt"},
    "ssh": {"repo": "openssh/openssh-portable", "manager": "apt"},
    "stunnel": {"repo": "mtrojnar/stunnel", "manager": "apt"},
}

BUILTIN_ENGINES = {"muxquantum", "rawsock", "aead"}


def _request_json(url: str, timeout: float) -> tuple[Any, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        return json.loads(response.read().decode("utf-8")), headers


def _version_key(value: str) -> tuple[tuple[int, Any], ...]:
    text = str(value or "").lower().lstrip("v")
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in re.findall(r"\d+|[a-z]+", text)
    )


def _is_newer(latest: str, installed: str) -> bool:
    if not latest or not installed or installed in {"bundled", "system", "builtin"}:
        return False
    return _version_key(latest) > _version_key(installed)


def _check_release_engine(
    engine_id: str,
    source: dict[str, Any],
    installed: str,
    timeout: float,
) -> dict[str, Any]:
    repo = source["repo"]
    started = time.monotonic()
    if source.get("release_prefixes"):
        releases, headers = _request_json(f"{GITHUB_API}/repos/{repo}/releases?per_page=30", timeout)
        tags = []
        for prefix in source["release_prefixes"]:
            release = next(
                (
                    item for item in releases
                    if not item.get("draft")
                    and str(item.get("tag_name") or "").startswith(prefix)
                ),
                None,
            )
            if not release:
                raise RuntimeError(f"No GitHub release found for {prefix}")
            tags.append(str(release.get("tag_name") or ""))
        latest = " + ".join(tags)
        installed_parts = [part.strip() for part in str(installed or "").split("+")]
        update_available = len(installed_parts) != len(tags) or any(
            _is_newer(tag, installed_parts[index] if index < len(installed_parts) else "")
            for index, tag in enumerate(tags)
        )
    else:
        release, headers = _request_json(f"{GITHUB_API}/repos/{repo}/releases/latest", timeout)
        latest = str(release.get("tag_name") or "")
        update_available = _is_newer(latest, installed)
    return {
        "engine": engine_id,
        "source_type": "github_release",
        "repo": repo,
        "reachable": True,
        "installed_version": installed or "",
        "latest_version": latest,
        "update_available": update_available,
        "up_to_date": bool(installed) and not update_available,
        "latency_ms": round((time.monotonic() - started) * 1000),
        "rate_limit_remaining": headers.get("x-ratelimit-remaining", ""),
        "error": "",
    }


def _check_repository(engine_id: str, source: dict[str, str], installed: str, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    repo = source["repo"]
    _, headers = _request_json(f"{GITHUB_API}/repos/{repo}", timeout)
    return {
        "engine": engine_id,
        "source_type": "system_package",
        "package_manager": source.get("manager", ""),
        "repo": repo,
        "reachable": True,
        "installed_version": installed or "system",
        "latest_version": "managed by operating system",
        "update_available": None,
        "up_to_date": None,
        "latency_ms": round((time.monotonic() - started) * 1000),
        "rate_limit_remaining": headers.get("x-ratelimit-remaining", ""),
        "error": "",
    }


def check_engine_updates(
    catalog: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    *,
    engine_id: str = "",
    timeout: float = 12.0,
    cache_seconds: float = 300.0,
) -> dict[str, Any]:
    """Check GitHub reachability and compare installed release tags."""
    now = time.time()
    if not engine_id:
        with _CACHE_LOCK:
            if _CACHE["result"] and now - float(_CACHE["created_at"]) < cache_seconds:
                cached = dict(_CACHE["result"])
                cached["cached"] = True
                return cached

    selected = [engine_id] if engine_id else sorted(catalog)
    unknown = [item for item in selected if item not in catalog]
    if unknown:
        return {"success": False, "error": f"Unknown engine: {unknown[0]}"}

    installed_manifest = manifest.get("engines", {}) if isinstance(manifest, dict) else {}
    results: dict[str, dict[str, Any]] = {}

    def worker(item: str) -> tuple[str, dict[str, Any]]:
        installed = str((installed_manifest.get(item) or {}).get("tag") or "")
        try:
            if item in RELEASE_SOURCES:
                return item, _check_release_engine(item, RELEASE_SOURCES[item], installed, timeout)
            if item in SYSTEM_SOURCES:
                return item, _check_repository(item, SYSTEM_SOURCES[item], installed, timeout)
            if item in BUILTIN_ENGINES:
                return item, {
                    "engine": item,
                    "source_type": "builtin",
                    "repo": "builtin",
                    "reachable": True,
                    "installed_version": "builtin",
                    "latest_version": "bundled with panel",
                    "update_available": False,
                    "up_to_date": True,
                    "latency_ms": 0,
                    "error": "",
                }
            return item, {
                "engine": item,
                "source_type": "unknown",
                "repo": str((catalog.get(item) or {}).get("repo") or ""),
                "reachable": False,
                "installed_version": installed,
                "latest_version": "",
                "update_available": None,
                "up_to_date": None,
                "latency_ms": 0,
                "error": "No update source is configured.",
            }
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
            return item, {
                "engine": item,
                "source_type": "github_release" if item in RELEASE_SOURCES else "system_package",
                "repo": str((RELEASE_SOURCES.get(item) or SYSTEM_SOURCES.get(item) or {}).get("repo") or ""),
                "reachable": False,
                "installed_version": installed,
                "latest_version": "",
                "update_available": None,
                "up_to_date": None,
                "latency_ms": 0,
                "error": str(exc)[:300],
            }

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(selected)))) as executor:
        futures = [executor.submit(worker, item) for item in selected]
        for future in as_completed(futures):
            key, value = future.result()
            results[key] = value

    payload = {
        "success": True,
        "checked_at": now,
        "cached": False,
        "summary": {
            "total": len(results),
            "reachable": sum(1 for item in results.values() if item.get("reachable")),
            "updates_available": sum(1 for item in results.values() if item.get("update_available") is True),
            "current": sum(1 for item in results.values() if item.get("up_to_date") is True),
            "system_managed": sum(1 for item in results.values() if item.get("source_type") == "system_package"),
            "failed": sum(1 for item in results.values() if not item.get("reachable")),
        },
        "engines": dict(sorted(results.items())),
    }
    if not engine_id:
        with _CACHE_LOCK:
            _CACHE["created_at"] = now
            _CACHE["result"] = payload
    return payload
