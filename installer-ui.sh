#!/usr/bin/env bash

have() { command -v "$1" >/dev/null 2>&1; }

ui_log() { printf '%s\n' "$*"; }
ui_info() { ui_log "[*] $*"; }
ui_ok() { ui_log "[+] $*"; }
ui_warn() { ui_log "[!] $*"; }

P00RIJA_UBUNTU_IR_MIRRORS="${P00RIJA_UBUNTU_IR_MIRRORS:-https://mirror.arvancloud.ir/ubuntu/ https://ubuntu.shatel.ir/ubuntu/ https://repo.iut.ac.ir/repo/ubuntu/ http://ir.archive.ubuntu.com/ubuntu/}"
P00RIJA_DEBIAN_IR_MIRRORS="${P00RIJA_DEBIAN_IR_MIRRORS:-https://archive.debian.petiak.ir/debian/ https://mirror.arvancloud.ir/debian/ http://deb.debian.org/debian/}"

is_private_or_local_ip() {
  python3 - "$1" <<'PY' >/dev/null 2>&1
import ipaddress, sys
ip = ipaddress.ip_address(sys.argv[1])
raise SystemExit(0 if (ip.is_private or ip.is_loopback or ip.is_link_local) else 1)
PY
}

detect_local_ip() {
  local ip=""
  ip=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
  if [[ -z "$ip" ]] && have ip; then
    ip=$(ip -o -4 addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -n1 || true)
  fi
  echo "${ip:-unknown}"
}

detect_public_ip() {
  local ip=""
  ip=$(curl -fsSL --max-time 4 https://api.ipify.org 2>/dev/null || true)
  [[ -z "$ip" ]] && ip=$(curl -fsSL --max-time 4 https://ifconfig.co/ip 2>/dev/null || true)
  [[ -z "$ip" ]] && ip=$(curl -fsSL --max-time 4 http://ip-api.com/line?fields=query 2>/dev/null || true)
  ip="${ip//$'\r'/}"
  ip="${ip//$'\n'/}"
  echo "$ip"
}

lookup_ip_country() {
  local ip="$1" result=""
  [[ -n "$ip" && "$ip" != "unknown" ]] || { echo "Unknown|"; return 0; }
  result=$(curl -fsSL --max-time 4 "http://ip-api.com/line/${ip}?fields=country,countryCode" 2>/dev/null || true)
  result="${result//$'\r'/}"
  if [[ -n "$result" ]]; then
    local country code
    country=$(printf '%s\n' "$result" | sed -n '1p')
    code=$(printf '%s\n' "$result" | sed -n '2p')
    echo "${country:-Unknown}|${code:-}"
    return 0
  fi
  local code=""
  code=$(curl -fsSL --max-time 4 "https://ipinfo.io/${ip}/country" 2>/dev/null || true)
  code="${code//$'\r'/}"
  code="${code//$'\n'/}"
  [[ -n "$code" ]] && echo "Unknown|$code" || echo "Unknown|"
}

detect_server_network() {
  P00RIJA_DETECTED_LOCAL_IP="${P00RIJA_DETECTED_LOCAL_IP:-$(detect_local_ip)}"
  P00RIJA_DETECTED_PUBLIC_IP="${P00RIJA_DETECTED_PUBLIC_IP:-}"
  P00RIJA_DETECTED_COUNTRY="${P00RIJA_DETECTED_COUNTRY:-Unknown}"
  P00RIJA_DETECTED_COUNTRY_CODE="${P00RIJA_DETECTED_COUNTRY_CODE:-}"
  P00RIJA_DETECTED_IS_LOCAL="${P00RIJA_DETECTED_IS_LOCAL:-false}"
  if [[ "$P00RIJA_DETECTED_LOCAL_IP" != "unknown" ]] && is_private_or_local_ip "$P00RIJA_DETECTED_LOCAL_IP"; then
    P00RIJA_DETECTED_IS_LOCAL="true"
  fi
  P00RIJA_DETECTED_PUBLIC_IP="$(detect_public_ip)"
  local lookup_ip="$P00RIJA_DETECTED_PUBLIC_IP"
  if [[ -z "$lookup_ip" && "$P00RIJA_DETECTED_IS_LOCAL" != "true" ]]; then
    lookup_ip="$P00RIJA_DETECTED_LOCAL_IP"
  fi
  if [[ -n "$lookup_ip" ]]; then
    local country_line=""
    country_line="$(lookup_ip_country "$lookup_ip")"
    P00RIJA_DETECTED_COUNTRY="${country_line%%|*}"
    P00RIJA_DETECTED_COUNTRY_CODE="${country_line#*|}"
  fi
  export P00RIJA_DETECTED_LOCAL_IP P00RIJA_DETECTED_PUBLIC_IP P00RIJA_DETECTED_COUNTRY P00RIJA_DETECTED_COUNTRY_CODE P00RIJA_DETECTED_IS_LOCAL
}

network_detection_text() {
  local internet_line="Internet IP: ${P00RIJA_DETECTED_PUBLIC_IP:-not detected}"
  if [[ "${P00RIJA_DETECTED_IS_LOCAL:-false}" == "true" ]]; then
    internet_line="Local/private server IP detected. Internet egress IP: ${P00RIJA_DETECTED_PUBLIC_IP:-not detected}"
  fi
  printf 'Detected server IP: %s\n%s\nCountry: %s %s\n\nChoose the repository/mirror profile for package installation.' \
    "${P00RIJA_DETECTED_LOCAL_IP:-unknown}" \
    "$internet_line" \
    "${P00RIJA_DETECTED_COUNTRY:-Unknown}" \
    "${P00RIJA_DETECTED_COUNTRY_CODE:+(${P00RIJA_DETECTED_COUNTRY_CODE})}"
}

detect_server_region() {
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(ir|IR)$ ]]; then echo "ir"; return 0; fi
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(global|GLOBAL|outside|OUTSIDE)$ ]]; then echo "global"; return 0; fi
  detect_server_network
  if [[ "${P00RIJA_DETECTED_COUNTRY_CODE:-}" == "IR" ]]; then echo "ir"; return 0; fi
  local cc=""
  cc=$(curl -fsSL --max-time 3 http://ip-api.com/line?fields=countryCode 2>/dev/null || true)
  [[ -z "$cc" ]] && cc=$(curl -fsSL --max-time 3 https://ipinfo.io/country 2>/dev/null || true)
  [[ -z "$cc" ]] && cc=$(curl -fsSL --max-time 3 https://ifconfig.co/country-iso 2>/dev/null || true)
  cc="${cc//$'\r'/}"
  cc="${cc//$'\n'/}"
  [[ "$cc" == "IR" ]] && echo "ir" || echo "global"
}

simple_menu() {
  local __p00rija_prompt="$1" __p00rija_default="$2"; shift 2
  local __p00rija_choice="" __p00rija_item
  printf '\n%s\n' "$__p00rija_prompt" >&2
  for __p00rija_item in "$@"; do
    printf '  %s) %s\n' "${__p00rija_item%%:*}" "${__p00rija_item#*:}" >&2
  done
  while true; do
    read -r -p "Selection [default: ${__p00rija_default}]: " __p00rija_choice
    __p00rija_choice=${__p00rija_choice:-$__p00rija_default}
    for __p00rija_item in "$@"; do
      if [[ "$__p00rija_choice" == "${__p00rija_item%%:*}" ]]; then
        echo "$__p00rija_choice"
        return 0
      fi
    done
    printf '[!] Invalid selection.\n' >&2
  done
}

configure_apt_iran_mirror() {
  [[ -f /etc/os-release ]] || return 0
  # shellcheck disable=SC1091
  . /etc/os-release
  local distro="${ID:-}" codename="${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}"
  [[ -n "$codename" ]] || return 0
  local backup_dir="/etc/apt/p00rija-backup-$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$backup_dir"
  find /etc/apt/sources.list.d -maxdepth 1 -type f -name '*.p00rija-disabled' -print0 2>/dev/null | while IFS= read -r -d '' stale; do
    mv -f "$stale" "$backup_dir/$(basename "$stale")" || rm -f "$stale" || true
  done
  find /etc/apt -maxdepth 2 \( -name '*.list' -o -name '*.sources' \) -type f -print0 2>/dev/null | while IFS= read -r -d '' src; do
    cp -f "$src" "$backup_dir/$(basename "$src").bak" || true
    mv -f "$src" "$backup_dir/$(basename "$src")" || true
  done
  mkdir -p /etc/apt/sources.list.d
  write_apt_iran_sources "$distro" "$codename" ""
  ui_info "Previous APT source files were moved to ${backup_dir}."
}

write_apt_iran_sources() {
  local distro="$1" codename="$2" mirror="${3:-}"
  if [[ "$distro" =~ ^(ubuntu|linuxmint|pop)$ ]]; then
    mirror="${mirror:-${P00RIJA_UBUNTU_IR_MIRRORS%% *}}"
    cat > /etc/apt/sources.list.d/p00rija-iran.sources <<EOF
Types: deb
URIs: ${mirror}
Suites: ${codename} ${codename}-updates ${codename}-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
    ui_ok "APT mirror switched to Ubuntu mirror: ${mirror}"
  elif [[ "$distro" =~ ^(debian)$ ]]; then
    mirror="${mirror:-${P00RIJA_DEBIAN_IR_MIRRORS%% *}}"
    cat > /etc/apt/sources.list.d/p00rija-iran.sources <<EOF
Types: deb
URIs: ${mirror}
Suites: ${codename} ${codename}-updates
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF
    ui_ok "APT mirror switched to Debian mirror: ${mirror}"
  else
    ui_warn "APT mirror auto-switch is not implemented for distro '${distro}'."
  fi
}

apt_clean_indexes() {
  rm -rf /var/lib/apt/lists/partial
  apt-get clean >/dev/null 2>&1 || true
}

apt_update_with_retries() {
  local region="${P00RIJA_SERVER_REGION:-}" mirror="" mirrors="" distro="" codename=""
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    distro="${ID:-}"
    codename="${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}"
  fi
  if [[ "$region" == "ir" && -n "$codename" && "$distro" =~ ^(ubuntu|linuxmint|pop|debian)$ ]]; then
    if [[ "$distro" =~ ^(ubuntu|linuxmint|pop)$ ]]; then
      mirrors="$P00RIJA_UBUNTU_IR_MIRRORS"
    else
      mirrors="$P00RIJA_DEBIAN_IR_MIRRORS"
    fi
    for mirror in $mirrors; do
      write_apt_iran_sources "$distro" "$codename" "$mirror"
      apt_clean_indexes
      ui_info "Running apt update using ${mirror}..."
      if apt-get update -o Acquire::Retries=2; then
        return 0
      fi
      ui_warn "APT mirror failed or is still syncing: ${mirror}. Trying next mirror..."
    done
    ui_warn "All configured mirrors failed. Trying the current APT sources one more time..."
  fi
  apt_clean_indexes
  apt-get update -o Acquire::Retries=2
}

configure_apk_iran_mirror() {
  [[ -f /etc/apk/repositories ]] || return 0
  local version="latest-stable"
  if [[ -f /etc/alpine-release ]]; then
    version="v$(cut -d. -f1,2 < /etc/alpine-release)"
  fi
  cp -f /etc/apk/repositories "/etc/apk/repositories.p00rija-backup.$(date +%Y%m%d_%H%M%S)" || true
  cat > /etc/apk/repositories <<EOF
https://mirror.arvancloud.ir/alpine/${version}/main
https://mirror.arvancloud.ir/alpine/${version}/community
EOF
  ui_ok "APK mirror switched to ArvanCloud Alpine mirror."
}

configure_package_mirrors() {
  local region="$1"
  [[ "$region" == "ir" ]] || return 0
  ui_info "Iran selected: switching package repositories before installing dependencies..."
  if have apt-get; then
    configure_apt_iran_mirror
  elif have apk; then
    configure_apk_iran_mirror
  elif have yum || have dnf; then
    ui_warn "YUM/DNF Iran mirror auto-switch is not enabled; Docker mirror will still be configured for Iran."
  fi
}

configure_docker_mirror() {
  local region="$1"
  mkdir -p /etc/docker
  python3 - "$region" <<'PY'
import json, os, sys
path = "/etc/docker/daemon.json"
region = sys.argv[1]
data = {}
if os.path.exists(path) and os.path.getsize(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        data = {}
if region == "ir":
    data["registry-mirrors"] = [
        "https://docker.kernel.ir",
        "https://docker.arvancloud.ir",
        "https://registry.docker.ir",
    ]
else:
    data.pop("registry-mirrors", None)
tmp = f"{path}.tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
os.replace(tmp, path)
PY
  systemctl restart docker >/dev/null 2>&1 || true
}

install_whiptail_or_dialog() {
  if have whiptail || have dialog; then
    return 0
  fi
  ui_info "whiptail/dialog is not installed. Installing terminal UI package..."
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    apt_update_with_retries
    apt-get install -y whiptail dialog
  elif have yum; then
    yum install -y newt dialog || true
  elif have dnf; then
    dnf install -y newt dialog || true
  elif have apk; then
    apk add newt dialog || true
  fi
}

ui_tool() {
  if have whiptail; then echo "whiptail"; return 0; fi
  if have dialog; then echo "dialog"; return 0; fi
  echo ""
}

ui_menu() {
  local __p00rija_outvar="$1" __p00rija_title="$2" __p00rija_text="$3" __p00rija_default="$4"; shift 4
  local __p00rija_tool __p00rija_choice __p00rija_item
  __p00rija_choice="$__p00rija_default"
  __p00rija_tool=$(ui_tool)
  if [[ -n "$__p00rija_tool" ]]; then
    local __p00rija_args=()
    for __p00rija_item in "$@"; do
      __p00rija_args+=("${__p00rija_item%%:*}" "${__p00rija_item#*:}")
    done
    if [[ "$__p00rija_tool" == "whiptail" ]]; then
      __p00rija_choice=$(whiptail --title "$__p00rija_title" --default-item "$__p00rija_default" --menu "$__p00rija_text" 20 78 10 "${__p00rija_args[@]}" 3>&1 1>&2 2>&3) || {
        ui_warn "Installer menu was cancelled."
        exit 1
      }
    else
      __p00rija_choice=$(dialog --title "$__p00rija_title" --default-item "$__p00rija_default" --menu "$__p00rija_text" 20 78 10 "${__p00rija_args[@]}" 3>&1 1>&2 2>&3) || {
        clear || true
        ui_warn "Installer menu was cancelled."
        exit 1
      }
      clear || true
    fi
  else
    __p00rija_choice=$(simple_menu "$__p00rija_text" "$__p00rija_default" "$@")
  fi
  __p00rija_choice="${__p00rija_choice:-$__p00rija_default}"
  printf -v "$__p00rija_outvar" '%s' "$__p00rija_choice"
}

ui_input() {
  local __p00rija_outvar="$1" __p00rija_title="$2" __p00rija_text="$3" __p00rija_default="${4:-}" __p00rija_tool __p00rija_value
  __p00rija_tool=$(ui_tool)
  if [[ -n "$__p00rija_tool" ]]; then
    if [[ "$__p00rija_tool" == "whiptail" ]]; then
      __p00rija_value=$(whiptail --title "$__p00rija_title" --inputbox "$__p00rija_text" 10 78 "$__p00rija_default" 3>&1 1>&2 2>&3) || {
        ui_warn "Installer input was cancelled."
        exit 1
      }
    else
      __p00rija_value=$(dialog --title "$__p00rija_title" --inputbox "$__p00rija_text" 10 78 "$__p00rija_default" 3>&1 1>&2 2>&3) || {
        clear || true
        ui_warn "Installer input was cancelled."
        exit 1
      }
      clear || true
    fi
  else
    read -r -p "${__p00rija_text} [${__p00rija_default}]: " __p00rija_value
    __p00rija_value=${__p00rija_value:-$__p00rija_default}
  fi
  printf -v "$__p00rija_outvar" '%s' "$__p00rija_value"
}

ui_password() {
  local __p00rija_outvar="$1" __p00rija_title="$2" __p00rija_text="$3" __p00rija_tool __p00rija_value
  __p00rija_tool=$(ui_tool)
  if [[ -n "$__p00rija_tool" ]]; then
    if [[ "$__p00rija_tool" == "whiptail" ]]; then
      __p00rija_value=$(whiptail --title "$__p00rija_title" --passwordbox "$__p00rija_text" 10 78 3>&1 1>&2 2>&3) || {
        ui_warn "Installer password input was cancelled."
        exit 1
      }
    else
      __p00rija_value=$(dialog --title "$__p00rija_title" --passwordbox "$__p00rija_text" 10 78 3>&1 1>&2 2>&3) || {
        clear || true
        ui_warn "Installer password input was cancelled."
        exit 1
      }
      clear || true
    fi
  else
    read -r -s -p "${__p00rija_text}: " __p00rija_value
    echo
  fi
  printf -v "$__p00rija_outvar" '%s' "$__p00rija_value"
}

ui_msg() {
  local __p00rija_title="$1" __p00rija_text="$2" __p00rija_tool
  __p00rija_tool=$(ui_tool)
  if [[ "$__p00rija_tool" == "whiptail" ]]; then
    whiptail --title "$__p00rija_title" --msgbox "$__p00rija_text" 14 78 || true
  elif [[ "$__p00rija_tool" == "dialog" ]]; then
    dialog --title "$__p00rija_title" --msgbox "$__p00rija_text" 14 78 || true
    clear || true
  else
    ui_log ""
    ui_log "== $__p00rija_title =="
    ui_log "$__p00rija_text"
  fi
}

bootstrap_region() {
  local __p00rija_outvar="$1" __p00rija_detected __p00rija_default __p00rija_choice=""
  __p00rija_detected=$(detect_server_region)
  __p00rija_default="2"
  [[ "$__p00rija_detected" == "ir" ]] && __p00rija_default="1"
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(ir|IR)$ ]]; then
    printf -v "$__p00rija_outvar" '%s' "ir"
    return 0
  fi
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(global|GLOBAL|outside|OUTSIDE)$ ]]; then
    printf -v "$__p00rija_outvar" '%s' "global"
    return 0
  fi
  detect_server_network
  ui_menu __p00rija_choice "Server location" "$(network_detection_text)" "$__p00rija_default" \
    "1:Iran - use Iran package/Docker mirrors" \
    "2:Global - use official repositories"
  __p00rija_choice="${__p00rija_choice:-$__p00rija_default}"
  [[ "$__p00rija_choice" == "1" ]] && printf -v "$__p00rija_outvar" '%s' "ir" || printf -v "$__p00rija_outvar" '%s' "global"
}

prepare_installer_ui() {
  local __p00rija_outvar="$1" __p00rija_region=""
  bootstrap_region __p00rija_region
  __p00rija_region="${__p00rija_region:-global}"
  configure_package_mirrors "$__p00rija_region"
  install_whiptail_or_dialog
  printf -v "$__p00rija_outvar" '%s' "$__p00rija_region"
}
