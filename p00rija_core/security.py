"""Security, enrollment, TOTP, and certificate helpers for P00RIJA TUNNEL."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import socket
import struct
import subprocess
import time
from urllib.parse import urlparse

CONFIG_DIR = os.environ.get("P00RIJA_CONFIG_DIR", "/opt/p00rija")

# --- Password hashing (PBKDF2-HMAC-SHA256, salted, backward-compatible) ---
# Stored format: "pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>"
# Legacy format (unsalted sha256 hex) is still VERIFIED but always upgraded on next login.
PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Hash a password with a fresh random salt using PBKDF2."""
    password = password or ""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


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
    # Legacy unsalted sha256 fallback (for databases created before this upgrade).
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored)


def password_needs_upgrade(stored: str) -> bool:
    """Return True if the stored hash uses the legacy unsalted sha256 scheme."""
    return bool(stored) and not stored.startswith("pbkdf2_sha256$")


def normalize_role(role):
    if role in ("iran", "internal"):
        return "internal"
    if role in ("eu", "foreign", "external"):
        return "external"
    return role

def role_matches(node_role, desired):
    return normalize_role(node_role) == normalize_role(desired)

def node_public_from_private(private_key):
    return hashlib.sha256(str(private_key).encode()).hexdigest()

def make_node_keypair():
    private_key = secrets.token_urlsafe(32)
    return private_key, node_public_from_private(private_key)

def normalize_node_token(token):
    token = str(token or "").strip()
    if token and not token.startswith("tok_") and re.fullmatch(r"[0-9a-fA-F]{16}", token):
        return f"tok_{token.lower()}"
    return token

def valid_node_signature(node, path, payload_text, signature):
    private_key = node.get("private_key", "")
    if not private_key:
        # Fail closed: unsigned nodes must be rejected unless the node record
        # explicitly opted out of command signing.
        return bool(node.get("signature_disabled") is True)
    expected = hmac.new(private_key.encode(), f"{path}\n{payload_text or ''}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def make_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

def verify_totp(secret, code, window=1):
    code = str(code or "").strip().replace(" ", "")
    if not secret or len(code) != 6 or not code.isdigit():
        return False
    try:
        padded = secret + "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(padded, casefold=True)
    except Exception:
        return False
    counter = int(time.time() // 30)
    for offset in range(-window, window + 1):
        msg = struct.pack(">Q", counter + offset)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        pos = digest[-1] & 0x0F
        token = (struct.unpack(">I", digest[pos:pos + 4])[0] & 0x7FFFFFFF) % 1000000
        if hmac.compare_digest(f"{token:06d}", code):
            return True
    return False

def is_ip_address(value):
    try:
        socket.inet_pton(socket.AF_INET, value)
        return True
    except Exception:
        try:
            socket.inet_pton(socket.AF_INET6, value)
            return True
        except Exception:
            return False

def normalize_cert_host(host):
    host = str(host or "").strip()
    if "://" in host:
        parsed = urlparse(host)
        host = parsed.hostname or host
    if host.startswith("[") and "]" in host:
        host = host[1:host.index("]")]
    if ":" in host and not is_ip_address(host):
        host = host.split(":", 1)[0]
    if not host or len(host) > 253 or any(ch in host for ch in "\\/'\"`$;|&<> \t\r\n"):
        return "localhost"
    return host

def unique_cert_hosts(primary_host=None):
    hosts = []
    for item in (
        primary_host,
        "localhost",
        "127.0.0.1",
        "::1",
        socket.gethostname(),
        socket.getfqdn(),
    ):
        host = normalize_cert_host(item)
        if host and host not in hosts:
            hosts.append(host)
    return hosts

def generate_local_panel_certificate(host="localhost", cert_path=None, key_path=None):
    cert_dir = f"{CONFIG_DIR}/certs"
    os.makedirs(cert_dir, exist_ok=True)
    cert_path = cert_path or f"{cert_dir}/cert.pem"
    key_path = key_path or f"{cert_dir}/key.pem"
    cfg_path = f"{cert_dir}/local-cert-openssl.cnf"
    hosts = unique_cert_hosts(host)
    san_parts = [f"{'IP' if is_ip_address(item) else 'DNS'}:{item}" for item in hosts]
    common_name = hosts[0] if hosts else "localhost"
    cfg_fd = os.open(cfg_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(cfg_fd, "w") as f:
        f.write(
            "[req]\n"
            "distinguished_name=req_distinguished_name\n"
            "x509_extensions=v3_req\n"
            "prompt=no\n"
            "[req_distinguished_name]\n"
            f"CN={common_name}\n"
            "[v3_req]\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth\n"
            f"subjectAltName={','.join(san_parts)}\n"
        )
    res = subprocess.run([
        "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
        "-days", "825", "-keyout", key_path, "-out", cert_path,
        "-config", cfg_path
    ], capture_output=True, text=True, timeout=30)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "OpenSSL failed")
    os.chmod(key_path, 0o600)
    os.chmod(cert_path, 0o644)
    return cert_path, key_path

def certificate_is_self_signed(cert_path):
    try:
        res = subprocess.run(
            ["openssl", "x509", "-noout", "-subject", "-issuer", "-in", cert_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode != 0:
            return False
        subject = ""
        issuer = ""
        for line in res.stdout.splitlines():
            if line.startswith("subject="):
                subject = line.split("=", 1)[1].strip()
            elif line.startswith("issuer="):
                issuer = line.split("=", 1)[1].strip()
        return bool(subject and issuer and subject == issuer)
    except Exception:
        return False


# --- Outbound URL / path safety guards ---

_FORBIDDEN_URL_SCHEMES = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def _ip_is_private(host: str) -> bool:
    """Return True when the host is (or resolves to) a non-public address."""
    import ipaddress

    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return bool(
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        )
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError):
        return True
    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            return True
    return False


def assert_safe_remote_url(url: str, *, allow_private: bool = False) -> str:
    """Validate an outbound URL before any request is issued.

    Only http/https is accepted, embedded credentials are rejected, and the
    host (IP literal or resolved name) must be public unless the caller
    explicitly permits private peers (e.g. a panel reachable on the LAN).
    Returns the URL unchanged for call-site convenience.
    """
    url = str(url or "")
    if not _FORBIDDEN_URL_SCHEMES.match(url):
        raise ValueError("URL must be absolute and start with a scheme")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise ValueError("Embedded credentials in URLs are not allowed")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL has no host")
    if not allow_private and _ip_is_private(host):
        raise ValueError(f"Refusing non-public remote host: {host}")
    return url


def ensure_within(base_dir: str, target_path: str) -> str:
    """Assert target_path resolves inside base_dir; return target_path.

    Guards every write whose path is assembled from external input so a
    traversal attempt fails loudly before any file is touched.
    """
    base_real = os.path.realpath(str(base_dir))
    target_real = os.path.realpath(str(target_path))
    if target_real != base_real and not target_real.startswith(base_real + os.sep):
        raise ValueError(f"Refusing path outside {base_dir}: {target_path}")
    return target_path

