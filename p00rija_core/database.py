"""JSON database storage for P00RIJA TUNNEL."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import copy
from collections.abc import Callable
from typing import Any

try:
    from .tunnel_methods import default_tunnel_profiles
except Exception:
    def default_tunnel_profiles() -> dict[str, Any]:
        return {}


class P00RIJADB:
    def __init__(
        self,
        filepath: str | None = None,
        *,
        config_dir: str | None = None,
        node_api_key: str = "",
        default_profiles_factory: Callable[[], dict[str, Any]] | None = None,
    ):
        config_dir = config_dir or os.environ.get("P00RIJA_CONFIG_DIR", "/opt/p00rija")
        self.filepath = filepath or os.environ.get("P00RIJA_DB_PATH", f"{config_dir}/p00rija_db.json")
        profiles_factory = default_profiles_factory or default_tunnel_profiles
        self.lock = threading.Lock()
        self.data = {
            "admin": {
                "username": "admin",
                "password_hash": hashlib.sha256(b"admin").hexdigest(),
            },
            "settings": {
                "port": 8080,
                "test_interval": 30,
                "max_idle_seconds": 300,
                "panel_tls": True,
                "cert_path": f"{config_dir}/certs/cert.pem",
                "key_path": f"{config_dir}/certs/key.pem",
                "two_factor_enabled": False,
                "two_factor_secret": "",
                "biometric_enabled": False,
                "node_api_key": node_api_key,
                "tunnel_profiles": profiles_factory(),
            },
            "nodes": {},
            "links": {},
            "node_commands": {},
            "logs": [],
        }
        self.load()

    def load(self) -> None:
        with self.lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r") as f:
                        loaded = json.load(f)
                    for key in self.data:
                        if key in loaded:
                            if key == "settings":
                                self.data[key].update(loaded[key])
                            else:
                                self.data[key] = loaded[key]
                except Exception as exc:
                    print(f"Error loading DB: {exc}")

    def save(self) -> None:
        with self.lock:
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                serialized = ""
                last_error = None
                for _ in range(4):
                    try:
                        serialized = json.dumps(copy.deepcopy(self.data), indent=4)
                        last_error = None
                        break
                    except RuntimeError as exc:
                        last_error = exc
                        time.sleep(0.01)
                if last_error is not None:
                    raise last_error
                tmp_path = f"{self.filepath}.tmp"
                with open(tmp_path, "w") as f:
                    f.write(serialized)
                os.chmod(tmp_path, 0o600)
                os.replace(tmp_path, self.filepath)
            except Exception as exc:
                print(f"Error saving DB: {exc}")

    def log(self, source: str, level: str, message: str) -> None:
        print(f"[{source.upper()}] [{level.upper()}] {message}", flush=True)
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "level": level,
            "message": message,
        }
        with self.lock:
            self.data.setdefault("logs", []).append(entry)
            if len(self.data["logs"]) > 1000:
                self.data["logs"] = self.data["logs"][-1000:]
        self.save()
