#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/p00rija"
PANEL_DIR="$APP_ROOT/panel"
NODE_DIR="$APP_ROOT/node"
LEGACY_DIR="$APP_ROOT"
PANEL_CONTAINER="p00rija-panel"
NODE_CONTAINER="p00rija-node"
LEGACY_CONTAINER="p00rija-tunnel"
PANEL_SERVICE="p00rija-panel.service"
NODE_SERVICE="p00rija-node.service"
LEGACY_SERVICE="p00rija-tunnel.service"
CLI_PATH="/usr/local/bin/p00rija"
MANAGER_PATH="/usr/local/bin/Pooriya-tunnel"
INSTALL_WORKDIR="${P00RIJA_INSTALL_WORKDIR:-/opt/p00rija-install}"
REPO_TARBALL_URL="${P00RIJA_REPO_TARBALL_URL:-https://github.com/Poorija/P00RIJA-TUNNEL/archive/refs/heads/main.tar.gz}"
REPO_RAW_PY_URL="${P00RIJA_REPO_RAW_PY_URL:-https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/P00RIJA.py}"
IMAGE_TAGS=("p00rija-tunnel:1.9.95" "p00rija-tunnel:latest")

need_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "[!] Run as root: sudo p00rija $*" >&2
    exit 1
  fi
}

have() { command -v "$1" >/dev/null 2>&1; }

usage() {
  cat <<'EOF'
P00RIJA server control

Usage:
  sudo p00rija status
  sudo p00rija start|stop|restart|logs
  sudo p00rija update [panel|node|all]
  sudo p00rija panel start|stop|restart|logs|status|update|reset-admin|uninstall
  sudo p00rija node  start|stop|restart|logs|status|update|uninstall
  sudo p00rija uninstall     # remove runtimes/images, keep /opt/p00rija data
  sudo p00rija purge         # remove runtimes/images/configs/CLI files
EOF
}

target_dir() {
  case "${1:-}" in
    panel) echo "$PANEL_DIR" ;;
    node) echo "$NODE_DIR" ;;
    legacy) echo "$LEGACY_DIR" ;;
    *) echo "" ;;
  esac
}

target_container() {
  case "${1:-}" in
    panel) echo "$PANEL_CONTAINER" ;;
    node) echo "$NODE_CONTAINER" ;;
    legacy) echo "$LEGACY_CONTAINER" ;;
    *) echo "" ;;
  esac
}

target_service() {
  case "${1:-}" in
    panel) echo "$PANEL_SERVICE" ;;
    node) echo "$NODE_SERVICE" ;;
    legacy) echo "$LEGACY_SERVICE" ;;
    *) echo "" ;;
  esac
}

target_exists() {
  local target="$1" dir container service
  dir=$(target_dir "$target")
  container=$(target_container "$target")
  service=$(target_service "$target")
  [[ -f "$dir/p00rija_config.json" ]] && return 0
  have docker && docker ps -a --format '{{.Names}}' | grep -qx "$container" && return 0
  systemctl list-unit-files "$service" >/dev/null 2>&1 && return 0
  return 1
}

targets_found() {
  local found=()
  target_exists panel && found+=("panel")
  target_exists node && found+=("node")
  target_exists legacy && found+=("legacy")
  printf '%s\n' "${found[@]}"
}

container_status() {
  local container="$1"
  if ! have docker; then echo "docker-missing"; return; fi
  if docker ps --format '{{.Names}}' | grep -qx "$container"; then echo "running"
  elif docker ps -a --format '{{.Names}}' | grep -qx "$container"; then echo "stopped"
  else echo "missing"; fi
}

service_status() {
  local service="$1"
  if systemctl list-unit-files "$service" >/dev/null 2>&1; then
    systemctl is-active --quiet "$service" && echo "running" || echo "stopped"
  else
    echo "missing"
  fi
}

extract_json_value() {
  local path="$1" expr="$2" default="${3:-}"
  [[ -f "$path" ]] || { echo "$default"; return; }
  python3 - "$path" "$expr" "$default" <<'PY'
import json, sys
path, expr, default = sys.argv[1:4]
try:
    data = json.load(open(path))
    value = data
    for part in expr.split("."):
        value = value.get(part, {}) if isinstance(value, dict) else {}
    print(value if value not in ({}, None, "") else default)
except Exception:
    print(default)
PY
}

show_one_status() {
  local target="$1" dir role url
  dir=$(target_dir "$target")
  role=$(extract_json_value "$dir/p00rija_config.json" role "$target")
  printf '%-7s role=%-9s docker=%-8s systemd=%-8s dir=%s\n' \
    "$target" "$role" "$(container_status "$(target_container "$target")")" "$(service_status "$(target_service "$target")")" "$dir"
  if [[ "$target" == "panel" ]]; then
    local host port
    host=$(extract_json_value "$dir/p00rija_db.json" settings.panel_host localhost)
    port=$(extract_json_value "$dir/p00rija_db.json" settings.port "")
    [[ -n "$port" ]] && url="https://${host}:${port}" && printf '        panel-url=%s\n' "$url"
  fi
}

status_all() {
  local any=0 target
  for target in panel node legacy; do
    if target_exists "$target"; then show_one_status "$target"; any=1; fi
  done
  [[ "$any" == "1" ]] || echo "No P00RIJA installation found."
}

start_target() {
  local target="$1" container service
  container=$(target_container "$target")
  service=$(target_service "$target")
  if have docker && docker ps -a --format '{{.Names}}' | grep -qx "$container"; then docker start "$container"
  elif systemctl list-unit-files "$service" >/dev/null 2>&1; then systemctl start "$service"
  else echo "[!] $target is not installed." >&2; return 1; fi
}

stop_target() {
  local target="$1"
  have docker && docker stop "$(target_container "$target")" >/dev/null 2>&1 || true
  systemctl stop "$(target_service "$target")" >/dev/null 2>&1 || true
}

restart_target() {
  local target="$1" container service
  container=$(target_container "$target")
  service=$(target_service "$target")
  if have docker && docker ps -a --format '{{.Names}}' | grep -qx "$container"; then docker restart "$container"
  elif systemctl list-unit-files "$service" >/dev/null 2>&1; then systemctl restart "$service"
  else echo "[!] $target is not installed." >&2; return 1; fi
}

logs_target() {
  local target="$1" container service
  container=$(target_container "$target")
  service=$(target_service "$target")
  if have docker && docker ps -a --format '{{.Names}}' | grep -qx "$container"; then docker logs -f "$container"
  elif systemctl list-unit-files "$service" >/dev/null 2>&1; then journalctl -u "$service" -n 100 -f
  else echo "[!] $target is not installed." >&2; return 1; fi
}

reset_panel_admin() {
  local db="$PANEL_DIR/p00rija_db.json" username password password2
  [[ -f "$db" ]] || db="$LEGACY_DIR/p00rija_db.json"
  [[ -f "$db" ]] || { echo "[!] Panel DB not found." >&2; return 1; }
  read -r -p "New admin username [admin]: " username
  username=${username:-admin}
  while [[ -z "${password:-}" ]]; do read -r -s -p "New admin password: " password; echo; done
  read -r -s -p "Repeat new admin password: " password2; echo
  [[ "$password" == "$password2" ]] || { echo "[!] Passwords do not match." >&2; return 1; }
  python3 - "$db" "$username" "$password" <<'PY'
import hashlib, json, os, sys, tempfile
path, username, password = sys.argv[1:4]
data = json.load(open(path))
data.setdefault("admin", {})["username"] = username
data["admin"]["password_hash"] = hashlib.sha256(password.encode()).hexdigest()
fd, tmp = tempfile.mkstemp(prefix=".p00rija-db-", dir=os.path.dirname(path))
with os.fdopen(fd, "w") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
os.chmod(tmp, 0o600)
os.replace(tmp, path)
PY
  restart_target panel >/dev/null 2>&1 || true
  echo "[+] Admin credentials reset. Settings, nodes, tunnels, and certificates were kept."
}

remove_target_runtime() {
  local target="$1" service
  service=$(target_service "$target")
  have docker && docker rm -f "$(target_container "$target")" >/dev/null 2>&1 || true
  systemctl stop "$service" >/dev/null 2>&1 || true
  systemctl disable "$service" >/dev/null 2>&1 || true
  rm -f "/etc/systemd/system/$service"
  systemctl daemon-reload >/dev/null 2>&1 || true
}

remove_images() {
  local image
  have docker || return 0
  for image in "${IMAGE_TAGS[@]}"; do docker rmi -f "$image" >/dev/null 2>&1 || true; done
}

extract_version_from_file() {
  local file="$1"
  [[ -f "$file" ]] || { echo "unknown"; return; }
  awk -F'"' '/^APP_VERSION = / {print $2; exit}' "$file"
}

local_installed_version() {
  if [[ -f "$PANEL_DIR/P00RIJA.py" ]]; then extract_version_from_file "$PANEL_DIR/P00RIJA.py"
  elif [[ -f "$NODE_DIR/P00RIJA.py" ]]; then extract_version_from_file "$NODE_DIR/P00RIJA.py"
  elif [[ -f "$LEGACY_DIR/P00RIJA.py" ]]; then extract_version_from_file "$LEGACY_DIR/P00RIJA.py"
  else echo "unknown"; fi
}

remote_github_version() {
  local tmp
  tmp=$(mktemp /tmp/p00rija-version.XXXXXX)
  if curl -fsSL --max-time 10 "$REPO_RAW_PY_URL" -o "$tmp"; then extract_version_from_file "$tmp"; else echo "unknown"; fi
  rm -f "$tmp"
}

download_github_package() {
  local tmp_dir archive src_dir
  have curl || { echo "[!] curl is required for GitHub update." >&2; return 1; }
  have tar || { echo "[!] tar is required for GitHub update." >&2; return 1; }
  tmp_dir="${INSTALL_WORKDIR}.tmp"
  archive="$tmp_dir/source.tar.gz"
  rm -rf "$tmp_dir"
  mkdir -p "$tmp_dir" "$INSTALL_WORKDIR"
  echo "[*] Downloading P00RIJA package from GitHub..."
  curl -fsSL "$REPO_TARBALL_URL" -o "$archive"
  tar -xzf "$archive" -C "$tmp_dir"
  src_dir="$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d -print -quit)"
  [[ -n "$src_dir" ]] || { echo "[!] GitHub package unpack failed." >&2; return 1; }
  rm -rf "${INSTALL_WORKDIR:?}/"*
  cp -a "$src_dir"/. "$INSTALL_WORKDIR"/
  rm -rf "$tmp_dir"
}

unpack_local_package() {
  local package_path="$1" tmp_dir src_dir
  [[ -f "$package_path" ]] || { echo "[!] Package file not found: $package_path" >&2; return 1; }
  tmp_dir="${INSTALL_WORKDIR}.tmp"
  rm -rf "$tmp_dir"
  mkdir -p "$tmp_dir" "$INSTALL_WORKDIR"
  case "$package_path" in
    *.zip) python3 - "$package_path" "$tmp_dir" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as zf:
    zf.extractall(sys.argv[2])
PY
      ;;
    *.tar.gz|*.tgz) tar -xzf "$package_path" -C "$tmp_dir" ;;
    *) echo "[!] Unsupported package. Use .zip, .tar.gz, or .tgz." >&2; return 1 ;;
  esac
  src_dir="$(find "$tmp_dir" -mindepth 1 -maxdepth 3 -type f -name install.sh -printf '%h\n' | head -n1)"
  [[ -n "$src_dir" ]] || { echo "[!] Could not find installer files in package." >&2; return 1; }
  rm -rf "${INSTALL_WORKDIR:?}/"*
  cp -a "$src_dir"/. "$INSTALL_WORKDIR"/
  rm -rf "$tmp_dir"
}

choose_update_target() {
  local requested="${1:-}" choice
  [[ "$requested" =~ ^(panel|node|all)$ ]] && { echo "$requested"; return; }
  echo "Choose update target:"
  echo "  1) Panel"
  echo "  2) Node"
  echo "  3) Panel and node"
  read -r -p "Selection [default: 1]: " choice
  choice=${choice:-1}
  case "$choice" in 2) echo "node" ;; 3) echo "all" ;; *) echo "panel" ;; esac
}

run_package_installer() {
  local target="$1"
  [[ -f "$INSTALL_WORKDIR/install-panel.sh" && -f "$INSTALL_WORKDIR/install-node.sh" ]] || {
    echo "[!] Installer scripts are missing in $INSTALL_WORKDIR." >&2
    return 1
  }
  case "$target" in
    panel) P00RIJA_INSTALL_MODE=update bash "$INSTALL_WORKDIR/install-panel.sh" --update ;;
    node) P00RIJA_INSTALL_MODE=update bash "$INSTALL_WORKDIR/install-node.sh" --update ;;
    all)
      P00RIJA_INSTALL_MODE=update bash "$INSTALL_WORKDIR/install-panel.sh" --update
      P00RIJA_INSTALL_MODE=update bash "$INSTALL_WORKDIR/install-node.sh" --update
      ;;
    *) echo "[!] Unknown update target: $target" >&2; return 1 ;;
  esac
}

update_from_package() {
  local requested_target="${1:-}" source_choice package_path target local_version remote_version continue_choice
  echo "P00RIJA update"
  echo "  1) GitHub"
  echo "  2) Local zip/tar package"
  read -r -p "Update source [default: 1]: " source_choice
  source_choice=${source_choice:-1}
  if [[ "$source_choice" == "2" ]]; then
    read -r -p "Local package path (.zip/.tar.gz): " package_path
    unpack_local_package "$package_path"
  else
    local_version="$(local_installed_version)"
    remote_version="$(remote_github_version)"
    echo "[*] Installed version: ${local_version:-unknown}"
    echo "[*] GitHub version: ${remote_version:-unknown}"
    if [[ "$remote_version" != "unknown" && "$local_version" == "$remote_version" ]]; then
      read -r -p "Same version is already installed. Continue anyway? [y/N]: " continue_choice
      [[ "$continue_choice" =~ ^[Yy]$ ]] || { echo "Aborted."; return 0; }
    fi
    download_github_package
  fi
  target="$(choose_update_target "$requested_target")"
  echo "[*] Existing panel/node data will be kept. Installers will refresh code, image, and containers."
  run_package_installer "$target"
}

run_for_found_targets() {
  local action="$1" target found=0
  while read -r target; do
    [[ -n "$target" ]] || continue
    found=1
    "$action" "$target"
  done < <(targets_found)
  [[ "$found" == "1" ]] || echo "[!] No P00RIJA installation found." >&2
}

uninstall_all_keep_data() {
  local target
  for target in panel node legacy; do remove_target_runtime "$target"; done
  remove_images
  echo "[+] Removed P00RIJA runtimes and images. Data under $APP_ROOT was kept."
}

purge_all() {
  local confirm
  echo "[!] This removes panel, node, configs, certificates, bundled engines, CLI files, and P00RIJA images."
  read -r -p "Type PURGE to continue: " confirm
  [[ "$confirm" == "PURGE" ]] || { echo "Aborted."; return 1; }
  uninstall_all_keep_data
  rm -rf "$APP_ROOT" "$INSTALL_WORKDIR"
  rm -f "$CLI_PATH" "$MANAGER_PATH" "/usr/local/bin/pahlavi-tunnel"
  echo "[+] P00RIJA has been purged from this server."
}

main() {
  local target="${1:-}" action="${2:-}"
  case "$target" in
    ""|-h|--help|help) usage ;;
    *)
      need_root "$@"
      case "$target" in
        status) status_all ;;
        update) update_from_package "${action:-}" ;;
        start) run_for_found_targets start_target ;;
        stop) run_for_found_targets stop_target ;;
        restart) run_for_found_targets restart_target ;;
        logs)
          local first
          first=$(targets_found | head -n1 || true)
          [[ -n "$first" ]] && logs_target "$first" || echo "[!] No P00RIJA installation found." >&2
          ;;
        uninstall) uninstall_all_keep_data ;;
        purge) purge_all ;;
        panel|node|legacy)
          case "$action" in
            start) start_target "$target" ;;
            stop) stop_target "$target" ;;
            restart) restart_target "$target" ;;
            logs) logs_target "$target" ;;
            status) show_one_status "$target" ;;
            update) update_from_package "$target" ;;
            reset-admin)
              [[ "$target" == "panel" || "$target" == "legacy" ]] || { echo "[!] reset-admin is only for panel." >&2; exit 1; }
              reset_panel_admin
              ;;
            uninstall) remove_target_runtime "$target"; echo "[+] Removed $target runtime. Data was kept." ;;
            *) usage; exit 1 ;;
          esac
          ;;
        *) usage; exit 1 ;;
      esac
      ;;
  esac
}

main "$@"
