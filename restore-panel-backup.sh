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

read -r -s -p "Backup password: " BACKUP_PASSWORD
echo
WORK="$(mktemp -d /tmp/p00rija-panel-restore.XXXXXX)"
cleanup() {
  rm -rf "$WORK"
}
trap cleanup EXIT

printf '%s' "$BACKUP_PASSWORD" | openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -pass stdin -in "$BACKUP" -out "$WORK/backup.tar.gz"
unset BACKUP_PASSWORD
tar -xzf "$WORK/backup.tar.gz" -C "$WORK"
bash "$WORK/p00rija-panel-backup/restore-panel.sh" "$NEW_URL" 1
echo "Restore completed. The source panel, if still running, is not modified."
