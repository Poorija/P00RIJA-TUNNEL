#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib import error, request


ROOT = Path(__file__).resolve().parent
STATE_DIR = ROOT / "tests" / "router-lab"
BASE_IMAGE = "p00rija-tunnel:1.9.95-routerlab-base"
LAB_IMAGE = "p00rija-tunnel:1.9.95-routerlab"
API_KEY = "router-lab-secret"
PANEL_WEB_PORT = int(os.environ.get("P00RIJA_ROUTER_LAB_WEB_PORT", "19080"))
PANEL_API_PORT = int(os.environ.get("P00RIJA_ROUTER_LAB_API_PORT", "19001"))
HOST_PANEL_WEB = f"https://127.0.0.1:{PANEL_WEB_PORT}"
HOST_PANEL_API = f"https://127.0.0.1:{PANEL_API_PORT}"
PANEL_CONTAINER_URL = "https://10.88.10.10:8000"
ACCESS_NETWORK = {"name": "p00rija-rt-access-net", "subnet": "10.88.250.0/24", "panel_ip": "10.88.250.10"}

ROUTER = {
    "name": "p00rija-rt-router",
    "image": "alpine:latest",
}

NETWORKS = [
    {"name": "p00rija-rt-panel-net", "subnet": "10.88.10.0/24", "router": "10.88.10.254"},
    {"name": "p00rija-rt-ir2-net", "subnet": "10.88.20.0/24", "router": "10.88.20.254"},
    {"name": "p00rija-rt-ext1-net", "subnet": "10.88.101.0/24", "router": "10.88.101.254"},
    {"name": "p00rija-rt-ext2-net", "subnet": "10.88.102.0/24", "router": "10.88.102.254"},
    {"name": "p00rija-rt-ext3-net", "subnet": "10.88.103.0/24", "router": "10.88.103.254"},
]

NODES = [
    {
        "name": "Internal Panel Node",
        "container": "p00rija-rt-ir-panel-node",
        "role": "internal",
        "ip": "10.88.10.10",
        "network_mode": "container:p00rija-rt-panel",
        "state": "ir-panel-node",
    },
    {
        "name": "Internal Node 2",
        "container": "p00rija-rt-ir-node-2",
        "role": "internal",
        "ip": "10.88.20.10",
        "network": "p00rija-rt-ir2-net",
        "router": "10.88.20.254",
        "state": "ir-node-2",
    },
    {
        "name": "External Node 1",
        "container": "p00rija-rt-foreign-node-1",
        "role": "external",
        "ip": "10.88.101.10",
        "network": "p00rija-rt-ext1-net",
        "router": "10.88.101.254",
        "state": "foreign-node-1",
    },
    {
        "name": "External Node 2",
        "container": "p00rija-rt-foreign-node-2",
        "role": "external",
        "ip": "10.88.102.10",
        "network": "p00rija-rt-ext2-net",
        "router": "10.88.102.254",
        "state": "foreign-node-2",
    },
    {
        "name": "External Node 3",
        "container": "p00rija-rt-foreign-node-3",
        "role": "external",
        "ip": "10.88.103.10",
        "network": "p00rija-rt-ext3-net",
        "router": "10.88.103.254",
        "state": "foreign-node-3",
    },
]

SUBNETS = [item["subnet"] for item in NETWORKS]


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def docker_rm(name: str) -> None:
    run(["docker", "rm", "-f", name], check=False, capture=True)


def build_images() -> None:
    run(["docker", "build", "--platform", "linux/amd64", "-t", BASE_IMAGE, "-f", str(ROOT / "Dockerfile"), str(ROOT)])
    with tempfile.TemporaryDirectory() as td:
        dockerfile = Path(td) / "Dockerfile"
        dockerfile.write_text(
            f"FROM {BASE_IMAGE}\n"
            "RUN apt-get update && apt-get install -y iproute2 iptables && rm -rf /var/lib/apt/lists/*\n",
            encoding="utf-8",
        )
        run(["docker", "build", "--platform", "linux/amd64", "-t", LAB_IMAGE, "-f", str(dockerfile), td])


def cleanup() -> None:
    for name in ["p00rija-rt-panel", ROUTER["name"], *(node["container"] for node in NODES)]:
        docker_rm(name)
    run(["docker", "network", "rm", ACCESS_NETWORK["name"]], check=False, capture=True)
    for net in NETWORKS:
        run(["docker", "network", "rm", net["name"]], check=False, capture=True)
    shutil.rmtree(STATE_DIR, ignore_errors=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def create_networks() -> None:
    run(["docker", "network", "create", "--subnet", ACCESS_NETWORK["subnet"], ACCESS_NETWORK["name"]])
    for net in NETWORKS:
        run(["docker", "network", "create", "--internal", "--subnet", net["subnet"], net["name"]])


def start_router() -> None:
    first = NETWORKS[0]
    run([
        "docker", "run", "-d",
        "--name", ROUTER["name"],
        "--cap-add", "NET_ADMIN",
        "--sysctl", "net.ipv4.ip_forward=1",
        "--network", first["name"],
        "--ip", first["router"],
        ROUTER["image"],
        "sh", "-lc", "sysctl -w net.ipv4.ip_forward=1 >/dev/null; sleep infinity",
    ])
    for net in NETWORKS[1:]:
        run(["docker", "network", "connect", "--ip", net["router"], net["name"], ROUTER["name"]])
    run(["docker", "exec", ROUTER["name"], "sh", "-lc", "cat /proc/sys/net/ipv4/ip_forward"], check=False)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare_panel_state() -> Path:
    panel_dir = STATE_DIR / "panel"
    write_json(panel_dir / "p00rija_config.json", {
        "role": "panel",
        "port": 8080,
        "api_port": 8000,
        "panel_host": "10.88.10.10",
    })
    write_json(panel_dir / "p00rija_db.json", {
        "admin": {"username": "admin", "password_hash": hashlib.sha256(b"admin").hexdigest()},
        "settings": {
            "port": 8080,
            "api_port": 8000,
            "panel_host": "10.88.10.10",
            "panel_tls": True,
            "node_api_key": API_KEY,
            "test_interval": 5,
            "max_idle_seconds": 300,
            "refresh_time": 5,
        },
        "nodes": {},
        "links": {},
        "node_commands": {},
        "logs": [],
    })
    return panel_dir


def start_panel() -> None:
    panel_dir = prepare_panel_state()
    run([
        "docker", "run", "-d",
        "--name", "p00rija-rt-panel",
        "--platform", "linux/amd64",
        "--cap-add", "NET_ADMIN",
        "--network", ACCESS_NETWORK["name"],
        "--ip", ACCESS_NETWORK["panel_ip"],
        "-p", f"{PANEL_WEB_PORT}:8080",
        "-p", f"{PANEL_API_PORT}:8000",
        "-e", f"P00RIJA_NODE_API_KEY={API_KEY}",
        "-e", "P00RIJA_ALLOW_INSECURE_ORBSTACK=1",
        "-v", f"{panel_dir}:/opt/p00rija",
        LAB_IMAGE,
        "python3", "/app/P00RIJA.py",
    ])
    run(["docker", "network", "connect", "--ip", "10.88.10.10", "p00rija-rt-panel-net", "p00rija-rt-panel"])
    add_routes("p00rija-rt-panel", "10.88.10.254", own_subnet="10.88.10.0/24")


def add_routes(container: str, gateway: str, own_subnet: str) -> None:
    for subnet in SUBNETS:
        if subnet == own_subnet:
            continue
        run(["docker", "exec", container, "ip", "route", "replace", subnet, "via", gateway])


def wait_for_panel() -> None:
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            http_json("GET", "/api/public-settings", timeout=3)
            host_web_get("/api/public-settings", timeout=3)
            return
        except Exception:
            time.sleep(1)
    logs = run(["docker", "logs", "--tail", "80", "p00rija-rt-panel"], check=False, capture=True)
    raise RuntimeError(f"Panel did not become ready.\n{logs.stdout}\n{logs.stderr}")


def http_json(method: str, path: str, payload: dict | None = None, token: str | None = None, timeout: int = 30) -> dict:
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    req = request.Request(HOST_PANEL_API + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with request.urlopen(req, context=ctx, timeout=timeout) as res:
        raw = res.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def host_web_get(path: str, timeout: int = 10) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with request.urlopen(HOST_PANEL_WEB + path, context=ctx, timeout=timeout) as res:
        return res.read().decode("utf-8")


def login() -> str:
    return http_json("POST", "/api/login", {"username": "admin", "password": "admin"})["token"]


def expect_http_error(method: str, path: str, payload: dict | None, token: str | None, expected: int) -> None:
    try:
        http_json(method, path, payload, token=token, timeout=10)
    except error.HTTPError as exc:
        if exc.code == expected:
            return
        raise RuntimeError(f"Expected HTTP {expected} from {path}, got {exc.code}") from exc
    raise RuntimeError(f"Expected HTTP {expected} from {path}, got success")


def assert_panel_contract(token: str) -> dict:
    routes = http_json("GET", "/api/system/routes", token=token, timeout=10)
    route_pairs = {(item.get("method"), item.get("path")) for item in routes.get("routes", [])}
    required_routes = {
        ("POST", "/api/nodes"),
        ("POST", "/api/nodes/edit"),
        ("POST", "/api/nodes/register"),
        ("POST", "/api/nodes/auto"),
        ("GET", "/api/status"),
        ("POST", "/api/links"),
    }
    missing = sorted(required_routes - route_pairs)
    if missing:
        raise RuntimeError(f"Panel API route registry is missing required router-lab routes: {missing}")
    expected_statuses = {
        "node_post_dispatch_ready",
        "link_get_runtime_dispatch_ready",
        "link_lifecycle_runtime_dispatch_ready",
    }
    if routes.get("migration_status") not in expected_statuses:
        raise RuntimeError(f"Unexpected API migration status: {routes.get('migration_status')}")

    audit = http_json("GET", "/api/system/audit", token=token, timeout=20)
    capability_ids = {item.get("id") for item in audit.get("capabilities", [])}
    required_capabilities = {
        "api_nodes_post_dispatch",
        "api_links_get_dispatch",
        "api_links_lifecycle_dispatch",
        "api_runtime_get_dispatch",
    }
    missing_capabilities = sorted(required_capabilities - capability_ids)
    if missing_capabilities:
        raise RuntimeError(f"Panel audit is missing extracted dispatcher capabilities: {missing_capabilities}")

    expect_http_error("POST", "/api/nodes/register", {
        "api_key": "wrong-router-lab-key",
        "name": "Router Lab Unauthorized Probe",
        "role": "internal",
        "ip": "10.88.255.250",
    }, token, 401)
    return routes


def register_nodes(token: str) -> dict[str, dict]:
    registered: dict[str, dict] = {}
    for node in NODES:
        data = http_json("POST", "/api/nodes/register", {
            "api_key": API_KEY,
            "name": node["name"],
            "role": node["role"],
            "ip": node["ip"],
            "tags": [
                {"name": "router-lab", "color": "#20c7b5"},
                {"name": node["role"], "color": "#22c55e" if node["role"] == "internal" else "#3b82f6"},
            ],
        }, token=token)
        missing = {"node_id", "token", "private_key", "public_key"} - set(data)
        if missing:
            raise RuntimeError(f"Node registration for {node['name']} missed response fields: {sorted(missing)}")
        registered[node["container"]] = {**node, **data}
    return registered


def start_node(node: dict) -> None:
    node_dir = STATE_DIR / node["state"]
    write_json(node_dir / "p00rija_config.json", {
        "role": node["role"],
        "panel_url": PANEL_CONTAINER_URL,
        "token": node["token"],
        "private_key": node["private_key"],
    })
    cmd = [
        "docker", "run", "-d",
        "--name", node["container"],
        "--platform", "linux/amd64",
        "--cap-add", "NET_ADMIN",
        "-v", f"{node_dir}:/opt/p00rija",
    ]
    if node.get("network_mode"):
        cmd += ["--network", node["network_mode"]]
    else:
        cmd += ["--network", node["network"], "--ip", node["ip"]]
    cmd += [LAB_IMAGE, "python3", "/app/P00RIJA.py"]
    run(cmd)
    if not node.get("network_mode"):
        own_subnet = next(net["subnet"] for net in NETWORKS if net["name"] == node["network"])
        add_routes(node["container"], node["router"], own_subnet)


def start_nodes(registered: dict[str, dict]) -> None:
    for node in registered.values():
        start_node(node)


def start_external_echo_servers() -> None:
    code = (
        "import socket,threading\n"
        "def h(c):\n"
        "    try:\n"
        "        data=c.recv(1024*1024)\n"
        "        c.sendall(b'P00RIJA_ROUTER_LAB_ECHO:' + data[:64])\n"
        "    except Exception: pass\n"
        "    finally:\n"
        "        try: c.close()\n"
        "        except Exception: pass\n"
        "s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(('0.0.0.0',8080)); s.listen(256)\n"
        "while True:\n"
        "    c,_=s.accept(); threading.Thread(target=h,args=(c,),daemon=True).start()\n"
    )
    for node in NODES:
        if node["role"] == "external":
            run(["docker", "exec", "-d", node["container"], "python3", "-c", code])


def wait_for_nodes_online(token: str, expected: int = 5) -> dict:
    deadline = time.time() + 120
    last = {}
    while time.time() < deadline:
        status = http_json("GET", "/api/status", token=token, timeout=10)
        nodes = status.get("nodes", {})
        online = [node for node in nodes.values() if node.get("status") == "online"]
        last = status
        if len(online) >= expected:
            return status
        time.sleep(3)
    print(json.dumps(last.get("nodes", {}), indent=2, ensure_ascii=False))
    raise RuntimeError("Not all nodes became online.")


def create_sample_links(token: str, status: dict) -> list[dict]:
    name_to_id = {node.get("name"): node_id for node_id, node in status.get("nodes", {}).items()}
    internals = ["Internal Panel Node", "Internal Node 2"]
    externals = ["External Node 1", "External Node 2", "External Node 3"]
    next_ports = {
        "Internal Panel Node": {"bridge": 7000, "user": 17000},
        "Internal Node 2": {"bridge": 7100, "user": 17100},
    }
    missing_nodes = sorted(set(internals + externals) - set(name_to_id))
    if missing_nodes:
        raise RuntimeError(f"Cannot create router-lab links; missing registered nodes: {missing_nodes}")
    created: list[dict] = []
    architectures = [
        {"data_plane_architecture": "shared_mux", "mux_carriers": 3, "bonding_max_lanes": 4},
        {"data_plane_architecture": "smart_hybrid", "mux_carriers": 3, "bonding_max_lanes": 4},
        {"data_plane_architecture": "shared_mux", "mux_carriers": 4, "bonding_max_lanes": 4},
        {"data_plane_architecture": "smart_hybrid", "mux_carriers": 2, "bonding_max_lanes": 6},
        {"data_plane_architecture": "adaptive_bonding", "mux_carriers": 2, "bonding_max_lanes": 8},
        {"data_plane_architecture": "per_user", "mux_carriers": 2, "bonding_max_lanes": 4},
    ]
    architecture_index = 0
    for external in externals:
        for internal in internals:
            ports = next_ports[internal]
            architecture = architectures[architecture_index]
            architecture_index += 1
            payload = {
                "name": f"RouterLab Reverse TCP {external} -> {internal}",
                "internal_node_id": name_to_id[internal],
                "external_node_id": name_to_id[external],
                "engine": "builtin",
                "tunnel_mode": "reverse_tcp",
                "transport": "reverse_tcp",
                "network": "tcp",
                "tls_enabled": False,
                "bridge_port": ports["bridge"],
                "sync_port": ports["bridge"] + 1,
                "pool_size": 24,
                **architecture,
                "obfs_host": "router-lab.local",
                "obfs_path": "/reverse-tcp",
            }
            link = http_json("POST", "/api/links", payload, token=token)
            http_json("POST", f"/api/links/ports?id={link['link_id']}", {
                "user_port": ports["user"],
                "target_port": 8080,
            }, token=token)
            created.append({
                **payload,
                "link_id": link["link_id"],
                "internal": internal,
                "external": external,
                "user_port": ports["user"],
                "target_port": 8080,
            })
            ports["bridge"] += 2
            ports["user"] += 1
    return created


def smoke_one_tunnel(container: str, port: int, message: str, deadline_seconds: int = 45) -> dict:
    code = (
        "import socket,sys\n"
        "port=int(sys.argv[1]); msg=sys.argv[2].encode()\n"
        "s=socket.create_connection(('127.0.0.1', port), 5)\n"
        "s.sendall(msg)\n"
        "data=s.recv(256)\n"
        "s.close()\n"
        "print(data.decode('utf-8', 'replace'))\n"
    )
    deadline = time.time() + deadline_seconds
    last_output = ""
    while time.time() < deadline:
        res = run([
            "docker", "exec", container,
            "python3", "-c", code, str(port), message,
        ], check=False, capture=True)
        last_output = (res.stdout or res.stderr or "").strip()
        if res.returncode == 0 and "P00RIJA_ROUTER_LAB_ECHO:" in last_output and message in last_output:
            return {"container": container, "port": port, "success": True, "response": last_output}
        time.sleep(2)
    return {"container": container, "port": port, "success": False, "response": last_output}


def tunnel_smoke_summary(links: list[dict]) -> list[dict]:
    results: list[dict] = []
    for item in links:
        container = "p00rija-rt-panel" if item["internal"] == "Internal Panel Node" else "p00rija-rt-ir-node-2"
        message = f"router-lab-{item['link_id']}-{item['user_port']}"
        result = smoke_one_tunnel(container, int(item["user_port"]), message)
        results.append({
            "link_id": item["link_id"],
            "name": item["name"],
            "container": result["container"],
            "user_port": result["port"],
            "success": result["success"],
            "response": result["response"],
        })
    failures = [item for item in results if not item["success"]]
    if failures:
        raise RuntimeError(f"Router-lab tunnel smoke failed: {json.dumps(failures, indent=2, ensure_ascii=False)}")
    return results


def container_thread_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for container in ["p00rija-rt-ir-panel-node", "p00rija-rt-ir-node-2", *(node["container"] for node in NODES[2:])]:
        result = run(
            ["docker", "exec", container, "sh", "-lc", "awk '/^Threads:/ {print $2}' /proc/1/status"],
            check=False,
            capture=True,
        )
        try:
            counts[container] = int((result.stdout or "").strip())
        except ValueError:
            counts[container] = -1
    return counts


def lifecycle_churn_summary(token: str, links: list[dict], cycles: int = 3) -> dict:
    before = container_thread_counts()
    for cycle in range(cycles):
        print(f"Lifecycle churn cycle {cycle + 1}/{cycles}: pausing all links...")
        for item in links:
            http_json("GET", f"/api/links/toggle-pause?id={item['link_id']}", token=token)
        time.sleep(7)
        print(f"Lifecycle churn cycle {cycle + 1}/{cycles}: resuming all links...")
        for item in links:
            http_json("GET", f"/api/links/toggle-pause?id={item['link_id']}", token=token)
        time.sleep(9)

    after = container_thread_counts()
    growth = {name: after.get(name, -1) - count for name, count in before.items()}
    excessive = {name: delta for name, delta in growth.items() if delta > 3}
    if excessive:
        raise RuntimeError(
            "Tunnel lifecycle leaked threads after repeated pause/resume: "
            + json.dumps({"before": before, "after": after, "growth": growth}, indent=2)
        )
    return {
        "cycles": cycles,
        "before": before,
        "after": after,
        "growth": growth,
        "max_allowed_growth": 3,
    }


def route_summary() -> dict[str, str]:
    checks = {
        "panel_to_ir2": ("p00rija-rt-panel", "10.88.20.10"),
        "foreign1_to_panel": ("p00rija-rt-foreign-node-1", "10.88.10.10"),
        "foreign2_to_ir2": ("p00rija-rt-foreign-node-2", "10.88.20.10"),
        "ir2_to_foreign3": ("p00rija-rt-ir-node-2", "10.88.103.10"),
    }
    out: dict[str, str] = {}
    for key, (container, target) in checks.items():
        res = run(["docker", "exec", container, "ip", "route", "get", target], check=False, capture=True)
        out[key] = (res.stdout or res.stderr).strip()
    return out


def print_summary(
    token: str,
    status: dict,
    links: list[dict],
    api_contract: dict,
    tunnel_smoke: list[dict],
    lifecycle_churn: dict,
) -> None:
    summary = {
        "panel_url": HOST_PANEL_WEB,
        "panel_api": HOST_PANEL_API,
        "browser_note": "Open panel_url exactly. Avoid the auto-generated p00rija-rt-panel.orb.local URL in this lab because OrbStack can proxy to a non-panel tunnel port.",
        "login": {"username": "admin", "password": "admin"},
        "api_contract": {
            "migration_status": api_contract.get("migration_status"),
            "route_count": api_contract.get("route_count"),
            "node_post_dispatcher": True,
            "node_registration_api_key": "verified",
        },
        "nodes": {
            node.get("name"): {
                "role": node.get("role"),
                "ip": node.get("ip"),
                "status": node.get("status"),
                "ping_ms": node.get("stats", {}).get("ping_ms"),
            }
            for node in status.get("nodes", {}).values()
        },
        "links": [
            {
                "name": item["name"],
                "link_id": item["link_id"],
                "user_port": item["user_port"],
                "target_port": item["target_port"],
                "engine": item["engine"],
                "mode": item["tunnel_mode"],
                "data_plane_architecture": item.get("data_plane_architecture", "per_user"),
                "mux_carriers": item.get("mux_carriers", 0),
                "bonding_max_lanes": item.get("bonding_max_lanes", 1),
            }
            for item in links
        ],
        "tunnel_smoke": tunnel_smoke,
        "lifecycle_churn": lifecycle_churn,
        "route_summary": route_summary(),
    }
    (STATE_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n=== ROUTER LAB READY ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nOpen the panel in your browser: {HOST_PANEL_WEB}")
    print("If OrbStack shows a 502 for p00rija-rt-panel.orb.local, use the URL above; the lab only publishes web/api on host ports "
          f"{PANEL_WEB_PORT}/{PANEL_API_PORT}.")
    print(f"\nBearer token for API smoke tests: {token}")
    print(f"State dir: {STATE_DIR}")


def main() -> int:
    build_images()
    cleanup()
    create_networks()
    start_router()
    start_panel()
    wait_for_panel()
    token = login()
    api_contract = assert_panel_contract(token)
    registered = register_nodes(token)
    start_nodes(registered)
    start_external_echo_servers()
    status = wait_for_nodes_online(token)
    links = create_sample_links(token, status)
    print("Waiting one config-sync cycle for tunnel workers...")
    time.sleep(12)
    tunnel_smoke = tunnel_smoke_summary(links)
    lifecycle_churn = lifecycle_churn_summary(token, links)
    tunnel_smoke = tunnel_smoke_summary(links)
    status = http_json("GET", "/api/status", token=token)
    print_summary(token, status, links, api_contract, tunnel_smoke, lifecycle_churn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
