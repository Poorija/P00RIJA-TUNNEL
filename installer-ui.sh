#!/usr/bin/env bash

have() { command -v "$1" >/dev/null 2>&1; }
export TERM="${TERM:-xterm}"

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  UI_RESET=$'\033[0m'
  UI_BOLD=$'\033[1m'
  UI_DIM=$'\033[2m'
  UI_CYAN=$'\033[38;5;45m'
  UI_PURPLE=$'\033[38;5;141m'
  UI_GREEN=$'\033[38;5;48m'
  UI_YELLOW=$'\033[38;5;220m'
  UI_RED=$'\033[38;5;203m'
else
  UI_RESET="" UI_BOLD="" UI_DIM="" UI_CYAN="" UI_PURPLE="" UI_GREEN="" UI_YELLOW="" UI_RED=""
fi

ui_columns() {
  local cols=80
  if [[ -t 1 ]] && have tput; then cols=$(tput cols 2>/dev/null || echo 80); fi
  [[ "$cols" =~ ^[0-9]+$ ]] || cols=80
  printf '%s' "$cols"
}

ui_center() {
  local text="$1" plain="$1" cols pad
  plain="${plain//$'\033'\[[0-9;]*m/}"
  cols=$(ui_columns)
  pad=$(( (cols - ${#plain}) / 2 ))
  (( pad < 0 )) && pad=0
  printf '%*s%s\n' "$pad" "" "$text"
}

ui_rule() {
  local cols line
  cols=$(ui_columns)
  (( cols > 86 )) && cols=86
  printf -v line '%*s' "$cols" ''
  printf '%s%s%s\n' "$UI_DIM" "${line// /─}" "$UI_RESET"
}

ui_banner() {
  local context="${1:-Unified Installer}"
  [[ "${P00RIJA_BANNER_SHOWN:-}" == "$context" ]] && return 0
  export P00RIJA_BANNER_SHOWN="$context"
  printf '\n'
  ui_center "${UI_CYAN}${UI_BOLD}██████╗  ██████╗  ██████╗ ██████╗ ██╗     ██╗ █████╗${UI_RESET}"
  ui_center "${UI_CYAN}${UI_BOLD}██╔══██╗██╔═████╗██╔═████╗██╔══██╗██║     ██║██╔══██╗${UI_RESET}"
  ui_center "${UI_PURPLE}${UI_BOLD}██████╔╝██║██╔██║██║██╔██║██████╔╝██║     ██║███████║${UI_RESET}"
  ui_center "${UI_PURPLE}${UI_BOLD}██╔═══╝ ████╔╝██║████╔╝██║██╔══██╗██║██   ██║██╔══██║${UI_RESET}"
  ui_center "${UI_CYAN}${UI_BOLD}██║     ╚██████╔╝╚██████╔╝██║  ██║██║╚█████╔╝██║  ██║${UI_RESET}"
  ui_center "${UI_CYAN}${UI_BOLD}╚═╝      ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝ ╚════╝ ╚═╝  ╚═╝${UI_RESET}"
  printf '\n'
  ui_center "${UI_BOLD}Multi-node reverse tunnel orchestration${UI_RESET}"
  ui_center "${UI_DIM}Secure • Adaptive • Observable • ${context}${UI_RESET}"
  ui_rule
}

ui_log() { printf '%s\n' "$*"; }
ui_info() { ui_log "${UI_CYAN}  ◆${UI_RESET} $*"; }
ui_ok() { ui_log "${UI_GREEN}  ✔${UI_RESET} $*"; }
ui_warn() { ui_log "${UI_YELLOW}  ⚠${UI_RESET} $*"; }
ui_error() { ui_log "${UI_RED}  ✖${UI_RESET} $*"; }
ui_section() {
  printf '\n%s%s  %s%s\n' "$UI_BOLD" "$UI_PURPLE" "$*" "$UI_RESET"
  ui_rule
}
ui_msg() {
  local title="${1:-P00RIJA}" text="${2:-}"
  if have whiptail && [[ -t 0 && -t 1 ]]; then
    whiptail --title "$title" --msgbox "$text" 18 78 || true
  else
    printf '\n%s%s%s\n%s\n' "$UI_BOLD" "$title" "$UI_RESET" "$text"
  fi
}

P00RIJA_UBUNTU_IR_MIRRORS="${P00RIJA_UBUNTU_IR_MIRRORS:-https://mirror.iranserver.com/ubuntu/}"
P00RIJA_DEBIAN_IR_MIRRORS="${P00RIJA_DEBIAN_IR_MIRRORS:-https://deb.debian.org/debian/}"
P00RIJA_DOCKER_IR_MIRRORS="${P00RIJA_DOCKER_IR_MIRRORS:-https://docker.iranserver.com}"

detect_server_region() {
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(ir|IR)$ ]]; then echo "ir"; return 0; fi
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(global|GLOBAL|outside|OUTSIDE)$ ]]; then echo "global"; return 0; fi
  local cc=""
  cc=$(curl -fsSL --max-time 3 http://ip-api.com/line?fields=countryCode 2>/dev/null || true)
  [[ -z "$cc" ]] && cc=$(curl -fsSL --max-time 3 https://ipinfo.io/country 2>/dev/null || true)
  [[ -z "$cc" ]] && cc=$(curl -fsSL --max-time 3 https://ifconfig.co/country-iso 2>/dev/null || true)
  cc="${cc//$'\r'/}"
  cc="${cc//$'\n'/}"
  [[ "$cc" == "IR" ]] && echo "ir" || echo "global"
}

simple_menu() {
  local prompt="$1"
  local default="$2"
  local choice=""
  local item=""
  shift 2
  printf '\n%s\n' "$prompt" >&2
  for item in "$@"; do
    printf '  %s) %s\n' "${item%%:*}" "${item#*:}" >&2
  done
  while true; do
    if ! read -r -p "Selection [default: ${default}]: " choice; then
      choice="$default"
    fi
    choice=${choice:-$default}
    for item in "$@"; do
      if [[ "$choice" == "${item%%:*}" ]]; then echo "$choice"; return 0; fi
    done
    printf '[!] Invalid selection.\n' >&2
  done
}

ui_menu() {
  local outvar="$1"
  local title="$2"
  local text="$3"
  local default="$4"
  local menu_choice=""
  shift 4
  if have whiptail && [[ -t 0 && -t 1 ]]; then
    local args=()
    local item=""
    for item in "$@"; do args+=("${item%%:*}" "${item#*:}"); done
    menu_choice=$(whiptail --title "$title" --default-item "$default" --menu "$text" 20 78 10 "${args[@]}" 3>&1 1>&2 2>&3) || exit 1
  else
    menu_choice=$(simple_menu "$text" "$default" "$@")
  fi
  printf -v "$outvar" '%s' "${menu_choice:-$default}"
}

ui_input() {
  local outvar="$1"
  local title="$2"
  local text="$3"
  local default="${4:-}"
  local input_value=""
  if have whiptail && [[ -t 0 && -t 1 ]]; then
    input_value=$(whiptail --title "$title" --inputbox "$text" 10 78 "$default" 3>&1 1>&2 2>&3) || exit 1
  else
    if ! read -r -p "${text} [${default}]: " input_value; then
      input_value="$default"
    fi
    input_value=${input_value:-$default}
  fi
  printf -v "$outvar" '%s' "$input_value"
}

ui_password() {
  local outvar="$1"
  local title="$2"
  local text="$3"
  local input_value=""
  if have whiptail && [[ -t 0 && -t 1 ]]; then
    input_value=$(whiptail --title "$title" --passwordbox "$text" 10 78 3>&1 1>&2 2>&3) || exit 1
  else
    if [[ ! -t 0 ]]; then
      return 1
    fi
    read -r -s -p "$text: " input_value
    printf '\n' >&2
  fi
  printf -v "$outvar" '%s' "$input_value"
}

write_apt_sources() {
  local distro="$1" codename="$2" mirror="$3"
  mkdir -p /etc/apt/sources.list.d
  if [[ "$distro" =~ ^(ubuntu|linuxmint|pop)$ ]]; then
    cat > /etc/apt/sources.list.d/p00rija-iran.sources <<EOF
Types: deb
URIs: ${mirror}
Suites: ${codename} ${codename}-updates ${codename}-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
  elif [[ "$distro" == "debian" ]]; then
    cat > /etc/apt/sources.list.d/p00rija-iran.sources <<EOF
Types: deb
URIs: ${mirror}
Suites: ${codename} ${codename}-updates
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF
  fi
}

configure_package_mirrors() {
  local region="$1"
  [[ "$region" == "ir" && -f /etc/os-release && -d /etc/apt ]] || return 0
  # shellcheck disable=SC1091
  . /etc/os-release
  local distro="${ID:-}" codename="${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}"
  [[ -n "$codename" && "$distro" =~ ^(ubuntu|linuxmint|pop|debian)$ ]] || return 0
  local backup_dir="/etc/apt/p00rija-backup-$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$backup_dir"
  find /etc/apt -maxdepth 2 \( -name '*.list' -o -name '*.sources' \) -type f -print0 2>/dev/null | while IFS= read -r -d '' src; do
    cp -f "$src" "$backup_dir/$(basename "$src").bak" || true
    mv -f "$src" "$backup_dir/$(basename "$src")" || true
  done
  ui_info "APT sources backed up to ${backup_dir}"
  apt_update_with_retries
}

apt_update_with_retries() {
  if ! have apt-get; then return 0; fi
  local distro="" codename="" mirrors="" mirror=""
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    distro="${ID:-}"
    codename="${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}"
  fi
  if [[ "${P00RIJA_SERVER_REGION:-}" == "ir" && -n "$codename" ]]; then
    [[ "$distro" =~ ^(ubuntu|linuxmint|pop)$ ]] && mirrors="$P00RIJA_UBUNTU_IR_MIRRORS" || mirrors="$P00RIJA_DEBIAN_IR_MIRRORS"
    for mirror in $mirrors; do
      write_apt_sources "$distro" "$codename" "$mirror"
      apt-get clean >/dev/null 2>&1 || true
      rm -rf /var/lib/apt/lists/partial
      ui_info "Running apt update using ${mirror}..."
      if apt-get update -o Acquire::Retries=2; then
        ui_ok "APT mirror is healthy: ${mirror}"
        return 0
      fi
      ui_warn "APT mirror failed: ${mirror}"
    done
  fi
  apt-get update -o Acquire::Retries=2
}

configure_docker_mirror() {
  local region="$1"
  mkdir -p /etc/docker
  python3 - "$region" "$P00RIJA_DOCKER_IR_MIRRORS" <<'PY'
import json, os, sys
path = "/etc/docker/daemon.json"
region, mirrors_text = sys.argv[1:3]
data = {}
if os.path.exists(path) and os.path.getsize(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        data = {}
mirrors = [item.strip() for item in mirrors_text.split() if item.strip()]
if region == "ir" and mirrors:
    data["registry-mirrors"] = mirrors
else:
    data.pop("registry-mirrors", None)
tmp = f"{path}.tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
os.replace(tmp, path)
PY
  systemctl restart docker >/dev/null 2>&1 || true
  if [[ "$region" == "ir" ]]; then
    ui_info "Docker registry mirror configured: ${P00RIJA_DOCKER_IR_MIRRORS}"
    if [[ "${P00RIJA_SKIP_DOCKER_MIRROR_PROBE:-0}" != "1" ]] && have docker; then
      if timeout 45 docker pull hello-world:latest >/dev/null 2>&1; then
        ui_ok "Docker mirror probe succeeded."
      else
        ui_warn "Docker mirror probe failed. Keeping the mirror config, but image pulls may need network access to Docker Hub."
      fi
    fi
  fi
}

prepare_installer_ui() {
  local outvar="$1"
  local detected=""
  local def_choice=""
  local choice=""
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(ir|IR)$ ]]; then
    printf -v "$outvar" '%s' "ir"
    export P00RIJA_SERVER_REGION="ir"
    configure_package_mirrors "ir"
    return 0
  fi
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(global|GLOBAL|outside|OUTSIDE)$ ]]; then
    printf -v "$outvar" '%s' "global"
    export P00RIJA_SERVER_REGION="global"
    configure_package_mirrors "global"
    return 0
  fi
  detected=$(detect_server_region)
  def_choice="2"
  [[ "$detected" == "ir" ]] && def_choice="1"
  ui_menu choice "Server location" "Choose repository/mirror profile. Iran mode uses IranServer for Ubuntu packages and official Docker registries." "$def_choice" \
    "1:Iran / IranServer Ubuntu mirror" \
    "2:Global official repositories"
  [[ "$choice" == "1" ]] && printf -v "$outvar" '%s' "ir" || printf -v "$outvar" '%s' "global"
  export P00RIJA_SERVER_REGION="${!outvar}"
  configure_package_mirrors "${!outvar}"
}
