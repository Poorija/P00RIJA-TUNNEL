# P00RIJA TUNNEL

![P00RIJA TUNNEL logo](assets/p00rija-logo.svg)

**Version:** 1.3.0  
**License:** GPL v3  
**Developer:** [Poorija](https://github.com/Poorija)  
**Email:** mohammadmahdi.farhadianfard@gmail.com

[فارسی](README_FA.md)

P00RIJA TUNNEL is a Docker-first, multi-node reverse tunneling control panel. It manages internal and external nodes, creates and monitors tunnel links, ships offline tunneling engines, and exposes live operational controls from one bilingual web panel.

Fresh databases still start with `admin` / `admin` only as an emergency default. The panel installer asks for a new admin password, and you should change default credentials immediately on any real server.

## Easy Install

Interactive installer:

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh
```

The main installer can install/update the panel, install/update a node, or run the panel step and then the node step. Panel and node installers still remain available as separate scripts.

Panel and node installers use an English `whiptail/dialog` terminal UI. At startup, the installer detects the server IP, checks whether it is local/private or public, looks up the public internet IP country, and uses that information to recommend Iran mirrors or official global repositories. If `whiptail` or `dialog` is missing, the installer installs one after the server location is selected and package mirrors are configured.

When these commands are run from GitHub and the local directory does not contain the full package, the installer automatically downloads the full repository archive into `/opt/p00rija-install` and continues from there. This keeps fonts, offline engines, Docker build files, and helper scripts available during installation.

Panel installer:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install-panel.sh)"
```

Node installer:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install-node.sh)"
```

Local source install:

```bash
git clone https://github.com/Poorija/P00RIJA-TUNNEL.git
cd P00RIJA-TUNNEL
sudo bash install.sh
```

If `/opt/p00rija/panel/p00rija_db.json` already exists, `install-panel.sh` offers an update mode that keeps the current database, certificates, nodes, tunnels, admin account, and settings, then rebuilds and restarts only the panel container with the new code.

After installation, the server command can update from GitHub or from a local `.zip` / `.tar.gz` package:

```bash
sudo p00rija update
sudo p00rija panel update
sudo p00rija node update
```

If a panel or node is already installed, the updater warns that existing data is kept and only code, bundled engines/fonts, Docker image, and the running container are refreshed unless you explicitly choose a fresh reinstall.

Offline package install:

```bash
tar -xzf p00rija-offline-bundle.tar.gz
cd P00RIJA-TUNNEL
sudo bash install-panel.sh
# or:
sudo bash install-node.sh
```

## Main Features

- Secure HTTPS panel with self-signed local/IP certificates, existing certificate import, or Let's Encrypt for domains.
- Docker bridge networking for the panel and host networking for real node servers by default; this keeps Docker out of per-port publishing and lets the Linux kernel own tunnel listeners directly. Docker bridge remains available as an isolated fallback with small/custom publish ranges.
- Iran/global server-location detection for Docker mirror selection.
- If Iran is selected, package-manager mirrors and Docker registry mirrors are switched before dependencies are installed.
- Automatic Docker installation, BBR optimization, and optional IPv6 disable controls.
- Node containers start with CPU, memory, PID, file-descriptor, and reverse-worker safeguards to avoid runaway load on small servers.
- Internal/external node management with signed node requests, API tokens, node tags, live ping in ms, and clear disconnected/stopped indicators.
- Live dashboard refresh that updates only charts, cards, node resources, traffic, threads, connections, and monitoring widgets.
- Tunnel management with Easy Mode, advanced mode, grouped tunnel categories, colored tags, pause/resume/edit controls, and per-category live charts.
- Smart tunnel test between two selected nodes with profile recommendations.
- Quick tunnel button for creating a low-load simple tunnel between two selected nodes.
- Built-in and external engine profiles for Builtin, GOST, Backhaul, Rathole, Chisel, FRP, Xray, Hysteria2, sing-box, TUIC, NaiveProxy, ShadowTLS, Brook, Mieru, and Mux/Quantum style profiles.
- Offline engine bundle support through `download_engines.py` and the `engines/` directory so panel and nodes can build containers without GitHub access.
- Encrypted SSH credential vault and SSH command runner for controlling selected nodes from the panel.
- Runtime monitoring for active tunnel sessions, system processes, threads, RSS memory, node resources, Docker status, and cleanup actions.
- Resource optimization tools for idle session cleanup, RAM/GC cleanup, and deeper runtime optimization.
- Appearance settings with Persian/English UI, Vazirmatn default font, multiple themes, and PWA support.
- Security settings for TOTP two-factor login and browser biometric quick unlock.

## Engines And Offline Bundle

To prepare an offline bundle:

```bash
python3 download_engines.py --bundle p00rija-offline-bundle.tar.gz
```

The bundle includes the application files, installer scripts, `engines/manifest.json`, downloaded engine binaries, and engine archives. The Docker image copies bundled engines into `/usr/local/bin` during build. Runtime images do not need to download engines from GitHub when the offline package is present.

The `fonts/` directory is also part of the offline package. Panel fonts, including Vazirmatn, are copied into the Docker image and do not depend on a CDN or public internet access.

## Panel And Node Flow

1. Install the panel and open the HTTPS URL shown by the installer.
2. Add internal and external nodes from the Nodes tab.
3. Copy each generated node token and optional private key into the node installer.
4. Create a tunnel from Tunnel Management using Easy Mode, a preset profile, smart test recommendation, or a fully custom profile.
5. Add port forwarding entries, then monitor live traffic, active sessions, resources, and logs.
6. Pause, resume, edit, or inspect engine config from the tunnel list.

## Management Command

```bash
sudo Pooriya-tunnel
```

Use the manager for start, stop, restart, logs, network optimization, and uninstall actions.

## Server Control CLI

Panel and node installers also install a host-level command that works without entering the container:

```bash
sudo p00rija status
sudo p00rija panel restart
sudo p00rija panel logs
sudo p00rija panel reset-admin
sudo p00rija node restart
sudo p00rija node logs
sudo p00rija uninstall
sudo p00rija purge
```

`uninstall` removes runtimes and images while keeping `/opt/p00rija` data.  
`purge` removes containers, images, configuration, certificates, bundled engines, and CLI files.

## Validation

Before publishing or installing from source, run:

```bash
python3 -m py_compile P00RIJA.py download_engines.py
bash -n install.sh install-panel.sh install-node.sh Pooriya-tunnel.sh
docker build --platform linux/amd64 -t p00rija-tunnel:1.3.0 .
```

## License

GPL v3. See [LICENSE](LICENSE).
