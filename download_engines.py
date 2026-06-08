#!/usr/bin/env python3
import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import ssl
import stat
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

ENGINES_DIR = Path("engines")
ARCHIVE_DIR = ENGINES_DIR / "archives"
MANIFEST_PATH = ENGINES_DIR / "manifest.json"
USER_AGENT = "P00RIJA-TUNNEL-offline-engine-bundler"


ENGINE_SPECS = {
    "xray": {
        "repo": "XTLS/Xray-core",
        "asset": ["Xray-linux-64.zip"],
        "bins": {"xray": "xray"},
    },
    "gost": {
        "repo": "go-gost/gost",
        "asset": ["linux_amd64.tar.gz"],
        "bins": {"gost": "gost"},
    },
    "backhaul": {
        "repo": "Musixal/Backhaul",
        "asset": ["backhaul_linux_amd64.tar.gz"],
        "bins": {"backhaul": "backhaul"},
    },
    "rathole": {
        "repo": "rapiz1/rathole",
        "asset": ["x86_64-unknown-linux-gnu.zip"],
        "bins": {"rathole": "rathole"},
    },
    "chisel": {
        "repo": "jpillora/chisel",
        "asset": ["linux_amd64.gz"],
        "bins": {"chisel": "chisel"},
    },
    "frp": {
        "repo": "fatedier/frp",
        "asset": ["linux_amd64.tar.gz"],
        "bins": {"frpc": "frpc", "frps": "frps"},
    },
    "hysteria2": {
        "repo": "apernet/hysteria",
        "asset": ["hysteria-linux-amd64"],
        "bins": {"hysteria": "hysteria", "hysteria2": "hysteria2"},
    },
    "singbox": {
        "repo": "SagerNet/sing-box",
        "asset": ["linux-amd64.tar.gz"],
        "bins": {"sing-box": "sing-box", "singbox": "sing-box"},
    },
    "naiveproxy": {
        "repo": "klzgrad/naiveproxy",
        "asset": ["linux-x64.tar.xz"],
        "bins": {"naive": "naive", "naiveproxy": "naiveproxy"},
    },
    "shadowtls": {
        "repo": "ihciah/shadow-tls",
        "asset": ["x86_64-unknown-linux-musl"],
        "bins": {"shadow-tls": "shadow-tls", "shadowtls": "shadowtls"},
    },
    "brook": {
        "repo": "txthinking/brook",
        "asset": ["brook_linux_amd64"],
        "bins": {"brook": "brook"},
    },
    "mieru": {
        "repo": "enfein/mieru",
        "asset": ["mieru_", "linux_amd64.tar.gz"],
        "bins": {"mieru": "mieru", "mita": "mita"},
        "extra_assets": [
            {"asset": ["mita_", "linux_amd64.tar.gz"], "bins": {"mita": "mita"}}
        ],
    },
}


def request_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode())


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as res:
        return res.read()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def match_asset(assets, patterns):
    patterns = [p.lower() for p in patterns]
    for asset in assets:
        name = asset["name"].lower()
        if all(pattern in name for pattern in patterns):
            return asset
    return None


def extract_archive(name, data, wanted):
    found = {}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        if name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(tmp)
        elif name.endswith(".tar.gz") or name.endswith(".tgz"):
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                tf.extractall(tmp)
        elif name.endswith(".tar.xz") or name.endswith(".txz"):
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as tf:
                tf.extractall(tmp)
        elif name.endswith(".gz"):
            out = tmp / name[:-3]
            with gzip.open(io.BytesIO(data)) as gz:
                out.write_bytes(gz.read())
        else:
            out = tmp / name
            out.write_bytes(data)

        for src_name, dst_name in wanted.items():
            for candidate in tmp.rglob(src_name):
                if candidate.is_file():
                    found[dst_name] = candidate.read_bytes()
                    break
        if not found:
            files = [p for p in tmp.rglob("*") if p.is_file()]
            if len(files) == 1:
                raw = files[0].read_bytes()
                for dst_name in set(wanted.values()):
                    found[dst_name] = raw
        return found


def install_binary(name, data):
    dest = ENGINES_DIR / name
    dest.write_bytes(data)
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def ensure_alias(alias, target):
    alias_path = ENGINES_DIR / alias
    target_path = ENGINES_DIR / target
    if alias_path.exists() or not target_path.exists():
        return
    try:
        alias_path.symlink_to(target)
    except Exception:
        shutil.copy2(target_path, alias_path)
        alias_path.chmod(alias_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def load_manifest():
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_manifest(manifest):
    manifest["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def bundle_archive(output):
    output = Path(output)
    with tarfile.open(output, "w:gz") as tf:
        for path in ["P00RIJA.py", "Dockerfile", "install.sh", "install-panel.sh", "install-node.sh", "Pooriya-tunnel.sh", "engines"]:
            p = Path(path)
            if p.exists():
                tf.add(p, arcname=p.name)
    print(f"Offline bundle written: {output}")


def fetch_engine(engine_id, spec, keep_archives=True):
    release = request_json(f"https://api.github.com/repos/{spec['repo']}/releases/latest")
    asset = match_asset(release.get("assets", []), spec["asset"])
    if not asset:
        raise RuntimeError(f"No matching linux/amd64 asset for {engine_id} in {spec['repo']}")
    print(f"[{engine_id}] {release.get('tag_name')} -> {asset['name']}")
    data = download(asset["browser_download_url"])
    extracted = extract_archive(asset["name"], data, spec["bins"])
    if not extracted:
        raise RuntimeError(f"No expected binary found in {asset['name']}")
    for dst, content in extracted.items():
        install_binary(dst, content)
    extra_results = []
    for extra in spec.get("extra_assets", []):
        extra_asset = match_asset(release.get("assets", []), extra["asset"])
        if not extra_asset:
            continue
        extra_data = download(extra_asset["browser_download_url"])
        extra_extracted = extract_archive(extra_asset["name"], extra_data, extra["bins"])
        for dst, content in extra_extracted.items():
            install_binary(dst, content)
        if keep_archives:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            (ARCHIVE_DIR / extra_asset["name"]).write_bytes(extra_data)
        extra_results.append({
            "asset": extra_asset["name"],
            "sha256": sha256(extra_data),
            "binaries": sorted(extra_extracted.keys())
        })
        extracted.update(extra_extracted)
    ensure_alias("singbox", "sing-box")
    ensure_alias("naiveproxy", "naive")
    if keep_archives:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        (ARCHIVE_DIR / asset["name"]).write_bytes(data)
    return {
        "repo": spec["repo"],
        "tag": release.get("tag_name"),
        "asset": asset["name"],
        "url": asset["browser_download_url"],
        "sha256": sha256(data),
        "binaries": sorted(extracted.keys()),
        "extra": extra_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Download all P00RIJA tunnel engines for offline installation.")
    parser.add_argument("--engine", action="append", choices=sorted(ENGINE_SPECS), help="Download only selected engine(s).")
    parser.add_argument("--no-archives", action="store_true", help="Do not keep original release archives under engines/archives.")
    parser.add_argument("--bundle", default="", help="Also create a complete offline tar.gz bundle.")
    args = parser.parse_args()

    ENGINES_DIR.mkdir(exist_ok=True)
    manifest = load_manifest()
    manifest.setdefault("engines", {})
    selected = args.engine or sorted(ENGINE_SPECS)
    failures = {}

    for engine_id in selected:
        try:
            manifest["engines"][engine_id] = fetch_engine(engine_id, ENGINE_SPECS[engine_id], keep_archives=not args.no_archives)
        except Exception as exc:
            failures[engine_id] = str(exc)
            print(f"[{engine_id}] ERROR: {exc}")

    manifest["failures"] = failures
    save_manifest(manifest)
    if args.bundle:
        bundle_archive(args.bundle)
    if failures:
        raise SystemExit(2)
    print("Done.")


if __name__ == "__main__":
    main()
