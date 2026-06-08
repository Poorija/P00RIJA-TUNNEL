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

IMAGE_TAGS=("p00rija-tunnel:1.3.0" "p00rija-tunnel:latest")
CLI_PATH="/usr/local/bin/p00rija"
MANAGER_PATH="/usr/local/bin/Pooriya-tunnel"
INSTALL_WORKDIR="${P00RIJA_INSTALL_WORKDIR:-/opt/p00rija-install}"
REPO_TARBALL_URL="${P00RIJA_REPO_TARBALL_URL:-https://github.com/Poorija/P00RIJA-TUNNEL/archive/refs/heads/main.tar.gz}"
REPO_RAW_PY_URL="${P00RIJA_REPO_RAW_PY_URL:-https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/P00RIJA.py}"

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
  sudo p00rija update            # update panel/node from GitHub or a local zip/tar package
  sudo p00rija panel start|stop|restart|logs|status|reset-admin|uninstall|purge
  sudo p00rija panel update
  sudo p00rija node  start|stop|restart|logs|status|uninstall|purge
  sudo p00rija node  update
  sudo p00rija uninstall        # remove containers/services/images, keep /opt/p00rija data
  sudo p00rija purge            # remove containers/services/images/configs/CLI files

Notes:
  reset-admin keeps panel settings, nodes, links, certificates, and tunnel configs.
  purge removes P00RIJA application files but does not uninstall Docker itself.
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
  if ! have docker; then
    echo "docker-missing"
    return
  fi
  if docker ps --format '{{.Names}}' | grep -qx "$container"; then
    echo "running"
  elif docker ps -a --format '{{.Names}}' | grep -qx "$container"; then
    echo "stopped"
  else
    echo "missing"
  fi
}

service_status() {
  local service="$1"
  if systemctl list-unit-files "$service" >/dev/null 2>&1; then
    if systemctl is-active --quiet "$service"; then
      echo "running"
    else
      echo "stopped"
    fi
  else
    echo "missing"
  fi
}

show_one_status() {
  local target="$1" dir container service role url
  dir=$(target_dir "$target")
  container=$(target_container "$target")
  service=$(target_service "$target")
  role="$target"
  url=""
  if [[ -f "$dir/p00rija_config.json" ]]; then
    role=$(python3 - "$dir/p00rija_config.json" <<'PY' 2>/dev/null || echo "$target"
import json, sys
data=json.load(open(sys.argv[1]))
print(data.get("role","unknown"))
PY
)
  fi
  if [[ "$target" == "panel" && -f "$dir/p00rija_db.json" ]]; then
    url=$(python3 - "$dir/p00rija_db.json" <<'PY' 2>/dev/null || true
import json, sys
data=json.load(open(sys.argv[1]))
s=data.get("settings",{})
scheme="https" if s.get("panel_tls", True) else "http"
host=s.get("panel_host","localhost")
port=s.get("port","")
print(f"{scheme}://{host}:{port}" if port else "")
PY
)
  fi
  printf '%-7s role=%-9s docker=%-8s systemd=%-8s dir=%s\n' "$target" "$role" "$(container_status "$container")" "$(service_status "$service")" "$dir"
  [[ -n "$url" ]] && printf '        panel-url=%s\n' "$url"
}

status_all() {
  local any=0 target
  for target in panel node legacy; do
    if target_exists "$target"; then
      show_one_status "$target"
      any=1
    fi
  done
  [[ "$any" == "1" ]] || echo "No P00RIJA installation found."
}

start_target() {
  local target="$1" container service
  container=$(target_container "$target")
  service=$(target_service "$target")
  if have docker && docker ps -a --format '{{.Names}}' | grep -qx "$container"; then
    docker start "$container"
  elif systemctl list-unit-files "$service" >/dev/null 2>&1; then
    systemctl start "$service"
  else
    echo "[!] $target is not installed." >&2
    return 1
  fi
}

stop_target() {
  local target="$1" container service
  container=$(target_container "$target")
  service=$(target_service "$target")
  have docker && docker stop "$container" >/dev/null 2>&1 || true
  systemctl stop "$service" >/dev/null 2>&1 || true
}

restart_target() {
  local target="$1" container service
  container=$(target_container "$target")
  service=$(target_service "$target")
  if have docker && docker ps -a --format '{{.Names}}' | grep -qx "$container"; then
    docker restart "$container"
  elif systemctl list-unit-files "$service" >/dev/null 2>&1; then
    systemctl restart "$service"
  else
    echo "[!] $target is not installed." >&2
    return 1
  fi
}

logs_target() {
  local target="$1" container service
  container=$(target_container "$target")
  service=$(target_service "$target")
  if have docker && docker ps -a --format '{{.Names}}' | grep -qx "$container"; then
    docker logs -f "$container"
  elif systemctl list-unit-files "$service" >/dev/null 2>&1; then
    journalctl -u "$service" -n 100 -f
  else
    echo "[!] $target is not installed." >&2
    return 1
  fi
}

reset_panel_admin() {
  local db="$PANEL_DIR/p00rija_db.json"
  if [[ ! -f "$db" && -f "$LEGACY_DIR/p00rija_db.json" ]]; then
    db="$LEGACY_DIR/p00rija_db.json"
  fi
  [[ -f "$db" ]] || { echo "[!] Panel DB not found." >&2; return 1; }
  local username password password2
  read -r -p "New admin username [admin]: " username
  username=${username:-admin}
  while [[ -z "${password:-}" ]]; do
    read -r -s -p "New admin password: " password
    echo
  done
  read -r -s -p "Repeat new admin password: " password2
  echo
  [[ "$password" == "$password2" ]] || { echo "[!] Passwords do not match." >&2; return 1; }
  python3 - "$db" "$username" "$password" <<'PY'
import hashlib, json, os, sys, tempfile
path, username, password = sys.argv[1:4]
with open(path) as f:
    data=json.load(f)
data.setdefault("admin", {})["username"] = username
data["admin"]["password_hash"] = hashlib.sha256(password.encode()).hexdigest()
fd, tmp = tempfile.mkstemp(prefix=".p00rija-db-", dir=os.path.dirname(path))
with os.fdopen(fd, "w") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
os.chmod(tmp, 0o600)
os.replace(tmp, path)
PY
  echo "[+] Admin credentials reset. Settings/nodes/tunnels were kept."
  restart_target panel >/dev/null 2>&1 || true
}

remove_target_runtime() {
  local target="$1" container service
  container=$(target_container "$target")
  service=$(target_service "$target")
  have docker && docker rm -f "$container" >/dev/null 2>&1 || true
  systemctl stop "$service" >/dev/null 2>&1 || true
  systemctl disable "$service" >/dev/null 2>&1 || true
  rm -f "/etc/systemd/system/$service"
  systemctl daemon-reload >/dev/null 2>&1 || true
}

uninstall_target_keep_data() {
  local target="$1"
  remove_target_runtime "$target"
  echo "[+] Removed $target runtime. Configuration data was kept."
}

remove_images() {
  local image
  if have docker; then
    for image in "${IMAGE_TAGS[@]}"; do
      docker rmi -f "$image" >/dev/null 2>&1 || true
    done
  fi
}

purge_all() {
  local confirm
  echo "[!] This will remove panel, node, configs, certificates, bundled engines, CLI files, and P00RIJA Docker images."
  echo "[!] Docker itself and generic system packages will not be uninstalled."
  read -r -p "Type PURGE to continue: " confirm
  [[ "$confirm" == "PURGE" ]] || { echo "Aborted."; return 1; }
  remove_target_runtime panel
  remove_target_runtime node
  remove_target_runtime legacy
  remove_images
  rm -rf "$APP_ROOT"
  rm -f "$CLI_PATH" "$MANAGER_PATH" "/usr/local/bin/pahlavi-tunnel"
  rm -f /etc/cron.daily/p00rija-cert-renew
  rm -f /etc/sysctl.d/99-p00rija-tunnel.conf
  if [[ -f /etc/sysctl.conf ]]; then
    cp -f /etc/sysctl.conf "/etc/sysctl.conf.p00rija-purge-backup.$(date +%Y%m%d_%H%M%S)" || true
    sed -i '/^net\.core\.default_qdisc=fq$/d;/^net\.ipv4\.tcp_congestion_control=bbr$/d;/^net\.ipv6\.conf\..*\.disable_ipv6 = 1$/d' /etc/sysctl.conf || true
  fi
  echo "[+] P00RIJA has been purged from this server."
}

uninstall_all_keep_data() {
  local target
  for target in panel node legacy; do
    remove_target_runtime "$target"
  done
  remove_images
  echo "[+] Removed P00RIJA runtimes and images. Data under $APP_ROOT was kept."
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

extract_version_from_file() {
  local file="$1"
  [[ -f "$file" ]] || { echo "unknown"; return 0; }
  awk -F'"' '/^APP_VERSION = / {print $2; exit}' "$file"
}

local_installed_version() {
  if [[ -f "$PANEL_DIR/P00RIJA.py" ]]; then
    extract_version_from_file "$PANEL_DIR/P00RIJA.py"
  elif [[ -f "$NODE_DIR/P00RIJA.py" ]]; then
    extract_version_from_file "$NODE_DIR/P00RIJA.py"
  elif [[ -f "$INSTALL_WORKDIR/P00RIJA.py" ]]; then
    extract_version_from_file "$INSTALL_WORKDIR/P00RIJA.py"
  else
    echo "unknown"
  fi
}

remote_github_version() {
  local tmp=""
  tmp=$(mktemp /tmp/p00rija-version.XXXXXX)
  if curl -fsSL --max-time 10 "$REPO_RAW_PY_URL" -o "$tmp"; then
    extract_version_from_file "$tmp"
  else
    echo "unknown"
  fi
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
    *.zip)
      python3 - "$package_path" "$tmp_dir" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as zf:
    zf.extractall(sys.argv[2])
PY
      ;;
    *.tar.gz|*.tgz)
      tar -xzf "$package_path" -C "$tmp_dir"
      ;;
    *)
      echo "[!] Unsupported package. Use .zip, .tar.gz, or .tgz." >&2
      return 1
      ;;
  esac
  src_dir="$(find "$tmp_dir" -mindepth 1 -maxdepth 2 -type f -name install.sh -printf '%h\n' | head -n1)"
  [[ -n "$src_dir" ]] || src_dir="$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d -print -quit)"
  [[ -n "$src_dir" ]] || { echo "[!] Could not find installer files in package." >&2; return 1; }
  rm -rf "${INSTALL_WORKDIR:?}/"*
  cp -a "$src_dir"/. "$INSTALL_WORKDIR"/
  rm -rf "$tmp_dir"
}

choose_update_target() {
  local default="${1:-}" choice=""
  if [[ "$default" =~ ^(panel|node|all)$ ]]; then
    echo "$default"
    return 0
  fi
  echo "Choose update target:"
  echo "  1) Panel"
  echo "  2) Node"
  echo "  3) Panel and node"
  read -r -p "Selection [default: 1]: " choice
  choice=${choice:-1}
  case "$choice" in
    2) echo "node" ;;
    3) echo "all" ;;
    *) echo "panel" ;;
  esac
}

run_package_installer() {
  local target="$1"
  [[ -f "$INSTALL_WORKDIR/install-panel.sh" && -f "$INSTALL_WORKDIR/install-node.sh" ]] || {
    echo "[!] Installer scripts are missing in $INSTALL_WORKDIR." >&2
    return 1
  }
  case "$target" in
    panel) bash "$INSTALL_WORKDIR/install-panel.sh" ;;
    node) bash "$INSTALL_WORKDIR/install-node.sh" ;;
    all)
      bash "$INSTALL_WORKDIR/install-panel.sh"
      bash "$INSTALL_WORKDIR/install-node.sh"
      ;;
    *) echo "[!] Unknown update target: $target" >&2; return 1 ;;
  esac
}

update_from_package() {
  local requested_target="${1:-}" source_choice="" package_path="" target="" local_version="" remote_version="" continue_choice=""
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
    if [[ -n "$remote_version" && "$remote_version" != "unknown" && "$local_version" == "$remote_version" ]]; then
      read -r -p "Same version is already installed. Continue anyway? [y/N]: " continue_choice
      [[ "$continue_choice" =~ ^[Yy]$ ]] || { echo "Aborted."; return 0; }
    elif [[ "$remote_version" != "unknown" ]]; then
      echo "[+] A GitHub package/version is available. Continuing with update."
    fi
    download_github_package
  fi
  target="$(choose_update_target "$requested_target")"
  echo "[*] Existing panel/node data will be kept. Installers update code and containers unless you explicitly choose fresh reinstall."
  run_package_installer "$target"
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
            reset-admin)
              [[ "$target" == "panel" || "$target" == "legacy" ]] || { echo "[!] reset-admin is only for panel." >&2; exit 1; }
              reset_panel_admin
              ;;
            update) update_from_package "$target" ;;
            uninstall) uninstall_target_keep_data "$target" ;;
            purge) purge_all ;;
            *) usage; exit 1 ;;
          esac
          ;;
        *) usage; exit 1 ;;
      esac
      ;;
  esac
}

main "$@"
