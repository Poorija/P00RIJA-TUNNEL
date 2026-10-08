"""Smart protocol/tunnel recommendation engine.

Analyzes the server's network conditions (region, UDP availability, CDN reachability,
DPI severity) and recommends the best tunnel profile from the catalog, including the
newest 2025-2026 anti-DPI strategies (AnyTLS, XHTTP split, REALITY→Hysteria2 chains,
ShadowTLS-v3 wrapping Shadowsocks-2022).

Recommendations are based on proven field experience documented in the mid-2026
censorship landscape (Iran-grade ML-DPI, selective whitelisting).
"""

from __future__ import annotations

import ipaddress
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


USER_AGENT = "P00RIJA-TUNNEL-protocol-advisor"

# Tiered recommendation sets. Each entry maps a "threat scenario" to an ordered list
# of profile IDs, best-first. Profile IDs MUST match keys produced by
# tunnel_methods.default_tunnel_profiles() so the panel can auto-select them.
RECOMMENDATION_MATRIX: dict[str, dict[str, Any]] = {
    "max_stealth": {
        "label": "Maximum stealth (Iran-grade ML-DPI, active probing)",
        "rationale": (
            "Use a TLS-mimicking entry that defeats both passive ML-DPI and active probing. "
            "REALITY+XHTTP split is the 2026 consensus hardest-to-detect setup; ShadowTLS-v3 "
            "wrapping SS-2022 defeats active probing; AnyTLS looks like ordinary HTTPS."
        ),
        "profiles": [
            "singbox_xhttp_reality",
            "ultra_stealth_shadowtls_h2",
            "ultra_stealth_anytls_h2",
            "ultra_stealth_reality_h2",
            "muxquantum_anytls",
        ],
        "udp_ok": True,
        "cdn_ok": True,
    },
    "balanced_speed": {
        "label": "Balanced speed + stealth (UDP partially available)",
        "rationale": (
            "Cross the DPI frontier with REALITY/TLS, then hand off to a high-throughput "
            "QUIC leg (Hysteria2/TUIC) where UDP is unblocked. AmneziaWG or Shadowsocks-2022 "
            "serve well as inner encrypted hops."
        ),
        "profiles": [
            "ultra_stealth_hysteria2_salamander",
            "hysteria2_quic",
            "tuic_quic_web",
            "singbox_reality_vision",
            "naiveproxy_https",
        ],
        "udp_ok": True,
        "cdn_ok": False,
    },
    "cdn_fallback": {
        "label": "CDN-fronted fallback (direct IPs get blocked)",
        "rationale": (
            "When direct server IPs are blocked, route through Cloudflare/CDN. Only TCP/WS/XHTTP "
            "transports traverse a CDN — QUIC (Hysteria2/TUIC) cannot. XHTTP over CDN is the "
            "modern replacement for the legacy VLESS+WS+CDN chain."
        ),
        "profiles": [
            "singbox_xhttp_reality",
            "muxquantum_wss_web",
            "hard",
            "gost_ws_grpc",
            "rathole_wss",
        ],
        "udp_ok": False,
        "cdn_ok": True,
    },
    "high_concurrency": {
        "label": "Maximum concurrency (reverse-tunnel multiplexing)",
        "rationale": (
            "For panels serving many users, use a reverse-tunnel engine with strong mux: "
            "Backhaul TCP-mux or Rathole give the best stability at high connection counts; "
            "the shared_mux_pool builtin profile spreads users over resilient carriers."
        ),
        "profiles": [
            "resilient",
            "backhaul_tcpmux",
            "smart_hybrid_mux_bonding",
            "shared_mux_pool",
            "rathole_wss",
        ],
        "udp_ok": False,
        "cdn_ok": False,
    },
    "site_to_site": {
        "label": "Site-to-site / device VPN",
        "rationale": (
            "AmneziaWG (WireGuard + junk-packet injection) defeats naive WG DPI and is the "
            "fastest kernel-level encrypted transport for relay-to-relay hops."
        ),
        "profiles": [
            "amneziawg_kernel",
        ],
        "udp_ok": True,
        "cdn_ok": False,
    },
}


def _probe_udp_connectivity(host: str = "1.1.1.1", port: int = 443, timeout: float = 3.0) -> bool:
    """Real UDP reachability probe.

    A bare UDP connect() always succeeds locally (no handshake), so send a
    minimal DNS A query for example.com to two public resolvers and require
    an actual response datagram on either socket. Overall budget is capped
    at ~3 seconds; each resolver gets at most 1.5 seconds.
    """
    # Minimal DNS query: 12-byte header (RD=1, QDCOUNT=1) + QNAME "example.com"
    # + QTYPE=A (0x0001) + QCLASS=IN (0x0001).
    dns_query = (
        b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        b"\x07example\x03com\x00"
        b"\x00\x01\x00\x01"
    )
    deadline = time.monotonic() + min(timeout, 3.0)
    for resolver in ("8.8.8.8", "1.1.1.1"):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(min(1.5, remaining))
                sock.sendto(dns_query, (resolver, 53))
                if sock.recvfrom(512)[0]:
                    return True
        except OSError:
            continue
    return False


_PROBE_HOST_ALLOWLIST = {"www.cloudflare.com", "github.com", "api.github.com", "www.google.com", "www.gstatic.com"}


def _probe_https(host: str, timeout: float = 5.0) -> tuple[bool, int]:
    """Probe a fixed, allowlisted HTTPS host and return (reachable, latency_ms).

    SSRF guard: only allowlisted hosts, https scheme, and every resolved IP
    must be public (no loopback/private/link-local/metadata ranges).
    """
    if host not in _PROBE_HOST_ALLOWLIST:
        return False, -1
    url = f"https://{host}/"
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False, -1
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return False, -1
    probe_host = parsed.hostname or ""
    if not probe_host:
        return False, -1
    try:
        resolved = [ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(probe_host, None)]
    except (socket.gaierror, UnicodeError, ValueError, OSError):
        return False, -1
    for addr in resolved:
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            return False, -1
    start = int(time.monotonic() * 1000)
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as _:
            return True, max(0, int(time.monotonic() * 1000) - start)
    except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError):
        return False, -1


def detect_network_conditions(region: str = "global") -> dict[str, Any]:
    """Probe the server's live network conditions for recommendation input."""
    udp_ok = _probe_udp_connectivity()
    # Cloudflare QUIC edge is a good proxy for "is the global UDP/QUIC path open".
    cdn_reachable, cdn_latency = _probe_https("www.cloudflare.com")
    github_reachable, _ = _probe_https("github.com")
    return {
        "region": region,
        "udp_outbound_ok": udp_ok,
        "cdn_reachable": cdn_reachable,
        "cdn_latency_ms": cdn_latency if cdn_reachable else None,
        "github_reachable": github_reachable,
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def recommend_profiles(
    region: str = "global",
    scenario: str | None = None,
    *,
    udp_ok: bool | None = None,
    cdn_reachable: bool | None = None,
    live_probe: bool = True,
) -> dict[str, Any]:
    """Return a recommendation report with the best profile IDs for the current scenario.

    If scenario is None, it is auto-selected from live conditions.
    """
    conditions: dict[str, Any] = {}
    if live_probe:
        try:
            conditions = detect_network_conditions(region)
        except Exception:
            conditions = {"region": region}
    # Caller overrides take precedence over probed values.
    if udp_ok is not None:
        conditions["udp_outbound_ok"] = udp_ok
    if cdn_reachable is not None:
        conditions["cdn_reachable"] = cdn_reachable

    # Auto-select scenario if not provided.
    if scenario is None:
        if region == "ir":
            scenario = "max_stealth"
        elif conditions.get("udp_outbound_ok"):
            scenario = "balanced_speed"
        elif conditions.get("cdn_reachable"):
            scenario = "cdn_fallback"
        else:
            scenario = "high_concurrency"

    matrix = RECOMMENDATION_MATRIX.get(scenario, RECOMMENDATION_MATRIX["max_stealth"])
    return {
        "success": True,
        "scenario": scenario,
        "scenario_label": matrix["label"],
        "rationale": matrix["rationale"],
        "recommended_profiles": matrix["profiles"],
        "conditions": conditions,
        "all_scenarios": {key: {"label": val["label"], "profiles": val["profiles"]} for key, val in RECOMMENDATION_MATRIX.items()},
        "advised_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
