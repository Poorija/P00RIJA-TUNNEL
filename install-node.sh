#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="/opt/p00rija/node"
BIN="/usr/local/bin/Pooriya-tunnel"
CONTROL_BIN="/usr/local/bin/p00rija"
CONTAINER="p00rija-node"
IMAGE="p00rija-tunnel:1.3.0"
P00RIJA_INTERNAL_PUBLISH_RANGES="${P00RIJA_DOCKER_PUBLISH_RANGES:-7000-7039:7000-7039,17000-17039:17000-17039}"
P00RIJA_EXTERNAL_PUBLISH_RANGES="${P00RIJA_DOCKER_PUBLISH_RANGES:-}"
P00RIJA_NODE_CPU_LIMIT="${P00RIJA_NODE_CPU_LIMIT:-0.90}"
P00RIJA_NODE_MEMORY_LIMIT="${P00RIJA_NODE_MEMORY_LIMIT:-1536m}"
P00RIJA_NODE_MEMORY_SWAP_LIMIT="${P00RIJA_NODE_MEMORY_SWAP_LIMIT:-2g}"
P00RIJA_NODE_PIDS_LIMIT="${P00RIJA_NODE_PIDS_LIMIT:-768}"
P00RIJA_NODE_NOFILE_LIMIT="${P00RIJA_NODE_NOFILE_LIMIT:-65535:65535}"
P00RIJA_MAX_REVERSE_WORKERS_PER_LINK="${P00RIJA_MAX_REVERSE_WORKERS_PER_LINK:-4}"
P00RIJA_MAX_POOL_SIZE_PER_LINK="${P00RIJA_MAX_POOL_SIZE_PER_LINK:-64}"
P00RIJA_NODE_NETWORK_MODE="${P00RIJA_NODE_NETWORK_MODE:-}"

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
    echo "[!] Installer package is missing. Run as root so it can download the full package: sudo bash install-node.sh" >&2
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
    echo "[!] Run as root: sudo bash install-node.sh" >&2
    exit 1
  fi
}

docker_publish_args() {
  local ranges="$1" range proto
  local args=()
  IFS=',' read -ra parts <<< "$ranges"
  for range in "${parts[@]}"; do
    range="${range//[[:space:]]/}"
    [[ -z "$range" ]] && continue
    proto="${range##*/}"
    if [[ "$range" == */* && ! "$proto" =~ ^(tcp|udp)$ ]]; then
      ui_warn "Skipping invalid publish rule '${range}'. Protocol must be tcp or udp."
      continue
    fi
    args+=("-p" "$range")
  done
  printf '%s\n' "${args[@]}"
}

choose_publish_ranges() {
  local __var="$1" role="$2" choice="" custom="" default_ranges=""
  if [[ "$role" == "internal" ]]; then
    default_ranges="$P00RIJA_INTERNAL_PUBLISH_RANGES"
    ui_menu choice "Node port publishing" "Choose how Docker bridge ports should be published. The safe default publishes only a small initial range and avoids high startup load." "1" \
      "1:Safe small range ${default_ranges:-none}" \
      "2:No published ports" \
      "3:Custom comma-separated ranges"
    case "$choice" in
      1) printf -v "$__var" '%s' "$default_ranges" ;;
      2) printf -v "$__var" '%s' "" ;;
      3)
        ui_input custom "Custom port ranges" "Example: 7000-7039:7000-7039,17000-17039:17000-17039" "$default_ranges"
        printf -v "$__var" '%s' "$custom"
        ;;
    esac
  else
    default_ranges="$P00RIJA_EXTERNAL_PUBLISH_RANGES"
    ui_menu choice "Node port publishing" "External nodes normally create outbound reverse connections and do not need inbound Docker-published ports." "1" \
      "1:No published ports" \
      "2:Custom comma-separated ranges"
    if [[ "$choice" == "2" ]]; then
      ui_input custom "Custom port ranges" "Example: 7000-7039:7000-7039" "$default_ranges"
      printf -v "$__var" '%s' "$custom"
    else
      printf -v "$__var" '%s' ""
    fi
  fi
}

choose_network_mode() {
  local __var="$1" choice=""
  if [[ "$P00RIJA_NODE_NETWORK_MODE" =~ ^(host|bridge)$ ]]; then
    printf -v "$__var" '%s' "$P00RIJA_NODE_NETWORK_MODE"
    return 0
  fi
  ui_menu choice "Node network mode" "Choose how this node should attach to the server network. Host mode is recommended for real servers because Docker will not publish/manage every tunnel port." "1" \
    "1:Host network - recommended for production" \
    "2:Docker bridge - isolated fallback"
  [[ "$choice" == "2" ]] && printf -v "$__var" '%s' "bridge" || printf -v "$__var" '%s' "host"
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

configure_docker_node_runtime() {
  ui_info "Applying Docker node runtime safeguards..."
  mkdir -p /etc/docker
  python3 - <<'PY'
import json, os
path = "/etc/docker/daemon.json"
data = {}
if os.path.exists(path) and os.path.getsize(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        data = {}
data["userland-proxy"] = False
data.setdefault("live-restore", True)
tmp = f"{path}.tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
os.replace(tmp, path)
PY
  systemctl restart docker >/dev/null 2>&1 || true
}

enable_bbr() {
  ui_info "Applying TCP/BBR network tuning..."
  if have sysctl; then
    grep -q "net.core.default_qdisc=fq" /etc/sysctl.conf || echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
    grep -q "net.ipv4.tcp_congestion_control=bbr" /etc/sysctl.conf || echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
    sysctl -p >/dev/null 2>&1 || true
  fi
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

load_existing_node_settings() {
  local network_mode="host" publish_ranges=""
  [[ -f "$CONFIG_DIR/.network_mode" ]] && network_mode="$(tr -d '\r\n' < "$CONFIG_DIR/.network_mode")"
  [[ "$network_mode" =~ ^(host|bridge)$ ]] || network_mode="host"
  [[ -f "$CONFIG_DIR/.publish_ranges" ]] && publish_ranges="$(cat "$CONFIG_DIR/.publish_ranges")"
  printf 'network_mode=%q\n' "$network_mode"
  printf 'publish_ranges=%q\n' "$publish_ranges"
}

run_node_container() {
  local network_mode="$1" publish_ranges="$2"
  publish_args=()
  if [[ "$network_mode" == "bridge" ]]; then
    mapfile -t publish_args < <(docker_publish_args "$publish_ranges")
  fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker run -d --name "$CONTAINER" \
    --network "$network_mode" \
    --restart unless-stopped \
    --cpus "$P00RIJA_NODE_CPU_LIMIT" \
    --memory "$P00RIJA_NODE_MEMORY_LIMIT" \
    --memory-swap "$P00RIJA_NODE_MEMORY_SWAP_LIMIT" \
    --pids-limit "$P00RIJA_NODE_PIDS_LIMIT" \
    --ulimit "nofile=$P00RIJA_NODE_NOFILE_LIMIT" \
    -e "P00RIJA_MAX_REVERSE_WORKERS_PER_LINK=$P00RIJA_MAX_REVERSE_WORKERS_PER_LINK" \
    -e "P00RIJA_MAX_POOL_SIZE_PER_LINK=$P00RIJA_MAX_POOL_SIZE_PER_LINK" \
    "${publish_args[@]}" \
    -v "$CONFIG_DIR:/opt/p00rija" \
    "$IMAGE"
}

verify_running_node_code() {
  ui_info "Verifying running node code inside Docker..."
  if ! docker exec "$CONTAINER" grep -q "payload_test_client" /app/P00RIJA.py 2>/dev/null; then
    ui_msg "Node update verification failed" "The running node container does not include the payload test client command. Re-run the update from the latest offline package."
    return 1
  fi
  if ! docker exec "$CONTAINER" grep -q "Direct bridge fallback" /app/P00RIJA.py 2>/dev/null; then
    ui_msg "Node update verification failed" "The running node container does not include the direct bridge fallback build. Re-run the update from the latest offline package."
    return 1
  fi
}

update_existing_node() {
  local region="$1" network_mode="" publish_ranges=""
  ui_info "Updating existing node while keeping panel URL, token, private key, role, and network settings..."
  build_image "$region"
  eval "$(load_existing_node_settings)"
  chmod 0600 "$CONFIG_DIR/p00rija_config.json" 2>/dev/null || true
  echo "docker" > "$CONFIG_DIR/.run_mode"
  echo "$network_mode" > "$CONFIG_DIR/.network_mode"
  echo "$publish_ranges" > "$CONFIG_DIR/.publish_ranges"
  run_node_container "$network_mode" "$publish_ranges"
  verify_running_node_code
  ui_msg "Node updated" "P00RIJA node was updated without resetting configuration.\n\nNetwork mode: ${network_mode}\nPublished ranges: ${publish_ranges:-none}\nServer CLI: sudo p00rija node status"
}

main() {
  need_root
  local region="" role_choice="" role="" panel_url="" node_token="" node_private_key="" publish_ranges="" network_mode="" install_mode=""
  prepare_installer_ui region
  if [[ -f "$CONFIG_DIR/p00rija_config.json" ]]; then
    ui_menu install_mode "Existing node detected" "A P00RIJA node is already installed. Update mode does not delete node configuration; it only refreshes node code, fonts, engines, Docker image, and the running container." "1" \
      "1:Update current node - keep config and keys" \
      "2:Fresh reinstall - reset node config"
    if [[ "$install_mode" == "1" ]]; then
      install_base_deps
      ensure_docker "$region"
      configure_docker_node_runtime
      enable_bbr
      update_existing_node "$region"
      return 0
    fi
  fi
  install_base_deps
  ensure_docker "$region"
  configure_docker_node_runtime
  enable_bbr

  ui_menu role_choice "Node type" "Choose the role of this server." "1" \
    "1:Internal node" \
    "2:External node"
  [[ "$role_choice" == "1" ]] && role="internal" || role="external"
  choose_network_mode network_mode
  if [[ "$network_mode" == "bridge" ]]; then
    choose_publish_ranges publish_ranges "$role"
  else
    publish_ranges=""
  fi
  while [[ -z "$panel_url" ]]; do
    ui_input panel_url "Panel URL" "Panel URL, for example https://panel.example.com:8443:" ""
  done
  while [[ -z "$node_token" ]]; do
    ui_input node_token "Node token" "Node API token from the panel:" ""
  done
  if [[ "$node_token" =~ ^[0-9a-fA-F]{16}$ ]]; then
    node_token="tok_${node_token,,}"
  fi
  while [[ -z "$node_private_key" ]]; do
    ui_input node_private_key "Node private key" "Node private key shown with the token in the panel:" ""
  done

  build_image "$region"
  python3 - "$role" "${panel_url%/}" "$node_token" "$node_private_key" "$CONFIG_DIR/p00rija_config.json" <<'PY'
import json, sys
json.dump({"role": sys.argv[1], "panel_url": sys.argv[2], "token": sys.argv[3], "private_key": sys.argv[4]}, open(sys.argv[5], "w"), indent=2)
PY
  chmod 0600 "$CONFIG_DIR/p00rija_config.json"
  echo "docker" > "$CONFIG_DIR/.run_mode"
  echo "$network_mode" > "$CONFIG_DIR/.network_mode"
  echo "$publish_ranges" > "$CONFIG_DIR/.publish_ranges"
  run_node_container "$network_mode" "$publish_ranges"
  verify_running_node_code
  ui_msg "Node installed" "P00RIJA ${role} node is running and polling:\n${panel_url}\n\nNetwork mode: ${network_mode}\nPublished ranges: ${publish_ranges:-none}\nCPU limit: ${P00RIJA_NODE_CPU_LIMIT}\nMemory limit: ${P00RIJA_NODE_MEMORY_LIMIT}\nSwap limit: ${P00RIJA_NODE_MEMORY_SWAP_LIMIT}\nMax reverse workers/link: ${P00RIJA_MAX_REVERSE_WORKERS_PER_LINK}\nMax pool/link: ${P00RIJA_MAX_POOL_SIZE_PER_LINK}\n\nServer CLI: sudo p00rija node status"
}

main "$@"
