"""Smart APT/Docker mirror selection for Iranian servers.

This module lets the panel API (and the runtime) re-probe available Iranian
Ubuntu/Debian and Docker registry mirrors, rank them by latency, and apply the
fastest reachable ones to /etc/apt/sources.list.d and /etc/docker/daemon.json.

It mirrors the probe logic that lives in installer-ui.sh so install-time and
runtime mirror selection stay in sync. All network probes are best-effort and
fail-open: if every probe fails we keep the existing configuration unchanged.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


USER_AGENT = "P00RIJA-TUNNEL-mirror-selector"
DEFAULT_PROBE_TIMEOUT = 4.0
DEFAULT_DOCKER_TOP_N = 3

# Smart mirror catalog — kept identical to installer-ui.sh so install and runtime agree.
UBUNTU_IR_MIRRORS = [
    "https://mirror.arvancloud.ir/ubuntu/",
    "https://mirror.iranserver.com/ubuntu/",
    "https://mirror.shatel.ir/ubuntu",
    "http://mirrors.pol.hostinja.com/ubuntu/",
    "http://ir.archive.ubuntu.com/ubuntu/",
]
DEBIAN_IR_MIRRORS = [
    "https://mirror.arvancloud.ir/debian/",
    "http://debian.pol.hostinja.com/debian/",
]
DOCKER_IR_MIRRORS = [
    "https://docker.arvancloud.ir",
    "https://registry.docker.ir",
    "https://docker.iranserver.com",
    "https://registry.liara.ir",
    "https://registry.ir.svrs.tech",
    "https://mirror.kargadan.ir",
    "https://docker.kernel.ir",
    "https://focker.ir",
]

_APT_SOURCES_PATH = "/etc/apt/sources.list.d/p00rija-iran.sources"
_DOCKER_DAEMON_PATH = "/etc/docker/daemon.json"
_OS_RELEASE_PATH = "/etc/os-release"
_CACHE: dict[str, Any] = {"created_at": 0.0, "result": {}}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 300.0  # seconds


def _now_ms() -> int:
    return int(time.monotonic() * 1000)


def _probe_url_is_safe(url: str) -> bool:
    """Inline SSRF guard: http(s) only, host present, resolved IPs must be public."""
    import ipaddress

    try:
        parsed = urllib.parse.urlparse(str(url))
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.username or parsed.password:
        return False
    host = parsed.hostname or ""
    if not host:
        return False
    try:
        candidates = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            candidates = [ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, None)]
        except (socket.gaierror, UnicodeError, ValueError, OSError):
            return False
    for addr in candidates:
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            return False
    return True


def _http_probe(url: str, timeout: float, accept_codes: tuple[int, ...] = (200,)) -> tuple[bool, int]:
    """Issue a HEAD/GET request and return (reachable, latency_ms)."""
    start = _now_ms()
    if not _probe_url_is_safe(url):
        return False, -1
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            ok = response.status in accept_codes
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False, -1
    return ok, max(0, _now_ms() - start)


def detect_distro() -> str:
    """Return the distro id from /etc/os-release (e.g. 'ubuntu', 'debian')."""
    info = _read_os_release()
    return str(info.get("ID", "")).lower()


def detect_codename() -> str:
    """Return the release codename (e.g. 'noble', 'jammy', 'resolute', 'bookworm')."""
    info = _read_os_release()
    return str(info.get("VERSION_CODENAME") or info.get("UBUNTU_CODENAME") or "").lower()


def detect_region() -> str:
    """Heuristic region detection via env override or country lookup. Returns 'ir' or 'global'."""
    env = os.environ.get("P00RIJA_SERVER_REGION", "").lower()
    if env in ("ir",):
        return "ir"
    if env in ("global", "outside"):
        return "global"
    return "global"


def _read_os_release() -> dict[str, str]:
    data: dict[str, str] = {}
    if not os.path.exists(_OS_RELEASE_PATH):
        return data
    try:
        with open(_OS_RELEASE_PATH, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                data[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return data


def probe_apt_mirror(mirror: str, codename: str, timeout: float = DEFAULT_PROBE_TIMEOUT) -> dict[str, Any]:
    """Probe a single APT mirror by fetching its Release file for the given codename."""
    probe_url = f"{mirror.rstrip('/')}/dists/{codename}/Release"
    ok, latency = _http_probe(probe_url, timeout)
    return {"mirror": mirror, "reachable": ok, "latency_ms": latency if ok else None}


def probe_docker_mirror(mirror: str, timeout: float = DEFAULT_PROBE_TIMEOUT) -> dict[str, Any]:
    """Probe a single Docker registry mirror via its v2 API endpoint."""
    probe_url = f"{mirror.rstrip('/')}/v2/"
    # 200 = reachable unauthenticated catalog; 401 = reachable but requires auth (still a valid mirror).
    ok, latency = _http_probe(probe_url, timeout, accept_codes=(200, 401))
    return {"mirror": mirror, "reachable": ok, "latency_ms": latency if ok else None}


def _rank(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort probe results: reachable first by latency ascending, unreachable last."""
    reachable = [r for r in results if r.get("reachable")]
    unreachable = [r for r in results if not r.get("reachable")]
    reachable.sort(key=lambda r: r.get("latency_ms") or 999999)
    return reachable + unreachable


def select_best_apt_mirrors(codename: str | None = None, timeout: float = DEFAULT_PROBE_TIMEOUT) -> list[dict[str, Any]]:
    """Probe all Ubuntu/Debian IR mirrors for the host's codename and return ranked results."""
    codename = codename or detect_codename()
    distro = detect_distro()
    if not codename or distro not in ("ubuntu", "linuxmint", "pop", "debian"):
        return []
    mirrors = UBUNTU_IR_MIRRORS if distro in ("ubuntu", "linuxmint", "pop") else DEBIAN_IR_MIRRORS
    with ThreadPoolExecutor(max_workers=min(8, len(mirrors))) as pool:
        futures = {pool.submit(probe_apt_mirror, m, codename, timeout): m for m in mirrors}
        results = [future.result() for future in as_completed(futures)]
    return _rank(results)


def select_best_docker_mirrors(
    timeout: float = DEFAULT_PROBE_TIMEOUT, top_n: int = DEFAULT_DOCKER_TOP_N
) -> list[dict[str, Any]]:
    """Probe all Docker IR registry mirrors and return ranked results (all reachable, best first)."""
    with ThreadPoolExecutor(max_workers=min(8, len(DOCKER_IR_MIRRORS))) as pool:
        futures = {pool.submit(probe_docker_mirror, m, timeout): m for m in DOCKER_IR_MIRRORS}
        results = [future.result() for future in as_completed(futures)]
    ranked = _rank(results)
    return ranked[:top_n] if top_n > 0 else ranked


def _write_apt_sources(distro: str, codename: str, mirror: str) -> bool:
    """Write a DEB822 .sources file for the chosen mirror. Returns True on success."""
    if not distro or not codename or not mirror:
        return False
    os.makedirs(os.path.dirname(_APT_SOURCES_PATH), exist_ok=True)
    if distro in ("ubuntu", "linuxmint", "pop"):
        keyring = "/usr/share/keyrings/ubuntu-archive-keyring.gpg"
        components = "main restricted universe multiverse"
        suites = f"{codename} {codename}-updates {codename}-security"
    elif distro == "debian":
        keyring = "/usr/share/keyrings/debian-archive-keyring.gpg"
        components = "main contrib non-free non-free-firmware"
        suites = f"{codename} {codename}-updates"
    else:
        return False
    content = (
        "Types: deb\n"
        f"URIs: {mirror}\n"
        f"Suites: {suites}\n"
        f"Components: {components}\n"
        f"Signed-By: {keyring}\n"
    )
    try:
        tmp = f"{_APT_SOURCES_PATH}.tmp"
        tmp_fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp, _APT_SOURCES_PATH)
        return True
    except OSError:
        return False


def _read_docker_daemon() -> dict[str, Any]:
    if not os.path.exists(_DOCKER_DAEMON_PATH) or os.path.getsize(_DOCKER_DAEMON_PATH) == 0:
        return {}
    try:
        with open(_DOCKER_DAEMON_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_docker_daemon(mirrors: list[str]) -> bool:
    """Update registry-mirrors in daemon.json. Returns True if the file changed.

    Only the top-3 probe-selected mirrors are written, and the file is touched
    solely when the mirror list actually differs from what is configured.
    """
    # Slice to the top-3 selected mirrors; a longer list slows pulls and most
    # daemons only try the first few entries anyway.
    selected = [str(m).rstrip("/") for m in (mirrors or [])][:DEFAULT_DOCKER_TOP_N]
    data = _read_docker_daemon()
    current = [str(m).rstrip("/") for m in (data.get("registry-mirrors") or [])]
    if current == selected:
        return False
    if selected:
        data["registry-mirrors"] = selected
    else:
        data.pop("registry-mirrors", None)
    os.makedirs(os.path.dirname(_DOCKER_DAEMON_PATH), exist_ok=True)
    try:
        tmp = f"{_DOCKER_DAEMON_PATH}.tmp"
        tmp_fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp, _DOCKER_DAEMON_PATH)
        return True
    except OSError:
        return False


def _restart_docker() -> bool:
    """Restart the Docker daemon via systemctl.

    Only invoked from the explicit force_restart=True host-control flow; the
    probe/apply API path must never restart Docker silently because that
    interrupts every running container on the host.
    """
    if not shutil.which("systemctl"):
        return False
    try:
        subprocess.run(["systemctl", "restart", "docker"], check=False, timeout=30, capture_output=True)
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def current_docker_mirrors() -> list[str]:
    """Return the mirrors currently configured in daemon.json (empty if none)."""
    data = _read_docker_daemon()
    value = data.get("registry-mirrors")
    return list(value) if isinstance(value, list) else []


def full_reprobe(
    force_apply: bool = False,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
    force_restart: bool = False,
) -> dict[str, Any]:
    """Probe APT + Docker mirrors, optionally apply the best ones, and return the full report.

    This is the entry point used by the panel API. It is safe to call repeatedly;
    results are cached for _CACHE_TTL seconds unless force_apply is True.
    Docker is never restarted silently: the report carries a warning directing
    the operator to host-control unless force_restart=True (host-control flow).
    """
    if not force_apply:
        with _CACHE_LOCK:
            if time.time() - _CACHE["created_at"] < _CACHE_TTL and _CACHE.get("result"):
                return _CACHE["result"]

    codename = detect_codename()
    distro = detect_distro()
    region = detect_region()
    apt_results: list[dict[str, Any]] = []
    docker_results: list[dict[str, Any]] = []
    applied_apt: str | None = None
    applied_docker: list[str] = []
    docker_restarted = False
    docker_restart_warning = ""

    if region == "ir":
        if codename and distro in ("ubuntu", "linuxmint", "pop", "debian"):
            apt_results = select_best_apt_mirrors(codename, timeout)
            if apt_results and apt_results[0].get("reachable") and force_apply:
                best = apt_results[0]["mirror"]
                if _write_apt_sources(distro, codename, best):
                    applied_apt = best
        docker_results = select_best_docker_mirrors(timeout)
        if docker_results and force_apply:
            best_docker = [r["mirror"] for r in docker_results if r.get("reachable")]
            if best_docker:
                if _write_docker_daemon(best_docker):
                    applied_docker = [m.rstrip("/") for m in best_docker[:DEFAULT_DOCKER_TOP_N]]
                    if force_restart:
                        docker_restarted = _restart_docker()
                        if not docker_restarted:
                            docker_restart_warning = (
                                "daemon.json was updated but the Docker daemon could not be restarted; "
                                "restart it manually so the new mirrors take effect."
                            )
                    else:
                        docker_restart_warning = (
                            "daemon.json was updated; Docker was NOT restarted to avoid disrupting "
                            "running containers. Restart it via host-control to apply the new mirrors."
                        )

    report = {
        "region": region,
        "distro": distro,
        "codename": codename,
        "apt_mirrors": apt_results,
        "docker_mirrors": docker_results,
        "applied_apt_mirror": applied_apt,
        "applied_docker_mirrors": applied_docker,
        "docker_restarted": docker_restarted,
        "docker_restart_warning": docker_restart_warning,
        "current_docker_mirrors": current_docker_mirrors(),
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with _CACHE_LOCK:
        _CACHE["created_at"] = time.time()
        _CACHE["result"] = report
    return report


def clear_cache() -> None:
    """Invalidate the cached probe report (used before a forced re-probe)."""
    with _CACHE_LOCK:
        _CACHE["created_at"] = 0.0
        _CACHE["result"] = {}
