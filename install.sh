#!/usr/bin/env bash
# ==============================================================================
# P00RIJA TUNNEL - Unified Panel/Node Installer
# ==============================================================================
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-${0:-}}"
if [[ -n "$SCRIPT_SOURCE" && "$SCRIPT_SOURCE" != "bash" && "$SCRIPT_SOURCE" != "-bash" && "$SCRIPT_SOURCE" != "sh" && -e "$SCRIPT_SOURCE" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
else
  SCRIPT_DIR="$(pwd)"
fi
P00RIJA_REPO_TARBALL_URL="${P00RIJA_REPO_TARBALL_URL:-https://github.com/Poorija/P00RIJA-TUNNEL/archive/refs/heads/main.tar.gz}"
P00RIJA_INSTALL_WORKDIR="${P00RIJA_INSTALL_WORKDIR:-/opt/p00rija-install}"
PANEL_INSTALLER="$SCRIPT_DIR/install-panel.sh"
NODE_INSTALLER="$SCRIPT_DIR/install-node.sh"

err() { printf '[!] %s\n' "$*" >&2; exit 1; }
info() { printf '[*] %s\n' "$*"; }
ok() { printf '[+] %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
export TERM="${TERM:-xterm}"

usage() {
  cat <<'EOF'
P00RIJA TUNNEL unified installer

Usage:
  sudo bash install.sh                 # Interactive menu
  sudo bash install.sh --panel          # Fresh/install panel
  sudo bash install.sh --node           # Fresh/install node
  sudo bash install.sh --both           # Install panel, then node on this server
  sudo bash install.sh --update-panel   # Update panel without wiping data
  sudo bash install.sh --update-node    # Update node without wiping data
  sudo bash install.sh --update-both    # Update panel and node without wiping data

Options:
  --region ir|global    Select package/Docker mirror profile once for child installers
  --help                Show this help

Environment:
  P00RIJA_SERVER_REGION=ir|global       Same as --region
EOF
}

need_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    err "Run as root: sudo bash install.sh"
  fi
}

ensure_installers_present() {
  local tmp_dir archive src_dir
  if [[ ! -f "$PANEL_INSTALLER" || ! -f "$NODE_INSTALLER" || ! -f "$SCRIPT_DIR/installer-ui.sh" ]]; then
    have curl || err "curl is required to download the full installer package."
    have tar || err "tar is required to unpack the full installer package."
    info "Downloading the complete installer package from GitHub..."
    tmp_dir="${P00RIJA_INSTALL_WORKDIR}.tmp"
    archive="$tmp_dir/source.tar.gz"
    rm -rf "$tmp_dir"
    mkdir -p "$tmp_dir" "$P00RIJA_INSTALL_WORKDIR"
    curl -fsSL --retry 3 --connect-timeout 12 "$P00RIJA_REPO_TARBALL_URL" -o "$archive"
    tar -xzf "$archive" -C "$tmp_dir"
    src_dir="$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d -print -quit)"
    [[ -n "$src_dir" ]] || err "Could not unpack the GitHub installer package."
    cp -a "$src_dir"/. "$P00RIJA_INSTALL_WORKDIR"/
    rm -rf "$tmp_dir"
    SCRIPT_DIR="$P00RIJA_INSTALL_WORKDIR"
    PANEL_INSTALLER="$SCRIPT_DIR/install-panel.sh"
    NODE_INSTALLER="$SCRIPT_DIR/install-node.sh"
  fi
  [[ -f "$PANEL_INSTALLER" ]] || err "Missing install-panel.sh in $SCRIPT_DIR"
  [[ -f "$NODE_INSTALLER" ]] || err "Missing install-node.sh in $SCRIPT_DIR"
  chmod +x "$PANEL_INSTALLER" "$NODE_INSTALLER" 2>/dev/null || true
}

bootstrap_graphical_ui() {
  have whiptail && return 0
  [[ -t 0 && -t 1 ]] || return 0
  info "Installing whiptail for graphical terminal installer..."
  export DEBIAN_FRONTEND=noninteractive
  if have apt-get; then
    apt-get update -o Acquire::Retries=2 >/dev/null 2>&1 || true
    apt-get install -y whiptail >/dev/null 2>&1 || apt-get install -y whiptail || true
  elif have yum; then
    yum install -y newt >/dev/null 2>&1 || true
  elif have dnf; then
    dnf install -y newt >/dev/null 2>&1 || true
  elif have apk; then
    apk add newt >/dev/null 2>&1 || true
  fi
  if ! have whiptail; then
    printf '[!] whiptail is not available; falling back to text prompts.\n' >&2
  fi
}

source_ui() {
  if declare -F ui_menu >/dev/null 2>&1; then return 0; fi
  if [[ -f "$SCRIPT_DIR/installer-ui.sh" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/installer-ui.sh"
    return 0
  fi
  return 1
}

select_region_once() {
  local region=""
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(ir|IR)$ ]]; then
    export P00RIJA_SERVER_REGION="ir"
    return 0
  fi
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(global|GLOBAL|outside|OUTSIDE)$ ]]; then
    export P00RIJA_SERVER_REGION="global"
    return 0
  fi
  if source_ui && declare -F prepare_installer_ui >/dev/null 2>&1; then
    prepare_installer_ui region
    export P00RIJA_SERVER_REGION="$region"
    return 0
  fi
  printf '\nServer location:\n'
  printf '  1) Iran/internal mirrors\n'
  printf '  2) Global official repositories\n'
  local choice=""
  if ! read -r -p "Selection [default: 2]: " choice; then
    choice="2"
  fi
  choice="${choice:-2}"
  [[ "$choice" == "1" ]] && export P00RIJA_SERVER_REGION="ir" || export P00RIJA_SERVER_REGION="global"
}

run_panel_install() {
  info "Starting panel install..."
  bash "$PANEL_INSTALLER"
}

run_node_install() {
  info "Starting node install..."
  bash "$NODE_INSTALLER"
}

run_panel_update() {
  info "Updating panel while keeping /opt/p00rija/panel state..."
  P00RIJA_INSTALL_MODE=update bash "$PANEL_INSTALLER" --update
}

run_node_update() {
  info "Updating node while keeping /opt/p00rija/node state..."
  P00RIJA_INSTALL_MODE=update bash "$NODE_INSTALLER" --update
}

run_update_existing_targets() {
  local updated_any="false"
  if [[ -f /opt/p00rija/panel/p00rija_config.json ]]; then
    run_panel_update
    updated_any="true"
  else
    info "Panel config not found; skipping panel update."
  fi
  if [[ -f /opt/p00rija/node/p00rija_config.json ]]; then
    run_node_update
    updated_any="true"
  else
    info "Node config not found; skipping node update."
  fi
  [[ "$updated_any" == "true" ]] || err "No existing panel/node config found under /opt/p00rija. Run a fresh install first."
}

interactive_action() {
  local action=""
  if source_ui && declare -F ui_menu >/dev/null 2>&1; then
    ui_menu action "P00RIJA installer" "Choose what to do on this server." "1" \
      "1:Install panel" \
      "2:Install node" \
      "3:Install panel + node on this server" \
      "4:Update panel and keep data" \
      "5:Update node and keep data" \
      "6:Update panel + node and keep data"
    printf '%s\n' "$action"
    return 0
  fi
  printf '\nWhat do you want to do?\n'
  printf '  1) Install panel\n'
  printf '  2) Install node\n'
  printf '  3) Install panel + node on this server\n'
  printf '  4) Update panel and keep data\n'
  printf '  5) Update node and keep data\n'
  printf '  6) Update panel + node and keep data\n'
  if ! read -r -p "Selection [default: 1]: " action; then
    action="1"
  fi
  printf '%s\n' "${action:-1}"
}

main() {
  local action=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --panel) action="install-panel" ;;
      --node) action="install-node" ;;
      --both|--panel-node|--panel+node) action="install-both" ;;
      --update-panel) action="update-panel" ;;
      --update-node) action="update-node" ;;
      --update-both|--update-all) action="update-both" ;;
      --update)
        action="${action:-update-auto}"
        ;;
      --region)
        shift
        [[ $# -gt 0 ]] || err "--region requires ir or global"
        case "$1" in
          ir|IR) export P00RIJA_SERVER_REGION="ir" ;;
          global|GLOBAL|outside|OUTSIDE) export P00RIJA_SERVER_REGION="global" ;;
          *) err "Invalid region '$1'. Use ir or global." ;;
        esac
        ;;
      --help|-h)
        usage
        return 0
        ;;
      *)
        err "Unknown option: $1"
        ;;
    esac
    shift
  done

  if [[ -z "$action" ]]; then
    need_root
    ensure_installers_present
    source_ui || true
    declare -F ui_banner >/dev/null 2>&1 && ui_banner "Unified Panel / Node Installer"
    bootstrap_graphical_ui
    case "$(interactive_action)" in
      1) action="install-panel" ;;
      2) action="install-node" ;;
      3) action="install-both" ;;
      4) action="update-panel" ;;
      5) action="update-node" ;;
      6) action="update-both" ;;
      *) err "Invalid selection" ;;
    esac
  fi

  need_root
  ensure_installers_present
  source_ui || true
  if [[ -n "$action" ]]; then
    declare -F ui_banner >/dev/null 2>&1 && ui_banner "Unified Panel / Node Installer"
  fi
  bootstrap_graphical_ui
  select_region_once
  if declare -F ui_section >/dev/null 2>&1; then
    ui_section "Installation profile"
    ui_info "Server region: ${P00RIJA_SERVER_REGION}"
  else
    info "Using server region profile: ${P00RIJA_SERVER_REGION}"
  fi

  case "$action" in
    install-panel)
      run_panel_install
      ;;
    install-node)
      run_node_install
      ;;
    install-both)
      run_panel_install
      ok "Panel install finished. Now installing a node on the same server."
      run_node_install
      ;;
    update-panel)
      run_panel_update
      ;;
    update-node)
      run_node_update
      ;;
    update-both)
      run_update_existing_targets
      ;;
    update-auto)
      run_update_existing_targets
      ;;
    *)
      err "Unsupported action: $action"
      ;;
  esac
  ok "P00RIJA installer finished."
}

main "$@"
