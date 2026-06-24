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
        return True
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
    with open(cfg_path, "w") as f:
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

