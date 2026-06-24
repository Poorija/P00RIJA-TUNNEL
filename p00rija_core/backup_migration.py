"""Portable encrypted panel backups and staged SSH host migration."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


_HOST_RE = re.compile(r"^[A-Za-z0-9._-]{1,253}$")


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _valid_host(value: str) -> str:
    host = str(value or "").strip()
    if not host or not _HOST_RE.fullmatch(host):
        raise ValueError("Invalid destination host or IP")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if "." not in host and host != "localhost":
            raise ValueError("Destination must be a valid IP address or hostname")
    return host


def normalize_panel_url(value: str) -> str:
    raw = str(value or "").strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("New panel URL must include http:// or https:// and a valid host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("New panel URL must not contain credentials, query, or fragment")
    _valid_host(parsed.hostname)
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Invalid panel URL port")
    # Node control-plane endpoints always live at /api/* on the panel origin.
    # A copied browser URL may contain the optional /manage-* concealment path;
    # retaining it would produce /manage-*/api/* and every heartbeat would 404.
    return f"{parsed.scheme}://{parsed.netloc}"


def _restore_script() -> str:
    return r"""#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="/opt/p00rija/panel"
IMAGE="p00rija-tunnel:migrated"
NEW_URL="${1:-}"
REGENERATE_CERT="${2:-1}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run restore as root" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y docker.io openssl ca-certificates curl
  elif command -v yum >/dev/null 2>&1; then
    yum install -y docker openssl ca-certificates curl
  elif command -v apk >/dev/null 2>&1; then
    apk add docker openssl ca-certificates curl
  else
    echo "Unsupported package manager; install Docker manually" >&2
    exit 1
  fi
fi
systemctl enable --now docker >/dev/null 2>&1 || true
mkdir -p "$TARGET"
if [[ -f "$TARGET/p00rija_db.json" ]]; then
  BK="/opt/p00rija/backups/pre-migration-$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BK"
  cp -a "$TARGET" "$BK/panel"
fi
cp -a "$ROOT/state/." "$TARGET/"
cp -a "$ROOT/app/." "$TARGET/"
chmod 0600 "$TARGET/p00rija_db.json" "$TARGET/p00rija_config.json" 2>/dev/null || true

python3 - "$TARGET/p00rija_db.json" "$TARGET/p00rija_config.json" "$NEW_URL" <<'PY'
import json, sys
from urllib.parse import urlparse
db_path, config_path, new_url = sys.argv[1:4]
with open(db_path) as f:
    db = json.load(f)
with open(config_path) as f:
    config = json.load(f)
if new_url:
    parsed = urlparse(new_url)
    settings = db.setdefault("settings", {})
    settings["panel_host"] = parsed.hostname
    if parsed.port:
        settings["api_port"] = parsed.port
        config["api_port"] = parsed.port
with open(db_path, "w") as f:
    json.dump(db, f, indent=2)
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
PY

if [[ "$REGENERATE_CERT" == "1" && -n "$NEW_URL" ]]; then
  HOST="$(python3 -c 'import sys; from urllib.parse import urlparse; print(urlparse(sys.argv[1]).hostname)' "$NEW_URL")"
  mkdir -p "$TARGET/certs"
  openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
    -keyout "$TARGET/certs/key.pem" -out "$TARGET/certs/cert.pem" \
    -subj "/CN=$HOST" -addext "subjectAltName=DNS:$HOST,IP:$HOST" >/dev/null 2>&1 || \
  openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
    -keyout "$TARGET/certs/key.pem" -out "$TARGET/certs/cert.pem" \
    -subj "/CN=$HOST" >/dev/null 2>&1
  chmod 0600 "$TARGET/certs/key.pem"
fi

cat > "$TARGET/Dockerfile" <<'EOF'
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping curl openssl procps openssh-client sshpass ca-certificates iproute2 wireguard-tools stunnel4 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY P00RIJA.py /app/P00RIJA.py
COPY download_engines.py /app/download_engines.py
COPY p00rija_core/ /app/p00rija_core/
COPY fonts/ /app/fonts/
COPY install.sh install-panel.sh install-node.sh installer-ui.sh Pooriya-tunnel.sh p00rija-control.sh restore-panel-backup.sh p00rija-host-agent.py README.md README_FA.md LICENSE Dockerfile /app/
COPY engines/ /usr/local/bin/
CMD ["python3", "/app/P00RIJA.py"]
EOF

mkdir -p "$TARGET/fonts" "$TARGET/engines"
docker build -t "$IMAGE" -f "$TARGET/Dockerfile" "$TARGET"
read -r WEB_PORT API_PORT < <(python3 - "$TARGET/p00rija_config.json" "$TARGET/p00rija_db.json" <<'PY'
import json, sys
port, api = 8080, 8000
for path in sys.argv[1:]:
    try:
        data=json.load(open(path))
        data=data.get("settings", data)
        port=int(data.get("port", port))
        api=int(data.get("api_port", api))
    except Exception:
        pass
print(port, api)
PY
)
docker rm -f p00rija-panel >/dev/null 2>&1 || true
ARGS=(-p "$WEB_PORT:$WEB_PORT")
[[ "$API_PORT" == "$WEB_PORT" ]] || ARGS+=(-p "$API_PORT:$API_PORT")
docker run -d --name p00rija-panel --restart unless-stopped --cap-add NET_ADMIN \
  "${ARGS[@]}" -v "$TARGET:/opt/p00rija" "$IMAGE"
if [[ -f "$TARGET/p00rija-host-agent.py" ]] && command -v systemctl >/dev/null 2>&1; then
  chmod 0700 "$TARGET/p00rija-host-agent.py"
  mkdir -p "$TARGET/host_control/requests" "$TARGET/host_control/results"
  chmod 0700 "$TARGET/host_control" "$TARGET/host_control/requests" "$TARGET/host_control/results"
  cat > /etc/systemd/system/p00rija-host-agent.service <<EOF
[Unit]
Description=P00RIJA privileged host control agent
After=docker.service network-online.target
Requires=docker.service
[Service]
Type=simple
ExecStart=/usr/bin/python3 $TARGET/p00rija-host-agent.py
Restart=always
RestartSec=2
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now p00rija-host-agent.service
fi
echo "P00RIJA panel restored on ports $WEB_PORT / $API_PORT"
"""


def _remote_restore_script() -> str:
    """Return a Bash-only remote restore runner.

    The SSH account may use fish, csh, or another login shell. This file is
    always invoked explicitly with /bin/bash so login-shell syntax cannot
    reinterpret `set -e`, `read -r`, or the remaining restore pipeline.
    """
    return r"""#!/usr/bin/env bash
set -euo pipefail
REMOTE_DIR="${1:?remote directory is required}"
NEW_PANEL_URL="${2:?new panel URL is required}"
REGENERATE_CERT="${3:-1}"
cd "$REMOTE_DIR"
cleanup_plaintext() {
  rm -f panel-backup.tar.gz
  rm -rf p00rija-panel-backup
}
trap cleanup_plaintext EXIT
IFS= read -r BACKUP_PASS
printf '%s' "$BACKUP_PASS" | openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -pass stdin -in panel-backup.enc -out panel-backup.tar.gz
unset BACKUP_PASS
tar -xzf panel-backup.tar.gz
/bin/bash p00rija-panel-backup/restore-panel.sh "$NEW_PANEL_URL" "$REGENERATE_CERT"
docker exec p00rija-panel python3 -c 'import P00RIJA; print(P00RIJA.APP_BUILD)'
"""


def _copy_file(source: str, target: str) -> bool:
    if not os.path.isfile(source) or os.path.islink(source):
        return False
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy2(source, target)
    return True


def build_encrypted_backup(
    *,
    config_dir: str,
    app_root: str,
    engines_dir: str,
    password: str,
    app_version: str,
    app_build: str,
    include_engines: bool = True,
) -> dict[str, Any]:
    if len(str(password or "")) < 8:
        raise ValueError("Backup password must be at least 8 characters")
    backup_root = os.path.join(config_dir, "panel_backups")
    os.makedirs(backup_root, exist_ok=True)
    backup_id = time.strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(3).hex()
    output_path = os.path.join(backup_root, f"p00rija-panel-backup-{backup_id}.tar.gz.enc")
    with tempfile.TemporaryDirectory(prefix="p00rija-backup-") as work:
        payload = os.path.join(work, "payload")
        state_dir = os.path.join(payload, "state")
        app_dir = os.path.join(payload, "app")
        os.makedirs(state_dir)
        os.makedirs(app_dir)
        state_items = (
            "p00rija_db.json", "p00rija_config.json", "panel_secret",
            "ssh_credentials.enc", ".run_mode", ".network_mode", ".publish_ranges",
        )
        copied_state = []
        for name in state_items:
            if _copy_file(os.path.join(config_dir, name), os.path.join(state_dir, name)):
                copied_state.append(name)
        for directory in ("certs", "acme_webroot"):
            source = os.path.join(config_dir, directory)
            if os.path.isdir(source):
                shutil.copytree(source, os.path.join(state_dir, directory), dirs_exist_ok=True)
                copied_state.append(directory)

        app_files = (
            "P00RIJA.py", "download_engines.py", "install.sh", "install-panel.sh",
            "install-node.sh", "installer-ui.sh", "Pooriya-tunnel.sh",
            "p00rija-control.sh", "restore-panel-backup.sh", "p00rija-host-agent.py", "README.md",
            "README_FA.md", "LICENSE", "Dockerfile",
        )
        for name in app_files:
            source = os.path.join(app_root, name)
            if not os.path.isfile(source):
                source = os.path.join(config_dir, name)
            _copy_file(source, os.path.join(app_dir, name))
        for directory in ("p00rija_core", "fonts"):
            source = os.path.join(app_root, directory)
            if not os.path.isdir(source):
                source = os.path.join(config_dir, directory)
            if os.path.isdir(source):
                shutil.copytree(source, os.path.join(app_dir, directory), dirs_exist_ok=True)
        os.makedirs(os.path.join(app_dir, "engines"), exist_ok=True)
        if include_engines:
            source = os.path.join(config_dir, "engines")
            if os.path.isdir(source):
                for name in os.listdir(source):
                    _copy_file(os.path.join(source, name), os.path.join(app_dir, "engines", name))

        restore_path = os.path.join(payload, "restore-panel.sh")
        Path(restore_path).write_text(_restore_script(), encoding="utf-8")
        os.chmod(restore_path, 0o700)
        manifest = {
            "format": 1,
            "created_at": time.time(),
            "app_version": app_version,
            "app_build": app_build,
            "include_engines": bool(include_engines),
            "state_items": copied_state,
        }
        Path(os.path.join(payload, "manifest.json")).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        plain_path = os.path.join(work, "backup.tar.gz")
        with tarfile.open(plain_path, "w:gz") as archive:
            archive.add(payload, arcname="p00rija-panel-backup")
        proc = subprocess.run(
            [
                "openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000",
                "-salt", "-pass", "stdin", "-in", plain_path, "-out", output_path,
            ],
            input=str(password).encode(),
            capture_output=True,
            timeout=1800,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode(errors="replace") or "Backup encryption failed")
    os.chmod(output_path, 0o600)
    return {
        "backup_id": backup_id,
        "path": output_path,
        "filename": os.path.basename(output_path),
        "size": os.path.getsize(output_path),
        "sha256": _sha256(output_path),
        "include_engines": bool(include_engines),
    }


def list_server_backups(config_dir: str) -> list[dict[str, Any]]:
    backup_root = os.path.realpath(os.path.join(config_dir, "panel_backups"))
    if not os.path.isdir(backup_root):
        return []
    rows = []
    for name in os.listdir(backup_root):
        if not name.startswith("p00rija-panel-backup-") or not name.endswith(".tar.gz.enc"):
            continue
        path = os.path.realpath(os.path.join(backup_root, name))
        if not path.startswith(backup_root + os.sep) or not os.path.isfile(path):
            continue
        stat_result = os.stat(path)
        backup_id = name[len("p00rija-panel-backup-"):-len(".tar.gz.enc")]
        rows.append({
            "backup_id": backup_id,
            "filename": name,
            "size": stat_result.st_size,
            "created_at": stat_result.st_mtime,
            "sha256": _sha256(path),
        })
    rows.sort(key=lambda item: item["created_at"], reverse=True)
    return rows


def _safe_extract_backup(archive_path: str, destination: str) -> str:
    root = os.path.realpath(destination)
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            target = os.path.realpath(os.path.join(root, member.name))
            if target != root and not target.startswith(root + os.sep):
                raise ValueError("Backup archive contains an unsafe path")
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError("Backup archive contains unsupported links or devices")
        archive.extractall(root, members=members)
    payload = os.path.join(root, "p00rija-panel-backup")
    if not os.path.isfile(os.path.join(payload, "manifest.json")):
        raise ValueError("Backup manifest is missing")
    if not os.path.isfile(os.path.join(payload, "state", "p00rija_db.json")):
        raise ValueError("Backup panel database is missing")
    if not os.path.isfile(os.path.join(payload, "state", "p00rija_config.json")):
        raise ValueError("Backup panel configuration is missing")
    return payload


def _replace_tree(source: str, target: str) -> None:
    if os.path.isdir(target) and not os.path.islink(target):
        shutil.rmtree(target)
    elif os.path.lexists(target):
        os.unlink(target)
    shutil.copytree(source, target)


def restore_encrypted_backup(
    *,
    backup_path: str,
    password: str,
    config_dir: str,
    new_panel_url: str = "",
    regenerate_certificate: bool = False,
) -> dict[str, Any]:
    """Validate and restore a portable backup into the mounted panel state.

    The current state is snapshotted before any replacement. Application files
    are restored into the persistent config directory and become the next image
    build source; the running process is restarted by the HTTP layer so restored
    state is loaded cleanly.
    """
    if len(str(password or "")) < 8:
        raise ValueError("Backup password must be at least 8 characters")
    backup_path = os.path.realpath(str(backup_path or ""))
    if not os.path.isfile(backup_path):
        raise ValueError("Encrypted backup file was not found")
    normalized_url = normalize_panel_url(new_panel_url) if str(new_panel_url or "").strip() else ""
    os.makedirs(config_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p00rija-panel-restore-") as work:
        plain_path = os.path.join(work, "backup.tar.gz")
        proc = subprocess.run(
            [
                "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000",
                "-pass", "stdin", "-in", backup_path, "-out", plain_path,
            ],
            input=str(password).encode(),
            capture_output=True,
            timeout=1800,
        )
        if proc.returncode != 0:
            raise ValueError("Backup password is incorrect or the backup file is damaged")
        payload = _safe_extract_backup(plain_path, work)
        manifest = json.loads(Path(os.path.join(payload, "manifest.json")).read_text(encoding="utf-8"))
        state_dir = os.path.join(payload, "state")
        app_dir = os.path.join(payload, "app")
        rollback_dir = os.path.join(
            config_dir,
            "backups",
            "pre-restore-" + time.strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(2).hex(),
        )
        os.makedirs(rollback_dir, exist_ok=True)
        for name in (
            "p00rija_db.json", "p00rija_config.json", "panel_secret",
            "ssh_credentials.enc", ".run_mode", ".network_mode", ".publish_ranges",
        ):
            current = os.path.join(config_dir, name)
            if os.path.isfile(current):
                _copy_file(current, os.path.join(rollback_dir, name))
        for name in ("certs", "acme_webroot"):
            current = os.path.join(config_dir, name)
            if os.path.isdir(current):
                shutil.copytree(current, os.path.join(rollback_dir, name), dirs_exist_ok=True)

        restored = []
        for name in os.listdir(state_dir):
            source = os.path.join(state_dir, name)
            target = os.path.join(config_dir, name)
            if os.path.isdir(source):
                _replace_tree(source, target)
            elif os.path.isfile(source):
                _copy_file(source, target)
            restored.append(name)
        if os.path.isdir(app_dir):
            for name in os.listdir(app_dir):
                source = os.path.join(app_dir, name)
                target = os.path.join(config_dir, name)
                if os.path.isdir(source):
                    _replace_tree(source, target)
                elif os.path.isfile(source):
                    _copy_file(source, target)

        if normalized_url:
            parsed = urlparse(normalized_url)
            db_path = os.path.join(config_dir, "p00rija_db.json")
            config_path = os.path.join(config_dir, "p00rija_config.json")
            db_data = json.loads(Path(db_path).read_text(encoding="utf-8"))
            config_data = json.loads(Path(config_path).read_text(encoding="utf-8"))
            settings = db_data.setdefault("settings", {})
            settings["panel_host"] = parsed.hostname
            if parsed.port:
                settings["api_port"] = parsed.port
                config_data["api_port"] = parsed.port
            Path(db_path).write_text(json.dumps(db_data, ensure_ascii=False, indent=2), encoding="utf-8")
            Path(config_path).write_text(json.dumps(config_data, ensure_ascii=False, indent=2), encoding="utf-8")
            if regenerate_certificate:
                cert_dir = os.path.join(config_dir, "certs")
                os.makedirs(cert_dir, exist_ok=True)
                host = parsed.hostname or "localhost"
                cert_proc = subprocess.run(
                    [
                        "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
                        "-days", "825", "-keyout", os.path.join(cert_dir, "key.pem"),
                        "-out", os.path.join(cert_dir, "cert.pem"), "-subj", f"/CN={host}",
                        "-addext", f"subjectAltName=DNS:{host}",
                    ],
                    capture_output=True,
                    timeout=120,
                )
                if cert_proc.returncode != 0:
                    raise RuntimeError(cert_proc.stderr.decode(errors="replace") or "Certificate generation failed")
                os.chmod(os.path.join(cert_dir, "key.pem"), 0o600)
        for protected in ("p00rija_db.json", "p00rija_config.json", "panel_secret", "ssh_credentials.enc"):
            path = os.path.join(config_dir, protected)
            if os.path.isfile(path):
                os.chmod(path, 0o600)
    return {
        "success": True,
        "filename": os.path.basename(backup_path),
        "sha256": _sha256(backup_path),
        "manifest": manifest,
        "restored_state": restored,
        "rollback_path": rollback_dir,
        "new_panel_url": normalized_url,
        "restart_required": True,
    }


def migrate_backup_over_ssh(
    *,
    backup_path: str,
    backup_password: str,
    host: str,
    port: int,
    username: str,
    password: str,
    new_panel_url: str,
    regenerate_certificate: bool = True,
) -> dict[str, Any]:
    host = _valid_host(host)
    new_panel_url = normalize_panel_url(new_panel_url)
    port = int(port or 22)
    if not 1 <= port <= 65535:
        raise ValueError("Invalid SSH port")
    username = str(username or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}", username):
        raise ValueError("Invalid SSH username")
    if not password:
        raise ValueError("Destination SSH password is required")
    if not shutil.which("sshpass"):
        raise RuntimeError("sshpass is required in the panel container")

    destination = f"{username}@{host}"
    remote_dir = f"/tmp/p00rija-migration-{int(time.time())}-{os.urandom(3).hex()}"
    ssh_env = dict(os.environ)
    ssh_env["SSHPASS"] = password
    ssh_base = [
        "sshpass", "-e", "ssh", "-p", str(port),
        "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=12", destination,
    ]
    scp_base = [
        "sshpass", "-e", "scp", "-P", str(port),
        "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=12",
    ]
    uid_check = subprocess.run(
        ssh_base + ["id -u"],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
        env=ssh_env,
    )
    if uid_check.stdout.strip() != "0":
        raise ValueError("Destination SSH user must be root")
    subprocess.run(ssh_base + [f"mkdir -p {shlex.quote(remote_dir)}"], check=True, capture_output=True, timeout=20, env=ssh_env)
    remote_backup = f"{remote_dir}/panel-backup.enc"
    subprocess.run(
        scp_base + [backup_path, f"{destination}:{remote_backup}"],
        check=True,
        capture_output=True,
        timeout=3600,
        env=ssh_env,
    )
    with tempfile.NamedTemporaryFile("w", prefix="p00rija-remote-restore-", suffix=".sh", delete=False) as script:
        script.write(_remote_restore_script())
        local_script = script.name
    remote_script = f"{remote_dir}/restore-remote.sh"
    try:
        subprocess.run(
            scp_base + [local_script, f"{destination}:{remote_script}"],
            check=True,
            capture_output=True,
            timeout=120,
            env=ssh_env,
        )
    finally:
        try:
            os.unlink(local_script)
        except OSError:
            pass
    remote_command = (
        f"/bin/bash {shlex.quote(remote_script)} {shlex.quote(remote_dir)} "
        f"{shlex.quote(new_panel_url)} {'1' if regenerate_certificate else '0'}"
    )
    proc = subprocess.run(
        ssh_base + [remote_command],
        capture_output=True,
        text=True,
        input=f"{backup_password}\n",
        timeout=3600,
        env=ssh_env,
    )
    if proc.returncode != 0:
        subprocess.run(
            ssh_base + [f"rm -rf {shlex.quote(remote_dir)}"],
            capture_output=True,
            timeout=30,
            env=ssh_env,
        )
        raise RuntimeError((proc.stderr or proc.stdout or "Destination restore failed")[-4000:])
    parsed = urlparse(new_panel_url)
    verify_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    verify = subprocess.run(
        ssh_base + [
            f"curl -skf --max-time 15 {parsed.scheme}://127.0.0.1:{int(verify_port)}/api/public-settings >/dev/null"
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env=ssh_env,
    )
    if verify.returncode != 0:
        raise RuntimeError("Destination panel was installed but its HTTPS health check failed")
    subprocess.run(
        ssh_base + [f"rm -rf {shlex.quote(remote_dir)}"],
        capture_output=True,
        timeout=30,
        env=ssh_env,
    )
    return {
        "success": True,
        "host": host,
        "port": port,
        "new_panel_url": new_panel_url,
        "remote_output": proc.stdout[-1000:],
    }
