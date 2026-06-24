"""Low-overhead host and process metrics for P00RIJA TUNNEL."""

from __future__ import annotations

import os
import resource
import subprocess
import sys
import time


class NetSpeedometer:
    def __init__(self):
        self.last_rx = 0
        self.last_tx = 0
        self.last_time = time.time()
        self.last_rx, self.last_tx = self.get_bytes()

    def get_bytes(self):
        rx, tx = 0, 0
        try:
            with open("/proc/net/dev", "r") as f:
                lines = f.readlines()
            for line in lines[2:]:
                parts = line.split()
                if len(parts) >= 10:
                    if "lo" in parts[0] or "docker" in parts[0] or "veth" in parts[0]:
                        continue
                    rx += int(parts[1])
                    tx += int(parts[9])
        except Exception:
            pass
        return rx, tx

    def sample(self):
        now = time.time()
        rx, tx = self.get_bytes()
        dt = now - self.last_time
        if dt <= 0:
            return 0, 0
        rx_speed = (rx - self.last_rx) / dt
        tx_speed = (tx - self.last_tx) / dt
        if rx_speed < 0: rx_speed = 0
        if tx_speed < 0: tx_speed = 0
        self.last_rx = rx
        self.last_tx = tx
        self.last_time = now
        return rx_speed, tx_speed

def get_cpu_percent():
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        parts = [int(x) for x in line.split()[1:5]]
        total = sum(parts)
        idle = parts[3]
        return total, idle
    except Exception:
        return 0, 0

def get_host_info():
    info = {
        "cpu_cores": os.cpu_count() or 1,
        "load_avg": [],
        "uptime_seconds": 0,
        "ram_total_gb": 0,
        "ram_free_gb": 0,
        "swap_total_gb": 0,
        "swap_free_gb": 0,
        "disk_total_gb": 0,
        "disk_free_gb": 0,
        "panel_pid": os.getpid(),
        "panel_rss_mb": 0,
        "docker": {
            "available": False,
            "containers_running": 0,
            "containers_total": 0,
            "images": 0,
            "version": ""
        }
    }
    try:
        info["load_avg"] = [round(x, 2) for x in os.getloadavg()]
    except Exception:
        pass
    try:
        with open("/proc/uptime", "r") as f:
            info["uptime_seconds"] = int(float(f.read().split()[0]))
    except Exception:
        pass
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("MemTotal:"):
                    info["ram_total_gb"] = round(int(line.split()[1]) / (1024 * 1024), 2)
                elif line.startswith("MemAvailable:"):
                    info["ram_free_gb"] = round(int(line.split()[1]) / (1024 * 1024), 2)
                elif line.startswith("SwapTotal:"):
                    info["swap_total_gb"] = round(int(line.split()[1]) / (1024 * 1024), 2)
                elif line.startswith("SwapFree:"):
                    info["swap_free_gb"] = round(int(line.split()[1]) / (1024 * 1024), 2)
    except:
        pass
    try:
        st = os.statvfs("/")
        info["disk_total_gb"] = round((st.f_blocks * st.f_frsize) / (1024**3), 2)
        info["disk_free_gb"] = round((st.f_bavail * st.f_frsize) / (1024**3), 2)
    except:
        pass
    try:
        info["panel_rss_mb"] = round(get_own_rss_kb() / 1024, 1)
    except Exception:
        pass
    try:
        if os.path.exists("/var/run/docker.sock") or subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True, timeout=2).returncode == 0:
            info["docker"]["available"] = True
            ver = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True, timeout=2)
            if ver.returncode == 0:
                info["docker"]["version"] = ver.stdout.strip()
            ps = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=2)
            if ps.returncode == 0:
                info["docker"]["containers_running"] = len([x for x in ps.stdout.splitlines() if x.strip()])
            psa = subprocess.run(["docker", "ps", "-aq"], capture_output=True, text=True, timeout=2)
            if psa.returncode == 0:
                info["docker"]["containers_total"] = len([x for x in psa.stdout.splitlines() if x.strip()])
            imgs = subprocess.run(["docker", "images", "-q"], capture_output=True, text=True, timeout=2)
            if imgs.returncode == 0:
                info["docker"]["images"] = len(set(x.strip() for x in imgs.stdout.splitlines() if x.strip()))
    except Exception:
        pass
    return info

def get_ram_percent():
    try:
        mem = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mem[parts[0].rstrip(":")] = int(parts[1])
        total = mem.get("MemTotal", 0)
        free = mem.get("MemFree", 0)
        buffers = mem.get("Buffers", 0)
        cached = mem.get("Cached", 0)
        used = total - free - buffers - cached
        return (used / total) * 100 if total > 0 else 0
    except Exception:
        return 0.0

def get_own_rss_kb():
    try:
        with open(f"/proc/{os.getpid()}/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except Exception:
        pass
    try:
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            rss = rss / 1024
        return int(rss)
    except Exception:
        return 0

