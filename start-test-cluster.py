import os, subprocess, json, hashlib, time

print("Setting up test cluster...")
os.makedirs("tests", exist_ok=True)

subprocess.run(["docker", "network", "create", "p00rija-test-net"], capture_output=True)
subprocess.run(["docker", "build", "--no-cache", "-t", "p00rija-tunnel:1.9.95", "-f", "Dockerfile", "."], check=True)

# 1. Setup Panel / Internal Node 1
os.makedirs("tests/panel", exist_ok=True)
pwd_hash = hashlib.sha256("admin".encode()).hexdigest()
db_data = {
    'admin': {'username': "admin", 'password_hash': pwd_hash},
    'settings': {
        'port': 8080,
        'api_port': 8000,
        'panel_host': 'http://panel-node:8000',
        'test_interval': 30,
        'max_idle_seconds': 300,
        'panel_tls': False,
        'node_api_key': 'test-secret-key'
    },
    'nodes': {}, 'links': {}, 'logs': []
}
with open("tests/panel/p00rija_db.json", "w") as f:
    json.dump(db_data, f)
    
with open("tests/panel/p00rija_config.json", "w") as f:
    json.dump({'role': 'panel', 'port': 8080, 'api_port': 8000}, f)

print("Starting panel-node...")
subprocess.run(["docker", "rm", "-f", "panel-node"], capture_output=True)
subprocess.run([
    "docker", "run", "-d", "--name", "panel-node", "--network", "p00rija-test-net",
    "-p", "8080:8080", "-p", "8001:8000",
    "-v", f"{os.path.abspath('tests/panel')}:/opt/p00rija",
    "p00rija-tunnel:1.9.95", "python3", "/app/P00RIJA.py"
], check=True)

# Give panel time to start
time.sleep(3)

# Login to get bearer token
res = subprocess.run([
    "curl", "-s", "-X", "POST", "http://localhost:8001/api/login",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({"username": "admin", "password": "admin"})
], capture_output=True, text=True)
login_data = json.loads(res.stdout)
bearer_token = login_data.get("token")
print(f"Logged in as admin, token: {bearer_token}")

# 2. Add nodes in the db dynamically so we have their tokens
nodes = [
    ("iran-node-1", "internal"),
    ("iran-node-2", "internal"),
    ("foreign-node-1", "external"),
    ("foreign-node-2", "external"),
    ("foreign-node-3", "external"),
    ("foreign-node-4", "external"),
    ("foreign-node-5", "external"),
    ("foreign-node-6", "external")
]

node_ids = {}

for name, role in nodes:
    os.makedirs(f"tests/{name}", exist_ok=True)
    # Register via API
    res = subprocess.run([
        "curl", "-s", "-X", "POST", "http://localhost:8001/api/nodes/register",
        "-H", f"Authorization: Bearer {bearer_token}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"api_key": "test-secret-key", "name": name, "role": role})
    ], capture_output=True, text=True)
    
    if res.returncode == 0:
        data = json.loads(res.stdout)
        token = data.get("token")
        private_key = data.get("private_key")
        node_id = data.get("node_id")
        node_ids[name] = node_id
        
        with open(f"tests/{name}/p00rija_config.json", "w") as f:
            json.dump({
                "role": role,
                "panel_url": "http://panel-node:8000",
                "token": token,
                "private_key": private_key
            }, f)
            
        print(f"Starting {name}...")
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        subprocess.run([
            "docker", "run", "-d", "--name", name, "--network", "p00rija-test-net",
            "-v", f"{os.path.abspath(f'tests/{name}')}:/opt/p00rija",
            "p00rija-tunnel:1.9.95", "python3", "/app/P00RIJA.py"
        ], check=True)

# 3. Create links
time.sleep(3)

# 6 links, mapping foreign nodes to Iran nodes
links_payloads = [
    {
        "name": "Link-1-TCP",
        "internal_node_id": node_ids["iran-node-1"],
        "external_node_id": node_ids["foreign-node-1"],
        "engine": "builtin",
        "tunnel_mode": "tcp",
        "transport": "tcp",
        "bridge_port": 7001,
        "sync_port": 7002,
    },
    {
        "name": "Link-2-WS",
        "internal_node_id": node_ids["iran-node-2"],
        "external_node_id": node_ids["foreign-node-2"],
        "engine": "builtin",
        "tunnel_mode": "websocket",
        "transport": "websocket",
        "bridge_port": 7003,
        "sync_port": 7004,
    },
    {
        "name": "Link-3-HTTP",
        "internal_node_id": node_ids["iran-node-1"],
        "external_node_id": node_ids["foreign-node-3"],
        "engine": "builtin",
        "tunnel_mode": "http_obfs",
        "transport": "tcp",
        "bridge_port": 7005,
        "sync_port": 7006,
    },
    {
        "name": "Link-4-Xray",
        "internal_node_id": node_ids["iran-node-2"],
        "external_node_id": node_ids["foreign-node-4"],
        "engine": "xray",
        "tunnel_mode": "vless_reality",
        "transport": "tcp",
        "bridge_port": 7007,
        "sync_port": 7008,
    },
    {
        "name": "Link-5-Gost",
        "internal_node_id": node_ids["iran-node-1"],
        "external_node_id": node_ids["foreign-node-5"],
        "engine": "gost",
        "tunnel_mode": "websocket",
        "transport": "websocket",
        "bridge_port": 7009,
        "sync_port": 7010,
    },
    {
        "name": "Link-6-MuxQuantum",
        "internal_node_id": node_ids["iran-node-2"],
        "external_node_id": node_ids["foreign-node-6"],
        "engine": "muxquantum",
        "tunnel_mode": "tcpmux",
        "transport": "tcpmux",
        "bridge_port": 7011,
        "sync_port": 7012,
    }
]

for p in links_payloads:
    res = subprocess.run([
        "curl", "-s", "-X", "POST", "http://localhost:8001/api/links",
        "-H", f"Authorization: Bearer {bearer_token}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(p)
    ], capture_output=True, text=True)
    print(f"Created link {p['name']}: {res.stdout}")

print("All nodes and links started successfully!")
