"""JSON database storage for P00RIJA TUNNEL."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import copy
from collections import deque
from collections.abc import Callable
from typing import Any

try:
    from .tunnel_methods import default_tunnel_profiles
except Exception:
    def default_tunnel_profiles() -> dict[str, Any]:
        return {}


# --- Password hashing (PBKDF2-HMAC-SHA256, salted, backward-compatible) ---
# Stored format: "pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>"
# Legacy unsalted sha256 hashes are still verified but upgraded on next login.
_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Hash a password with a fresh random salt using PBKDF2."""
    password = password or ""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash (PBKDF2 or legacy unsalted sha256)."""
    password = password or ""
    stored = stored or ""
    if stored.startswith("pbkdf2_sha256$"):
        try:
            parts = stored.split("$")
            if len(parts) != 4:
                return False
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            expected = bytes.fromhex(parts[3])
        except (ValueError, IndexError):
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(digest, expected)
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored)


def password_needs_upgrade(stored: str) -> bool:
    """Return True if the stored hash uses the legacy unsalted sha256 scheme."""
    return bool(stored) and not stored.startswith("pbkdf2_sha256$")


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
        self.lock = threading.RLock()
        self.data = {
            "admin": {
                "username": "admin",
                "password_hash": hash_password("admin"),
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
        self._log_buffer: deque = deque(maxlen=1000)
        self.load()

    def load(self) -> None:
        with self.lock:
            # Defaults are only valid when no database file exists yet; a corrupt
            # file must fail closed instead of silently resetting to the default
            # admin credentials.
            if not os.path.exists(self.filepath):
                return
            try:
                with open(self.filepath, "r") as f:
                    loaded = json.load(f)
            except Exception as exc:
                corrupt_path = f"{self.filepath}.corrupt-{int(time.time())}"
                try:
                    os.replace(self.filepath, corrupt_path)
                except OSError:
                    corrupt_path = self.filepath
                raise RuntimeError(
                    f"Database file is corrupt ({exc}); original moved to {corrupt_path}"
                ) from exc
            if not isinstance(loaded, dict):
                corrupt_path = f"{self.filepath}.corrupt-{int(time.time())}"
                try:
                    os.replace(self.filepath, corrupt_path)
                except OSError:
                    corrupt_path = self.filepath
                raise RuntimeError(
                    f"Database file has an unexpected structure; original moved to {corrupt_path}"
                )
            for key in self.data:
                if key in loaded:
                    if key == "settings":
                        self.data[key].update(loaded[key])
                    else:
                        self.data[key] = loaded[key]

    def save(self) -> None:
        with self.lock:
            parent = os.path.dirname(self.filepath)
            if parent:
                os.makedirs(parent, exist_ok=True)
            if self._log_buffer:
                logs = self.data.setdefault("logs", [])
                logs.extend(self._log_buffer)
                self._log_buffer.clear()
                if len(logs) > 1000:
                    del logs[:len(logs) - 1000]
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
            tmp_fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(tmp_fd, "w") as f:
                f.write(serialized)
            os.replace(tmp_path, self.filepath)

    def update(self, mutator: Callable[[dict[str, Any]], None]) -> None:
        """Atomically apply a mutation to self.data under the write lock, then persist.

        Use this for read-modify-write sequences (port allocation, node add, etc.) so
        concurrent request threads cannot interleave and corrupt the in-memory dict.
        """
        with self.lock:
            mutator(self.data)
        self.save()

    def log(self, source: str, level: str, message: str) -> None:
        print(f"[{source.upper()}] [{level.upper()}] {message}", flush=True)
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "level": level,
            "message": message,
        }
        with self.lock:
            # Buffered in memory; flushed to disk by the next save() so hot
            # log paths do not rewrite the whole DB file on every event.
            self._log_buffer.append(entry)
