#!/usr/bin/env bash

have() { command -v "$1" >/dev/null 2>&1; }
export TERM="${TERM:-xterm}"

# Hash a panel admin password with PBKDF2-HMAC-SHA256 + random salt (matches database.py).
# The plaintext password is passed via the env var P00RIJA_HASH_INPUT so it never appears
# in process args / ps output. Output format: pbkdf2_sha256$<iter>$<salt_hex>$<hash_hex>
p00rija_hash_password() {
  P00RIJA_HASH_INPUT="${1:-}" python3 - <<'PY'
import hashlib, os, secrets
password = os.environ.get("P00RIJA_HASH_INPUT", "")
iterations = 200_000
salt = secrets.token_bytes(16)
digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
print(f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}")
PY
  unset P00RIJA_HASH_INPUT 2>/dev/null || true
}

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

# Smart mirror catalog — probes run by select_best_*() pick the fastest reachable one.
# Ubuntu mirrors (IR): IranServer (primary), Shatel, official IR country mirror,
# Arvancloud, pol.hostinja. Candidates are probe-ranked, so order is a preference only.
P00RIJA_UBUNTU_IR_MIRRORS="${P00RIJA_UBUNTU_IR_MIRRORS:-https://mirror.iranserver.com/ubuntu/ https://mirror.shatel.ir/ubuntu/ http://ir.archive.ubuntu.com/ubuntu/ https://mirror.arvancloud.ir/ubuntu/ http://mirrors.pol.hostinja.com/ubuntu/}"
# Debian mirrors (IR): Arvancloud, pol.hostinja.
P00RIJA_DEBIAN_IR_MIRRORS="${P00RIJA_DEBIAN_IR_MIRRORS:-https://mirror.arvancloud.ir/debian/ http://debian.pol.hostinja.com/debian/}"
# Docker registry mirrors (IR): svrs.tech, Kargadan, Arvancloud, kernel.ir, focker.ir,
# plus registry.docker.ir, IranServer, Liara. Probe-ranked fastest-first.
P00RIJA_DOCKER_IR_MIRRORS="${P00RIJA_DOCKER_IR_MIRRORS:-https://registry.ir.svrs.tech https://mirror.kargadan.ir https://docker.arvancloud.ir https://docker.kernel.ir https://focker.ir https://registry.docker.ir https://docker.iranserver.com https://registry.liara.ir}"
# How many seconds to wait per mirror probe. Tunable for slow links.
P00RIJA_MIRROR_PROBE_TIMEOUT="${P00RIJA_MIRROR_PROBE_TIMEOUT:-4}"
# Set P00RIJA_SKIP_MIRROR_PROBE=1 to trust the catalog order without probing (fast, non-interactive CI).
P00RIJA_SKIP_MIRROR_PROBE="${P00RIJA_SKIP_MIRROR_PROBE:-0}"

detect_server_region() {
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(ir|IR)$ ]]; then echo "ir"; return 0; fi
  if [[ "${P00RIJA_SERVER_REGION:-}" =~ ^(global|GLOBAL|outside|OUTSIDE)$ ]]; then echo "global"; return 0; fi
  # Region detection is advisory only: HTTPS endpoints, short timeouts, and a logged
  # default of "global" when detection is unavailable. Interactive callers still
  # confirm the result afterwards via the region prompt/menu in prepare_installer_ui.
  local cc=""
  cc=$(curl -fsSL --max-time 3 https://ip-api.com/line?fields=countryCode 2>/dev/null || true)
  [[ -z "$cc" ]] && cc=$(curl -fsSL --max-time 3 https://ipinfo.io/country 2>/dev/null || true)
  [[ -z "$cc" ]] && cc=$(curl -fsSL --max-time 3 https://ifconfig.co/country-iso 2>/dev/null || true)
  cc="${cc//$'\r'/}"
  cc="${cc//$'\n'/}"
  if [[ -z "$cc" ]]; then
    echo "[i] Region detection unavailable; defaulting to global repositories." >&2
    echo "global"
    return 0
  fi
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
  # Headless/CI installs: P00RIJA_UI_PASSWORD provides the secret without a
  # terminal (only ever read from the environment of the invoking root shell).
  if [[ -n "${P00RIJA_UI_PASSWORD:-}" ]]; then
    printf -v "$outvar" '%s' "$P00RIJA_UI_PASSWORD"
    return 0
  fi
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

# Portable millisecond timestamp (date +%s%3N is NOT portable across GNU/BSD/macOS).
now_ms() {
  python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || date +%s 2>/dev/null || echo 0
}

# Probe a single APT mirror by fetching its Release file for the current codename.
# Prints "latency_ms" on success (>=0) or "fail" on failure.
probe_apt_mirror() {
  local mirror="$1" codename="$2" timeout="${P00RIJA_MIRROR_PROBE_TIMEOUT:-4}"
  local probe_url="${mirror%/}/dists/${codename}/Release"
  local start_ms end_ms http_code
  if ! have curl; then echo "fail"; return 0; fi
  start_ms=$(now_ms)
  # NOTE: no -f here; we want the raw HTTP code so 401/403/302 reachable mirrors are counted.
  http_code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$timeout" "$probe_url" 2>/dev/null || echo "000")
  end_ms=$(now_ms)
  if [[ "$http_code" == "200" ]]; then
    echo $(( end_ms - start_ms ))
  else
    echo "fail"
  fi
}

# Probe all APT mirrors in $1 for codename $2 and return them sorted fastest-first.
# If P00RIJA_SKIP_MIRROR_PROBE=1 or curl is missing, returns the catalog order unchanged.
# Output: one mirror URL per line, fastest first.
select_best_apt_mirror() {
  local mirrors="$1" codename="$2" mirror latency results=""
  if [[ "$P00RIJA_SKIP_MIRROR_PROBE" == "1" || -z "$codename" ]]; then
    printf '%s\n' $mirrors
    return 0
  fi
  # Collect results into a variable first (NOT a pipeline) so we can detect "all failed".
  for mirror in $mirrors; do
    latency=$(probe_apt_mirror "$mirror" "$codename")
    if [[ "$latency" != "fail" ]]; then
      results+="${latency} ${mirror}"$'\n'
    fi
  done
  if [[ -n "$results" ]]; then
    printf '%s' "$results" | sort -n | while IFS=' ' read -r _ m; do [[ -n "$m" ]] && printf '%s\n' "$m"; done
  else
    printf '%s\n' $mirrors
  fi
}

# Probe a single Docker registry mirror by issuing a lightweight v2 API request.
# Prints "latency_ms" on success, or "fail".
probe_docker_mirror() {
  local mirror="$1" timeout="${P00RIJA_MIRROR_PROBE_TIMEOUT:-4}"
  local probe_url="${mirror%/}/v2/"
  local start_ms end_ms http_code
  if ! have curl; then echo "fail"; return 0; fi
  start_ms=$(now_ms)
  # NOTE: no -f here; 200 = reachable unauthenticated catalog, 401 = reachable but requires auth (valid mirror).
  http_code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$timeout" "$probe_url" 2>/dev/null || echo "000")
  end_ms=$(now_ms)
  if [[ "$http_code" == "200" || "$http_code" == "401" ]]; then
    echo $(( end_ms - start_ms ))
  else
    echo "fail"
  fi
}

# Probe all Docker registry mirrors in $1 and return them sorted fastest-first (all reachable ones).
select_best_docker_mirrors() {
  local mirrors="$1" mirror latency results=""
  if [[ "$P00RIJA_SKIP_MIRROR_PROBE" == "1" ]]; then
    printf '%s\n' $mirrors
    return 0
  fi
  for mirror in $mirrors; do
    latency=$(probe_docker_mirror "$mirror")
    if [[ "$latency" != "fail" ]]; then
      results+="${latency} ${mirror}"$'\n'
    fi
  done
  if [[ -n "$results" ]]; then
    printf '%s' "$results" | sort -n | while IFS=' ' read -r _ m; do [[ -n "$m" ]] && printf '%s\n' "$m"; done
  else
    printf '%s\n' $mirrors
  fi
}

# Move the original APT sources (preserved by configure_package_mirrors) back into
# place and drop the IR override file, so the system returns to its prior sources.
restore_apt_sources_from_backup() {
  local backup_dir="$1" src name
  [[ -n "$backup_dir" && -d "$backup_dir" ]] || return 0
  rm -f /etc/apt/sources.list.d/p00rija-iran.sources
  while IFS= read -r -d '' src; do
    name="$(basename "$src")"
    if [[ "$name" == "sources.list" ]]; then
      mv -f "$src" /etc/apt/sources.list || true
    else
      mv -f "$src" "/etc/apt/sources.list.d/$name" || true
    fi
  done < <(find "$backup_dir" -maxdepth 1 -type f \( -name '*.list' -o -name '*.sources' \) -print0 2>/dev/null)
  ui_info "Restored original APT sources from ${backup_dir}"
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
  # Only touch the two canonical source locations; scanning all of /etc/apt would
  # also sweep up files inside earlier p00rija-backup-* directories. Path
  # operands must actually exist: `find <missing-path>` exits 1, which under
  # `set -eo pipefail` would abort the whole installer.
  local -a src_roots=()
  [[ -f /etc/apt/sources.list ]] && src_roots+=("/etc/apt/sources.list")
  [[ -d /etc/apt/sources.list.d ]] && src_roots+=("/etc/apt/sources.list.d")
  if (( ${#src_roots[@]} )); then
    find "${src_roots[@]}" -maxdepth 1 \( -name '*.list' -o -name '*.sources' \) -type f -print0 2>/dev/null | while IFS= read -r -d '' src; do
      cp -f "$src" "$backup_dir/$(basename "$src").bak" || true
      mv -f "$src" "$backup_dir/$(basename "$src")" || true
    done || true
  fi
  ui_info "APT sources backed up to ${backup_dir}"
  apt_update_with_retries "$distro" "$codename" "$backup_dir"
}

apt_update_with_retries() {
  if ! have apt-get; then return 0; fi
  local distro="" codename="" backup_dir="${3:-}" mirrors="" mirror="" best=""
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    distro="${ID:-}"
    codename="${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}"
  fi
  # Allow callers to pass distro/codename explicitly (after configure_package_mirrors sources /etc/os-release).
  distro="${1:-$distro}"
  codename="${2:-$codename}"
  if [[ "${P00RIJA_SERVER_REGION:-}" == "ir" && -n "$codename" ]]; then
    if [[ "$distro" =~ ^(ubuntu|linuxmint|pop)$ ]]; then mirrors="$P00RIJA_UBUNTU_IR_MIRRORS"; else mirrors="$P00RIJA_DEBIAN_IR_MIRRORS"; fi
    ui_info "Probing APT mirrors for ${codename} (region: ir)..."
    while IFS= read -r best; do
      [[ -n "$best" ]] || continue
      write_apt_sources "$distro" "$codename" "$best"
      apt-get clean >/dev/null 2>&1 || true
      rm -rf /var/lib/apt/lists/partial
      ui_info "Running apt update using ${best}..."
      if apt-get update -o Acquire::Retries=2; then
        ui_ok "APT mirror selected: ${best}"
        return 0
      fi
      ui_warn "APT mirror failed at update time: ${best}"
    done < <(select_best_apt_mirror "$mirrors" "$codename")
    ui_warn "All IR APT mirrors failed at update time. Restoring original apt sources before falling back."
    restore_apt_sources_from_backup "$backup_dir"
  fi
  apt-get update -o Acquire::Retries=2
}

configure_docker_mirror() {
  local region="$1"
  local selected=""
  if [[ "$region" == "ir" ]]; then
    ui_info "Probing Docker registry mirrors (region: ir)..."
    selected="$(select_best_docker_mirrors "$P00RIJA_DOCKER_IR_MIRRORS" | tr '\n' ' ')"
    selected="${selected% }"
    [[ -z "$selected" ]] && selected="$P00RIJA_DOCKER_IR_MIRRORS"
  fi
  mkdir -p /etc/docker
  python3 - "$region" "$selected" <<'PY'
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
    ui_info "Docker registry mirrors configured: ${selected}"
    if [[ "${P00RIJA_SKIP_DOCKER_MIRROR_PROBE:-0}" != "1" ]] && have docker; then
      if timeout 45 docker pull hello-world:latest >/dev/null 2>&1; then
        ui_ok "Docker mirror functional (image pull succeeded)."
      else
        ui_warn "Docker image pull probe failed. Keeping the mirror config, but pulls may need direct Docker Hub access."
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
