#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash restore-panel-backup.sh <backup.enc> <new-api-url>" >&2
  exit 1
fi

BACKUP="${1:-}"
NEW_URL="${2:-}"
if [[ ! -f "$BACKUP" ]]; then
  echo "Encrypted backup file not found: $BACKUP" >&2
  exit 1
fi
if [[ ! "$NEW_URL" =~ ^https?:// ]]; then
  echo "New panel API URL is required, for example https://panel.example.com:8000" >&2
  exit 1
fi

# Prefer the installed wrapper (kept current by install-panel.sh updates) over an
# arbitrary downloaded or archive-bundled copy of this script; only fall back to
# this copy when no installed version exists. The path check prevents self-recursion.
INSTALLED_WRAPPER="/opt/p00rija/panel/restore-panel-backup.sh"
if [[ -f "$INSTALLED_WRAPPER" ]] && [[ "$(readlink -f "${BASH_SOURCE[0]:-$0}" 2>/dev/null)" != "$(readlink -f "$INSTALLED_WRAPPER" 2>/dev/null)" ]]; then
  echo "[i] Using installed restore wrapper: $INSTALLED_WRAPPER"
  exec bash "$INSTALLED_WRAPPER" "$BACKUP" "$NEW_URL"
fi

read -r -s -p "Backup password: " BACKUP_PASSWORD
echo
WORK="$(mktemp -d /tmp/p00rija-panel-restore.XXXXXX)"
cleanup() {
  rm -rf "$WORK"
}
trap cleanup EXIT

printf '%s' "$BACKUP_PASSWORD" | openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -pass stdin -in "$BACKUP" -out "$WORK/backup.tar.gz" 2>/dev/null || {
    echo "Decryption failed. Wrong password or corrupted backup." >&2
    exit 1
  }
# Clear the password from the environment ASAP (also cleared in the cleanup trap below).
unset BACKUP_PASSWORD 2>/dev/null || true

# Safe extraction: python3 tarfile with the strict "data" filter (no absolute paths,
# no ".." traversal, no symlinks/hardlinks, no device nodes). If the interpreter is
# too old for filter=, fall back to equally strict manual member validation.
python3 - "$WORK/backup.tar.gz" "$WORK" <<'PY'
import sys
import tarfile

archive_path, dest = sys.argv[1:3]

def member_is_safe(member):
    # Strict: relative paths only, no ".." components, no links at all.
    if member.name.startswith("/") or member.name.startswith("\\"):
        return False
    parts = member.name.replace("\\", "/").split("/")
    if ".." in parts:
        return False
    if member.issym() or member.islnk():
        return False
    if member.isdev():
        return False
    return True

try:
    with tarfile.open(archive_path, "r:gz") as tf:
        bad = [m.name for m in tf.getmembers() if not member_is_safe(m)]
        if bad:
            raise SystemExit(
                "Backup contains unsafe path entries (absolute, '..', or links): "
                + ", ".join(bad[:5])
            )
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            # Python without the filter= argument: members were validated strictly above.
            tf.extractall(dest)
except tarfile.TarError as exc:
    raise SystemExit(f"Backup archive is corrupted or truncated: {exc}")
PY

RESTORE_SCRIPT="$WORK/p00rija-panel-backup/restore-panel.sh"
if [[ ! -f "$RESTORE_SCRIPT" ]]; then
  echo "Restore script not found inside backup (expected p00rija-panel-backup/restore-panel.sh)." >&2
  exit 1
fi
bash "$RESTORE_SCRIPT" "$NEW_URL" 1
echo "Restore completed. The source panel, if still running, is not modified."
