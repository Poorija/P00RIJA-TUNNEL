#!/usr/bin/env python3
"""Privileged host-side controller for panel ports, ACME, and local panel node."""

from __future__ import annotations

import fcntl
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse


PANEL_DIR = os.environ.get("P00RIJA_PANEL_DIR", "/opt/p00rija/panel")
CONTROL_DIR = os.path.join(PANEL_DIR, "host_control")
REQUEST_DIR = os.path.join(CONTROL_DIR, "requests")
RESULT_DIR = os.path.join(CONTROL_DIR, "results")
HEARTBEAT = os.path.join(CONTROL_DIR, "agent-heartbeat.json")
PANEL_CONTAINER = "p00rija-panel"
PANEL_NODE_CONTAINER = "p00rija-panel-node"
DOMAIN_RE = re.compile(r"(?=^.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}$")
DNS_PROVIDER_PLUGINS = {
    "cloudflare": ("certbot-dns-cloudflare", "dns-cloudflare", "--dns-cloudflare-credentials"),
    "digitalocean": ("certbot-dns-digitalocean", "dns-digitalocean", "--dns-digitalocean-credentials"),
    "rfc2136": ("certbot-dns-rfc2136", "dns-rfc2136", "--dns-rfc2136-credentials"),
    "route53": ("python3-certbot-dns-route53", "dns-route53", ""),
}


def atomic_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    temp = path + ".tmp"
    Path(temp).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def run(command: list[str], *, timeout: int = 600, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=check)


def panel_paths() -> tuple[str, str]:
    return os.path.join(PANEL_DIR, "p00rija_config.json"), os.path.join(PANEL_DIR, "p00rija_db.json")


def load_panel_state() -> tuple[dict, dict]:
    config_path, db_path = panel_paths()
    return json.loads(Path(config_path).read_text()), json.loads(Path(db_path).read_text())


def save_panel_state(config: dict, db: dict) -> None:
    config_path, db_path = panel_paths()
    atomic_json(config_path, config)
    atomic_json(db_path, db)


def current_image() -> str:
    try:
        return run(["docker", "inspect", "-f", "{{.Config.Image}}", PANEL_CONTAINER], timeout=20).stdout.strip()
    except Exception:
        return "p00rija-tunnel:1.9.95"


def port_is_available(port: int, current_ports: set[int]) -> bool:
    if port in current_ports:
        return True
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def recreate_panel(web_port: int, api_port: int) -> None:
    image = current_image()
    run(["docker", "rm", "-f", PANEL_CONTAINER], timeout=60, check=False)
    command = [
        "docker", "run", "-d", "--name", PANEL_CONTAINER,
        "--network", "bridge", "--restart", "unless-stopped",
        "--cap-add", "NET_ADMIN",
        "-p", f"{web_port}:{web_port}",
    ]
    if api_port != web_port:
        command += ["-p", f"{api_port}:{api_port}"]
    if os.path.exists("/dev/net/tun"):
        command += ["--device", "/dev/net/tun"]
    command += ["-v", f"{PANEL_DIR}:/opt/p00rija", image]
    run(command, timeout=120)


def install_certbot() -> None:
    if shutil.which("certbot"):
        return
    if shutil.which("apt-get"):
        run(["apt-get", "update", "-y"], timeout=600)
        run(["apt-get", "install", "-y", "certbot"], timeout=600)
    elif shutil.which("dnf"):
        run(["dnf", "install", "-y", "certbot"], timeout=600)
    elif shutil.which("yum"):
        run(["yum", "install", "-y", "certbot"], timeout=600)
    elif shutil.which("apk"):
        run(["apk", "add", "certbot"], timeout=600)
    else:
        raise RuntimeError("No supported package manager was found to install Certbot")


def install_dns_plugin(provider: str) -> tuple[str, str]:
    package, authenticator, credential_flag = DNS_PROVIDER_PLUGINS[provider]
    if shutil.which("apt-get"):
        run(["apt-get", "update", "-y"], timeout=600)
        result = run(["apt-get", "install", "-y", package], timeout=600, check=False)
    elif shutil.which("dnf"):
        result = run(["dnf", "install", "-y", package], timeout=600, check=False)
    elif shutil.which("yum"):
        result = run(["yum", "install", "-y", package], timeout=600, check=False)
    elif shutil.which("apk"):
        result = run(["apk", "add", package], timeout=600, check=False)
    else:
        raise RuntimeError("No supported package manager was found for the Certbot DNS plugin")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or f"Could not install {package}")[-4000:])
    return authenticator, credential_flag


def public_ipv4() -> str:
    try:
        value = run(["curl", "-4fsS", "--max-time", "10", "https://api.ipify.org"], timeout=15).stdout.strip()
        ipaddress.ip_address(value)
        return value
    except Exception:
        return ""


def issue_certificate(payload: dict) -> dict:
    domain = str(payload.get("domain") or "").strip().lower().rstrip(".")
    email = str(payload.get("email") or "").strip()
    challenge = str(payload.get("challenge") or "http-01").strip().lower()
    wildcard = bool(payload.get("wildcard", False)) or domain.startswith("*.")
    base_domain = domain[2:] if domain.startswith("*.") else domain
    if not DOMAIN_RE.fullmatch(base_domain):
        raise ValueError("A valid public domain name is required")
    if not EMAIL_RE.fullmatch(email):
        raise ValueError("A valid Let's Encrypt account email is required")
    config, db = load_panel_state()
    install_certbot()
    domains = [base_domain]
    if wildcard or domain.startswith("*."):
        domains.append(f"*.{base_domain}")
        challenge = "dns-01"
    if challenge == "dns-01":
        provider = str(payload.get("dns_provider") or "").strip().lower()
        if provider not in DNS_PROVIDER_PLUGINS:
            raise ValueError("A supported DNS provider is required for DNS-01")
        authenticator, credential_flag = install_dns_plugin(provider)
        command = [
            "certbot", "certonly", f"--{authenticator}",
            "--preferred-challenges", "dns",
            "--email", email, "--agree-tos", "--non-interactive",
            "--keep-until-expiring",
        ]
        credentials = str(payload.get("dns_credentials") or "").strip()
        if credential_flag:
            if not credentials or len(credentials) > 12000:
                raise ValueError("DNS API credentials are required")
            credentials_dir = os.path.join(PANEL_DIR, "acme_credentials")
            os.makedirs(credentials_dir, mode=0o700, exist_ok=True)
            credentials_path = os.path.join(credentials_dir, f"{provider}.ini")
            Path(credentials_path).write_text(credentials + "\n", encoding="utf-8")
            os.chmod(credentials_path, 0o600)
            command += [credential_flag, credentials_path]
        propagation = max(10, min(600, int(payload.get("dns_propagation_seconds") or 30)))
        propagation_flag = f"--dns-{provider}-propagation-seconds"
        if provider != "route53":
            command += [propagation_flag, str(propagation)]
    elif challenge == "http-01":
        resolved = sorted({item[4][0] for item in socket.getaddrinfo(base_domain, 80, socket.AF_INET, socket.SOCK_STREAM)})
        public_ip = public_ipv4()
        if public_ip and public_ip not in resolved:
            raise ValueError(f"Domain DNS resolves to {', '.join(resolved) or 'nothing'}, not this server {public_ip}")
        current_ports = {int(config.get("port", 8080)), int(config.get("api_port", 8000))}
        if not port_is_available(80, current_ports):
            owner = run(["sh", "-c", "ss -lntp '( sport = :80 )' 2>/dev/null || true"], check=False).stdout.strip()
            raise RuntimeError(f"TCP port 80 is occupied. HTTP-01 requires public port 80. {owner}")
        command = [
            "certbot", "certonly", "--standalone", "--preferred-challenges", "http",
            "--http-01-port", "80", "--email", email,
            "--agree-tos", "--non-interactive", "--keep-until-expiring",
        ]
    else:
        raise ValueError("Unsupported ACME challenge type")
    for cert_domain in domains:
        command += ["-d", cert_domain]
    result = run(command, timeout=900, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Certbot failed")[-5000:]
        raise RuntimeError(detail)
    live = f"/etc/letsencrypt/live/{base_domain}"
    cert_dir = os.path.join(PANEL_DIR, "certs")
    os.makedirs(cert_dir, mode=0o700, exist_ok=True)
    shutil.copy2(os.path.join(live, "fullchain.pem"), os.path.join(cert_dir, "cert.pem"))
    shutil.copy2(os.path.join(live, "privkey.pem"), os.path.join(cert_dir, "key.pem"))
    os.chmod(os.path.join(cert_dir, "cert.pem"), 0o644)
    os.chmod(os.path.join(cert_dir, "key.pem"), 0o600)
    deploy_hook = "/etc/letsencrypt/renewal-hooks/deploy/p00rija-panel"
    os.makedirs(os.path.dirname(deploy_hook), mode=0o755, exist_ok=True)
    Path(deploy_hook).write_text(
        """#!/usr/bin/env bash
set -euo pipefail
install -m 0644 "$RENEWED_LINEAGE/fullchain.pem" /opt/p00rija/panel/certs/cert.pem
install -m 0600 "$RENEWED_LINEAGE/privkey.pem" /opt/p00rija/panel/certs/key.pem
docker restart p00rija-panel >/dev/null
""",
        encoding="utf-8",
    )
    os.chmod(deploy_hook, 0o700)
    settings = db.setdefault("settings", {})
    settings.update({
        "panel_host": base_domain,
        "panel_tls": True,
        "cert_path": "/opt/p00rija/certs/cert.pem",
        "key_path": "/opt/p00rija/certs/key.pem",
        "cert_auto_generated": False,
        "letsencrypt_domain": base_domain,
        "letsencrypt_email": email,
        "letsencrypt_challenge": challenge,
        "letsencrypt_wildcard": wildcard,
        "letsencrypt_dns_provider": str(payload.get("dns_provider") or "") if challenge == "dns-01" else "",
    })
    save_panel_state(config, db)
    return {
        "success": True,
        "domain": base_domain,
        "domains": domains,
        "challenge": challenge,
        "wildcard": wildcard,
        "cert_path": "/opt/p00rija/certs/cert.pem",
        "key_path": "/opt/p00rija/certs/key.pem",
        "restart_required": True,
        "message": "Certificate issued. Restart the panel to load it.",
    }


def change_panel_ports(payload: dict) -> dict:
    web_port = int(payload.get("web_port") or 0)
    api_port = int(payload.get("api_port") or 0)
    if not 1 <= web_port <= 65535 or not 1 <= api_port <= 65535:
        raise ValueError("Panel ports must be between 1 and 65535")
    if web_port == 22 or api_port == 22:
        raise ValueError("Port 22 is reserved for SSH")
    config, db = load_panel_state()
    old_ports = {int(config.get("port", 8080)), int(config.get("api_port", 8000))}
    for port in {web_port, api_port}:
        if not port_is_available(port, old_ports):
            raise ValueError(f"Port {port} is already occupied on the host")
    config["port"] = web_port
    config["api_port"] = api_port
    db.setdefault("settings", {})["port"] = web_port
    db.setdefault("settings", {})["api_port"] = api_port
    save_panel_state(config, db)
    recreate_panel(web_port, api_port)
    host = str(db.get("settings", {}).get("panel_host") or payload.get("host") or "127.0.0.1")
    return {
        "success": True,
        "web_port": web_port,
        "api_port": api_port,
        "new_panel_url": f"https://{host}:{web_port}",
    }


def start_panel_node(payload: dict) -> dict:
    node_dir = "/opt/p00rija/panel-node"
    os.makedirs(node_dir, mode=0o700, exist_ok=True)
    config = {
        "role": "internal",
        "panel_url": str(payload["panel_url"]).rstrip("/"),
        "token": str(payload["token"]),
        "private_key": str(payload["private_key"]),
    }
    atomic_json(os.path.join(node_dir, "p00rija_config.json"), config)
    Path(os.path.join(node_dir, ".run_mode")).write_text("docker\n")
    Path(os.path.join(node_dir, ".network_mode")).write_text("host\n")
    Path(os.path.join(node_dir, ".publish_ranges")).write_text("\n")
    image = current_image()
    run(["docker", "rm", "-f", PANEL_NODE_CONTAINER], timeout=60, check=False)
    command = [
        "docker", "run", "-d", "--name", PANEL_NODE_CONTAINER,
        "--network", "host", "--restart", "unless-stopped",
        "--cap-add", "NET_ADMIN", "--pids-limit", "768",
        "--ulimit", "nofile=262144:262144",
    ]
    if os.path.exists("/dev/net/tun"):
        command += ["--device", "/dev/net/tun"]
    command += ["-v", f"{node_dir}:/opt/p00rija", image]
    run(command, timeout=120)
    return {
        "success": True,
        "node_id": payload.get("node_id"),
        "container": PANEL_NODE_CONTAINER,
        "network_mode": "host",
        "panel_url": config["panel_url"],
    }


def handle(request: dict) -> dict:
    action = request.get("action")
    payload = request.get("payload") or {}
    if action == "certificate":
        return issue_certificate(payload)
    if action == "panel_ports":
        return change_panel_ports(payload)
    if action == "panel_node":
        return start_panel_node(payload)
    raise ValueError("Unsupported host-control action")


def main() -> None:
    if os.geteuid() != 0:
        raise SystemExit("p00rija-host-agent must run as root")
    for path in (CONTROL_DIR, REQUEST_DIR, RESULT_DIR):
        os.makedirs(path, mode=0o700, exist_ok=True)
        os.chmod(path, 0o700)
    lock_file = open(os.path.join(CONTROL_DIR, "agent.lock"), "w")
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    while True:
        atomic_json(HEARTBEAT, {"timestamp": time.time(), "pid": os.getpid()})
        for path in sorted(Path(REQUEST_DIR).glob("*.json")):
            try:
                request = json.loads(path.read_text(encoding="utf-8"))
                if time.time() < float(request.get("not_before", 0) or 0):
                    continue
                request_id = str(request.get("id") or path.stem)
                started = time.time()
                try:
                    result = handle(request)
                    result.update({"request_id": request_id, "pending": False, "finished_at": time.time()})
                except Exception as exc:
                    result = {
                        "success": False,
                        "request_id": request_id,
                        "pending": False,
                        "error": str(exc)[-6000:],
                        "finished_at": time.time(),
                    }
                result["elapsed_seconds"] = round(time.time() - started, 3)
                atomic_json(os.path.join(RESULT_DIR, f"{request_id}.json"), result)
                path.unlink(missing_ok=True)
            except Exception:
                path.rename(path.with_suffix(".invalid"))
        cutoff = time.time() - 86400
        for result_path in Path(RESULT_DIR).glob("*.json"):
            try:
                if result_path.stat().st_mtime < cutoff:
                    result_path.unlink()
            except OSError:
                pass
        time.sleep(1)


if __name__ == "__main__":
    main()
