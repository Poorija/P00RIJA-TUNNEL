# P00RIJA TUNNEL

![P00RIJA TUNNEL logo](assets/p00rija-logo.svg)

**Version:** 1.9.95  
**License:** GPL v3  
**Developer:** [Poorija](https://github.com/Poorija)  
**Email:** mohammadmahdi.farhadianfard@gmail.com

[فارسی](README_FA.md)

P00RIJA TUNNEL is a Docker-first, multi-node reverse tunneling control panel. It manages internal and external nodes, creates and monitors tunnel links, ships bundled tunneling engines, and exposes live operational controls from one bilingual web panel.

Fresh databases still start with `admin` / `admin` only as an emergency default. The panel installer asks for a new admin password, and you should change default credentials immediately on any real server.

The panel is designed for real operational use: certificate management, node enrollment, SSH control, tunnel creation, speed testing, engine management, backup/restore, host migration, monitoring, data-plane tuning, and mobile-friendly administration are all available from the web UI.

Transport and profile tooling covers classic reverse TCP, WebSocket/TLS, HTTP/2, HTTP/3/QUIC, REALITY, XHTTP, ShadowTLS, AnyTLS, MASQUE CONNECT-UDP, AmneziaWG/WireGuard-style paths, shared multiplexing, adaptive bonding, and hybrid mux/bonding modes. Availability depends on the installed engine binaries and the selected node capabilities.

## Easy Install

Interactive installer:

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh
```

This is the recommended command. If only `install.sh` is present, it downloads the complete `main` branch archive from `https://github.com/Poorija/P00RIJA-TUNNEL` into `/opt/p00rija-install` before continuing, so the graphical helper, Docker files, fonts, bundled engine binaries, and panel/node installers remain available. The raw URL and repository archive were verified on June 24, 2026.

Panel installer:

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh --panel
```

Node installer:

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh --node
```

Local source install:

```bash
git clone https://github.com/Poorija/P00RIJA-TUNNEL.git
cd P00RIJA-TUNNEL
sudo bash install.sh
```

Offline package install:

```bash
tar -xzf p00rija-offline-bundle.tar.gz
cd P00RIJA-TUNNEL
sudo bash install-panel.sh
# or:
sudo bash install-node.sh
```

## Panel Capabilities

### Installation, host control, and deployment

- Unified graphical terminal installer for panel, node, or combined installation, with whiptail menus, text fallback, Iran/global mirror selection, Docker installation, BBR tuning, and automatic full-package bootstrap from GitHub.
- Docker-first deployment for both panel and nodes, with bundled fonts, assets, core modules, and engine binaries copied into the runtime image.
- Host-side control agent for safe panel/API port remapping, certificate operations, and creating the panel server as a real internal node without exposing the Docker socket inside the web container.
- Iran/global server-location handling. Iran mode uses IranServer APT mirrors and Docker pull mirrors where applicable.
- Management CLI through `sudo Pooriya-tunnel` for start, stop, restart, logs, update, network optimization, and uninstall workflows.

### Security, access, and certificates

- HTTPS panel with local/IP certificates, imported certificates, Let's Encrypt HTTP-01, and DNS-01-capable certificate workflows for domains and wildcard use cases.
- Optional randomized management path guarded by a signed HttpOnly cookie. Ordinary panel/login paths can return 404 while node-control APIs remain stable.
- Admin login protection with TOTP two-factor authentication and browser biometric quick unlock.
- Signed node requests, enrollment tokens, optional node private keys, and a local encrypted SSH credential vault.
- Certificate, key, token, SSH vault, and node identity data can be included in encrypted backups and restored on another host.

### Node management

- Internal, external, and panel-as-node management from one Servers tab.
- Live node status, ping, traffic, CPU/RAM pressure, Docker/runtime status, resource snapshots, tags, role labels, and connection indicators.
- Node SSH connection manager with saved encrypted credentials, command execution, and interactive control from the panel.
- Node update and compatibility checks for current, outdated, build-mismatched, ahead, and incompatible nodes.
- Live node ordering and tag display with persistent ordering and touch-friendly controls.

### Tunnel and port-forward management

- Easy Mode and Advanced Mode tunnel creation.
- Two tunnel directions: External to Internal and Internal to External.
- Backend-verified Bridge/Sync port allocation, with optional manual port override that still rejects collisions on selected nodes.
- Tunnel categories, per-category ordering, per-tunnel ordering, colored speed/security/stability tags, pause/resume/edit/delete actions, live status, and engine config preview.
- Port-forward entry management per tunnel with listener/target ports, status, install-package action, and traffic visibility.
- Quick tunnel creation for low-load simple tunnels between selected nodes.

### Transport profiles and engine coverage

- Built-in reverse tunnel engine plus external engines and profiles for Reverse TCP, AmneziaWG v2, WireGuard-style paths, GOST, Backhaul, Rathole, Chisel, FRP, Xray, Hysteria2, sing-box, TUIC, NaiveProxy, ShadowTLS, Brook, Mieru, MASQUE, and Mux/Quantum-style profiles.
- Profile catalog with speed, security, and stability scoring.
- Support for modern profile families such as REALITY gRPC/HTTP2, XHTTP + REALITY, AnyTLS, ShadowTLS, HTTP/2 TLS, HTTP/3/QUIC, MASQUE CONNECT-UDP, MASQUE QUIC-aware proxy, TUIC UDP-over-stream, TURN-like TLS relay, and ECH-capable configurations where DNS/client/provider support exists.
- Engine Manager for binary discovery, health checks, executable permission repair, version checks, archive/manual install, process stop/restart, and engine update checks.
- Bundled `engines/` directory plus `download_engines.py` for refreshing or rebuilding engine assets.

### Smart testing and speed testing

- Smart Benchmark between selected nodes using liveness, ping/loss, TCP reachability probes, CPU/RAM/thread pressure, installed engine compatibility, metadata scoring, and selectable balanced/speed/stability/security objectives.
- Graphical iperf3 Speed Test Center for selected node pairs, selected-node mesh testing, and node-to-Internet iperf3 testing against an operator-provided host.
- iperf3 preflight/install checks on participating nodes, JSON result display, upload/download Mbps, jitter, loss, retransmits, CPU usage, errors, and temporary server cleanup.
- Profile recommendation output for best balanced, fastest, most stable, and security-oriented choices.

### Data-plane architecture and performance controls

- Per-tunnel data-plane selection: Per-user Classic, Adaptive Bonding, Shared Mux Pool, or Smart Hybrid Mux + Bonding.
- Adaptive Bonding for compatible built-in links with 2–16 lanes, ordered frames, CRC32 validation, per-lane queues, and automatic lane budgeting under concurrent-user pressure.
- Shared Mux Pool with persistent carriers, stream placement, keepalive, recovery behavior, and lower connection-count pressure for many-user scenarios.
- Smart Hybrid mode combining shared mux carriers for normal users with adaptive bonding for heavy/idle flows.
- Optional TCP Brutal detection and opt-in use for suitable packet-loss scenarios when the required host/kernel capability is available.

### Backup, restore, and migration

- AES-256 encrypted panel backups containing panel state, settings, nodes, tunnels, tokens, certificates, SSH vault data, application files, and optional offline engines.
- Backup download from the panel.
- In-panel restore by direct upload from the administrator's computer or by selecting an encrypted backup already stored on the server.
- Restore validation, rollback snapshot creation, state/application restore, and controlled panel restart.
- Direct migration to a new SSH host with destination host credentials, staged restore, new panel endpoint verification, node endpoint update, and old-panel fallback behavior.

### Monitoring, logs, and optimization

- Live dashboard for charts, cards, node resources, traffic, threads, active sessions, Docker status, and monitoring widgets.
- Runtime session monitoring for active tunnel sessions, process/session/resource data, and node-side runtime state.
- System logs, bounded log storage, CSV export, and operational event history.
- Link Guardian for ready-worker tuning, dead/excess reserve socket cleanup, active-session preservation, health-scan rate limiting, and duplicate command suppression.
- Resource optimizers for idle session cleanup, RAM/GC cleanup, thread pressure handling, and conservative pressure-based idle retention.

### UI, localization, and mobile layout

- Persian and English UI with Vazirmatn default font, multiple themes, PWA support, and browser-side translation auditing.
- Responsive mobile/tablet layouts where node and port tables become readable cards, wide operational tables remain touch-scrollable, charts resize to their containers, and modal forms become safe-area-aware bottom sheets.
- Direction-aware ordering controls for nodes, tunnel categories, and tunnels with distinct up/down icons and live persisted reordering.

## Engines And Offline Bundle

To prepare an offline bundle:

```bash
python3 download_engines.py --bundle p00rija-offline-bundle.tar.gz
```

The bundle includes the application files, modular core, installer scripts, README files, offline fonts, assets, `engines/manifest.json`, downloaded engine binaries, and engine archives. The Docker image copies bundled engines into `/usr/local/bin` and fonts into `/app/fonts` during build. Runtime images do not need to download engines from GitHub when the offline package is present.

Reverse TCP uses the built-in P00RIJA worker pool for direct reverse port forwarding. AmneziaWG v2 is bundled with `amneziawg-go`, `awg`, and `awg-quick`; panel and node containers are prepared with NET_ADMIN/TUN support so AmneziaWG configs can run on Linux hosts.

The Engine Manager health test checks every expected binary, fixes executable permissions when needed, runs lightweight version probes on Linux, and reports architecture mismatches clearly during local development. Stop/restart terminates matching runtime processes and leaves tunnel configs ready to relaunch the engine.

## Panel And Node Flow

1. Install the panel and open the HTTPS URL shown by the installer.
2. Add internal and external nodes from the Nodes tab.
3. Copy each generated node token and optional private key into the node installer.
4. Create a tunnel from Tunnel Management using Easy Mode, a preset profile, smart test recommendation, or a fully custom profile.
5. Add port forwarding entries, then monitor live traffic, active sessions, resources, and logs.
6. Pause, resume, edit, or inspect engine config from the tunnel list.

### Tunnel Directions

`External -> Internal` is the default reverse-tunnel path: the internal node listens on Bridge/Sync ports and the external node dials into it. Use it when the internal node has reachable ports or direct routing between both sides.

```text
External Node (client/dialer)  ====>  Internal Node (server/listener)
```

`Internal -> External` reverses the initiation side: the external node listens and the internal node dials outward. Use it when the internal node is behind NAT/firewall but can make outbound connections to the external VPS.

```text
Internal Node (client/dialer)  ====>  External Node (server/listener)
```

Tunnel profiles are also shown as a decision catalog. Green means strong, yellow means normal, and red means weak for Speed, Security, and Stability.

Preset families include MASQUE/CONNECT-UDP over HTTP/3, MASQUE QUIC-aware proxy, sing-box XHTTP REALITY, TUIC UDP-over-stream, and TURN-like TLS relay profiles. These profiles require the matching core/binary on the node, and the panel can validate, score, export, and apply them like other profiles.

For current deployments, test Hysteria2 on clean UDP paths and AnyTLS or XHTTP/REALITY where ordinary TLS/HTTP camouflage is more reliable. For the built-in data plane, Smart Hybrid is the recommended mixed-workload default: concurrent ordinary users share 2–4 persistent Mux carriers, while an idle/heavy flow can use Adaptive Bonding. Choose pure Shared Mux when connection count and many-user stability matter most, pure Adaptive Bonding where per-flow shaping limits a single transfer, and Per-user Classic for compatibility or diagnosis. Bonding does not create new physical bandwidth; it only aggregates lanes when the route or provider limits individual flows.

## Management Command

```bash
sudo Pooriya-tunnel
```

Use the manager for start, stop, restart, logs, network optimization, and uninstall actions.

To restore a downloaded encrypted backup on a clean server:

```bash
sudo bash restore-panel-backup.sh /path/to/p00rija-panel-backup-....tar.gz.enc https://new-panel.example.com:8000
```

## Validation

Before publishing or installing from source, run:

```bash
python3 -m py_compile P00RIJA.py download_engines.py p00rija_core/*.py
bash -n install.sh install-panel.sh install-node.sh Pooriya-tunnel.sh
docker build --platform linux/amd64 -t p00rija-tunnel:1.9.95 .
```

For a complete GitHub release, publish the generated `P00RIJA-TUNNEL-GitHub-v1.9.95-*.tar.gz` archive with bundled engine binaries. It excludes local caches, debug helpers, old release archives, and runtime state, while keeping `engines/` ready so users who download the repository/package receive a complete installable tree. Operators can still refresh engine binaries later with `python3 download_engines.py`.

## License

GPL v3. See [LICENSE](LICENSE).
