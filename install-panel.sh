#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="/opt/p00rija/panel"
BIN="/usr/local/bin/Pooriya-tunnel"
CONTROL_BIN="/usr/local/bin/p00rija"
CONTAINER="p00rija-panel"
VERSION="1.9.95"
IMAGE="p00rija-tunnel:${VERSION}"
P00RIJA_DOCKER_IR_MIRRORS="${P00RIJA_DOCKER_IR_MIRRORS:-https://docker.iranserver.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/installer-ui.sh" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/installer-ui.sh"
else
  HELPER_URL="${P00RIJA_REPO_RAW:-https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main}/installer-ui.sh"
  HELPER_TMP="/tmp/p00rija-installer-ui.sh"
  if curl -fsSL "$HELPER_URL" -o "$HELPER_TMP"; then
    # shellcheck disable=SC1090
    source "$HELPER_TMP"
  fi
fi

need_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "[!] Run as root: sudo bash install-panel.sh" >&2
    exit 1
  fi
}

have() { command -v "$1" >/dev/null 2>&1; }

prompt_line() {
  local prompt_outvar="$1"
  local prompt="$2"
  local default="${3:-}"
  local value=""
  if declare -F ui_input >/dev/null 2>&1; then
    ui_input value "P00RIJA installer" "$prompt" "$default"
  elif ! read -r -p "$prompt" value; then
    value="$default"
  fi
  printf -v "$prompt_outvar" '%s' "${value:-$default}"
}

prompt_secret_required() {
  local prompt_outvar="$1"
  local prompt="$2"
  local value=""
  if declare -F ui_password >/dev/null 2>&1; then
    ui_password value "P00RIJA installer" "$prompt" || return 1
  elif [[ ! -t 0 ]]; then
    echo "[!] Interactive input is required for this value." >&2
    return 1
  else
    read -r -s -p "$prompt" value
    echo
  fi
  [[ -n "$value" ]] || return 1
  printf -v "$prompt_outvar" '%s' "$value"
}

is_update_mode() {
  [[ "${1:-}" == "--update" || "${P00RIJA_INSTALL_MODE:-}" == "update" ]]
}

backup_existing_state() {
  [[ -d "$CONFIG_DIR" ]] || return 0
  local backup_dir="$CONFIG_DIR/backups/update-$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$backup_dir"
  for item in p00rija_config.json p00rija_db.json .run_mode certs; do
    [[ -e "$CONFIG_DIR/$item" ]] && cp -a "$CONFIG_DIR/$item" "$backup_dir/"
  done
  echo "[i] Existing panel state backed up to $backup_dir"
}

read_panel_ports() {
  python3 - "$CONFIG_DIR/p00rija_config.json" "$CONFIG_DIR/p00rija_db.json" <<'PY'
import json, sys
config_path, db_path = sys.argv[1:3]
port, api_port = 8080, 8000
for path in (db_path, config_path):
    try:
        with open(path) as f:
            data = json.load(f)
        source = data.get("settings", data)
        port = int(source.get("port", port))
        api_port = int(source.get("api_port", api_port))
    except Exception:
        pass
print(port, api_port)
PY
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
    echo "[i] Docker registry mirror configured: ${P00RIJA_DOCKER_IR_MIRRORS}"
    if [[ "${P00RIJA_SKIP_DOCKER_MIRROR_PROBE:-0}" != "1" ]] && have docker; then
      if timeout 45 docker pull hello-world:latest >/dev/null 2>&1; then
        echo "[+] Docker mirror probe succeeded."
      else
        echo "[!] Docker mirror probe failed. Keeping the mirror config, but image pulls may need network access to Docker Hub."
      fi
    fi
  fi
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

install_docker_pkg() {
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    if declare -F apt_update_with_retries >/dev/null 2>&1; then apt_update_with_retries; else apt-get update -y; fi
    apt-get install -y docker.io python3 curl ca-certificates jq openssl whiptail
  elif have yum; then
    yum install -y docker python3 curl ca-certificates jq openssl newt
  elif have apk; then
    apk add docker python3 curl ca-certificates jq openssl newt
    rc-update add docker boot >/dev/null 2>&1 || true
  fi
}

install_base_deps() {
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    if declare -F apt_update_with_retries >/dev/null 2>&1; then apt_update_with_retries; else apt-get update -y; fi
    apt-get install -y python3 curl ca-certificates jq openssl whiptail
  elif have yum; then
    yum install -y python3 curl ca-certificates jq openssl newt || dnf install -y python3 curl ca-certificates jq openssl newt
  elif have apk; then
    apk add python3 curl ca-certificates jq openssl newt
  fi
}

ensure_docker() {
  local region="$1"
  if have docker; then
    systemctl enable docker >/dev/null 2>&1 || true
    systemctl start docker >/dev/null 2>&1 || true
    return 0
  fi
  
  if [[ "$region" != "ir" ]]; then
    echo "[i] Installing official Docker using get.docker.com..."
    if curl -fsSL https://get.docker.com -o /tmp/get-docker.sh; then
      sh /tmp/get-docker.sh
      rm -f /tmp/get-docker.sh
    else
      echo "[!] Failed to download Docker install script, falling back to package manager."
      install_docker_pkg
    fi
  else
    echo "[i] Installing Docker via local package manager (Iran compatible)..."
    install_docker_pkg
  fi
  systemctl enable docker >/dev/null 2>&1 || true
  systemctl start docker >/dev/null 2>&1 || true
}

enable_bbr() {
  echo "[i] Optimizing network kernel (Enabling BBR)..."
  if have sysctl; then
    # Only append if not already present
    if ! grep -q "net.core.default_qdisc=fq" /etc/sysctl.conf; then
      echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
    fi
    if ! grep -q "net.ipv4.tcp_congestion_control=bbr" /etc/sysctl.conf; then
      echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
    fi
    sysctl -p >/dev/null 2>&1 || true
  fi
}

disable_ipv6() {
  echo "[i] Disabling IPv6 system-wide..."
  if have sysctl; then
    if ! grep -q "net.ipv6.conf.all.disable_ipv6 = 1" /etc/sysctl.conf; then
      echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf
      echo "net.ipv6.conf.default.disable_ipv6 = 1" >> /etc/sysctl.conf
      echo "net.ipv6.conf.lo.disable_ipv6 = 1" >> /etc/sysctl.conf
    fi
    sysctl -p >/dev/null 2>&1 || true
  fi
}

build_image() {
  local region="${1:-global}"
  mkdir -p "$CONFIG_DIR"
  if [[ -f "$SCRIPT_DIR/P00RIJA.py" ]]; then
    install -m 0755 "$SCRIPT_DIR/P00RIJA.py" "$CONFIG_DIR/P00RIJA.py"
  else
    curl -fsSL "https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/P00RIJA.py" -o "$CONFIG_DIR/P00RIJA.py"
    chmod 0755 "$CONFIG_DIR/P00RIJA.py"
  fi

  if [[ -f "$SCRIPT_DIR/download_engines.py" ]]; then
    install -m 0755 "$SCRIPT_DIR/download_engines.py" "$CONFIG_DIR/download_engines.py"
  else
    printf '%s\n' '#!/usr/bin/env python3' 'print("download_engines.py is not bundled in this install package.")' > "$CONFIG_DIR/download_engines.py"
    chmod 0755 "$CONFIG_DIR/download_engines.py"
  fi
  
  if [[ -f "$SCRIPT_DIR/Pooriya-tunnel.sh" ]]; then
    install -m 0755 "$SCRIPT_DIR/Pooriya-tunnel.sh" "$BIN"
  else
    curl -fsSL "https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/Pooriya-tunnel.sh" -o "$BIN"
    chmod 0755 "$BIN"
  fi
  if [[ -f "$SCRIPT_DIR/p00rija-control.sh" ]]; then
    install -m 0755 "$SCRIPT_DIR/p00rija-control.sh" "$CONTROL_BIN"
  fi

  if [[ -d "$SCRIPT_DIR/engines" ]]; then
    rm -rf "$CONFIG_DIR/engines"
    cp -r "$SCRIPT_DIR/engines" "$CONFIG_DIR/engines"
  else
    mkdir -p "$CONFIG_DIR/engines"
  fi
  if [[ -d "$SCRIPT_DIR/fonts" ]]; then
    rm -rf "$CONFIG_DIR/fonts"
    cp -r "$SCRIPT_DIR/fonts" "$CONFIG_DIR/fonts"
  else
    mkdir -p "$CONFIG_DIR/fonts"
  fi
  if [[ -d "$SCRIPT_DIR/p00rija_core" ]]; then
    rm -rf "$CONFIG_DIR/p00rija_core"
    cp -r "$SCRIPT_DIR/p00rija_core" "$CONFIG_DIR/p00rija_core"
  else
    mkdir -p "$CONFIG_DIR/p00rija_core"
    printf '%s\n' '"""Fallback empty module package."""' > "$CONFIG_DIR/p00rija_core/__init__.py"
  fi
  local package_file
  for package_file in install.sh install-panel.sh install-node.sh installer-ui.sh Pooriya-tunnel.sh p00rija-control.sh restore-panel-backup.sh p00rija-host-agent.py README.md README_FA.md LICENSE .dockerignore; do
    if [[ -f "$SCRIPT_DIR/$package_file" ]]; then
      install -m 0644 "$SCRIPT_DIR/$package_file" "$CONFIG_DIR/$package_file"
    fi
  done

  cat > "$CONFIG_DIR/Dockerfile" <<'EOF'
FROM python:3.11-slim
ARG P00RIJA_REGION=global
ENV PYTHONUNBUFFERED=1
RUN if [ "$P00RIJA_REGION" = "ir" ]; then \
      sed -i 's|http://deb.debian.org/debian-security|https://mirror.iranserver.com/debian-security|g; s|http://deb.debian.org/debian|https://mirror.iranserver.com/debian|g' /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true; \
    fi && \
    apt-get -o Acquire::Check-Valid-Until=false update && apt-get install -y --no-install-recommends openssl iputils-ping iperf3 curl procps openssh-client sshpass ca-certificates iproute2 wireguard-tools stunnel4 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY P00RIJA.py /app/P00RIJA.py
COPY download_engines.py /app/download_engines.py
COPY p00rija_core/ /app/p00rija_core/
COPY fonts/ /app/fonts/
COPY install.sh install-panel.sh install-node.sh installer-ui.sh Pooriya-tunnel.sh p00rija-control.sh restore-panel-backup.sh p00rija-host-agent.py README.md README_FA.md LICENSE Dockerfile /app/
COPY engines/ /usr/local/bin/
CMD ["python3", "/app/P00RIJA.py"]
EOF
  docker build --build-arg "P00RIJA_REGION=$region" -t "$IMAGE" -f "$CONFIG_DIR/Dockerfile" "$CONFIG_DIR"
}

install_host_agent() {
  [[ -f "$CONFIG_DIR/p00rija-host-agent.py" ]] || {
    echo "[!] Host agent file is missing; panel port and Let's Encrypt controls will be unavailable." >&2
    return 1
  }
  mkdir -p "$CONFIG_DIR/host_control/requests" "$CONFIG_DIR/host_control/results"
  chmod 0700 "$CONFIG_DIR/host_control" "$CONFIG_DIR/host_control/requests" "$CONFIG_DIR/host_control/results"
  chmod 0700 "$CONFIG_DIR/p00rija-host-agent.py"
  if ! have certbot; then
    if have apt-get; then
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -y
      apt-get install -y certbot
    elif have dnf; then
      dnf install -y certbot
    elif have yum; then
      yum install -y certbot
    elif have apk; then
      apk add certbot
    fi
  fi
  cat > /etc/systemd/system/p00rija-host-agent.service <<EOF
[Unit]
Description=P00RIJA privileged host control agent
After=docker.service network-online.target
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 $CONFIG_DIR/p00rija-host-agent.py
Restart=always
RestartSec=2
UMask=0077
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now p00rija-host-agent.service
}

run_panel_container() {
  local port="$1" api_port="$2"
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  local tun_args=(--cap-add NET_ADMIN)
  if [[ -c /dev/net/tun ]]; then
    tun_args+=(--device /dev/net/tun)
  fi
  local publish_args=(-p "$port:$port")
  if [[ "$api_port" != "$port" ]]; then
    publish_args+=(-p "$api_port:$api_port")
  fi
  docker run -d --name "$CONTAINER" --network bridge --restart unless-stopped \
    "${tun_args[@]}" \
    "${publish_args[@]}" \
    -v "$CONFIG_DIR:/opt/p00rija" \
    "$IMAGE"
}

update_existing_panel() {
  [[ -f "$CONFIG_DIR/p00rija_config.json" ]] || {
    echo "[!] Existing panel config was not found at $CONFIG_DIR/p00rija_config.json" >&2
    echo "[!] Run a fresh panel install first, or remove --update." >&2
    exit 1
  }
  local region="global" port api_port
  region=$(detect_server_region)
  export P00RIJA_SERVER_REGION="$region"
  declare -F configure_package_mirrors >/dev/null 2>&1 && configure_package_mirrors "$region"
  install_base_deps
  ensure_docker "$region"
  configure_docker_mirror "$region"
  backup_existing_state
  build_image "$region"
  install_host_agent
  read -r port api_port <<< "$(read_panel_ports)"
  echo "docker" > "$CONFIG_DIR/.run_mode"
  run_panel_container "$port" "$api_port"
  echo "[+] Panel updated to ${IMAGE#*:}. Existing database, nodes, tunnels, and certificates were kept."
  echo "[i] Published ports: web=$port api=$api_port"
}

copy_existing_certificates() {
  mkdir -p "$CONFIG_DIR/certs"
  local user_cert_path="" user_key_path=""
  while [[ ! -f "$user_cert_path" ]]; do
    prompt_line user_cert_path "Existing certificate/fullchain path: "
    [[ -f "$user_cert_path" ]] || echo "[!] Certificate file not found."
  done
  while [[ ! -f "$user_key_path" ]]; do
    prompt_line user_key_path "Existing private key path: "
    [[ -f "$user_key_path" ]] || echo "[!] Private key file not found."
  done
  install -m 0644 "$user_cert_path" "$CONFIG_DIR/certs/cert.pem"
  install -m 0600 "$user_key_path" "$CONFIG_DIR/certs/key.pem"
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
}

generate_letsencrypt_cert() {
  local domain="$1" email="${2:-}"
  mkdir -p "$CONFIG_DIR/certs"
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y certbot
  elif have yum; then
    yum install -y certbot || dnf install -y certbot
  elif have apk; then
    apk add certbot
  fi
  local -a cmd=(certbot certonly --standalone -d "$domain" --agree-tos --non-interactive)
  if [[ -n "$email" ]]; then
    cmd+=(--email "$email")
  else
    cmd+=(--register-unsafely-without-email)
  fi
  if "${cmd[@]}"; then
    install -m 0644 "/etc/letsencrypt/live/${domain}/fullchain.pem" "$CONFIG_DIR/certs/cert.pem"
    install -m 0600 "/etc/letsencrypt/live/${domain}/privkey.pem" "$CONFIG_DIR/certs/key.pem"
    return 0
  fi
  return 1
}

main() {
  need_root
  declare -F ui_banner >/dev/null 2>&1 && ui_banner "Central Panel Installer"
  if is_update_mode "${1:-}"; then
    update_existing_panel
    return 0
  fi
  local region="global"
  if declare -F prepare_installer_ui >/dev/null 2>&1; then
    prepare_installer_ui region
  else
    region=$(detect_server_region)
    local def_choice="2"
    if [[ "$region" == "ir" ]]; then
      echo "[i] Auto-detected Iran server location."
      def_choice="1"
    fi
    prompt_line region_choice "Server location? [1] Iran/internal mirrors [2] Global Docker [default: $def_choice]: " "$def_choice"
    region_choice=${region_choice:-$def_choice}
    [[ "$region_choice" == "1" ]] && region="ir" || region="global"
  fi
  install_base_deps
  
  ensure_docker "$region"
  configure_docker_mirror "$region"
  enable_bbr

  local rand_port=$(( RANDOM % 55535 + 10000 ))
  local port="" api_port="" username="admin" password="" panel_host="127.0.0.1" cert_auto_generated=true
  if declare -F ui_menu >/dev/null 2>&1; then
    ui_menu access_choice "Panel access mode" "Choose how users will open the panel." "1" \
      "1:IP/local HTTPS with self-signed certificate" \
      "2:Domain HTTPS"
  else
    echo "Panel access mode:"
    echo "1) IP/local HTTPS with self-signed certificate"
    echo "2) Domain HTTPS"
    prompt_line access_choice "Selection [1-2, default: 1]: " "1"
  fi
  access_choice=${access_choice:-1}
  if [[ "$access_choice" == "2" ]]; then
    while [[ -z "$panel_host" || "$panel_host" == "127.0.0.1" ]]; do
      prompt_line panel_host "Panel domain (example: panel.example.com): "
    done
    if declare -F ui_menu >/dev/null 2>&1; then
      ui_menu cert_choice "SSL certificate source" "Choose certificate source for the panel domain." "3" \
        "1:Use existing certificate files" \
        "2:Get Let's Encrypt certificate now" \
        "3:Generate self-signed certificate"
    else
      echo "SSL certificate source:"
      echo "1) Use existing certificate files"
      echo "2) Get Let's Encrypt certificate now"
      echo "3) Generate self-signed certificate for this domain"
      prompt_line cert_choice "Selection [1-3, default: 3]: " "3"
    fi
    cert_choice=${cert_choice:-3}
    if [[ "$cert_choice" == "1" ]]; then
      copy_existing_certificates
      cert_auto_generated=false
    elif [[ "$cert_choice" == "2" ]]; then
      prompt_line le_email "Email for Let's Encrypt (optional): "
      if generate_letsencrypt_cert "$panel_host" "$le_email"; then
        cert_auto_generated=false
      else
        echo "[!] Let's Encrypt failed. Generating a self-signed certificate instead."
        generate_self_signed_cert "$panel_host"
        cert_auto_generated=true
      fi
    else
      generate_self_signed_cert "$panel_host"
      cert_auto_generated=true
    fi
  else
    local detected_ip; detected_ip=$(curl -fsSL --max-time 3 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}' || echo "127.0.0.1")
    prompt_line panel_host "Panel IP/host for certificate [$detected_ip]: " "$detected_ip"
    panel_host=${panel_host:-$detected_ip}
    generate_self_signed_cert "$panel_host"
    cert_auto_generated=true
  fi
  prompt_line port "Panel port [$rand_port]: " "$rand_port"
  port=${port:-$rand_port}
  prompt_line api_port "API port [8000]: " "8000"
  api_port=${api_port:-8000}
  
  prompt_line username "Admin username [admin]: " "admin"
  username=${username:-admin}
  while [[ -z "$password" ]]; do
    if ! prompt_secret_required password "Admin password: "; then
      echo "[!] Admin password is required." >&2
      exit 1
    fi
  done

  build_image "$region"
  install_host_agent
  
  local pwd_hash; pwd_hash=$(python3 -c "import hashlib; print(hashlib.sha256(input().encode()).hexdigest())" <<< "$password")
  
  mkdir -p "$CONFIG_DIR"
  python3 -c "
import json, sys
data = {
    'admin': {'username': sys.argv[1], 'password_hash': sys.argv[2]},
    'settings': {
        'port': int(sys.argv[3]),
        'api_port': int(sys.argv[4]),
        'panel_host': sys.argv[5],
        'test_interval': 30,
        'max_idle_seconds': 300,
        'panel_tls': True,
        'cert_path': f'/opt/p00rija/certs/cert.pem',
        'key_path': f'/opt/p00rija/certs/key.pem',
        'cert_auto_generated': sys.argv[6].lower() == 'true'
    },
    'nodes': {}, 'links': {}, 'logs': []
}
json.dump(data, open(sys.argv[7], 'w'), indent=4)
" "$username" "$pwd_hash" "$port" "$api_port" "$panel_host" "$cert_auto_generated" "$CONFIG_DIR/p00rija_db.json"
  chmod 0600 "$CONFIG_DIR/p00rija_db.json"
  
  install -m 0600 /dev/null "$CONFIG_DIR/p00rija_config.json"
  python3 -c "import json, sys; json.dump({'role': 'panel', 'port': int(sys.argv[1]), 'api_port': int(sys.argv[2])}, open(sys.argv[3], 'w'), indent=4)" "$port" "$api_port" "$CONFIG_DIR/p00rija_config.json"
  echo "docker" > "$CONFIG_DIR/.run_mode"
  run_panel_container "$port" "$api_port"
  echo "[+] Panel is running securely on HTTPS port $port"
  echo "[i] Open: https://$panel_host:$port"
  echo "[i] Docker bridge mode is enabled. Published web/api ports: $port,$api_port"
  echo "[i] You can also install a node on this server without conflicts."
}

main "$@"
