"""GitHub release and installed-version checks for tunnel engines.

Rate-limit resilient: results are cached in memory and on disk, GitHub API
calls are serialized through one shared opener with spacing, HTTP 403/429 are
converted into structured ``rate_limited`` results instead of exceptions, and
an optional ``GITHUB_TOKEN`` environment variable raises the quota. ETags from
previous checks are replayed for conditional revalidation.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable


GITHUB_API = "https://api.github.com"
USER_AGENT = "P00RIJA-TUNNEL-engine-update-checker"
DEFAULT_CACHE_SECONDS = 6 * 3600.0  # 6h TTL for check results
DISK_CACHE_FILENAME = "engine_update_cache.json"
REQUEST_SPACING_SECONDS = 0.4  # minimum delay between GitHub API calls
RATE_LIMIT_FALLBACK_RETRY_AFTER = 900.0  # used when GitHub sends no reset header
RATE_LIMIT_RETRY_CAP = 600.0  # bounded sleep inside update_all_engines

_CACHE: dict[str, Any] = {"created_at": 0.0, "result": {}, "etags": {}}
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
    "hedioum": {"repo": "hedioum/Hedioum-Pool-Tunnel"},
    "cloak": {"repo": "cbeuw/Cloak"},
    "tuic": {
        "repo": "tuic-protocol/tuic",
        "release_prefixes": ("tuic-server-", "tuic-client-"),
    },
}

SYSTEM_SOURCES: dict[str, dict[str, str]] = {
    "wireguard": {"repo": "WireGuard/wireguard-tools", "manager": "apt"},
    "ssh": {"repo": "openssh/openssh-portable", "manager": "apt"},
    "stunnel": {"repo": "mtrojnar/stunnel", "manager": "apt"},
    "phormal": {"repo": "Schmi7zz/Phormal", "manager": "raw-script", "source_type": "source_repository"},
}

BUILTIN_ENGINES = {"muxquantum", "rawsock", "aead"}

# Serialize every GitHub API call through one shared opener with spacing so
# repeated update checks cannot burn the hourly anonymous quota.
_OPENER_LOCK = threading.Lock()
_SHARED_OPENER = urllib.request.build_opener()
_LAST_REQUEST_AT = {"monotonic": 0.0}


def _disk_cache_path() -> str:
    db_path = os.environ.get("P00RIJA_DB_PATH", "")
    if db_path:
        return os.path.join(os.path.dirname(os.path.abspath(db_path)), DISK_CACHE_FILENAME)
    config_dir = os.environ.get("P00RIJA_CONFIG_DIR", "/opt/p00rija")
    return os.path.join(config_dir, DISK_CACHE_FILENAME)


def _read_disk_cache() -> dict[str, Any]:
    try:
        with open(_disk_cache_path(), encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("result"), dict):
            data.setdefault("etags", {})
            return data
    except Exception:
        pass
    return {"created_at": 0.0, "result": {}, "etags": {}}


def _write_disk_cache(payload: dict[str, Any], etags: dict[str, str]) -> None:
    try:
        path = _disk_cache_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp"
        tmp_fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            json.dump(
                {"created_at": payload.get("checked_at") or time.time(), "result": payload, "etags": etags},
                handle,
            )
        os.replace(tmp_path, path)
    except Exception:
        pass


def clear_engine_update_cache() -> None:
    with _CACHE_LOCK:
        _CACHE["created_at"] = 0.0
        _CACHE["result"] = {}
        _CACHE["etags"] = {}
    try:
        path = _disk_cache_path()
        if os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


class _RateLimited(Exception):
    """Raised when GitHub answers 403/429 with (or without) a reset header."""

    def __init__(self, retry_after: float, remaining: str = "", message: str = ""):
        super().__init__(message or "GitHub API rate limit exceeded")
        self.retry_after = max(0.0, float(retry_after))
        self.remaining = remaining


def _github_headers(etag: str = "") -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if etag:
        headers["If-None-Match"] = etag
    return headers


def _request_json(url: str, timeout: float, etag: str = "") -> tuple[Any, dict[str, str]]:
    """GET <url> through the shared serialized opener.

    Returns (data, headers); data is None when the server answered 304 Not
    Modified (ETag revalidation). Raises _RateLimited on 403/429.
    """
    request = urllib.request.Request(url, headers=_github_headers(etag))
    with _OPENER_LOCK:
        wait = REQUEST_SPACING_SECONDS - (time.monotonic() - _LAST_REQUEST_AT["monotonic"])
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST_AT["monotonic"] = time.monotonic()
        try:
            with _SHARED_OPENER.open(request, timeout=timeout) as response:
                headers = {key.lower(): value for key, value in response.headers.items()}
                return json.loads(response.read().decode("utf-8")), headers
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                headers = {key.lower(): value for key, value in (exc.headers or {}).items()}
                return None, headers
            if exc.code in (403, 429):
                remaining = ""
                retry_after = RATE_LIMIT_FALLBACK_RETRY_AFTER
                try:
                    response_headers = {key.lower(): value for key, value in (exc.headers or {}).items()}
                    remaining = str(response_headers.get("x-ratelimit-remaining", ""))
                    reset_value = response_headers.get("x-ratelimit-reset", "")
                    if reset_value:
                        retry_after = max(0.0, float(reset_value) - time.time())
                except Exception:
                    pass
                body_snippet = ""
                try:
                    body_snippet = (exc.read().decode("utf-8", "ignore") or "")[:200]
                except Exception:
                    pass
                raise _RateLimited(
                    retry_after,
                    remaining,
                    body_snippet or f"HTTP {exc.code} from GitHub API",
                ) from exc
            raise


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


def _update_available_from_latest(latest: str, installed: str) -> bool:
    """Recompute update availability from a joined latest tag ("a + b")."""
    latest_tags = [tag.strip() for tag in str(latest or "").split("+") if tag.strip()]
    if not latest_tags:
        return False
    installed_parts = [part.strip() for part in str(installed or "").split("+")]
    return len(installed_parts) != len(latest_tags) or any(
        _is_newer(tag, installed_parts[index] if index < len(installed_parts) else "")
        for index, tag in enumerate(latest_tags)
    )


def _etag_store_key(repo: str, path: str) -> str:
    return f"{repo}:{path}"


def _check_release_engine(
    engine_id: str,
    source: dict[str, Any],
    installed: str,
    timeout: float,
    *,
    previous: dict[str, Any] | None = None,
    etags: dict[str, str] | None = None,
) -> dict[str, Any]:
    repo = source["repo"]
    started = time.monotonic()
    etags = etags if etags is not None else {}
    previous = previous or {}
    if source.get("release_prefixes"):
        list_path = f"/repos/{repo}/releases?per_page=30"
        url = f"{GITHUB_API}{list_path}"
        releases, headers = _request_json(url, timeout, etag=etags.get(_etag_store_key(repo, list_path), ""))
        etags[_etag_store_key(repo, list_path)] = str(headers.get("etag", "") or "")
        if releases is None:
            # 304 Not Modified: reuse the cached tags, recompute against the
            # currently installed version.
            latest = str(previous.get("latest_version") or "")
            return {
                "engine": engine_id,
                "source_type": "github_release",
                "repo": repo,
                "reachable": True,
                "installed_version": installed or "",
                "latest_version": latest,
                "update_available": _update_available_from_latest(latest, installed),
                "up_to_date": bool(installed) and not _update_available_from_latest(latest, installed),
                "latency_ms": 0,
                "rate_limit_remaining": headers.get("x-ratelimit-remaining", previous.get("rate_limit_remaining", "")),
                "not_modified": True,
                "error": "",
            }
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
        update_available = _update_available_from_latest(latest, installed)
    else:
        latest_path = f"/repos/{repo}/releases/latest"
        url = f"{GITHUB_API}{latest_path}"
        release, headers = _request_json(url, timeout, etag=etags.get(_etag_store_key(repo, latest_path), ""))
        etags[_etag_store_key(repo, latest_path)] = str(headers.get("etag", "") or "")
        if release is None:
            latest = str(previous.get("latest_version") or "")
            update_available = _update_available_from_latest(latest, installed)
        else:
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


def _check_repository(
    engine_id: str,
    source: dict[str, str],
    installed: str,
    timeout: float,
    *,
    etags: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    repo = source["repo"]
    etags = etags if etags is not None else {}
    repo_path = f"/repos/{repo}"
    _, headers = _request_json(
        f"{GITHUB_API}{repo_path}", timeout, etag=etags.get(_etag_store_key(repo, repo_path), "")
    )
    etags[_etag_store_key(repo, repo_path)] = str(headers.get("etag", "") or "")
    return {
        "engine": engine_id,
        "source_type": source.get("source_type") or "system_package",
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
    cache_seconds: float = DEFAULT_CACHE_SECONDS,
) -> dict[str, Any]:
    """Check GitHub reachability and compare installed release tags.

    Results are cached in memory and on disk for ``cache_seconds``. Rate-limited
    responses come back as ``{"success": True, "rate_limited": True,
    "retry_after": <seconds>, ...}`` instead of raising, so the panel UI can
    show a friendly message rather than a 500.
    """
    now = time.time()
    if not engine_id:
        with _CACHE_LOCK:
            if _CACHE["result"] and now - float(_CACHE["created_at"]) < cache_seconds:
                cached = dict(_CACHE["result"])
                cached["cached"] = True
                return cached
        disk = _read_disk_cache()
        if disk.get("result") and now - float(disk.get("created_at") or 0.0) < cache_seconds:
            with _CACHE_LOCK:
                _CACHE["created_at"] = float(disk.get("created_at") or 0.0)
                _CACHE["result"] = disk["result"]
                _CACHE["etags"] = disk.get("etags") or {}
            cached = dict(disk["result"])
            cached["cached"] = True
            return cached

    selected = [engine_id] if engine_id else sorted(catalog)
    unknown = [item for item in selected if item not in catalog]
    if unknown:
        return {"success": False, "error": f"Unknown engine: {unknown[0]}"}

    installed_manifest = manifest.get("engines", {}) if isinstance(manifest, dict) else {}
    results: dict[str, dict[str, Any]] = {}
    # Replay ETags and previous results from the last known check (memory or
    # disk) so an expired cache revalidates cheaply via 304 responses.
    run_etags: dict[str, str] = {}
    with _CACHE_LOCK:
        previous_engines = dict((_CACHE["result"].get("engines") or {}))
        run_etags.update({key: value for key, value in (_CACHE.get("etags") or {}).items()})
    if not previous_engines or not run_etags:
        disk_previous = _read_disk_cache()
        if not previous_engines:
            previous_engines = dict((disk_previous.get("result") or {}).get("engines") or {})
        if not run_etags:
            run_etags.update(disk_previous.get("etags") or {})
    previous_final = previous_engines

    def worker(item: str) -> tuple[str, dict[str, Any]]:
        installed = str((installed_manifest.get(item) or {}).get("tag") or "")
        try:
            if item in RELEASE_SOURCES:
                return item, _check_release_engine(
                    item,
                    RELEASE_SOURCES[item],
                    installed,
                    timeout,
                    previous=previous_final.get(item) or {},
                    etags=run_etags,
                )
            if item in SYSTEM_SOURCES:
                return item, _check_repository(item, SYSTEM_SOURCES[item], installed, timeout, etags=run_etags)
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
        except _RateLimited as exc:
            return item, {
                "engine": item,
                "source_type": "github_release" if item in RELEASE_SOURCES else "system_package",
                "repo": str((RELEASE_SOURCES.get(item) or SYSTEM_SOURCES.get(item) or {}).get("repo") or ""),
                "reachable": False,
                "rate_limited": True,
                "retry_after": round(exc.retry_after),
                "installed_version": installed,
                "latest_version": "",
                "update_available": None,
                "up_to_date": None,
                "latency_ms": 0,
                "rate_limit_remaining": exc.remaining,
                "error": "GitHub API rate limit exceeded",
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

    rate_limited_results = [item for item in results.values() if item.get("rate_limited")]
    retry_after = max((int(item.get("retry_after") or 0) for item in rate_limited_results), default=0)
    remaining_values = [
        str(item.get("rate_limit_remaining"))
        for item in results.values()
        if str(item.get("rate_limit_remaining") or "").strip().isdigit()
    ]
    payload = {
        "success": True,
        "checked_at": now,
        "cached": False,
        "rate_limited": bool(rate_limited_results),
        "retry_after": retry_after,
        "rate_limit_remaining": min(int(value) for value in remaining_values) if remaining_values else "",
        "summary": {
            "total": len(results),
            "reachable": sum(1 for item in results.values() if item.get("reachable")),
            "updates_available": sum(1 for item in results.values() if item.get("update_available") is True),
            "current": sum(1 for item in results.values() if item.get("up_to_date") is True),
            "system_managed": sum(1 for item in results.values() if item.get("source_type") == "system_package"),
            "failed": sum(1 for item in results.values() if not item.get("reachable")),
            "rate_limited": len(rate_limited_results),
        },
        "engines": dict(sorted(results.items())),
    }
    if not engine_id and not rate_limited_results:
        with _CACHE_LOCK:
            _CACHE["created_at"] = now
            _CACHE["result"] = payload
            _CACHE["etags"] = run_etags
        _write_disk_cache(payload, run_etags)
    return payload


def update_all_engines(
    progress_cb: Callable[[dict[str, Any]], None] | None = None,
    *,
    check_updates: Callable[[str], dict[str, Any]] | None = None,
    updater: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Sequentially update every engine that has an available update.

    ``check_updates("")`` must return the ``check_engine_updates`` payload for
    all engines and ``updater(engine_id)`` updates one engine (the panel wires
    these to its own wrappers, e.g. ``install_engine_from_github``). GitHub
    rate-limit waits are respected with a bounded backoff between engines.
    """
    if check_updates is None or updater is None:
        raise ValueError(
            "update_all_engines requires check_updates and updater callables from the panel runtime"
        )

    def report(update: dict[str, Any]) -> None:
        if progress_cb:
            try:
                progress_cb(update)
            except Exception:
                pass

    report({"phase": "checking"})
    results = check_updates("") or {}
    if not results.get("success"):
        raise RuntimeError(str(results.get("error") or "Engine update check failed"))
    if results.get("rate_limited"):
        retry_after = min(float(results.get("retry_after") or 0), RATE_LIMIT_RETRY_CAP)
        report({"phase": "rate_limited", "rate_limited": True, "retry_after": retry_after})
        if retry_after > 0:
            time.sleep(retry_after)
        results = check_updates("") or {}

    engines = results.get("engines") or {}
    targets = [
        engine_id
        for engine_id, info in sorted(engines.items())
        if info.get("update_available") is True and info.get("source_type") == "github_release"
    ]
    report({"phase": "updating", "total": len(targets), "targets": targets})

    updated: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, engine_id in enumerate(targets, 1):
        report({"current_engine": engine_id, "completed": index - 1})
        try:
            outcome = updater(engine_id)
            if isinstance(outcome, dict):
                outcome.pop("output", None)
                updated.append(outcome)
            else:
                updated.append({"engine": engine_id, "result": str(outcome)[:500]})
        except Exception as exc:
            message = str(exc)
            retry_after = 0.0
            if "rate limit" in message.lower():
                # The single-engine updater surfaces GitHub rate limits as
                # runtime errors; back off (bounded) before the next engine.
                retry_after = RATE_LIMIT_RETRY_CAP
                time.sleep(retry_after)
            errors.append({"engine": engine_id, "error": message[-1000:], "retry_after": retry_after})
        report({
            "completed": index,
            "results": list(updated),
            "errors": list(errors),
            "current_engine": "",
        })

    summary = {
        "success": not errors,
        "total": len(targets),
        "updated": len(updated),
        "failed": len(errors),
        "targets": targets,
        "results": updated,
        "errors": errors,
    }
    report({"phase": "completed", **summary})
    return summary


# --- Panel self-update check (server -> GitHub) ---

PANEL_REPO_LATEST_PATH = "/repos/Poorija/P00RIJA-TUNNEL/releases/latest"
PANEL_REPO_TAGS_PATH = "/repos/Poorija/P00RIJA-TUNNEL/tags"
PANEL_MAIN_VERSION_URL = "https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/P00RIJA.py"
PANEL_COMMITS_URL = "https://github.com/Poorija/P00RIJA-TUNNEL/commits/main"
PANEL_CHECK_CACHE_SECONDS = 15 * 60.0
_PANEL_CHECK_CACHE: dict[str, Any] = {"at": 0.0, "result": {}}


def _panel_main_branch_version() -> tuple[str, str]:
    """Last-resort fallback: read APP_VERSION from the raw main-branch entrypoint.

    Keeps the update check useful for deployments whose repository has not
    published any release or tag yet. Returns ("", "") when unavailable.
    """
    request = urllib.request.Request(PANEL_MAIN_VERSION_URL, headers=_github_headers(""))
    with _OPENER_LOCK:
        wait = REQUEST_SPACING_SECONDS - (time.monotonic() - _LAST_REQUEST_AT["monotonic"])
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST_AT["monotonic"] = time.monotonic()
        try:
            with _SHARED_OPENER.open(request, timeout=10) as response:
                text = response.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return "", ""
            raise
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        return "", ""
    return match.group(1), PANEL_COMMITS_URL


def _panel_latest_version() -> tuple[str, str]:
    """Return (latest_version, release_url) from GitHub, tags as fallback."""
    try:
        data, _ = _request_json(f"{GITHUB_API}{PANEL_REPO_LATEST_PATH}", timeout=10)
    except urllib.error.HTTPError as exc:
        # A private/absent release set answers 404 here; fall back to tags.
        if exc.code != 404:
            raise
        data = None
    if isinstance(data, dict) and data.get("tag_name"):
        return str(data["tag_name"]), str(data.get("html_url") or "")
    # No releases published yet: fall back to the newest tag.
    try:
        tags, _ = _request_json(f"{GITHUB_API}{PANEL_REPO_TAGS_PATH}", timeout=10)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        tags = None
    if isinstance(tags, list) and tags:
        first = tags[0]
        return str(first.get("name") or ""), str(first.get("zipball_url") or "")
    # Neither releases nor tags: derive the version from the main branch.
    return _panel_main_branch_version()


def check_panel_update(current_version: str) -> dict[str, Any]:
    """Compare APP_VERSION against the newest GitHub release of the panel.

    Never raises on rate limits: returns a structured ``rate_limited`` payload
    so the UI can show a friendly retry hint. Results are cached briefly.
    """
    now = time.monotonic()
    with _CACHE_LOCK:
        if _PANEL_CHECK_CACHE["result"] and now - _PANEL_CHECK_CACHE["at"] < PANEL_CHECK_CACHE_SECONDS:
            cached = dict(_PANEL_CHECK_CACHE["result"])
            cached["cached"] = True
            return cached
    current = str(current_version or "").lstrip("vV")
    try:
        latest_raw, release_url = _panel_latest_version()
    except _RateLimited as exc:
        return {
            "success": True,
            "rate_limited": True,
            "retry_after": int(max(0.0, min(exc.retry_after, RATE_LIMIT_RETRY_CAP))),
            "rate_limit_remaining": getattr(exc, "remaining", ""),
            "current": current,
        }
    except Exception as exc:  # network/DNS failures must not 500 the endpoint
        return {"success": True, "current": current, "error": str(exc)}
    latest = latest_raw.lstrip("vV")
    result = {
        "success": True,
        "current": current,
        "latest": latest,
        "latest_tag": latest_raw,
        "update_available": bool(latest) and _is_newer(latest, current),
        "release_url": release_url,
        "no_release": not bool(latest),
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with _CACHE_LOCK:
        _PANEL_CHECK_CACHE["at"] = now
        _PANEL_CHECK_CACHE["result"] = dict(result)
    return result
