#!/usr/bin/env bash
# ==============================================================================
# P00RIJA TUNNEL - Management Shell Script
# Handles installation, Docker and systemd execution modes, and CLI Setup Wizard.
# ==============================================================================
set -euo pipefail

APP_NAME="P00RIJA TUNNEL"
VERSION="1.3.0"
TG_ID="@IlyaahD"
GITHUB_REPO="github.com/Poorija/P00RIJA-Tunnel"

PY_SRC="/opt/p00rija/P00RIJA.py"
INSTALL_PATH="/usr/local/bin/Pooriya-tunnel"
CONTROL_PATH="/usr/local/bin/p00rija"
SERVICE_PATH="/etc/systemd/system/p00rija-tunnel.service"
CONFIG_DIR="/opt/p00rija"
CONFIG_PATH="$CONFIG_DIR/p00rija_config.json"
DOCKER_CONTAINER_NAME="p00rija-tunnel"
P00RIJA_DOCKER_PUBLISH_RANGES="${P00RIJA_DOCKER_PUBLISH_RANGES:-7000-7999:7000-7999,17000-17999:17000-17999}"

# Colors
if [[ -t 1 ]]; then
  CLR_RESET="\033[0m"; CLR_DIM="\033[2m"; CLR_BOLD="\033[1m"
  CLR_RED="\033[31m"; CLR_GREEN="\033[32m"; CLR_YELLOW="\033[33m"
  CLR_CYAN="\033[36m"; CLR_WHITE="\033[97m"
else
  CLR_RESET=""; CLR_DIM=""; CLR_BOLD=""
  CLR_RED=""; CLR_GREEN=""; CLR_YELLOW=""
  CLR_CYAN=""; CLR_WHITE=""
fi

# Root check
need_root() {
  if [[ "$(id -u)" != "0" ]]; then
    echo -e "${CLR_RED}[!] Error: This script must be run as root (sudo -i)${CLR_RESET}" >&2
    exit 1
  fi
}

pause() {
  echo -e "\n"
  read -r -p "Press Enter to continue..." _ || true
}

have() {
  command -v "$1" >/dev/null 2>&1
}

docker_bridge_publish_args() {
  local role="unknown"
  local panel_ports="8080 8081"
  if [[ -f "$CONFIG_PATH" ]]; then
    role=$(python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); print(data.get("role","unknown"))' "$CONFIG_PATH" 2>/dev/null || echo "unknown")
    panel_ports=$(python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); print(int(data.get("port",8080)), int(data.get("api_port",8081)))' "$CONFIG_PATH" 2>/dev/null || echo "8080 8081")
  fi
  if [[ "$role" == "panel" ]]; then
    local web_port api_port
    read -r web_port api_port <<< "$panel_ports"
    printf '%s\n' "-p" "${web_port}:${web_port}" "-p" "${api_port}:${api_port}"
    return 0
  fi
  local range
  IFS=',' read -ra ranges <<< "$P00RIJA_DOCKER_PUBLISH_RANGES"
  for range in "${ranges[@]}"; do
    range="${range//[[:space:]]/}"
    if [[ -n "$range" ]]; then
      printf '%s\n' "-p" "$range"
    fi
  done
}

# Graphical Box Utilities
draw_box_top() {
  local title="$1"
  local width=60
  local title_len=${#title}
  local padding=$(( (width - title_len - 2) / 2 ))
  local pad_str=""
  for ((i=0; i<padding; i++)); do pad_str+="─"; done
  echo -e "${CLR_CYAN}┌${pad_str} ${CLR_BOLD}${CLR_WHITE}${title}${CLR_RESET}${CLR_CYAN} ${pad_str}┐${CLR_RESET}"
}

draw_box_bottom() {
  echo -e "${CLR_CYAN}└────────────────────────────────────────────────────────────┘${CLR_RESET}"
}

# Detect Public IP address of the server
detect_public_ip() {
  local ip
  ip=$(curl -fsSL --max-time 3 api.ipify.org 2>/dev/null || curl -fsSL --max-time 3 ifconfig.me 2>/dev/null || echo "")
  if [[ -z "$ip" ]]; then
    ip=$(hostname -I | awk '{print $1}' || echo "127.0.0.1")
  fi
  echo "$ip"
}

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

select_server_region() {
  local detected; detected=$(detect_server_region)
  local def_choice="2"
  if [[ "$detected" == "ir" ]]; then
    echo -e "${CLR_GREEN}[+] Server location auto-detected as Iran.${CLR_RESET}" >&2
    def_choice="1"
  else
    echo -e "${CLR_CYAN}[*] Server location auto-detected as outside Iran/global.${CLR_RESET}" >&2
  fi
  local region_choice=""
  read -r -p "Server location? [1] Iran/internal Docker mirrors [2] Global official Docker [default: ${def_choice}]: " region_choice
  region_choice=${region_choice:-$def_choice}
  [[ "$region_choice" == "1" ]] && echo "ir" || echo "global"
}

configure_docker_mirror() {
  local region="${1:-global}"
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
    data["registry-mirrors"] = ["https://docker.arvancloud.ir", "https://registry.docker.ir"]
else:
    data.pop("registry-mirrors", None)
tmp = f"{path}.tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
os.replace(tmp, path)
PY
  systemctl restart docker >/dev/null 2>&1 || true
}

# Auto-detect existing installations
detect_existing_install() {
  if [[ -f "$CONFIG_PATH" ]]; then
    local role; role=$(grep -o '"role": *"[^"]*"' "$CONFIG_PATH" | cut -d'"' -f4 || echo "unknown")
    local run_mode; run_mode=$(get_run_mode)
    
    local status="${CLR_RED}STOPPED${CLR_RESET}"
    if [[ "$run_mode" == "docker" ]]; then
      if docker ps --format '{{.Names}}' | grep -q "^${DOCKER_CONTAINER_NAME}$"; then
        status="${CLR_GREEN}RUNNING (DOCKER)${CLR_RESET}"
      fi
    else
      if systemctl is-active --quiet p00rija-tunnel.service 2>/dev/null; then
        status="${CLR_GREEN}RUNNING (SYSTEMD)${CLR_RESET}"
      fi
    fi
    
    local display_role="${role^^}"
    if [[ "$role" == "external" || "$role" == "external" ]]; then
      display_role="EXTERNAL NODE"
    elif [[ "$role" == "internal" ]]; then
      display_role="INTERNAL NODE"
    elif [[ "$role" == "panel" ]]; then
      display_role="PANEL"
    fi
    
    echo -e "${CLR_YELLOW}[i] Current Active Configuration:${CLR_RESET}"
    echo -e "    Role: ${CLR_BOLD}${CLR_WHITE}${display_role}${CLR_RESET}"
    echo -e "    Runner Mode: ${CLR_BOLD}${CLR_WHITE}${run_mode^^}${CLR_RESET}"
    echo -e "    Status: ${status}"
    if [[ "$role" == "panel" ]]; then
      local port; port=$(grep -o '"port": *[0-9]*' "$CONFIG_PATH" | awk -F': ' '{print $2}' || echo "8080")
      local tls_status="http"
      local panel_host="localhost"
      if [[ -f "/opt/p00rija/p00rija_db.json" ]]; then
        if grep -q '"panel_tls": *true' "/opt/p00rija/p00rija_db.json"; then
          tls_status="https"
        fi
        panel_host=$(grep -o '"panel_host": *"[^"]*"' "/opt/p00rija/p00rija_db.json" | cut -d'"' -f4 || echo "localhost")
      fi
      if [[ -z "$panel_host" ]]; then
        panel_host="localhost"
      fi
      echo -e "    Web Console Access: ${CLR_BOLD}${CLR_CYAN}${tls_status}://${panel_host}:${port}${CLR_RESET}"
    else
      local panel_url; panel_url=$(grep -o '"panel_url": *"[^"]*"' "$CONFIG_PATH" | cut -d'"' -f4 || echo "")
      echo -e "    Connected Panel: ${CLR_BOLD}${CLR_CYAN}${panel_url}${CLR_RESET}"
    fi
    echo -e "${CLR_DIM}------------------------------------------------------------${CLR_RESET}"
  fi
}

# Install packages
install_dependencies() {
  echo -e "${CLR_CYAN}[*] Installing required system packages...${CLR_RESET}"
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y >/dev/null 2>&1 || true
    apt-get install -y python3 curl ca-certificates iproute2 jq openssl >/dev/null 2>&1 || true
  elif have yum; then
    yum install -y python3 curl ca-certificates iproute jq openssl >/dev/null 2>&1 || dnf install -y python3 curl ca-certificates iproute jq openssl >/dev/null 2>&1 || true
  elif have apk; then
    apk add python3 curl ca-certificates iproute2 jq openssl >/dev/null 2>&1 || true
  fi
}

ensure_env() {
  mkdir -p "$CONFIG_DIR"
  if [[ ! -f "$PY_SRC" ]]; then
    if [[ -f "./P00RIJA.py" ]]; then
      cp "./P00RIJA.py" "$PY_SRC"
      chmod +x "$PY_SRC"
    else
      echo -e "${CLR_RED}[!] Core script P00RIJA.py not found in current directory!${CLR_RESET}"
      exit 1
    fi
  fi
  if [[ -d "./fonts" ]]; then
    rm -rf "$CONFIG_DIR/fonts"
    cp -r "./fonts" "$CONFIG_DIR/fonts"
  fi
  if [[ -d "./engines" ]]; then
    rm -rf "$CONFIG_DIR/engines"
    cp -r "./engines" "$CONFIG_DIR/engines"
  fi
  if [[ -f "./download_engines.py" ]]; then
    cp -f "./download_engines.py" "$CONFIG_DIR/download_engines.py"
    chmod +x "$CONFIG_DIR/download_engines.py"
  fi
  if [[ -f "./p00rija-control.sh" ]]; then
    install -m 0755 "./p00rija-control.sh" "$CONTROL_PATH"
  fi
}

detect_os_and_arch() {
  local os="unknown"
  local arch="unknown"

  # CPU Architecture detection
  local uname_m; uname_m=$(uname -m)
  case "$uname_m" in
    x86_64) arch="x86_64" ;;
    aarch64|arm64) arch="arm64" ;;
    armv7l|armhf) arch="armhf" ;;
    *) arch="$uname_m" ;;
  esac

  # OS Distribution detection
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    os="$ID"
  elif have lsb_release; then
    os=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
  fi

  echo "$os" "$arch"
}

manage_docker_install() {
  local region="${1:-$(detect_server_region)}"
  if have docker; then
    if systemctl is-active --quiet docker 2>/dev/null; then
      configure_docker_mirror "$region"
      return 0
    else
      echo -e "${CLR_YELLOW}[*] Starting Docker service...${CLR_RESET}"
      systemctl start docker >/dev/null 2>&1 || true
      systemctl enable docker >/dev/null 2>&1 || true
      configure_docker_mirror "$region"
      return 0
    fi
  fi

  local info; info=$(detect_os_and_arch)
  local distro; distro=$(echo "$info" | awk '{print $1}')
  local cpu_arch; cpu_arch=$(echo "$info" | awk '{print $2}')

  echo -e "${CLR_CYAN}[*] Docker Engine is not installed on this server.${CLR_RESET}"
  echo -e "${CLR_CYAN}[*] Detected Distro: ${CLR_BOLD}${CLR_WHITE}${distro}${CLR_RESET}, CPU Architecture: ${CLR_BOLD}${CLR_WHITE}${cpu_arch}${CLR_RESET}"
  if [[ "$region" == "ir" ]]; then
    echo -e "${CLR_CYAN}[*] Installing Docker through local package manager for Iran compatibility...${CLR_RESET}"
    if have apt-get; then
      apt-get install -y docker.io >/dev/null 2>&1 || true
    elif have yum; then
      yum install -y docker >/dev/null 2>&1 || dnf install -y docker >/dev/null 2>&1 || true
    elif have apk; then
      apk add docker >/dev/null 2>&1 || true
      rc-update add docker boot >/dev/null 2>&1 || true
    fi
  else
    echo -e "${CLR_CYAN}[*] Starting official Docker installation...${CLR_RESET}"
  fi

  # Update system package repository lists & install prerequisites
  if [[ "$distro" == "ubuntu" || "$distro" == "debian" || "$distro" == "mint" || "$distro" == "pop" ]]; then
    echo -e "${CLR_CYAN}[*] Updating apt package cache...${CLR_RESET}"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y >/dev/null 2>&1 || true
    apt-get install -y curl ca-certificates gnupg >/dev/null 2>&1 || true
  elif [[ "$distro" == "centos" || "$distro" == "rhel" || "$distro" == "rocky" || "$distro" == "almalinux" || "$distro" == "fedora" ]]; then
    echo -e "${CLR_CYAN}[*] Installing yum/dnf prerequisites...${CLR_RESET}"
    yum install -y curl ca-certificates >/dev/null 2>&1 || dnf install -y curl ca-certificates >/dev/null 2>&1 || true
  fi

  # Call official Docker installer script only outside Iran.
  if [[ "$region" != "ir" ]] && curl -fsSL https://get.docker.com | sh; then
    systemctl daemon-reload
    systemctl enable docker >/dev/null 2>&1 || true
    systemctl start docker >/dev/null 2>&1 || true
    configure_docker_mirror "$region"
    if have docker; then
      echo -e "${CLR_GREEN}[+] Docker Engine installed and running successfully!${CLR_RESET}"
      return 0
    fi
  fi

  # Fallback to direct package manager if convenice script failed
  echo -e "${CLR_YELLOW}[!] Primary installation script failed. Attempting package manager fallback...${CLR_RESET}"
  if have apt-get; then
    apt-get install -y docker.io >/dev/null 2>&1 || true
  elif have yum; then
    yum install -y docker >/dev/null 2>&1 || dnf install -y docker >/dev/null 2>&1 || true
  fi

  if have docker; then
    systemctl enable docker >/dev/null 2>&1 || true
    systemctl start docker >/dev/null 2>&1 || true
    configure_docker_mirror "$region"
    echo -e "${CLR_GREEN}[+] Docker fallback installation succeeded!${CLR_RESET}"
    return 0
  else
    echo -e "${CLR_RED}[!] Error: Auto-installation failed. Please install Docker manually on this server.${CLR_RESET}"
    return 1
  fi
}

run_docker_container() {
  local region="${1:-$(detect_server_region)}"
  manage_docker_install "$region"
  configure_docker_mirror "$region"
  echo -e "${CLR_CYAN}[*] Building P00RIJA TUNNEL Docker image...${CLR_RESET}"
  
  if [[ -d "./engines" ]]; then
    cp -r "./engines" "$CONFIG_DIR/engines"
  elif [[ -d "/opt/p00rija/engines" ]]; then
    cp -r "/opt/p00rija/engines" "$CONFIG_DIR/engines"
  else
    mkdir -p "$CONFIG_DIR/engines"
  fi

  cat > "$CONFIG_DIR/Dockerfile" <<EOF
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y openssl iputils-ping curl procps openssh-client sshpass ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY P00RIJA.py /app/P00RIJA.py
COPY download_engines.py /app/download_engines.py
COPY fonts/ /app/fonts/
COPY engines/ /usr/local/bin/
EXPOSE 8080
CMD ["python3", "/app/P00RIJA.py"]
EOF
  cp -f "$PY_SRC" "$CONFIG_DIR/P00RIJA.py"
  [[ -f "$CONFIG_DIR/download_engines.py" ]] || printf '%s\n' '#!/usr/bin/env python3' 'print("download_engines.py is not bundled.")' > "$CONFIG_DIR/download_engines.py"
  [[ -d "$CONFIG_DIR/fonts" ]] || mkdir -p "$CONFIG_DIR/fonts"
  
  docker build -t p00rija-tunnel:latest -f "$CONFIG_DIR/Dockerfile" "$CONFIG_DIR"
  
  docker stop "$DOCKER_CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rm "$DOCKER_CONTAINER_NAME" >/dev/null 2>&1 || true
  
  echo -e "${CLR_CYAN}[*] Starting Docker container...${CLR_RESET}"
  mapfile -t publish_args < <(docker_bridge_publish_args)
  docker run -d \
    --name "$DOCKER_CONTAINER_NAME" \
    --network bridge \
    --restart always \
    "${publish_args[@]}" \
    -v "$CONFIG_DIR:$CONFIG_DIR" \
    p00rija-tunnel:latest
    
  echo -e "${CLR_GREEN}[+] Docker container started successfully in bridge mode.${CLR_RESET}"
  echo -e "${CLR_CYAN}[i] Published Docker ports/ranges are controlled by the host OS/Docker NAT.${CLR_RESET}"
}

setup_systemd_service() {
  echo -e "${CLR_CYAN}[*] Creating systemd service configuration...${CLR_RESET}"
  cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=P00RIJA Tunnel Daemon (Panel/Node)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$CONFIG_DIR
ExecStart=/usr/bin/python3 $PY_SRC
Restart=always
RestartSec=3
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable p00rija-tunnel.service >/dev/null 2>&1 || true
  systemctl restart p00rija-tunnel.service
  echo -e "${CLR_GREEN}[+] Systemd service started successfully.${CLR_RESET}"
}

# Let's Encrypt Standalone Issuance
generate_letsencrypt_cert() {
  local domain="$1"
  local email="${2:-}"
  
  echo -e "${CLR_CYAN}[*] Installing certbot dependencies...${CLR_RESET}"
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y >/dev/null 2>&1 || true
    apt-get install -y certbot >/dev/null 2>&1 || true
  elif have yum; then
    yum install -y certbot >/dev/null 2>&1 || true
  elif have apk; then
    apk add certbot >/dev/null 2>&1 || true
  fi

  # Free port 80 if occupied
  local stopped_services=()
  if have ss; then
    if ss -lntp | grep -q ":80 "; then
      echo -e "${CLR_YELLOW}[!] Warning: Port 80 is occupied. Attempting to temporarily free...${CLR_RESET}"
      for service in nginx apache2 httpd; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
          systemctl stop "$service" >/dev/null 2>&1 || true
          stopped_services+=("$service")
        fi
      done
    fi
  fi

  echo -e "${CLR_CYAN}[*] Requesting Let's Encrypt Certificate for ${domain}...${CLR_RESET}"
  local -a cmd=(certbot certonly --standalone -d "$domain" --agree-tos --non-interactive)
  if [[ -n "$email" ]]; then
    cmd+=(--email "$email")
  else
    cmd+=(--register-unsafely-without-email)
  fi
  
  if "${cmd[@]}"; then
    mkdir -p "$CONFIG_DIR/certs"
    install -m 0644 "/etc/letsencrypt/live/${domain}/fullchain.pem" "$CONFIG_DIR/certs/cert.pem"
    install -m 0600 "/etc/letsencrypt/live/${domain}/privkey.pem" "$CONFIG_DIR/certs/key.pem"
    echo -e "${CLR_GREEN}[+] Let's Encrypt certificate generated successfully.${CLR_RESET}"
    
    if (( ${#stopped_services[@]} > 0 )); then
      for service in "${stopped_services[@]}"; do
        systemctl start "$service" >/dev/null 2>&1 || true
      done
    fi

    # Register automatic daily certificate renewal cron job
    if [[ -d "/etc/cron.daily" ]]; then
      echo -e "${CLR_CYAN}[*] Registering daily renewal job...${CLR_RESET}"
      cat > "/etc/cron.daily/p00rija-cert-renew" <<'EOF'
#!/bin/bash
certbot renew --post-hook "/usr/local/bin/Pooriya-tunnel restart" >/dev/null 2>&1
EOF
      chmod +x "/etc/cron.daily/p00rija-cert-renew"
    fi
    return 0
  else
    echo -e "${CLR_RED}[!] Error: Certificate generation failed.${CLR_RESET}"
    echo -e "${CLR_YELLOW}[i] Check your domain DNS settings and make sure port 80 is open.${CLR_RESET}"
    
    for service in "${stopped_services[@]}"; do
      systemctl start "$service" >/dev/null 2>&1 || true
    done
    return 1
  fi
}

generate_self_signed_cert() {
  local host="$1"
  mkdir -p "$CONFIG_DIR/certs"
  local san_type="DNS"
  if python3 - "$host" <<'PY' >/dev/null 2>&1
import ipaddress, sys
ipaddress.ip_address(sys.argv[1])
PY
  then
    san_type="IP"
  fi
  cat > "$CONFIG_DIR/certs/local-cert-openssl.cnf" <<EOF
[req]
distinguished_name=req_distinguished_name
x509_extensions=v3_req
prompt=no
[req_distinguished_name]
CN=${host}
[v3_req]
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=${san_type}:${host},DNS:localhost,IP:127.0.0.1,IP:::1
EOF
  openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
    -keyout "$CONFIG_DIR/certs/key.pem" \
    -out "$CONFIG_DIR/certs/cert.pem" \
    -config "$CONFIG_DIR/certs/local-cert-openssl.cnf"
  chmod 0600 "$CONFIG_DIR/certs/key.pem"
  chmod 0644 "$CONFIG_DIR/certs/cert.pem"
  echo -e "${CLR_GREEN}[+] Self-signed local HTTPS certificate generated for ${host}.${CLR_RESET}"
}

# Graphical setup wizard
run_setup_wizard() {
  clear || true
  draw_box_top "P00RIJA TUNNEL SETUP WIZARD"
  
  # Check if already installed
  if [[ -f "$CONFIG_PATH" ]]; then
    local existing_role; existing_role=$(grep -o '"role": *"[^"]*"' "$CONFIG_PATH" | cut -d'"' -f4 || echo "unknown")
    local existing_mode; existing_mode=$(get_run_mode)
    
    local display_role="${existing_role^^}"
    if [[ "$existing_role" == "external" || "$existing_role" == "external" ]]; then
      display_role="EXTERNAL NODE"
    elif [[ "$existing_role" == "internal" ]]; then
      display_role="INTERNAL NODE"
    elif [[ "$existing_role" == "panel" ]]; then
      display_role="PANEL"
    fi
    
    echo -e "│  ${CLR_YELLOW}[!] P00RIJA TUNNEL is already installed on this server!${CLR_RESET}"
    echo -e "│  Role: ${CLR_BOLD}${CLR_WHITE}${display_role}${CLR_RESET}"
    echo -e "│  Run Mode: ${CLR_BOLD}${CLR_WHITE}${existing_mode^^}${CLR_RESET}"
    echo -e "│"
    echo -e "│  Please choose an option:"
    echo -e "│  1) Reconfigure / Overwrite configuration"
    echo -e "│  2) Uninstall completely now"
    echo -e "│  3) Cancel and return to main menu"
    draw_box_bottom
    
    local existing_action=""
    while [[ ! "$existing_action" =~ ^[1-3]$ ]]; do
      read -r -p "Selection (1-3) [default: 3]: " existing_action
      existing_action=${existing_action:-3}
    done
    
    if [[ "$existing_action" == "2" ]]; then
      uninstall_all
      return
    elif [[ "$existing_action" == "3" ]]; then
      echo -e "${CLR_YELLOW}[i] Setup aborted.${CLR_RESET}"
      return
    else
      # Reconfigure/Overwrite: create backup
      mkdir -p "$CONFIG_DIR/backups"
      local ts; ts=$(date +%Y%m%d_%H%M%S)
      [[ -f "$CONFIG_PATH" ]] && cp -f "$CONFIG_PATH" "$CONFIG_DIR/backups/config_$ts.json"
      [[ -f "$CONFIG_DIR/p00rija_db.json" ]] && cp -f "$CONFIG_DIR/p00rija_db.json" "$CONFIG_DIR/backups/db_$ts.json"
      echo -e "${CLR_GREEN}[+] Backed up existing configurations to $CONFIG_DIR/backups/${CLR_RESET}"
    fi
  fi

  # Role Selection
  clear || true
  draw_box_top "P00RIJA TUNNEL SETUP WIZARD"
  echo -e "│  ${CLR_WHITE}Please select your installation role:${CLR_RESET}"
  echo -e "│  1) Panel (Web Central Management Console Server)"
  echo -e "│  2) Node (Internal or External Node)"
  draw_box_bottom
  
  local role_choice=""
  while [[ ! "$role_choice" =~ ^[1-2]$ ]]; do
    read -r -p "Selection (1-2): " role_choice
  done

  local run_mode="docker" # default recommendation
  local role="panel"
  local port=8080
  local username="admin"
  local password=""
  local panel_url=""
  local token=""
  local panel_tls=true
  local panel_host="localhost"
  local server_region="global"
  local cert_auto_generated=true

  server_region=$(select_server_region)
  
  if [[ "$role_choice" == "1" ]]; then
    # Panel Installation
    role="panel"
    
    # 1. Ask for Docker or Native Host
    clear || true
    draw_box_top "PANEL DEPLOYMENT RUNNER"
    echo -e "│  ${CLR_WHITE}Choose Panel Execution Environment (Recommended: Docker):${CLR_RESET}"
    echo -e "│  1) Docker (Containerized - Recommended)${CLR_GREEN} [Recommended]${CLR_RESET}"
    echo -e "│  2) Systemd (Native Host Linux Service)"
    draw_box_bottom
    
    local run_choice=""
    while [[ ! "$run_choice" =~ ^[1-2]$ ]]; do
      read -r -p "Selection (1-2) [default: 1]: " run_choice
      run_choice=${run_choice:-1}
    done
    [[ "$run_choice" == "2" ]] && run_mode="systemd"

    # 2. Ask for IP or Domain Name. HTTPS is always enforced by the panel.
    clear || true
    draw_box_top "PANEL ACCESS SETUP"
    echo -e "│  ${CLR_WHITE}Select how you want to configure secure panel access:${CLR_RESET}"
    echo -e "│  1) Public IP Address + local HTTPS certificate"
    echo -e "│  2) Domain Name + HTTPS certificate"
    draw_box_bottom
    
    local access_choice=""
    while [[ ! "$access_choice" =~ ^[1-2]$ ]]; do
      read -r -p "Selection (1-2) [default: 1]: " access_choice
      access_choice=${access_choice:-1}
    done

    if [[ "$access_choice" == "1" ]]; then
      # Direct IP setup
      local detected_ip; detected_ip=$(detect_public_ip)
      clear || true
      draw_box_top "CONFIRM IP ADDRESS"
      echo -e "│  Detected Server Public IP: ${CLR_BOLD}${CLR_CYAN}${detected_ip}${CLR_RESET}"
      draw_box_bottom
      
      local confirm_ip="y"
      read -r -p "Is this IP address correct? (y/n) [default: y]: " confirm_ip
      confirm_ip=${confirm_ip:-y}
      if [[ "${confirm_ip,,}" != "y" ]]; then
        read -r -p "Enter Server IP Address manually: " detected_ip
      fi
      panel_host="$detected_ip"
      generate_self_signed_cert "$panel_host"
      cert_auto_generated=true
    else
      # Domain Setup
      local domain=""
      clear || true
      draw_box_top "DOMAIN SETUP PROPERTIES"
      while [[ -z "$domain" ]]; do
        read -r -p "Enter Domain Name (e.g., panel.yoursite.com): " domain
      done
      panel_host="$domain"
      
      echo -e "│  ${CLR_WHITE}Do you have SSL Certificates or want auto-issuance?${CLR_RESET}"
      echo -e "│  1) Use pre-existing local certificates (I have certificate files)"
      echo -e "│  2) Generate free Let's Encrypt SSL certificate (Obtain certificate)"
      echo -e "│  3) Generate self-signed certificate for this domain"
      draw_box_bottom
      
      local cert_choice=""
      while [[ ! "$cert_choice" =~ ^[1-3]$ ]]; do
        read -r -p "Selection (1-3) [default: 3]: " cert_choice
        cert_choice=${cert_choice:-3}
      done

      mkdir -p "$CONFIG_DIR/certs"
      if [[ "$cert_choice" == "1" ]]; then
        local user_cert_path=""
        local user_key_path=""
        while [[ ! -f "$user_cert_path" ]]; do
          read -r -p "Enter path to cert file (fullchain.pem): " user_cert_path
          if [[ ! -f "$user_cert_path" ]]; then
            echo -e "${CLR_RED}[!] File not found. Please enter a valid path.${CLR_RESET}"
          fi
        done
        while [[ ! -f "$user_key_path" ]]; do
          read -r -p "Enter path to private key file (privkey.pem): " user_key_path
          if [[ ! -f "$user_key_path" ]]; then
            echo -e "${CLR_RED}[!] File not found. Please enter a valid path.${CLR_RESET}"
          fi
        done
        cp -f "$user_cert_path" "$CONFIG_DIR/certs/cert.pem"
        cp -f "$user_key_path" "$CONFIG_DIR/certs/key.pem"
        chmod 0644 "$CONFIG_DIR/certs/cert.pem"
        chmod 0600 "$CONFIG_DIR/certs/key.pem"
        cert_auto_generated=false
        echo -e "${CLR_GREEN}[+] SSL certificates copied successfully.${CLR_RESET}"
      elif [[ "$cert_choice" == "2" ]]; then
        local email=""
        read -r -p "Enter your email for Let's Encrypt (optional, press Enter to skip): " email
        if generate_letsencrypt_cert "$domain" "$email"; then
          cert_auto_generated=false
        else
          echo -e "${CLR_YELLOW}[!] Let's Encrypt failed. Generating a local self-signed certificate instead.${CLR_RESET}"
          generate_self_signed_cert "$domain"
          cert_auto_generated=true
        fi
      else
        generate_self_signed_cert "$domain"
        cert_auto_generated=true
      fi
    fi

    # 3. Ask for Panel Port (default 8080) with port conflict check
    while true; do
      clear || true
      draw_box_top "PANEL MANAGEMENT PORT"
      echo -e "│  ${CLR_WHITE}Set the port for the Panel web interface:${CLR_RESET}"
      echo -e "│  Default is 8080, but you can configure any open port."
      draw_box_bottom
      read -r -p "Enter Panel Management Port (default: 8080): " port_in
      port=${port_in:-8080}
      if ! [[ "$port" =~ ^[0-9]+$ ]] || (( port < 1 || port > 65535 )); then
        echo -e "${CLR_RED}[!] Invalid port number${CLR_RESET}"
        sleep 1
        continue
      fi
      
      if have ss; then
        if ss -lntp | grep -qE "[:.]${port}[[:space:]]"; then
          echo -e "${CLR_YELLOW}[!] Warning: Port ${port} is currently in use on the host!${CLR_RESET}"
          local force_port="n"
          read -r -p "Are you sure you want to use this port anyway? (y/n) [default: n]: " force_port
          force_port=${force_port:-n}
          if [[ "${force_port,,}" == "y" ]]; then
            break
          fi
        else
          break
        fi
      else
        break
      fi
    done

    # 4. Ask for Admin Credentials
    clear || true
    draw_box_top "ADMIN CREDENTIALS"
    echo -e "│  ${CLR_WHITE}Configure the admin user to log into the web console:${CLR_RESET}"
    draw_box_bottom
    read -r -p "Admin Username (default: admin): " user_in
    username=${user_in:-admin}
    while [[ -z "$password" ]]; do
      read -r -s -p "Admin Password (required): " password
      echo ""
    done

    # Generate initial JSON database securely
    local pwd_hash; pwd_hash=$(python3 -c "import hashlib; print(hashlib.sha256(input().encode()).hexdigest())" <<< "$password")
    
    mkdir -p "$CONFIG_DIR"
    python3 -c "
import json, sys
data = {
    'admin': {'username': sys.argv[1], 'password_hash': sys.argv[2]},
    'settings': {
        'port': int(sys.argv[3]),
        'panel_host': sys.argv[4],
        'test_interval': 30,
        'max_idle_seconds': 300,
        'panel_tls': True,
        'cert_path': f'{sys.argv[6]}/certs/cert.pem',
        'key_path': f'{sys.argv[6]}/certs/key.pem',
        'cert_auto_generated': sys.argv[8].lower() == 'true'
    },
    'nodes': {}, 'links': {}, 'logs': []
}
json.dump(data, open(sys.argv[7], 'w'), indent=4)
" "$username" "$pwd_hash" "$port" "$panel_host" "${panel_tls:-true}" "$CONFIG_DIR" "$CONFIG_DIR/p00rija_db.json" "$cert_auto_generated"
    chmod 0600 "$CONFIG_DIR/p00rija_db.json"

  else
    # Node Installation (Internal or External Node)
    clear || true
    draw_box_top "NODE TYPE SELECTION"
    echo -e "│  ${CLR_WHITE}Please choose the Node Type:${CLR_RESET}"
    echo -e "│  1) Internal Node (Handles local entry connections)"
    echo -e "│  2) External Node (Connects reverse tunnel to Internal Node)"
    draw_box_bottom
    
    local type_choice=""
    while [[ ! "$type_choice" =~ ^[1-2]$ ]]; do
      read -r -p "Selection (1-2): " type_choice
    done
    if [[ "$type_choice" == "1" ]]; then
      role="internal"
    else
      role="external"
    fi
    
    # Choose Native or Docker for Node
    clear || true
    draw_box_top "NODE DEPLOYMENT ENVIRONMENT"
    echo -e "│  ${CLR_WHITE}Choose Node Execution Environment (Recommended: Docker):${CLR_RESET}"
    echo -e "│  1) Docker (Containerized - Recommended)${CLR_GREEN} [Recommended]${CLR_RESET}"
    echo -e "│  2) Systemd (Native Host Linux Service)"
    draw_box_bottom
    
    local run_choice=""
    while [[ ! "$run_choice" =~ ^[1-2]$ ]]; do
      read -r -p "Selection (1-2) [default: 1]: " run_choice
      run_choice=${run_choice:-1}
    done
    [[ "$run_choice" == "2" ]] && run_mode="systemd"

    # Ask for Web Panel credentials
    clear || true
    draw_box_top "NODE ACCESS CREDENTIALS"
    echo -e "│  ${CLR_WHITE}Enter details to connect this Node to the central Panel:${CLR_RESET}"
    draw_box_bottom
    while [[ -z "$panel_url" ]]; do
      read -r -p "Web Panel API URL (e.g. https://domain.com:8080 or https://1.2.3.4:8080): " panel_url
    done
    while [[ -z "$token" ]]; do
      read -r -p "Node Access Token (from Panel UI): " token
    done
    local private_key=""
    read -r -p "Node Private Key (from Panel UI, optional): " private_key
  fi

  # Save Config JSON securely
  install -m 0600 /dev/null "$CONFIG_PATH"
  if [[ "$role" == "panel" ]]; then
    python3 -c "import json, sys; json.dump({'role': 'panel', 'port': int(sys.argv[1])}, open(sys.argv[2], 'w'), indent=4)" "$port" "$CONFIG_PATH"
  else
    python3 -c "import json, sys; json.dump({'role': sys.argv[1], 'panel_url': sys.argv[2], 'token': sys.argv[3], 'private_key': sys.argv[4]}, open(sys.argv[5], 'w'), indent=4)" "$role" "${panel_url%/}" "$token" "$private_key" "$CONFIG_PATH"
  fi
  
  # Register runtime mode
  echo "$run_mode" > "$CONFIG_DIR/.run_mode"
  
  # Execute target launcher
  if [[ "$run_mode" == "docker" ]]; then
    systemctl stop p00rija-tunnel.service >/dev/null 2>&1 || true
    systemctl disable p00rija-tunnel.service >/dev/null 2>&1 || true
    run_docker_container "$server_region"
  else
    docker stop "$DOCKER_CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rm "$DOCKER_CONTAINER_NAME" >/dev/null 2>&1 || true
    setup_systemd_service
  fi

  local display_role_msg="PANEL"
  if [[ "$role" == "internal" ]]; then
    display_role_msg="INTERNAL NODE"
  elif [[ "$role" == "external" ]]; then
    display_role_msg="EXTERNAL NODE"
  fi
  
  echo -e "${CLR_GREEN}[+] P00RIJA TUNNEL (${display_role_msg}) successfully set up on ${run_mode^^}!${CLR_RESET}"
}

get_run_mode() {
  local run_mode_file="$CONFIG_DIR/.run_mode"
  if [[ -f "$run_mode_file" ]]; then
    cat "$run_mode_file"
  else
    echo "systemd"
  fi
}

start_tunnel() {
  local mode; mode=$(get_run_mode)
  if [[ "$mode" == "docker" ]]; then
    docker start "$DOCKER_CONTAINER_NAME"
  else
    systemctl start p00rija-tunnel.service
  fi
  echo -e "${CLR_GREEN}[+] Service started.${CLR_RESET}"
}

stop_tunnel() {
  local mode; mode=$(get_run_mode)
  if [[ "$mode" == "docker" ]]; then
    docker stop "$DOCKER_CONTAINER_NAME"
  else
    systemctl stop p00rija-tunnel.service
  fi
  echo -e "${CLR_YELLOW}[-] Service stopped.${CLR_RESET}"
}

restart_tunnel() {
  local mode; mode=$(get_run_mode)
  if [[ "$mode" == "docker" ]]; then
    docker restart "$DOCKER_CONTAINER_NAME"
  else
    systemctl restart p00rija-tunnel.service
  fi
  echo -e "${CLR_GREEN}[+] Service restarted.${CLR_RESET}"
}

show_logs() {
  local mode; mode=$(get_run_mode)
  if [[ "$mode" == "docker" ]]; then
    docker logs -f "$DOCKER_CONTAINER_NAME" || true
  else
    journalctl -u p00rija-tunnel.service -n 50 -f || true
  fi
}

optimize_server() {
  echo -e "\n${CLR_CYAN}[*] Optimizing system TCP and networking stack...${CLR_RESET}"
  if have modprobe; then
    modprobe tcp_bbr >/dev/null 2>&1 || true
  fi

  if have sysctl; then
    sysctl -w net.core.default_qdisc=fq >/dev/null 2>&1 || true
    sysctl -w net.ipv4.tcp_congestion_control=bbr >/dev/null 2>&1 || true
    
    local conf="/etc/sysctl.d/99-p00rija-tunnel.conf"
    cat > "$conf" <<'EOF'
# P00RIJA Tunnel - network tuning
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr

# Connection limits and buffer sizes
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
net.ipv4.tcp_max_syn_backlog=8192
net.core.somaxconn=16384
EOF
    sysctl --system >/dev/null 2>&1 || true
    echo -e "${CLR_GREEN}[+] TCP Optimization and BBR applied successfully.${CLR_RESET}"
  fi
}

uninstall_all() {
  echo -e "${CLR_RED}[*] Uninstalling P00RIJA TUNNEL...${CLR_RESET}"
  
  docker stop "$DOCKER_CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rm "$DOCKER_CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rmi p00rija-tunnel:latest >/dev/null 2>&1 || true
  
  systemctl stop p00rija-tunnel.service >/dev/null 2>&1 || true
  systemctl disable p00rija-tunnel.service >/dev/null 2>&1 || true
  rm -f "$SERVICE_PATH" >/dev/null 2>&1 || true
  systemctl daemon-reload
  
  read -r -p "Are you sure you want to uninstall and delete all data in $CONFIG_DIR? (type YES): " confirm
  if [[ "$confirm" == "YES" ]]; then
    rm -rf "$CONFIG_DIR" >/dev/null 2>&1 || true
  else
    echo -e "${CLR_YELLOW}[*] Kept configuration data at $CONFIG_DIR${CLR_RESET}"
  fi
  rm -f "$INSTALL_PATH" >/dev/null 2>&1 || true
  
  # Cleanup legacy paths
  rm -f "/usr/local/bin/pahlavi-tunnel" >/dev/null 2>&1 || true
  rm -rf "/opt/pahlavi" >/dev/null 2>&1 || true
  
  echo -e "${CLR_GREEN}[+] Uninstalled successfully.${CLR_RESET}"
}

print_banner() {
  local service_status="${CLR_RED}STOPPED${CLR_RESET}"
  local mode; mode=$(get_run_mode)
  
  if [[ "$mode" == "docker" ]]; then
    if docker ps --format '{{.Names}}' | grep -q "^${DOCKER_CONTAINER_NAME}$"; then
      service_status="${CLR_GREEN}RUNNING (DOCKER)${CLR_RESET}"
    fi
  else
    if systemctl is-active --quiet p00rija-tunnel.service 2>/dev/null; then
      service_status="${CLR_GREEN}RUNNING (SYSTEMD)${CLR_RESET}"
    fi
  fi
  
  echo -e "${CLR_CYAN}${CLR_BOLD}"
  echo "    ____  ____  ____  ____  ________ ___      _______  ___  _  _______ "
  echo "   / __ \/ __ \/ __ \/ __ \/  _/ __//   |    /_  __/ / / / |/ / / / __/"
  echo "  / /_/ / /_/ / /_/ / /_/ // // _/ / /| |     / / / /_/ /    / /_/ _/  "
  echo " / ____/\____/\____/_/ \_\___/___//_/ |_|    /_/  \____/_/|_/\____/___/ "
  echo "                                                                       "
  echo -e "${CLR_RESET}"
  echo -e "${CLR_GREEN}Version:${CLR_RESET} v${VERSION}"
  echo -e "${CLR_GREEN}Telegram ID:${CLR_RESET} ${TG_ID}"
  echo -e "${CLR_CYAN}Service Status:${CLR_RESET} ${service_status}"
  echo -e "${CLR_DIM}============================================================${CLR_RESET}"
  
  # Dynamic Check and Show Configuration Details
  detect_existing_install
}

# ===================== Main Execution =====================
need_root
install_dependencies
ensure_env

# If existing setup is Docker, verify Docker is installed on startup
if [[ "$(get_run_mode)" == "docker" ]]; then
  manage_docker_install
fi

# Register global command alias
if [[ ! -f "$INSTALL_PATH" ]] || ! diff -q "$0" "$INSTALL_PATH" >/dev/null 2>&1; then
  cp -f "$0" "$INSTALL_PATH"
  chmod +x "$INSTALL_PATH"
  echo -e "${CLR_GREEN}[+] CLI manager registered globally. Run with: sudo Pooriya-tunnel${CLR_RESET}"
fi

if [[ -f "./p00rija-control.sh" ]]; then
  install -m 0755 "./p00rija-control.sh" "$CONTROL_PATH"
  echo -e "${CLR_GREEN}[+] Server control CLI registered globally. Run with: sudo p00rija status${CLR_RESET}"
fi

while true; do
  clear || true
  print_banner

  echo -e "${CLR_WHITE}${CLR_BOLD}1.${CLR_RESET} Run Interactive Setup Wizard"
  echo -e "${CLR_WHITE}${CLR_BOLD}2.${CLR_RESET} Start Tunnel Daemon"
  echo -e "${CLR_WHITE}${CLR_BOLD}3.${CLR_RESET} Stop Tunnel Daemon"
  echo -e "${CLR_WHITE}${CLR_BOLD}4.${CLR_RESET} Restart Tunnel Daemon"
  echo -e "${CLR_WHITE}${CLR_BOLD}5.${CLR_RESET} Show Real-Time Core Logs"
  echo -e "${CLR_WHITE}${CLR_BOLD}6.${CLR_RESET} Optimize Linux TCP (BBR + Somaxconn)"
  echo -e "${CLR_WHITE}${CLR_BOLD}7.${CLR_RESET} Uninstall P00RIJA TUNNEL"
  echo -e "${CLR_WHITE}${CLR_BOLD}0.${CLR_RESET} Exit"
  echo -e "${CLR_DIM}------------------------------------------------------------${CLR_RESET}"

  read -r -p "Select option: " choice
  case "$choice" in
    1) run_setup_wizard; pause ;;
    2) start_tunnel; sleep 1 ;;
    3) stop_tunnel; sleep 1 ;;
    4) restart_tunnel; sleep 1 ;;
    5) show_logs ;;
    6) optimize_server; pause ;;
    7) uninstall_all; pause; exit 0 ;;
    0) exit 0 ;;
    *) echo -e "${CLR_RED}Invalid option.${CLR_RESET}"; sleep 1 ;;
  esac
done
