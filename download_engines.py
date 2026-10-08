#!/usr/bin/env python3
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

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
    "amneziawg": {
        "repo": "amnezia-vpn/amneziawg-tools",
        # amneziawg tools are userspace and cross-compatible across Ubuntu LTS releases.
        # Try newer Ubuntu assets first (24.04, then 22.04, then 20.04) so hosts running
        # Ubuntu 24/26 pick the closest build, while older hosts still find a match.
        "asset": ["ubuntu-24.04-amneziawg-tools.zip", "ubuntu-22.04-amneziawg-tools.zip", "ubuntu-20.04-amneziawg-tools.zip"],
        "bins": {"awg": "awg", "awg-quick": "awg-quick"},
        "go_repo": "amnezia-vpn/amneziawg-go",
        "go_branch": "master",
        "go_binary": "amneziawg-go",
    },
    "tuic": {
        "repo": "tuic-protocol/tuic",
        "components": [
            {
                "release_prefix": "tuic-server-",
                "asset": ["x86_64-unknown-linux-musl"],
                "binary": "tuic-server",
            },
            {
                "release_prefix": "tuic-client-",
                "asset": ["x86_64-unknown-linux-musl"],
                "binary": "tuic-client",
            },
        ],
    },
    "masque": {
        "repo": "ferneast/masque-tunnel",
        "asset": ["masque-tunnel-linux-amd64.tar.gz"],
        "bins": {"masque-tunnel-linux-amd64": "masque-tunnel"},
    },
    "phormal": {
        "repo": "Schmi7zz/Phormal",
        # Resolve the branch tip to a commit SHA once and download at that exact
        # revision, so the manifest records an immutable upstream version.
        "pin_commit_branch": "main",
        "raw_files": [
            {
                "url": "https://raw.githubusercontent.com/Schmi7zz/Phormal/main/phormal.sh",
                "binary": "phormal",
            }
        ],
    },
    "hedioum": {
        "repo": "hedioum/Hedioum-Pool-Tunnel",
        "asset": ["hedioum-tunnel"],
        "bins": {"hedioum-tunnel": "hedioum-tunnel"},
        "extra_assets": [
            {"asset": ["hedioum-tunnel-arm64"], "bins": {"hedioum-tunnel-arm64": "hedioum-tunnel-arm64"}}
        ],
    },
    "cloak": {
        "repo": "cbeuw/Cloak",
        "asset": ["ck-client-linux-amd64"],
        "bins": {"ck-client-linux-amd64": "ck-client"},
        "extra_assets": [
            {"asset": ["ck-server-linux-amd64"], "bins": {"ck-server-linux-amd64": "ck-server"}}
        ],
    },
}


_GITHUB_HOSTS = {
    "api.github.com",
    "github.com",
    "www.github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "raw.githubusercontent.com",
    "codeload.github.com",
}


def _assert_github_url(url):
    """Only GitHub-owned hosts are ever fetched by this tool."""
    parsed = urllib.parse.urlparse(str(url))
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise ValueError("Embedded credentials in URLs are not allowed")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL has no host")
    if host not in _GITHUB_HOSTS:
        raise ValueError(f"Refusing non-GitHub host: {host}")
    return url


def request_json(url):
    url = _assert_github_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode())


def download(url):
    url = _assert_github_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as res:
        return res.read()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def match_asset(assets, patterns):
    patterns = [p.lower() for p in patterns]
    # Two matching modes:
    #  - "candidate" mode: every pattern looks like a full asset filename (contains a file
    #    extension like .zip/.tar.gz/.gz). These are mutually-exclusive alternatives, so we
    #    return the FIRST pattern (in given priority order) that matches any asset. This is
    #    what lets amneziawg prefer ubuntu-24.04 then fall back to 22.04 / 20.04.
    #  - "token" mode (default): every pattern is a substring token, and ALL must be present
    #    in a single asset name (logical AND). Used by most engines.
    looks_like_filename = lambda p: any(p.endswith(ext) for ext in (".zip", ".tar.gz", ".tgz", ".gz", ".xz", ".txz"))
    if len(patterns) > 1 and all(looks_like_filename(p) for p in patterns):
        for candidate in patterns:
            for asset in assets:
                if candidate in asset["name"].lower():
                    return asset
        return None
    for asset in assets:
        name = asset["name"].lower()
        if all(pattern in name for pattern in patterns):
            return asset
    return None


def validate_member_path(name):
    # Reject absolute paths and any '..' path component (tar and zip members alike).
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts:
        raise RuntimeError(f"Refusing to extract unsafe archive path: {name!r}")


def safe_extract_tar(tf, dest):
    try:
        tf.extractall(dest, filter="data")
    except TypeError:
        # Python without the filter= argument (older interpreters): validate strictly
        # ourselves — relative paths only, no '..', no symlinks/hardlinks, no devices.
        for member in tf.getmembers():
            validate_member_path(member.name)
            if member.issym() or member.islnk() or member.isdev():
                raise RuntimeError(f"Refusing to extract unsafe archive member: {member.name!r}")
        tf.extractall(dest)


def safe_extract_zip(zf, dest):
    for info in zf.infolist():
        validate_member_path(info.filename)
    zf.extractall(dest)


def extract_archive(name, data, wanted):
    found = {}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        if name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                safe_extract_zip(zf, tmp)
        elif name.endswith(".tar.gz") or name.endswith(".tgz"):
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                safe_extract_tar(tf, tmp)
        elif name.endswith(".tar.xz") or name.endswith(".txz"):
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as tf:
                safe_extract_tar(tf, tmp)
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
    # Atomic write (temp file + os.replace) so a crash can never leave a truncated
    # or half-written manifest behind.
    tmp = str(MANIFEST_PATH) + ".tmp"
    if ".." in Path(tmp).parts:
        raise ValueError("Refusing manifest path with '..' components")
    tmp_fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, str(MANIFEST_PATH))


def bundle_archive(output):
    output = Path(output)
    with tarfile.open(output, "w:gz") as tf:
        bundle_paths = [
            "P00RIJA.py",
            "p00rija_core",
            "Dockerfile",
            ".dockerignore",
            "install.sh",
            "install-panel.sh",
            "install-node.sh",
            "installer-ui.sh",
            "Pooriya-tunnel.sh",
            "p00rija-control.sh",
            "restore-panel-backup.sh",
            "p00rija-host-agent.py",
            "download_engines.py",
            "README.md",
            "LICENSE",
            "assets",
            "fonts",
            "engines",
        ]
        for path in bundle_paths:
            p = Path(path)
            if p.exists():
                tf.add(p, arcname=p.name)
    print(f"Offline bundle written: {output}")


def fetch_engine(engine_id, spec, keep_archives=True):
    if spec.get("raw_files"):
        # Pin branch-based raw downloads to an immutable commit SHA: resolve the branch
        # tip once via the GitHub API, rewrite the URL to that revision, and record the
        # SHA in the manifest so it always describes an exact upstream version.
        pin_branch = spec.get("pin_commit_branch")
        commit_sha = ""
        if pin_branch:
            commit = request_json(f"https://api.github.com/repos/{spec['repo']}/commits/{pin_branch}")
            commit_sha = str(commit.get("sha") or "")
            if not re.fullmatch(r"[0-9a-f]{7,40}", commit_sha):
                raise RuntimeError(f"Could not resolve commit SHA for {spec['repo']}#{pin_branch}")
            print(f"[{engine_id}] pinned {pin_branch} -> {commit_sha[:12]}")
        installed = []
        raw_results = []
        for raw_file in spec["raw_files"]:
            url = raw_file["url"]
            if commit_sha and pin_branch:
                url = url.replace(f"/{pin_branch}/", f"/{commit_sha}/")
            binary = raw_file["binary"]
            print(f"[{engine_id}] raw -> {binary}")
            data = download(url)
            install_binary(binary, data)
            installed.append(binary)
            if keep_archives:
                ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                archive_name = raw_file.get("archive_name") or f"{binary}.raw"
                (ARCHIVE_DIR / archive_name).write_bytes(data)
            raw_results.append({
                "asset": raw_file.get("archive_name") or binary,
                "url": url,
                "sha256": sha256(data),
                "binary": binary,
            })
        return {
            "repo": spec["repo"],
            "tag": commit_sha or "main",
            "commit": commit_sha,
            "asset": " + ".join(item["asset"] for item in raw_results),
            "url": raw_results[0]["url"] if raw_results else "",
            "sha256": sha256("".join(item["sha256"] for item in raw_results).encode()),
            "binaries": installed,
            "raw_files": raw_results,
        }
    if spec.get("components"):
        releases = request_json(f"https://api.github.com/repos/{spec['repo']}/releases?per_page=30")
        installed = []
        component_results = []
        for component in spec["components"]:
            release = next(
                (item for item in releases if str(item.get("tag_name", "")).startswith(component["release_prefix"])),
                None,
            )
            if not release:
                raise RuntimeError(f"No release found for {component['release_prefix']}")
            asset = match_asset(release.get("assets", []), component["asset"])
            if not asset:
                raise RuntimeError(f"No linux/amd64 asset found for {component['binary']}")
            data = download(asset["browser_download_url"])
            install_binary(component["binary"], data)
            installed.append(component["binary"])
            if keep_archives:
                ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                (ARCHIVE_DIR / asset["name"]).write_bytes(data)
            component_results.append({
                "tag": release.get("tag_name"),
                "asset": asset["name"],
                "url": asset["browser_download_url"],
                "sha256": sha256(data),
                "binary": component["binary"],
            })
        return {
            "repo": spec["repo"],
            "tag": " + ".join(item["tag"] for item in component_results),
            "asset": " + ".join(item["asset"] for item in component_results),
            "url": component_results[0]["url"],
            "sha256": sha256("".join(item["sha256"] for item in component_results).encode()),
            "binaries": installed,
            "components": component_results,
        }
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
    source_result = None
    if engine_id == "amneziawg":
        source_name = "amneziawg-go-master.tar.gz"
        source_url = f"https://github.com/{spec['go_repo']}/archive/refs/heads/{spec.get('go_branch', 'master')}.tar.gz"
        source_data = download(source_url)
        if keep_archives:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            (ARCHIVE_DIR / source_name).write_bytes(source_data)
        source_result = {"asset": source_name, "sha256": sha256(source_data), "built": False}
        go_bin = shutil.which("go")
        if go_bin:
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                with tarfile.open(fileobj=io.BytesIO(source_data), mode="r:gz") as tf:
                    safe_extract_tar(tf, tmp)
                roots = [p for p in tmp.iterdir() if p.is_dir()]
                if roots:
                    env = os.environ.copy()
                    env.update({"GOOS": "linux", "GOARCH": "amd64", "CGO_ENABLED": "0"})
                    out = tmp / spec.get("go_binary", "amneziawg-go")
                    subprocess.run([go_bin, "build", "-o", str(out), "."], cwd=roots[0], env=env, check=True)
                    install_binary(spec.get("go_binary", "amneziawg-go"), out.read_bytes())
                    extracted[spec.get("go_binary", "amneziawg-go")] = out.read_bytes()
                    source_result["built"] = True
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
        "source": source_result,
    }


def main():
    global ENGINES_DIR, ARCHIVE_DIR, MANIFEST_PATH
    parser = argparse.ArgumentParser(description="Download all P00RIJA tunnel engines for offline installation.")
    parser.add_argument("--engine", action="append", choices=sorted(ENGINE_SPECS), help="Download only selected engine(s).")
    parser.add_argument("--no-archives", action="store_true", help="Do not keep original release archives under engines/archives.")
    parser.add_argument("--bundle", default="", help="Also create a complete offline tar.gz bundle.")
    parser.add_argument("--output-dir", default="engines", help="Directory where engine binaries and manifest are installed.")
    args = parser.parse_args()

    ENGINES_DIR = Path(args.output_dir).expanduser().resolve()
    ARCHIVE_DIR = ENGINES_DIR / "archives"
    MANIFEST_PATH = ENGINES_DIR / "manifest.json"
    ENGINES_DIR.mkdir(parents=True, exist_ok=True)
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
            # Drop this engine's stale entry: the download failed, so any binaries
            # left on disk are from an older run and the manifest must not claim
            # they are current.
            if manifest["engines"].pop(engine_id, None) is not None:
                print(f"[{engine_id}] Removed stale manifest entry (disk state for this engine may be outdated).")

    manifest["failures"] = failures
    save_manifest(manifest)
    if args.bundle:
        bundle_archive(args.bundle)
    if failures:
        raise SystemExit(2)
    print("Done.")


if __name__ == "__main__":
    main()
