#!/usr/bin/env bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-${0:-}}"
if [[ -n "$SCRIPT_SOURCE" && "$SCRIPT_SOURCE" != "bash" && "$SCRIPT_SOURCE" != "-bash" && "$SCRIPT_SOURCE" != "sh" && -e "$SCRIPT_SOURCE" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
else
  SCRIPT_DIR="$(pwd)"
fi
P00RIJA_REPO_TARBALL_URL="${P00RIJA_REPO_TARBALL_URL:-https://github.com/Poorija/P00RIJA-TUNNEL/archive/refs/heads/main.tar.gz}"
P00RIJA_INSTALL_WORKDIR="${P00RIJA_INSTALL_WORKDIR:-/opt/p00rija-install}"

bootstrap_installer_package() {
  local required_file="$1" tmp_dir="" archive="" src_dir=""
  [[ -f "$SCRIPT_DIR/$required_file" ]] && return 0
  if [[ -f "$P00RIJA_INSTALL_WORKDIR/$required_file" ]]; then
    SCRIPT_DIR="$P00RIJA_INSTALL_WORKDIR"
    return 0
  fi
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "[!] Installer package is missing. Run as root so it can download the full package: sudo bash install.sh" >&2
    exit 1
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "[!] curl is required to bootstrap the GitHub installer package." >&2
    exit 1
  fi
  if ! command -v tar >/dev/null 2>&1; then
    echo "[!] tar is required to bootstrap the GitHub installer package." >&2
    exit 1
  fi
  echo "[*] Full installer package is missing. Downloading from GitHub..."
  tmp_dir="${P00RIJA_INSTALL_WORKDIR}.tmp"
  archive="$tmp_dir/source.tar.gz"
  rm -rf "$tmp_dir"
  mkdir -p "$tmp_dir" "$P00RIJA_INSTALL_WORKDIR"
  curl -fsSL "$P00RIJA_REPO_TARBALL_URL" -o "$archive"
  tar -xzf "$archive" -C "$tmp_dir"
  src_dir="$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d -print -quit)"
  if [[ -z "$src_dir" ]]; then
    echo "[!] Could not unpack the GitHub installer package." >&2
    exit 1
  fi
  cp -a "$src_dir"/. "$P00RIJA_INSTALL_WORKDIR"/
  rm -rf "$tmp_dir"
  SCRIPT_DIR="$P00RIJA_INSTALL_WORKDIR"
}

bootstrap_installer_package "installer-ui.sh"
if [[ -f "$SCRIPT_DIR/installer-ui.sh" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/installer-ui.sh"
else
  echo "[!] installer-ui.sh is missing. Run this installer from the offline package directory." >&2
  exit 1
fi

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "[!] Please run as root: sudo bash install.sh" >&2
  exit 1
fi

main() {
  local region="" choice=""
  prepare_installer_ui region
  export P00RIJA_SERVER_REGION="$region"
  ui_menu choice "P00RIJA TUNNEL Installer" "Main installer. You can install or update the panel, a node, or both. Existing installations are updated without deleting data unless you explicitly choose a fresh reinstall." "1" \
    "1:Install/update central panel" \
    "2:Install/update internal/external node" \
    "3:Install/update panel, then node"
  if [[ "$choice" == "1" ]]; then
    exec bash "$SCRIPT_DIR/install-panel.sh"
  elif [[ "$choice" == "2" ]]; then
    exec bash "$SCRIPT_DIR/install-node.sh"
  else
    bash "$SCRIPT_DIR/install-panel.sh"
    ui_msg "Panel step finished" "The panel step is finished.\n\nIf this is a fresh install, open the panel, create/add the node entry, copy the node token and private key, then continue with the node installer."
    exec bash "$SCRIPT_DIR/install-node.sh"
  fi
}

main "$@"
