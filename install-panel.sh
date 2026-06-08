#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="/opt/p00rija/panel"
BIN="/usr/local/bin/Pooriya-tunnel"
CONTROL_BIN="/usr/local/bin/p00rija"
CONTAINER="p00rija-panel"
IMAGE="p00rija-tunnel:1.3.0"

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
    echo "[!] Installer package is missing. Run as root so it can download the full package: sudo bash install-panel.sh" >&2
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

need_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "[!] Run as root: sudo bash install-panel.sh" >&2
    exit 1
  fi
}

install_base_deps() {
  ui_info "Installing base dependencies..."
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    apt_update_with_retries
    apt-get install -y python3 curl ca-certificates jq openssl
  elif have yum; then
    yum install -y python3 curl ca-certificates jq openssl || dnf install -y python3 curl ca-certificates jq openssl
  elif have apk; then
    apk add python3 curl ca-certificates jq openssl
  fi
}

install_docker_pkg() {
  ui_info "Installing Docker from the selected package repositories..."
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    apt_update_with_retries
    apt-get install -y docker.io python3 curl ca-certificates jq openssl
  elif have yum; then
    yum install -y docker python3 curl ca-certificates jq openssl || dnf install -y docker python3 curl ca-certificates jq openssl
  elif have apk; then
    apk add docker python3 curl ca-certificates jq openssl
    rc-update add docker boot >/dev/null 2>&1 || true
  fi
}

ensure_docker() {
  local region="$1"
  if have docker; then
    systemctl enable docker >/dev/null 2>&1 || true
    systemctl start docker >/dev/null 2>&1 || true
    configure_docker_mirror "$region"
    return 0
  fi
  if [[ "$region" == "ir" ]]; then
    install_docker_pkg
  else
    ui_info "Docker is missing. Trying official Docker installer first..."
    if curl -fsSL https://get.docker.com -o /tmp/get-docker.sh; then
      sh /tmp/get-docker.sh
      rm -f /tmp/get-docker.sh
    else
      ui_warn "Official Docker installer failed. Falling back to package manager."
      install_docker_pkg
    fi
  fi
  systemctl enable docker >/dev/null 2>&1 || true
  systemctl start docker >/dev/null 2>&1 || true
  configure_docker_mirror "$region"
}

enable_bbr() {
  ui_info "Applying TCP/BBR network tuning..."
  if have sysctl; then
    grep -q "net.core.default_qdisc=fq" /etc/sysctl.conf || echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
    grep -q "net.ipv4.tcp_congestion_control=bbr" /etc/sysctl.conf || echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
    sysctl -p >/dev/null 2>&1 || true
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
}

copy_existing_certificates() {
  local cert_path="" key_path=""
  mkdir -p "$CONFIG_DIR/certs"
  while [[ ! -f "$cert_path" ]]; do
    ui_input cert_path "Existing certificate" "Fullchain/certificate file path:" ""
    [[ -f "$cert_path" ]] || ui_msg "File not found" "Certificate file was not found. Please enter a valid path."
  done
  while [[ ! -f "$key_path" ]]; do
    ui_input key_path "Existing private key" "Private key file path:" ""
    [[ -f "$key_path" ]] || ui_msg "File not found" "Private key file was not found. Please enter a valid path."
  done
  install -m 0644 "$cert_path" "$CONFIG_DIR/certs/cert.pem"
  install -m 0600 "$key_path" "$CONFIG_DIR/certs/key.pem"
}

generate_letsencrypt_cert() {
  local domain="$1" email="${2:-}"
  mkdir -p "$CONFIG_DIR/certs"
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    apt_update_with_retries
    apt-get install -y certbot
  elif have yum; then
    yum install -y certbot || dnf install -y certbot
  elif have apk; then
    apk add certbot
  fi
  local -a cmd=(certbot certonly --standalone -d "$domain" --agree-tos --non-interactive)
  if [[ -n "$email" ]]; then cmd+=(--email "$email"); else cmd+=(--register-unsafely-without-email); fi
  if "${cmd[@]}"; then
    install -m 0644 "/etc/letsencrypt/live/${domain}/fullchain.pem" "$CONFIG_DIR/certs/cert.pem"
    install -m 0600 "/etc/letsencrypt/live/${domain}/privkey.pem" "$CONFIG_DIR/certs/key.pem"
    return 0
  fi
  return 1
}

build_image() {
  local region="$1"
  ui_info "Preparing offline Docker build context..."
  mkdir -p "$CONFIG_DIR"
  install -m 0755 "$SCRIPT_DIR/P00RIJA.py" "$CONFIG_DIR/P00RIJA.py"
  install -m 0755 "$SCRIPT_DIR/download_engines.py" "$CONFIG_DIR/download_engines.py"
  install -m 0755 "$SCRIPT_DIR/Pooriya-tunnel.sh" "$BIN"
  install -m 0755 "$SCRIPT_DIR/p00rija-control.sh" "$CONTROL_BIN"
  rm -rf "$CONFIG_DIR/engines" "$CONFIG_DIR/fonts"
  cp -r "$SCRIPT_DIR/engines" "$CONFIG_DIR/engines"
  cp -r "$SCRIPT_DIR/fonts" "$CONFIG_DIR/fonts"
  cat > "$CONFIG_DIR/Dockerfile" <<'EOF'
FROM python:3.11-slim
ARG P00RIJA_REGION=global
ENV PYTHONUNBUFFERED=1
RUN if [ "$P00RIJA_REGION" = "ir" ]; then \
      sed -i 's#http://deb.debian.org/debian#https://archive.debian.petiak.ir/debian#g; s#https://deb.debian.org/debian#https://archive.debian.petiak.ir/debian#g; s#http://ftp.debian.org/debian#https://archive.debian.petiak.ir/debian#g' /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true; \
    fi && \
    (apt-get update -o Acquire::Retries=2 || (apt-get clean; rm -rf /var/lib/apt/lists/*; sed -i 's#https://archive.debian.petiak.ir/debian#http://deb.debian.org/debian#g' /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true; apt-get update -o Acquire::Retries=2)) && \
    apt-get install -y openssl iputils-ping curl procps openssh-client sshpass ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY P00RIJA.py /app/P00RIJA.py
COPY download_engines.py /app/download_engines.py
COPY fonts/ /app/fonts/
COPY engines/ /usr/local/bin/
CMD ["python3", "/app/P00RIJA.py"]
EOF
  docker build --build-arg "P00RIJA_REGION=$region" -t "$IMAGE" -f "$CONFIG_DIR/Dockerfile" "$CONFIG_DIR"
}

load_existing_panel_settings() {
  python3 - "$CONFIG_DIR/p00rija_config.json" "$CONFIG_DIR/p00rija_db.json" <<'PY'
import json, os, shlex, sys
cfg_path, db_path = sys.argv[1], sys.argv[2]
cfg = {}
db = {}
if os.path.exists(cfg_path):
    with open(cfg_path) as f:
        cfg = json.load(f)
if os.path.exists(db_path):
    with open(db_path) as f:
        db = json.load(f)
settings = db.get("settings", {})
values = {
    "port": cfg.get("port") or settings.get("port") or 8080,
    "api_port": cfg.get("api_port") or settings.get("api_port") or 8000,
    "panel_host": settings.get("panel_host") or cfg.get("panel_host") or "127.0.0.1",
}
for key, value in values.items():
    print(f"{key}={shlex.quote(str(value))}")
PY
}

verify_running_panel_code() {
  ui_info "Verifying running panel code inside Docker..."
  if ! docker exec "$CONTAINER" grep -q "/api/links/payload-test" /app/P00RIJA.py 2>/dev/null; then
    ui_msg "Panel update verification failed" "The running panel container does not include the payload-test API. Re-run the update from the latest offline package and make sure Docker rebuilt the image."
    return 1
  fi
  if ! docker exec "$CONTAINER" grep -q "direct_bridge_fallback" /app/P00RIJA.py 2>/dev/null; then
    ui_msg "Panel update verification failed" "The running panel container does not include the direct bridge fallback build. Re-run the update from the latest offline package."
    return 1
  fi
}

update_existing_panel() {
  local region="$1" port="" api_port="" panel_host=""
  ui_info "Updating existing panel while keeping database, certificates, nodes, tunnels, and settings..."
  build_image "$region"
  eval "$(load_existing_panel_settings)"
  chmod 0600 "$CONFIG_DIR/p00rija_db.json" "$CONFIG_DIR/p00rija_config.json" 2>/dev/null || true
  echo "docker" > "$CONFIG_DIR/.run_mode"
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker run -d --name "$CONTAINER" --network bridge --restart always -p "$port:$port" -p "$api_port:$api_port" -v "$CONFIG_DIR:/opt/p00rija" "$IMAGE"
  verify_running_panel_code
  ui_msg "Panel updated" "P00RIJA Panel was updated without resetting data.\n\nOpen: https://${panel_host}:${port}\nAPI port: ${api_port}\nServer CLI: sudo p00rija panel status"
}

main() {
  need_root
  local region="" access_choice="" cert_choice="" panel_host="" port="" api_port="" username="" password="" le_email="" cert_auto_generated=true install_mode=""
  prepare_installer_ui region
  if [[ -f "$CONFIG_DIR/p00rija_db.json" && -f "$CONFIG_DIR/p00rija_config.json" ]]; then
    ui_menu install_mode "Existing panel detected" "A P00RIJA panel is already installed. Update mode does not delete data; it only refreshes panel code, fonts, engines, Docker image, and the running container." "1" \
      "1:Update current panel - keep data and settings" \
      "2:Fresh reinstall - reset panel data"
    if [[ "$install_mode" == "1" ]]; then
      install_base_deps
      ensure_docker "$region"
      enable_bbr
      update_existing_panel "$region"
      return 0
    fi
  fi
  install_base_deps
  ensure_docker "$region"
  enable_bbr

  ui_menu access_choice "Panel access" "Choose how users will open the HTTPS panel." "1" \
    "1:IP/local HTTPS with self-signed certificate" \
    "2:Domain HTTPS"
  if [[ "$access_choice" == "2" ]]; then
    ui_input panel_host "Panel domain" "Domain name, for example panel.example.com:" ""
    ui_menu cert_choice "TLS certificate" "Choose certificate source." "3" \
      "1:Use existing certificate/key files" \
      "2:Get Let's Encrypt certificate now" \
      "3:Generate self-signed certificate"
    if [[ "$cert_choice" == "1" ]]; then
      copy_existing_certificates
      cert_auto_generated=false
    elif [[ "$cert_choice" == "2" ]]; then
      ui_input le_email "Let's Encrypt" "Email address, optional:" ""
      if generate_letsencrypt_cert "$panel_host" "$le_email"; then
        cert_auto_generated=false
      else
        ui_msg "Let's Encrypt failed" "Let's Encrypt failed. A self-signed certificate will be generated instead."
        generate_self_signed_cert "$panel_host"
      fi
    else
      generate_self_signed_cert "$panel_host"
    fi
  else
    local detected_ip=""
    detected_ip=$(curl -fsSL --max-time 3 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}' || echo "127.0.0.1")
    ui_input panel_host "Panel IP/host" "IP or hostname for the local certificate:" "$detected_ip"
    generate_self_signed_cert "$panel_host"
  fi

  ui_input port "Panel port" "HTTPS panel port:" "$(( RANDOM % 55535 + 10000 ))"
  ui_input api_port "API port" "Panel API port:" "8000"
  ui_input username "Admin account" "Admin username:" "admin"
  while [[ -z "${password:-}" ]]; do
    ui_password password "Admin password" "Admin password:"
  done

  build_image "$region"
  local pwd_hash
  pwd_hash=$(python3 -c "import hashlib; print(hashlib.sha256(input().encode()).hexdigest())" <<< "$password")
  python3 - "$username" "$pwd_hash" "$port" "$api_port" "$panel_host" "$cert_auto_generated" "$CONFIG_DIR/p00rija_db.json" <<'PY'
import json, sys
username, pwd_hash, port, api_port, host, auto, path = sys.argv[1:8]
data = {
    "admin": {"username": username, "password_hash": pwd_hash},
    "settings": {
        "port": int(port), "api_port": int(api_port), "panel_host": host,
        "test_interval": 30, "max_idle_seconds": 300, "panel_tls": True,
        "cert_path": "/opt/p00rija/certs/cert.pem",
        "key_path": "/opt/p00rija/certs/key.pem",
        "cert_auto_generated": auto.lower() == "true",
    },
    "nodes": {}, "links": {}, "logs": []
}
json.dump(data, open(path, "w"), indent=4)
PY
  chmod 0600 "$CONFIG_DIR/p00rija_db.json"
  python3 - "$port" "$api_port" "$CONFIG_DIR/p00rija_config.json" <<'PY'
import json, sys
json.dump({"role": "panel", "port": int(sys.argv[1]), "api_port": int(sys.argv[2])}, open(sys.argv[3], "w"), indent=4)
PY
  chmod 0600 "$CONFIG_DIR/p00rija_config.json"
  echo "docker" > "$CONFIG_DIR/.run_mode"
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker run -d --name "$CONTAINER" --network bridge --restart always -p "$port:$port" -p "$api_port:$api_port" -v "$CONFIG_DIR:/opt/p00rija" "$IMAGE"
  verify_running_panel_code
  ui_msg "Panel installed" "P00RIJA Panel is running.\n\nOpen: https://${panel_host}:${port}\nAPI port: ${api_port}\nServer CLI: sudo p00rija panel status"
}

main "$@"
