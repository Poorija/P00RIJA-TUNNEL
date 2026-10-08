"""Interactive first-run setup wizard for P00RIJA TUNNEL.

Collected answers are persisted to the node/panel config file; the runtime
always re-reads them from disk, keeping interactive input out of the
request path.
"""

from __future__ import annotations

import json
import os
import secrets
import sys

from .security import assert_safe_remote_url, hash_password

CONFIG_PATH = os.environ.get("P00RIJA_CONFIG_DIR", "/opt/p00rija") + "/p00rija_config.json"


def start_setup_wizard(db):
    print("==================================================")
    print("           P00RIJA TUNNEL Setup Wizard            ")
    print("==================================================")
    print("Please select the role of this server:")
    print("1) Panel (Central management web console)")
    print("2) Internal Node (Handles local entry listeners)")
    print("3) External Node (Establish reverse tunnels to internal nodes)")
    role_choice = input("Selection (1-3): ").strip()

    if role_choice == "1":
        rand_port = secrets.randbelow(50000) + 10000
        port_input = input(f"Web panel port (default: {rand_port}): ").strip()
        port = int(port_input) if port_input else rand_port

        api_port_input = input("Node API port (default: 8000): ").strip()
        api_port = int(api_port_input) if api_port_input else 8000

        username = input("Admin username (default: admin): ").strip() or "admin"
        password = ""
        while not password:
            password = input("Admin password (required): ").strip()

        config = {
            "role": "panel",
            "port": port,
            "api_port": api_port,
        }
        db.data["settings"]["port"] = port
        db.data["settings"]["api_port"] = api_port
        db.data["admin"]["username"] = username
        db.data["admin"]["password_hash"] = hash_password(password)
        db.save()

    elif role_choice in ("2", "3"):
        role = "internal" if role_choice == "2" else "external"
        panel_url = ""
        while not panel_url:
            panel_url = input("Web Panel API URL (e.g. http://1.2.3.4:8080): ").strip()
        # Validate the operator-supplied panel URL before it is ever stored.
        assert_safe_remote_url(panel_url.rstrip("/") + "/")
        token = ""
        while not token:
            token = input("Node Token (from the Panel UI): ").strip()

        config = {
            "role": role,
            "panel_url": panel_url.rstrip("/"),
            "token": token,
        }
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    config_fd = os.open(CONFIG_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(config_fd, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Configuration written to {CONFIG_PATH}. Start container/service to run.")
