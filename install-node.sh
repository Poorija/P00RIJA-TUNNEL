#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="/opt/p00rija/node"
BIN="/usr/local/bin/Pooriya-tunnel"
CONTROL_BIN="/usr/local/bin/p00rija"
CONTAINER="p00rija-node"
VERSION="1.9.95"
IMAGE="p00rija-tunnel:${VERSION}"
P00RIJA_INTERNAL_PUBLISH_RANGES="${P00RIJA_DOCKER_PUBLISH_RANGES:-7000-7039:7000-7039,17000-17039:17000-17039}"
P00RIJA_EXTERNAL_PUBLISH_RANGES="${P00RIJA_DOCKER_PUBLISH_RANGES:-}"
P00RIJA_NODE_CPU_LIMIT="${P00RIJA_NODE_CPU_LIMIT:-0.90}"
P00RIJA_NODE_MEMORY_LIMIT="${P00RIJA_NODE_MEMORY_LIMIT:-1536m}"
P00RIJA_NODE_MEMORY_SWAP_LIMIT="${P00RIJA_NODE_MEMORY_SWAP_LIMIT:-2g}"
P00RIJA_NODE_PIDS_LIMIT="${P00RIJA_NODE_PIDS_LIMIT:-768}"
P00RIJA_NODE_NOFILE_LIMIT="${P00RIJA_NODE_NOFILE_LIMIT:-65535:65535}"
P00RIJA_MAX_REVERSE_WORKERS_PER_LINK="${P00RIJA_MAX_REVERSE_WORKERS_PER_LINK:-16}"
P00RIJA_MAX_POOL_SIZE_PER_LINK="${P00RIJA_MAX_POOL_SIZE_PER_LINK:-32}"
P00RIJA_MIN_READY_WORKERS_PER_LINK="${P00RIJA_MIN_READY_WORKERS_PER_LINK:-2}"
P00RIJA_DIRECT_BRIDGE_FALLBACK="${P00RIJA_DIRECT_BRIDGE_FALLBACK:-0}"
P00RIJA_SOCKET_BUFFER_BYTES="${P00RIJA_SOCKET_BUFFER_BYTES:-2097152}"
P00RIJA_COPY_BUFFER_BYTES="${P00RIJA_COPY_BUFFER_BYTES:-524288}"
P00RIJA_WEBSOCKET_MASK_CLIENT="${P00RIJA_WEBSOCKET_MASK_CLIENT:-0}"
P00RIJA_KEEP_BRIDGE_NETWORK="${P00RIJA_KEEP_BRIDGE_NETWORK:-0}"
P00RIJA_NODE_NETWORK_MODE="${P00RIJA_NODE_NETWORK_MODE:-}"

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
  else
    echo "[!] installer-ui.sh is missing and could not be downloaded from $HELPER_URL." >&2
    exit 1
  fi
fi

need_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "[!] Run as root: sudo bash install-node.sh" >&2
    exit 1
  fi
}

is_update_mode() {
  [[ "${1:-}" == "--update" || "${P00RIJA_INSTALL_MODE:-}" == "update" ]]
}

backup_existing_state() {
  [[ -d "$CONFIG_DIR" ]] || return 0
  local backup_dir="$CONFIG_DIR/backups/update-$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$backup_dir"
  for item in p00rija_config.json p00rija_db.json .run_mode .network_mode .publish_ranges; do
    [[ -e "$CONFIG_DIR/$item" ]] && cp -a "$CONFIG_DIR/$item" "$backup_dir/"
  done
  echo "[i] Existing node state backed up to $backup_dir"
}

node_config_value() {
  local key="$1" default="$2"
  python3 - "$CONFIG_DIR/p00rija_config.json" "$key" "$default" <<'PY'
import json, sys
path, key, default = sys.argv[1:4]
try:
    with open(path) as f:
        data = json.load(f)
    print(data.get(key) or default)
except Exception:
    print(default)
PY
}

normalize_panel_control_url() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import urlparse

raw = sys.argv[1].strip().rstrip("/")
parsed = urlparse(raw)
if parsed.scheme not in ("http", "https") or not parsed.hostname:
    raise SystemExit("Panel URL must include http:// or https:// and a valid host")
if parsed.username or parsed.password or parsed.query or parsed.fragment:
    raise SystemExit("Panel URL must not contain credentials, query, or fragment")
print(f"{parsed.scheme}://{parsed.netloc}")
PY
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
  local __var="$1" role="$2" choice custom default_ranges
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
  local __var="$1" choice
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
    apt-get install -y python3 curl ca-certificates jq openssl whiptail
  elif have yum; then
    yum install -y python3 curl ca-certificates jq openssl newt || dnf install -y python3 curl ca-certificates jq openssl newt
  elif have apk; then
    apk add python3 curl ca-certificates jq openssl newt
  fi
}

install_docker_pkg() {
  ui_info "Installing Docker from the selected package repositories..."
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    apt_update_with_retries
    apt-get install -y docker.io python3 curl ca-certificates jq openssl whiptail
  elif have yum; then
    yum install -y docker python3 curl ca-certificates jq openssl newt || dnf install -y docker python3 curl ca-certificates jq openssl newt
  elif have apk; then
    apk add docker python3 curl ca-certificates jq openssl newt
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
  rm -rf "$CONFIG_DIR/engines" "$CONFIG_DIR/fonts" "$CONFIG_DIR/p00rija_core"
  cp -r "$SCRIPT_DIR/engines" "$CONFIG_DIR/engines"
  cp -r "$SCRIPT_DIR/fonts" "$CONFIG_DIR/fonts"
  if [[ -d "$SCRIPT_DIR/p00rija_core" ]]; then
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

main() {
  need_root
  declare -F ui_banner >/dev/null 2>&1 && ui_banner "Internal / External Node Installer"
  local region role_choice role panel_url node_token node_private_key publish_ranges network_mode
  prepare_installer_ui region
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
  ui_input panel_url "Panel URL" "Panel URL, for example https://panel.example.com:8443:" ""
  panel_url="$(normalize_panel_control_url "$panel_url")"
  ui_input node_token "Node token" "Node API token from the panel:" ""
  ui_input node_private_key "Node private key" "Node private key from the panel, optional:" ""

  build_image "$region"
  python3 - "$role" "${panel_url%/}" "$node_token" "$node_private_key" "$CONFIG_DIR/p00rija_config.json" <<'PY'
import json, sys
json.dump({"role": sys.argv[1], "panel_url": sys.argv[2], "token": sys.argv[3], "private_key": sys.argv[4]}, open(sys.argv[5], "w"), indent=2)
PY
  chmod 0600 "$CONFIG_DIR/p00rija_config.json"
  echo "docker" > "$CONFIG_DIR/.run_mode"
  echo "$network_mode" > "$CONFIG_DIR/.network_mode"
  echo "$publish_ranges" > "$CONFIG_DIR/.publish_ranges"
  run_node_container "$role" "$network_mode" "$publish_ranges" "$panel_url"
  ui_msg "Node installed" "P00RIJA ${role} node is running and polling:\n${panel_url}\n\nNetwork mode: ${network_mode}\nPublished ranges: ${publish_ranges:-none}\nCPU limit: ${P00RIJA_NODE_CPU_LIMIT}\nMemory limit: ${P00RIJA_NODE_MEMORY_LIMIT}\nSwap limit: ${P00RIJA_NODE_MEMORY_SWAP_LIMIT}\nMax reverse workers/link: ${P00RIJA_MAX_REVERSE_WORKERS_PER_LINK}\nMax pool/link: ${P00RIJA_MAX_POOL_SIZE_PER_LINK}\n\nServer CLI: sudo p00rija node status"
}

run_node_container() {
  local role="$1" network_mode="$2" publish_ranges="$3" panel_url="${4:-}"
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  publish_args=()
  if [[ "$network_mode" == "bridge" ]]; then
    mapfile -t publish_args < <(docker_publish_args "$publish_ranges")
  fi
  tun_args=(--cap-add NET_ADMIN)
  if [[ -c /dev/net/tun ]]; then
    tun_args+=(--device /dev/net/tun)
  fi
  docker run -d --name "$CONTAINER" \
    --network "$network_mode" \
    --restart unless-stopped \
    "${tun_args[@]}" \
    --cpus "$P00RIJA_NODE_CPU_LIMIT" \
    --memory "$P00RIJA_NODE_MEMORY_LIMIT" \
    --memory-swap "$P00RIJA_NODE_MEMORY_SWAP_LIMIT" \
    --pids-limit "$P00RIJA_NODE_PIDS_LIMIT" \
    --ulimit "nofile=$P00RIJA_NODE_NOFILE_LIMIT" \
    -e "P00RIJA_MAX_REVERSE_WORKERS_PER_LINK=$P00RIJA_MAX_REVERSE_WORKERS_PER_LINK" \
    -e "P00RIJA_MAX_POOL_SIZE_PER_LINK=$P00RIJA_MAX_POOL_SIZE_PER_LINK" \
    -e "P00RIJA_MIN_READY_WORKERS_PER_LINK=$P00RIJA_MIN_READY_WORKERS_PER_LINK" \
    -e "P00RIJA_DIRECT_BRIDGE_FALLBACK=$P00RIJA_DIRECT_BRIDGE_FALLBACK" \
    -e "P00RIJA_SOCKET_BUFFER_BYTES=$P00RIJA_SOCKET_BUFFER_BYTES" \
    -e "P00RIJA_COPY_BUFFER_BYTES=$P00RIJA_COPY_BUFFER_BYTES" \
    -e "P00RIJA_WEBSOCKET_MASK_CLIENT=$P00RIJA_WEBSOCKET_MASK_CLIENT" \
    --add-host "host.docker.internal:host-gateway" \
    "${publish_args[@]}" \
    -v "$CONFIG_DIR:/opt/p00rija" \
    "$IMAGE"
}

update_existing_node() {
  [[ -f "$CONFIG_DIR/p00rija_config.json" ]] || {
    echo "[!] Existing node config was not found at $CONFIG_DIR/p00rija_config.json" >&2
    echo "[!] Run a fresh node install first, or remove --update." >&2
    exit 1
  }
  local region role network_mode publish_ranges panel_url
  region=$(detect_server_region)
  export P00RIJA_SERVER_REGION="$region"
  declare -F configure_package_mirrors >/dev/null 2>&1 && configure_package_mirrors "$region"
  install_base_deps
  ensure_docker "$region"
  configure_docker_node_runtime
  enable_bbr
  backup_existing_state
  build_image "$region"
  role=$(node_config_value role internal)
  panel_url=$(node_config_value panel_url "")
  network_mode="$(cat "$CONFIG_DIR/.network_mode" 2>/dev/null || echo "${P00RIJA_NODE_NETWORK_MODE:-host}")"
  [[ "$network_mode" =~ ^(host|bridge)$ ]] || network_mode="host"
  publish_ranges="$(cat "$CONFIG_DIR/.publish_ranges" 2>/dev/null || true)"
  if [[ "$network_mode" == "bridge" && "$P00RIJA_KEEP_BRIDGE_NETWORK" != "1" ]]; then
    echo "[i] Migrating node from Docker bridge to host network for reliable VPN entry/target ports."
    network_mode="host"
    publish_ranges=""
  fi
  if [[ "$network_mode" == "bridge" && -z "$publish_ranges" && "$role" == "internal" ]]; then
    publish_ranges="$P00RIJA_INTERNAL_PUBLISH_RANGES"
  fi
  echo "docker" > "$CONFIG_DIR/.run_mode"
  echo "$network_mode" > "$CONFIG_DIR/.network_mode"
  echo "$publish_ranges" > "$CONFIG_DIR/.publish_ranges"
  run_node_container "$role" "$network_mode" "$publish_ranges" "$panel_url"
  echo "[+] Node updated to ${IMAGE#*:}. Existing token, private key, DB, and runtime config were kept."
}

if is_update_mode "${1:-}"; then
  need_root
  declare -F ui_banner >/dev/null 2>&1 && ui_banner "Node Updater"
  update_existing_node
else
  main "$@"
fi
