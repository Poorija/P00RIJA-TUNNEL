#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import request

IMAGE = "p00rija-tunnel:1.9.95"
ROOT = os.path.abspath(os.path.dirname(__file__))
STATE_DIR = os.path.join(ROOT, "tests", "realistic-load")
PANEL_WEB_PORT = int(os.environ.get("P00RIJA_TEST_PANEL_WEB_PORT", "18080"))
PANEL_API_PORT = int(os.environ.get("P00RIJA_TEST_PANEL_API_PORT", "18001"))
PANEL_API = f"http://127.0.0.1:{PANEL_API_PORT}"
PANEL_IN_DOCKER = f"http://host.docker.internal:{PANEL_API_PORT}"
NODE_LIMITS = ["--cpus", "1", "--memory", "2g", "--memory-swap", "6g", "--storage-opt", "size=10G"]

NETWORKS = [
    ("rt-panel-net", "172.31.5.0/24"),
    ("rt-iran-panel-net", "172.31.10.0/24"),
    ("rt-iran-node-2-net", "172.31.20.0/24"),
    ("rt-foreign-node-1-net", "172.31.101.0/24"),
    ("rt-foreign-node-2-net", "172.31.102.0/24"),
    ("rt-foreign-node-3-net", "172.31.103.0/24"),
]

NODES = [
    {"name": "iran-panel-node", "role": "internal", "network": "rt-iran-panel-net", "ip": "host.docker.internal"},
    {"name": "iran-node-2", "role": "internal", "network": "rt-iran-node-2-net", "ip": "host.docker.internal"},
    {"name": "foreign-node-1", "role": "external", "network": "rt-foreign-node-1-net", "ip": "172.31.101.10"},
    {"name": "foreign-node-2", "role": "external", "network": "rt-foreign-node-2-net", "ip": "172.31.102.10"},
    {"name": "foreign-node-3", "role": "external", "network": "rt-foreign-node-3-net", "ip": "172.31.103.10"},
]

TUNNEL_MODELS = [
    {"engine": "builtin", "tunnel_mode": "tcp", "transport": "tcp", "network": "tcp", "tls_enabled": False},
    {"engine": "builtin", "tunnel_mode": "websocket", "transport": "websocket", "network": "tcp", "tls_enabled": False},
    {"engine": "builtin", "tunnel_mode": "http_obfs", "transport": "ws", "network": "tcp", "tls_enabled": False},
    {"engine": "gost", "tunnel_mode": "grpc", "transport": "grpc", "network": "tcp", "tls_enabled": False},
    {"engine": "backhaul", "tunnel_mode": "tcpmux", "transport": "tcpmux", "network": "tcp", "tls_enabled": False},
    {"engine": "frp", "tunnel_mode": "tcp_udp", "transport": "tcp", "network": "tcp_udp", "tls_enabled": False},
    {"engine": "frp", "tunnel_mode": "kcp", "transport": "kcp", "network": "udp", "tls_enabled": False},
    {"engine": "xray", "tunnel_mode": "vless_reality", "transport": "tcp", "network": "tcp", "tls_enabled": False},
    {"engine": "muxquantum", "tunnel_mode": "quantummux", "transport": "quantummux", "network": "tcp", "tls_enabled": False},
    {"engine": "muxquantum", "tunnel_mode": "tunmux", "transport": "tunmux", "network": "tcp", "tls_enabled": False},
    {"engine": "hysteria2", "tunnel_mode": "quic", "transport": "quic", "network": "udp", "tls_enabled": False},
]


def run(cmd, check=True, capture=False):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def docker_run(args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode == 0:
        print(result.stdout.strip())
        return
    compact = []
    skip = False
    for part in args:
        if skip:
            skip = False
            continue
        if part in ("--cpus", "--memory", "--memory-swap", "--storage-opt"):
            skip = True
            continue
        compact.append(part)
    print(result.stderr.strip())
    print("Retrying without Docker resource flags.")
    run(compact)


def http_json(method, path, payload=None, token=None, timeout=45):
    data = json.dumps(payload or {}).encode() if payload is not None else None
    req = request.Request(PANEL_API + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with request.urlopen(req, timeout=timeout) as res:
        raw = res.read().decode()
        return json.loads(raw) if raw else {}


def wait_for_panel():
    for _ in range(60):
        try:
            http_json("GET", "/api/public-settings", timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("panel did not become ready")


def prepare():
    shutil.rmtree(STATE_DIR, ignore_errors=True)
    os.makedirs(STATE_DIR, exist_ok=True)
    for name in ["p00rija-panel", *(node["name"] for node in NODES)]:
        run(["docker", "rm", "-f", name], check=False)
    for name, subnet in NETWORKS:
        run(["docker", "network", "rm", name], check=False)
        run(["docker", "network", "create", "--subnet", subnet, name])
    run(["docker", "build", "-t", IMAGE, "-f", os.path.join(ROOT, "Dockerfile"), ROOT])


def start_panel():
    panel_dir = os.path.join(STATE_DIR, "panel")
    os.makedirs(panel_dir, exist_ok=True)
    db_data = {
        "admin": {"username": "admin", "password_hash": hashlib.sha256(b"admin").hexdigest()},
        "settings": {"port": 8080, "api_port": 8000, "panel_host": PANEL_IN_DOCKER, "node_api_key": "realistic-load-secret", "panel_tls": False},
        "nodes": {},
        "links": {},
        "logs": [],
    }
    with open(os.path.join(panel_dir, "p00rija_db.json"), "w") as f:
        json.dump(db_data, f)
    with open(os.path.join(panel_dir, "p00rija_config.json"), "w") as f:
        json.dump({"role": "panel", "port": 8080, "api_port": 8000}, f)
    docker_run([
        "docker", "run", "-d", "--name", "p00rija-panel",
        "--network", "rt-panel-net", "--add-host", "host.docker.internal:host-gateway",
        "-p", f"{PANEL_WEB_PORT}:8080", "-p", f"{PANEL_API_PORT}:8000",
        *NODE_LIMITS,
        "-v", f"{panel_dir}:/opt/p00rija",
        IMAGE, "python3", "/app/P00RIJA.py",
    ])
    wait_for_panel()
    return http_json("POST", "/api/login", {"username": "admin", "password": "admin"})["token"]


def register_and_start_nodes(token):
    node_ids = {}
    for node in NODES:
        data = http_json("POST", "/api/nodes/register", {
            "api_key": "realistic-load-secret",
            "name": node["name"],
            "role": node["role"],
            "ip": node["ip"],
        }, token=token)
        node_ids[node["name"]] = data["node_id"]
        node_dir = os.path.join(STATE_DIR, node["name"])
        os.makedirs(node_dir, exist_ok=True)
        with open(os.path.join(node_dir, "p00rija_config.json"), "w") as f:
            json.dump({"role": node["role"], "panel_url": PANEL_IN_DOCKER, "token": data["token"], "private_key": data["private_key"]}, f)
        ports = []
        if node["name"] == "iran-panel-node":
            ports = ["-p", "7000-7149:7000-7149", "-p", "17000-17149:17000-17149"]
        elif node["name"] == "iran-node-2":
            ports = ["-p", "7150-7299:7150-7299", "-p", "17150-17299:17150-17299"]
        docker_run([
            "docker", "run", "-d", "--name", node["name"],
            "--network", node["network"], "--add-host", "host.docker.internal:host-gateway",
            *ports,
            *NODE_LIMITS,
            "-v", f"{node_dir}:/opt/p00rija",
            IMAGE, "python3", "/app/P00RIJA.py",
        ])
    return node_ids


def start_foreign_target_servers():
    server_code = (
        "import socket,threading,time\n"
        "s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('0.0.0.0',8080));s.listen(2048)\n"
        "def h(c):\n"
        "    try:\n"
        "        c.settimeout(120); c.recv(1); time.sleep(30); c.sendall(b'OK')\n"
        "    except Exception: pass\n"
        "    finally:\n"
        "        try: c.close()\n"
        "        except Exception: pass\n"
        "while True:\n"
        "    c,a=s.accept(); threading.Thread(target=h,args=(c,),daemon=True).start()\n"
    )
    for node in ["foreign-node-1", "foreign-node-2", "foreign-node-3"]:
        run(["docker", "exec", "-d", node, "python3", "-c", server_code], check=False)


def create_links(token, node_ids):
    links = []
    next_bridge = {"iran-panel-node": 7000, "iran-node-2": 7150}
    next_user_port = {"iran-panel-node": 17000, "iran-node-2": 17150}
    for foreign in ["foreign-node-1", "foreign-node-2", "foreign-node-3"]:
        for internal in ["iran-panel-node", "iran-node-2"]:
            for model in TUNNEL_MODELS:
                bridge = next_bridge[internal]
                user_port = next_user_port[internal]
                payload = {
                    "name": f"{foreign}-to-{internal}-{model['engine']}-{model['tunnel_mode']}",
                    "internal_node_id": node_ids[internal],
                    "external_node_id": node_ids[foreign],
                    "bridge_port": bridge,
                    "sync_port": bridge + 1,
                    "pool_size": 100,
                    "obfs_host": "speedtest.net",
                    "obfs_path": "/load-test",
                    "tls_sni": "speedtest.net",
                    **model,
                }
                data = http_json("POST", "/api/links", payload, token=token)
                link_id = data["link_id"]
                http_json("POST", f"/api/links/ports?id={link_id}", {"user_port": user_port, "target_port": 8080}, token=token)
                links.append({"id": link_id, "internal": internal, "foreign": foreign, "user_port": user_port})
                next_bridge[internal] += 2
                next_user_port[internal] += 1
    return links


def hold_tunnel_connections(links, per_link=1):
    sockets = []
    deadline = time.time() + 30
    for link in links:
        for _ in range(per_link):
            while time.time() < deadline:
                try:
                    s = socket.create_connection(("127.0.0.1", int(link["user_port"])), timeout=5)
                    s.sendall(b"G")
                    sockets.append(s)
                    break
                except Exception:
                    time.sleep(0.2)
    return sockets


def load_panel(token, links):
    paths = ["/api/status", "/api/runtime/resources", "/api/runtime/sessions"]
    failures = []

    def hit(i):
        try:
            if i % 5 == 0 and links:
                return http_json("GET", f"/api/links/test?id={links[i % len(links)]['id']}", token=token)
            return http_json("GET", paths[i % len(paths)], token=token)
        except Exception as exc:
            return {"error": str(exc)}

    with ThreadPoolExecutor(max_workers=80) as pool:
        futures = [pool.submit(hit, i) for i in range(1200)]
        for future in as_completed(futures):
            result = future.result()
            if isinstance(result, dict) and result.get("error"):
                failures.append(result["error"])
    return failures


def main():
    prepare()
    token = start_panel()
    node_ids = register_and_start_nodes(token)
    start_foreign_target_servers()
    print("Waiting for node reports and config sync...")
    time.sleep(20)
    links = create_links(token, node_ids)
    print(f"Created {len(links)} tunnel links.")
    time.sleep(25)
    if links:
        http_json("GET", f"/api/links/toggle-pause?id={links[0]['id']}", token=token)
        time.sleep(6)
        http_json("GET", f"/api/links/toggle-pause?id={links[0]['id']}", token=token)
    held_sockets = hold_tunnel_connections(links[:24], per_link=1)
    time.sleep(6)
    failures = load_panel(token, links)
    status = http_json("GET", "/api/status", token=token)
    runtime = http_json("GET", "/api/runtime/sessions", token=token)
    online = [n["name"] for n in status.get("nodes", {}).values() if n.get("status") == "online"]
    print(json.dumps({
        "nodes_online": online,
        "links_created": len(links),
        "held_tunnel_connections": len(held_sockets),
        "runtime_sessions_seen": len(runtime.get("sessions", [])),
        "load_failures": failures[:20],
        "load_failure_count": len(failures)
    }, indent=2))
    for s in held_sockets:
        try:
            s.close()
        except Exception:
            pass
    sys.exit(2 if failures else 0)


if __name__ == "__main__":
    main()
