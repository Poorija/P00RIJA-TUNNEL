"""System and modularity audit helpers for P00RIJA TUNNEL."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


REQUIRED_PACKAGE_FILES = (
    "P00RIJA.py",
    "install.sh",
    "install-panel.sh",
    "install-node.sh",
    "installer-ui.sh",
    "Pooriya-tunnel.sh",
    "p00rija-control.sh",
    "restore-panel-backup.sh",
    "p00rija-host-agent.py",
    "download_engines.py",
    "Dockerfile",
    "README.md",
    "README_FA.md",
    "LICENSE",
)

CORE_MODULES = (
    "p00rija_core/__init__.py",
    "p00rija_core/api.py",
    "p00rija_core/database.py",
    "p00rija_core/engines.py",
    "p00rija_core/links_api.py",
    "p00rija_core/metrics.py",
    "p00rija_core/runtime_api.py",
    "p00rija_core/security.py",
    "p00rija_core/tunnel_methods.py",
    "p00rija_core/system_audit.py",
    "p00rija_core/ui.py",
    "p00rija_core/backup_migration.py",
    "p00rija_core/engine_updates.py",
    "p00rija_core/versioning.py",
    "p00rija_core/host_control.py",
    "p00rija_core/handler_runtime.py",
)

MODULE_RESPONSIBILITIES = (
    {
        "module": "p00rija_core.api",
        "status": "extracted",
        "responsibility": "API route inventory plus extracted public/system/dashboard/node GET/SSH/POST dispatchers for the panel handler",
    },
    {
        "module": "p00rija_core.links_api",
        "status": "extracted",
        "responsibility": "link pause, live test, engine config preview, create/edit/delete, and port mapping dispatchers",
    },
    {
        "module": "p00rija_core.runtime_api",
        "status": "extracted",
        "responsibility": "runtime process/session/resource monitoring GET dispatchers",
    },
    {
        "module": "p00rija_core.database",
        "status": "extracted",
        "responsibility": "JSON persistence, default admin/settings bootstrap, bounded log storage",
    },
    {
        "module": "p00rija_core.security",
        "status": "extracted",
        "responsibility": "node enrollment tokens, key pairing, request signatures, TOTP, local TLS certificates",
    },
    {
        "module": "p00rija_core.metrics",
        "status": "extracted",
        "responsibility": "low-overhead CPU/RAM/network/host metrics and panel RSS measurement",
    },
    {
        "module": "p00rija_core.tunnel_methods",
        "status": "extracted",
        "responsibility": "tunnel profile catalog, profile scoring, Xray/Hysteria/Mux/AmneziaWG config builders",
    },
    {
        "module": "p00rija_core.engines",
        "status": "extracted",
        "responsibility": "engine catalog, binary discovery, health checks, process control, archive install",
    },
    {
        "module": "p00rija_core.ui",
        "status": "extracted",
        "responsibility": "embedded dashboard HTML/CSS/JS, PWA manifest, service worker, logo, font content typing",
    },
    {
        "module": "p00rija_core.handler_runtime",
        "status": "extracted",
        "responsibility": "threaded HTTP request handler, authenticated panel routes, node control endpoints, and response streaming",
    },
    {
        "module": "p00rija_core.engine_updates",
        "status": "extracted",
        "responsibility": "parallel GitHub release reachability checks and installed/latest engine version comparison",
    },
    {
        "module": "p00rija_core.versioning",
        "status": "extracted",
        "responsibility": "panel and node semantic-version compatibility classification",
    },
    {
        "module": "p00rija_core.host_control",
        "status": "extracted",
        "responsibility": "safe filesystem bridge to the privileged panel host agent",
    },
)


def _line_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _file_entry(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    return {
        "path": relative,
        "present": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "lines": _line_count(path) if path.is_file() else 0,
    }


def _engine_installed(root: Path, engines_dir: str, bins: list[str]) -> bool:
    if not bins:
        return True
    candidates = [
        Path(engines_dir),
        root / "engines",
        Path("/app/engines"),
        Path("/usr/local/bin"),
    ]
    for binary in bins:
        if not any((base / binary).exists() for base in candidates) and not shutil.which(binary):
            return False
    return True


def _manifest_summary(root: Path, engines_dir: str) -> dict[str, Any]:
    for path in (Path(engines_dir) / "manifest.json", root / "engines" / "manifest.json", Path("/app/engines/manifest.json")):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "present": True,
                "path": str(path),
                "engines": len(data.get("engines", {})),
                "failures": len(data.get("failures", {})),
                "generated_at": data.get("generated_at", ""),
            }
        except Exception as exc:
            return {"present": True, "path": str(path), "error": str(exc)}
    return {"present": False, "engines": 0, "failures": 0}


def build_system_audit(
    *,
    root: str | None,
    config_dir: str,
    engines_dir: str,
    db_data: dict[str, Any],
    engine_catalog: dict[str, dict[str, Any]],
    app_version: str,
) -> dict[str, Any]:
    project_root = Path(root or os.getcwd()).resolve()
    package_files = [_file_entry(project_root, item) for item in REQUIRED_PACKAGE_FILES]
    modules = [_file_entry(project_root, item) for item in CORE_MODULES]
    main_file = _file_entry(project_root, "P00RIJA.py")

    present_package = sum(1 for item in package_files if item["present"])
    present_modules = sum(1 for item in modules if item["present"])
    missing_package = [item["path"] for item in package_files if not item["present"]]
    missing_modules = [item["path"] for item in modules if not item["present"]]

    engine_items = []
    for engine_id, info in sorted(engine_catalog.items()):
        bins = list(info.get("bins") or [])
        installed = _engine_installed(project_root, engines_dir, bins)
        engine_items.append({
            "id": engine_id,
            "repo": info.get("repo", ""),
            "installed": installed,
            "bins": bins,
        })

    installed_engines = sum(1 for item in engine_items if item["installed"])
    manifest = _manifest_summary(project_root, engines_dir)

    score = 45
    score += round((present_package / max(1, len(REQUIRED_PACKAGE_FILES))) * 20)
    score += round((present_modules / max(1, len(CORE_MODULES))) * 20)
    score += round((installed_engines / max(1, len(engine_items))) * 15)
    handler_extracted = (project_root / "p00rija_core/handler_runtime.py").exists()
    if not handler_extracted and main_file["lines"] > 10000:
        score -= 10
    elif not handler_extracted and main_file["lines"] > 7000:
        score -= 6
    if missing_package:
        score -= min(15, len(missing_package) * 3)
    score = max(0, min(100, score))

    recommendations: list[str] = []
    if main_file["lines"] > 7000 and not handler_extracted:
        recommendations.append("Split the HTTP handler and runtime monitor out of P00RIJA.py in the next refactor pass.")
    elif main_file["lines"] > 4500 and not handler_extracted:
        recommendations.append("UI and major API groups are extracted. Continue by moving settings and runtime optimization controllers out of P00RIJA.py.")
    if missing_package:
        recommendations.append("Package is missing installer/runtime files: " + ", ".join(missing_package[:5]))
    if missing_modules:
        recommendations.append("Core module set is incomplete: " + ", ".join(missing_modules))
    missing_engines = [item["id"] for item in engine_items if not item["installed"]]
    if missing_engines:
        recommendations.append("Some optional engines are not bundled or installed: " + ", ".join(missing_engines[:8]))
    if not manifest.get("present"):
        recommendations.append("Engine manifest is missing; keep engines/manifest.json in offline packages for reproducible installs.")
    if not recommendations:
        recommendations.append("All required package, engine, handler, runtime, and modular readiness checks passed.")

    settings = db_data.get("settings", {}) if isinstance(db_data, dict) else {}
    stats = {
        "nodes": len(db_data.get("nodes", {})) if isinstance(db_data, dict) else 0,
        "links": len(db_data.get("links", {})) if isinstance(db_data, dict) else 0,
        "profiles": len(settings.get("tunnel_profiles", {})) if isinstance(settings, dict) else 0,
        "logs": len(db_data.get("logs", [])) if isinstance(db_data, dict) else 0,
    }

    capabilities = [
        {"id": "offline_package", "ready": not missing_package, "label": "Offline installer package"},
        {"id": "docker_panel_node", "ready": all((project_root / item).exists() for item in ("install-panel.sh", "install-node.sh", "Dockerfile")), "label": "Docker panel/node deployment"},
        {"id": "engine_catalog", "ready": installed_engines > 0, "label": "Bundled tunnel engines"},
        {"id": "profile_catalog", "ready": stats["profiles"] > 0, "label": "Tunneling profile catalog"},
        {"id": "runtime_monitor", "ready": True, "label": "Runtime/session/resource monitor"},
        {"id": "system_audit", "ready": True, "label": "Modularity and readiness audit"},
        {"id": "architecture_map", "ready": True, "label": "Module responsibility map"},
        {"id": "ui_module", "ready": (project_root / "p00rija_core/ui.py").exists(), "label": "Extracted dashboard UI module"},
        {"id": "api_registry", "ready": (project_root / "p00rija_core/api.py").exists(), "label": "API route registry"},
        {"id": "api_public_system_dispatch", "ready": (project_root / "p00rija_core/api.py").exists(), "label": "Extracted public/system API dispatcher"},
        {"id": "api_dashboard_dispatch", "ready": (project_root / "p00rija_core/api.py").exists(), "label": "Extracted dashboard/status/logs API dispatcher"},
        {"id": "api_nodes_get_dispatch", "ready": (project_root / "p00rija_core/api.py").exists(), "label": "Extracted nodes secrets/test/pause API dispatcher"},
        {"id": "api_nodes_ssh_dispatch", "ready": (project_root / "p00rija_core/api.py").exists(), "label": "Extracted node SSH API dispatcher"},
        {"id": "api_nodes_post_dispatch", "ready": (project_root / "p00rija_core/api.py").exists(), "label": "Extracted node create/edit/register/auto API dispatcher"},
        {"id": "api_links_get_dispatch", "ready": (project_root / "p00rija_core/links_api.py").exists(), "label": "Extracted link GET/test/config dispatcher"},
        {"id": "api_links_lifecycle_dispatch", "ready": (project_root / "p00rija_core/links_api.py").exists(), "label": "Extracted link create/edit/delete/ports API dispatcher"},
        {"id": "api_runtime_get_dispatch", "ready": (project_root / "p00rija_core/runtime_api.py").exists(), "label": "Extracted runtime monitor GET dispatcher"},
        {"id": "http_handler_runtime", "ready": handler_extracted, "label": "Extracted HTTP handler/runtime module"},
        {"id": "engine_update_checker", "ready": (project_root / "p00rija_core/engine_updates.py").exists(), "label": "Engine GitHub update checker"},
        {"id": "node_version_checker", "ready": (project_root / "p00rija_core/versioning.py").exists(), "label": "Panel/node version compatibility checker"},
    ]

    return {
        "version": app_version,
        "score": score,
        "root": str(project_root),
        "config_dir": config_dir,
        "main_file": main_file,
        "package_files": package_files,
        "modules": modules,
        "module_responsibilities": list(MODULE_RESPONSIBILITIES),
        "engines": {
            "total": len(engine_items),
            "installed": installed_engines,
            "missing": missing_engines,
            "manifest": manifest,
            "items": engine_items,
        },
        "stats": stats,
        "capabilities": capabilities,
        "recommendations": recommendations,
        "next_feature_candidates": [
            "Config backup/restore snapshots from the panel",
            "Scheduled self-audit with warning badge",
            "Scheduled engine and node compatibility checks with optional notifications",
            "Per-route adaptive carrier telemetry for automatic capacity tuning",
        ],
    }
