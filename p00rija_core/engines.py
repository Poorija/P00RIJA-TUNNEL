from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any


DEFAULT_ENGINE_CATALOG: dict[str, dict[str, Any]] = {
    "xray": {"bins": ["xray"], "repo": "XTLS/Xray-core"},
    "gost": {"bins": ["gost"], "repo": "go-gost/gost"},
    "backhaul": {"bins": ["backhaul"], "repo": "Musixal/Backhaul"},
    "rathole": {"bins": ["rathole"], "repo": "rapiz1/rathole"},
    "chisel": {"bins": ["chisel"], "repo": "jpillora/chisel"},
    "frp": {"bins": ["frpc", "frps"], "repo": "fatedier/frp"},
    "hysteria2": {"bins": ["hysteria", "hysteria2"], "repo": "apernet/hysteria"},
    "singbox": {"bins": ["sing-box", "singbox"], "repo": "SagerNet/sing-box"},
    "tuic": {"bins": ["tuic-server", "tuic-client"], "repo": "tuic-protocol/tuic"},
    "masque": {"bins": ["masque-tunnel"], "repo": "ferneast/masque-tunnel"},
    "naiveproxy": {"bins": ["naive", "naiveproxy"], "repo": "klzgrad/naiveproxy"},
    "shadowtls": {"bins": ["shadow-tls", "shadowtls"], "repo": "ihciah/shadow-tls"},
    "brook": {"bins": ["brook"], "repo": "txthinking/brook"},
    "mieru": {"bins": ["mieru", "mita"], "repo": "enfein/mieru"},
    "muxquantum": {"bins": [], "repo": "builtin"},
}


VERSION_ARGS = (
    ("--version",),
    ("-version",),
    ("version",),
    ("-v",),
)


def build_engine_catalog(extra_catalog: dict[str, dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    catalog = {key: dict(value) for key, value in DEFAULT_ENGINE_CATALOG.items()}
    for key, value in (extra_catalog or {}).items():
        catalog[key] = dict(value)
    return catalog


def _candidate_dirs(engines_dir: str, cwd: str | None = None) -> list[str]:
    base_cwd = cwd or os.getcwd()
    return [
        engines_dir,
        os.path.join(base_cwd, "engines"),
        "/app/engines",
        "/usr/local/bin",
    ]


def engine_binary_path(binary: str, engines_dir: str, cwd: str | None = None) -> str:
    for base in _candidate_dirs(engines_dir, cwd):
        path = os.path.join(base, binary)
        if os.path.exists(path):
            return path
    system_path = shutil.which(binary)
    if system_path:
        return system_path
    return ""


def _manifest_paths(engines_dir: str, cwd: str | None = None) -> list[str]:
    base_cwd = cwd or os.getcwd()
    return [
        os.path.join(engines_dir, "manifest.json"),
        os.path.join(base_cwd, "engines", "manifest.json"),
        "/app/engines/manifest.json",
        "/usr/local/bin/manifest.json",
    ]


def load_engine_manifest(engines_dir: str, cwd: str | None = None) -> dict[str, Any]:
    for manifest_path in _manifest_paths(engines_dir, cwd):
        if not os.path.exists(manifest_path):
            continue
        try:
            with open(manifest_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    return {}


def _engine_paths(catalog: dict[str, dict[str, Any]], engine_id: str, engines_dir: str, cwd: str | None = None) -> list[str]:
    info = catalog.get(engine_id) or {}
    paths = [engine_binary_path(binary, engines_dir, cwd) for binary in info.get("bins", [])]
    return [path for path in paths if path]


def list_engine_status(catalog: dict[str, dict[str, Any]], engines_dir: str, cwd: str | None = None) -> dict[str, dict[str, Any]]:
    manifest = load_engine_manifest(engines_dir, cwd)
    engines: dict[str, dict[str, Any]] = {}
    for engine_id, info in catalog.items():
        paths = _engine_paths(catalog, engine_id, engines_dir, cwd)
        required = list(info.get("bins", []))
        installed = engine_id == "muxquantum" or (bool(required) and len(paths) == len(required))
        engines[engine_id] = {
            "repo": info.get("repo"),
            "installed": installed,
            "paths": paths,
            "enabled": (bool(paths) and all(os.access(path, os.X_OK) for path in paths)) or engine_id == "muxquantum",
            "version": manifest.get("engines", {}).get(engine_id, {}).get("tag", "bundled" if installed else ""),
            "asset": manifest.get("engines", {}).get(engine_id, {}).get("asset", ""),
        }
    return engines


def _read_proc_name(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmdline = f.read().replace(b"\x00", b" ").decode("utf-8", "ignore").strip()
        if cmdline:
            return cmdline
    except Exception:
        pass
    try:
        with open(f"/proc/{pid}/comm", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""


def _proc_exe_name(pid: int) -> str:
    """Basename of the process executable from /proc/<pid>/exe ('' if unknown)."""
    try:
        return os.path.basename(os.readlink(f"/proc/{pid}/exe"))
    except Exception:
        return ""


def _proc_argv0(pid: int) -> str:
    """First NUL-separated token of /proc/<pid>/cmdline ('' if unknown)."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            first = f.read().split(b"\x00", 1)[0].decode("utf-8", "ignore").strip()
        if first:
            # Only the basename is a stable comparison target (argv[0] may be a path).
            return os.path.basename(first)
    except Exception:
        pass
    return ""


def _ancestor_pids(pid: int) -> set[int]:
    """All ancestor pids of `pid` by walking /proc/<pid>/status PPid lines."""
    ancestors: set[int] = set()
    current = pid
    for _ in range(4096):  # hard cap against corrupt PPid chains
        try:
            with open(f"/proc/{current}/status", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("PPid:"):
                        parent = int(line.split(":", 1)[1].strip() or 0)
                        break
                else:
                    break
        except Exception:
            break
        if parent <= 0 or parent in ancestors:
            break
        ancestors.add(parent)
        current = parent
    return ancestors


def _matching_pids(names: set[str]) -> list[int]:
    """Return pids whose executable or argv[0] exactly matches one of `names`.

    Substring matching is intentionally avoided: an engine named ``ssh`` must
    never match ``sshd``, and a path like /opt/p00rija/engines/wg must not
    match unrelated processes that merely mention the name in their cmdline.
    The current process and all of its ancestors are never matched.
    """
    proc_root = Path("/proc")
    if not proc_root.exists():
        return []
    current = os.getpid()
    protected = {current} | _ancestor_pids(current)
    exact_names = {name for name in names if name}
    matches: list[int] = []
    for item in proc_root.iterdir():
        if not item.name.isdigit():
            continue
        pid = int(item.name)
        if pid in protected:
            continue
        exe_name = _proc_exe_name(pid)
        if exe_name and exe_name in exact_names:
            matches.append(pid)
            continue
        argv0 = _proc_argv0(pid)
        if argv0 and argv0 in exact_names:
            matches.append(pid)
    return matches


def _terminate_engine_processes(names: set[str], timeout: float = 2.0) -> dict[str, Any]:
    pids = _matching_pids(names)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            continue
    deadline = time.time() + timeout
    while time.time() < deadline and any(os.path.exists(f"/proc/{pid}") for pid in pids):
        time.sleep(0.05)
    killed: list[int] = []
    for pid in pids:
        if os.path.exists(f"/proc/{pid}"):
            try:
                os.kill(pid, signal.SIGKILL)
                killed.append(pid)
            except Exception:
                pass
    return {"matched_pids": pids, "force_killed_pids": killed}


def _ensure_executable(paths: list[str]) -> list[str]:
    changed: list[str] = []
    for path in paths:
        try:
            mode = os.stat(path).st_mode
            if not os.access(path, os.X_OK):
                os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                changed.append(path)
        except Exception:
            continue
    return changed


def _probe_binary(path: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": path,
        "executable": os.access(path, os.X_OK),
        "version": "",
        "returncode": None,
        "error": "",
    }
    if not result["executable"]:
        result["error"] = "not executable"
        return result
    for args in VERSION_ARGS:
        try:
            proc = subprocess.run([path, *args], capture_output=True, text=True, timeout=3)
            output = (proc.stdout or proc.stderr or "").strip()
            result["returncode"] = proc.returncode
            if output:
                result["version"] = output.splitlines()[0][:240]
            if proc.returncode in (0, 1, 2) or result["version"]:
                return result
        except OSError as exc:
            result["error"] = str(exc)
            if "Exec format error" in str(exc):
                return result
        except subprocess.TimeoutExpired:
            result["error"] = "version probe timed out"
            return result
        except Exception as exc:
            result["error"] = str(exc)
    return result


def check_engine_health(catalog: dict[str, dict[str, Any]], engine_id: str, engines_dir: str, cwd: str | None = None) -> dict[str, Any]:
    if engine_id == "muxquantum":
        return {
            "success": True,
            "engine": engine_id,
            "healthy": True,
            "message": "Built-in Mux/Quantum engine is available.",
            "results": [],
        }
    if engine_id not in catalog:
        return {"success": False, "engine": engine_id, "healthy": False, "message": "Unknown engine"}
    required = list(catalog[engine_id].get("bins") or [])
    paths = _engine_paths(catalog, engine_id, engines_dir, cwd)
    found_names = {os.path.basename(path) for path in paths}
    missing = [binary for binary in required if binary not in found_names]
    if not paths:
        return {
            "success": True,
            "engine": engine_id,
            "healthy": False,
            "message": "Engine binary was not found.",
            "paths": [],
            "results": [],
        }
    _ensure_executable(paths)
    results = [_probe_binary(path) for path in paths]
    executable_count = sum(1 for item in results if item.get("executable"))
    runnable_count = sum(1 for item in results if item.get("returncode") in (0, 1, 2) or item.get("version"))
    arch_errors = [item for item in results if "Exec format error" in (item.get("error") or "")]
    healthy = not missing and executable_count == len(required) and (
        runnable_count > 0 or executable_count == len(results)
    )
    if missing:
        message = "One or more required engine binaries are missing."
    elif runnable_count:
        message = "Engine binary is executable and responded to a version probe."
    elif arch_errors and executable_count:
        message = "Engine binary is executable but cannot be run on this development architecture."
    elif executable_count:
        message = "Engine binary is executable. Runtime tunnel config is required for a full start test."
    else:
        message = "Engine binary exists but is not executable."
    return {
        "success": True,
        "engine": engine_id,
        "healthy": healthy,
        "message": message,
        "missing_binaries": missing,
        "paths": paths,
        "results": results,
    }


def control_engine_process(
    catalog: dict[str, dict[str, Any]],
    engine_id: str,
    action: str,
    engines_dir: str,
    cwd: str | None = None,
) -> dict[str, Any]:
    if action not in {"start", "stop", "restart"}:
        return {"success": False, "error": "Invalid action"}
    if engine_id == "muxquantum":
        return {
            "success": True,
            "engine": engine_id,
            "action": action,
            "message": "Mux/Quantum is built into the panel and does not run as a separate process.",
            "health": check_engine_health(catalog, engine_id, engines_dir, cwd),
        }
    info = catalog.get(engine_id)
    if not info:
        return {"success": False, "error": "Unknown engine"}
    paths = _engine_paths(catalog, engine_id, engines_dir, cwd)
    if not paths:
        return {"success": False, "error": "Engine binary was not found", "matched": 0}
    names = {os.path.basename(path) for path in paths} | set(info.get("bins", []))
    terminated: dict[str, Any] = {"matched_pids": [], "force_killed_pids": []}
    if action in {"stop", "restart"}:
        terminated = _terminate_engine_processes(names)
    changed = _ensure_executable(paths) if action in {"start", "restart"} else []
    health = check_engine_health(catalog, engine_id, engines_dir, cwd)
    if action == "stop":
        message = "Engine runtime processes were stopped. Tunnels will start the engine again when their config is applied."
    elif action == "restart":
        message = "Engine binaries were refreshed, old runtime processes were stopped, and health was checked. Tunnels will relaunch from their config."
    else:
        message = "Engine binaries are ready. Engines without a standalone daemon start when a tunnel config launches them."
    return {
        "success": True,
        "engine": engine_id,
        "action": action,
        "matched": len(paths),
        "paths": paths,
        "chmod_changed": changed,
        "terminated": terminated,
        "health": health,
        "message": message,
    }


def safe_extract_tar(tf: tarfile.TarFile, dest: str) -> None:
    """Extract a tar archive rejecting absolute paths, traversal, and links."""
    try:
        tf.extractall(dest, filter="data")
        return
    except TypeError:
        pass
    dest_real = os.path.realpath(dest)
    for member in tf.getmembers():
        name = member.name
        if name.startswith("/") or name.startswith("\\") or ".." in name.replace("\\", "/").split("/"):
            raise ValueError(f"Unsafe path in archive: {name}")
        if member.issym() or member.islnk():
            raise ValueError(f"Unsupported link entry in archive: {name}")
        target = os.path.realpath(os.path.join(dest, name))
        if not target.startswith(dest_real + os.sep) and target != dest_real:
            raise ValueError(f"Unsafe path in archive: {name}")
    tf.extractall(dest)


def safe_extract_zip(zf: zipfile.ZipFile, dest: str) -> None:
    """Extract a zip archive rejecting absolute paths and traversal entries."""
    dest_real = os.path.realpath(dest)
    for name in zf.namelist():
        if name.startswith("/") or name.startswith("\\") or ".." in name.replace("\\", "/").split("/"):
            raise ValueError(f"Unsafe path in archive: {name}")
        target = os.path.realpath(os.path.join(dest, name))
        if not target.startswith(dest_real + os.sep) and target != dest_real:
            raise ValueError(f"Unsafe path in archive: {name}")
    zf.extractall(dest)


def install_engine_archive(
    catalog: dict[str, dict[str, Any]],
    engine_id: str,
    filename: str,
    content: bytes,
    engines_dir: str,
) -> list[str]:
    info = catalog.get(engine_id)
    if not info:
        raise ValueError("Unknown engine")
    wanted = set(info.get("bins", []))
    if not wanted:
        raise ValueError("This engine is built-in and has no external binary")
    os.makedirs(engines_dir, exist_ok=True)
    installed: list[str] = []
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(filename or "engine.bin")).strip(".") or "engine.bin"
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "extract")
        os.makedirs(root, exist_ok=True)
        archive = os.path.join(td, safe_name)
        archive_fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(archive_fd, "wb") as f:
            f.write(content)
        if safe_name.endswith(".zip"):
            with zipfile.ZipFile(archive) as zf:
                safe_extract_zip(zf, root)
        elif safe_name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive, "r:gz") as tf:
                safe_extract_tar(tf, root)
        elif safe_name.endswith((".tar.xz", ".txz")):
            with tarfile.open(archive, "r:xz") as tf:
                safe_extract_tar(tf, root)
        elif safe_name.endswith(".gz"):
            out_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name[:-3]).strip(".") or "engine.bin"
            out_path = os.path.join(root, out_name)
            if ".." in os.path.relpath(out_path, root).split(os.sep):
                raise ValueError("unsafe archive member path")
            out_fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            with gzip.open(archive, "rb") as gz, os.fdopen(out_fd, "wb") as out:
                out.write(gz.read())
        else:
            shutil.copy2(archive, os.path.join(root, safe_name))
        for dirpath, _, filenames in os.walk(root):
            for item in filenames:
                if item not in wanted:
                    continue
                dest = os.path.join(engines_dir, item)
                shutil.copy2(os.path.join(dirpath, item), dest)
                os.chmod(dest, os.stat(dest).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                installed.append(item)
    if not installed:
        raise ValueError("No expected engine binary found in archive")
    return installed
