"""Embedded panel UI and browser-facing static assets for P00RIJA TUNNEL."""

from __future__ import annotations

import json

PANEL_PAGE_ROUTES = (
    "/",
    "/index.html",
    "/login",
    "/nodes",
    "/links",
    "/speedtest",
    "/logs",
    "/settings",
    "/monitor",
    "/appearance",
    "/help",
    "/about",
)


def build_manifest(start_url: str = "/") -> bytes:
    return json.dumps({
        "name": "P00RIJA TUNNEL Panel",
        "short_name": "P00RIJA",
        "start_url": start_url or "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#07100f",
        "theme_color": "#20c7b5",
        "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}],
    }).encode("utf-8")


def service_worker_script() -> bytes:
    return (
        "self.addEventListener('install',e=>self.skipWaiting());\n"
        "self.addEventListener('activate',e=>e.waitUntil((async()=>{if(self.caches){const keys=await caches.keys();await Promise.all(keys.map(k=>caches.delete(k)));}await self.registration.unregister();await self.clients.claim();})()));\n"
    ).encode("utf-8")


def font_content_type(path: str) -> str:
    if path.endswith(".woff2"):
        return "font/woff2"
    if path.endswith(".woff"):
        return "font/woff"
    if path.endswith(".ttf"):
        return "font/ttf"
    return "application/octet-stream"


APP_LOGO_SVG = """<svg id="Layer_1" xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 256 256">
  <defs>
    <style>
      .st0, .st1 {
        stroke: #3a86ff;
      }

      .st0, .st1, .st2, .st3, .st4 {
        stroke-linecap: round;
        stroke-linejoin: round;
      }

      .st0, .st4 {
        fill: #fff;
        stroke-width: 4px;
      }

      .st1, .st2 {
        stroke-width: 16px;
      }

      .st1, .st2, .st3 {
        fill: none;
      }

      .st2, .st4 {
        stroke: #00ebff;
      }

      .st3 {
        stroke: #7000ff;
        stroke-dasharray: 4 6;
        stroke-width: 3px;
      }

      .st5 {
        fill: #0b132b;
      }
    </style>
  </defs>
  <rect class="st5" width="256" height="256" rx="40.96" ry="40.96"/>
  <path class="st2" d="M51.2,102.4h153.6M204.8,102.4l-25.6-25.6M204.8,102.4l-25.6,25.6"/>
  <path class="st1" d="M204.8,153.6H51.2M51.2,153.6l25.6-25.6M51.2,153.6l25.6,25.6"/>
  <line class="st3" x1="128" y1="39.21" x2="128" y2="216.79"/>
  <circle class="st0" cx="128" cy="102.4" r="12.8"/>
  <circle class="st4" cx="128" cy="153.6" r="12.8"/>
</svg>"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پنل مدیریت P00RIJA TUNNEL</title>
    <meta name="theme-color" content="#20c7b5">
    <link rel="manifest" href="/manifest.webmanifest">
    <style>
        @font-face { font-family: 'Vazirmatn'; src: url('/fonts/vazirmatn.woff2') format('woff2'); font-weight: normal; font-style: normal; font-display: swap; }
        @font-face { font-family: 'Shabnam'; src: url('/fonts/shabnam.woff2') format('woff2'); font-weight: normal; font-style: normal; font-display: swap; }
        @font-face { font-family: 'Sahel'; src: url('/fonts/sahel.woff2') format('woff2'); font-weight: normal; font-style: normal; font-display: swap; }
        @font-face { font-family: 'Inter'; src: url('/fonts/inter.woff2') format('woff2'); font-weight: normal; font-style: normal; font-display: swap; }
        @font-face { font-family: 'BYekan'; src: url('/fonts/BYekan.ttf') format('truetype'); font-weight: normal; font-style: normal; font-display: swap; }
        :root {
            --bg-main: #07100f;
            --bg-panel: #0c1716;
            --bg-card: rgba(13, 24, 23, 0.82);
            --border-card: rgba(148, 163, 184, 0.18);
            --accent-blue: #20c7b5;
            --accent-purple: #7c5cff;
            --text-primary: #f8fafc;
            --text-secondary: #9fb1bd;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --font-family: Vazirmatn, Tahoma, "Segoe UI", Arial, sans-serif;
            --select-bg: #0c1716;
            --select-fg: #f8fafc;
            --dropdown-bg: #0b1716;
            color-scheme: dark;
        }

        body.theme-light {
            --bg-main: #eef7f4;
            --bg-panel: #ffffff;
            --bg-card: rgba(255, 255, 255, 0.92);
            --border-card: rgba(15, 23, 42, 0.14);
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --accent-blue: #0f9f8f;
            --accent-purple: #4f46e5;
            --select-bg: #ffffff;
            --select-fg: #0f172a;
            --dropdown-bg: #ffffff;
            color-scheme: light;
        }

        body.theme-cyberpunk {
            --bg-main: #08060f;
            --bg-panel: #120820;
            --bg-card: rgba(22, 11, 36, 0.88);
            --border-card: rgba(255, 0, 153, 0.28);
            --accent-blue: #00e5ff;
            --accent-purple: #ff2bd6;
            --text-secondary: #d5b8ff;
            --select-bg: #120820;
            --select-fg: #f8fafc;
            --dropdown-bg: #160a25;
        }

        body.theme-forest {
            --bg-main: #07130d;
            --bg-panel: #0d2015;
            --bg-card: rgba(14, 38, 24, 0.88);
            --border-card: rgba(134, 239, 172, 0.22);
            --accent-blue: #34d399;
            --accent-purple: #84cc16;
            --text-secondary: #b9d6c5;
            --select-bg: #0d2015;
            --select-fg: #f8fafc;
            --dropdown-bg: #102719;
        }

        body.theme-ocean {
            --bg-main: #06111d;
            --bg-panel: #071827;
            --bg-card: rgba(10, 31, 48, 0.88);
            --border-card: rgba(56, 189, 248, 0.24);
                    --accent-blue: #38bdf8;
            --accent-purple: #22d3ee;
            --text-secondary: #b7d4e8;
            --select-bg: #071827;
            --select-fg: #f8fafc;
            --dropdown-bg: #081d2e;
        }

        body.font-vazirmatn { --font-family: Vazirmatn, Tahoma, "Segoe UI", Arial, sans-serif; }
        body.font-sahel { --font-family: Sahel, Tahoma, "Segoe UI", Arial, sans-serif; }
        body.font-shabnam { --font-family: Shabnam, Tahoma, "Segoe UI", Arial, sans-serif; }
        body.font-inter { --font-family: Inter, "Segoe UI", Arial, sans-serif; }
        body.font-byekan { --font-family: BYekan, "B Yekan", Tahoma, sans-serif; }
        body.font-system { --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: var(--font-family, inherit);
        }

        body {
            background:
                linear-gradient(145deg, rgba(32, 199, 181, 0.09), transparent 36%),
                linear-gradient(315deg, rgba(124, 92, 255, 0.08), transparent 40%),
                var(--bg-main);
            color: var(--text-primary);
            font-family: var(--font-family);
            min-height: 100vh;
            display: flex;
            overflow-x: hidden;
            font-feature-settings: "kern" 1;
        }

        .ambient-glow {
            display: none;
        }
        #glow-1 { top: -100px; left: -100px; }
        #glow-2 { bottom: -150px; right: -150px; }

        #login-screen {
            position: fixed;
            inset: 0;
            background-color: var(--bg-main);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }

        .login-card {
            width: 100%;
            max-width: 400px;
            padding: 40px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 8px;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.34);
            text-align: center;
            animation: panelEnter 0.45s ease both;
        }

        .login-logo {
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            margin-bottom: 30px;
        }

        .brand-logo {
            width: 74px;
            height: 74px;
            filter: drop-shadow(0 14px 28px rgba(32, 199, 181, 0.22));
            animation: logoPulse 3.6s ease-in-out infinite;
        }

        .brand-logo.small {
            width: 42px;
            height: 42px;
            animation-duration: 4.8s;
        }

        .brand-logo.tiny {
            width: 28px;
            height: 28px;
            animation-duration: 5.2s;
        }

        .logo-wordmark {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 0;
        }

        .form-group {
            margin-bottom: 20px;
            text-align: right;
        }

        .form-group label {
            display: block;
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }

        .form-input {
            width: 100%;
            padding: 12px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 16px;
            font-family: var(--font-family);
            transition: all 0.3s ease;
            text-align: left;
        }

        .form-input:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.15);
            background: rgba(255, 255, 255, 0.05);
        }

        .btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 20px rgba(0, 240, 255, 0.2);
        }

        .btn:active {
            transform: translateY(0) scale(0.99);
        }

        aside {
            width: 260px;
            background: var(--bg-panel);
            border-left: 1px solid var(--border-card);
            display: flex;
            flex-direction: column;
            padding: 30px 20px;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 40px;
            text-align: center;
        }

        .brand span {
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 14px 20px;
            border-radius: 8px;
            color: var(--text-secondary);
            text-decoration: none;
            font-weight: 500;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .nav-item:hover, .nav-item.active {
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-card);
            transform: translateX(-2px);
        }

        .nav-item.active {
            border-right: 4px solid var(--accent-blue);
            background: rgba(0, 240, 255, 0.03);
        }

        .nav-item i {
            width: 20px;
            height: 20px;
        }

        main {
            flex-grow: 1;
            padding: 32px;
            max-width: 1400px;
            margin: 0 auto;
            width: calc(100% - 260px);
            overflow-y: auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
        }

        .page-title h1 {
            font-size: 28px;
            font-weight: 600;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }

        .toolbar-select {
            width: auto;
            min-width: 130px;
            padding: 9px 12px;
            font-size: 13px;
            background: var(--select-bg);
        }

        select, option, button, input, textarea {
            font-family: var(--font-family);
            color: var(--text-primary);
        }

        select.form-input {
            appearance: none;
            -webkit-appearance: none;
            background-color: var(--select-bg) !important;
            color: var(--select-fg) !important;
            border-color: var(--border-card);
            background-image:
                linear-gradient(45deg, transparent 50%, var(--text-secondary) 50%),
                linear-gradient(135deg, var(--text-secondary) 50%, transparent 50%);
            background-position:
                calc(100% - 18px) calc(50% - 3px),
                calc(100% - 13px) calc(50% - 3px);
            background-size: 5px 5px, 5px 5px;
            background-repeat: no-repeat;
            padding-right: 34px;
        }

        html[dir="rtl"] select.form-input {
            background-position:
                18px calc(50% - 3px),
                23px calc(50% - 3px);
            padding-right: 16px;
            padding-left: 34px;
        }

        select option {
            background-color: var(--select-bg) !important;
            color: var(--select-fg) !important;
        }

        .mobile-menu-btn {
            display: none;
            width: auto;
            padding: 10px 12px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 8px;
            color: var(--text-primary);
        }

        .status-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-card);
            padding: 8px 16px;
            border-radius: 50px;
            font-size: 14px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--success);
            box-shadow: 0 0 10px var(--success);
            animation: statusPulse 1.9s ease-in-out infinite;
            flex: 0 0 auto;
        }

        .status-dot.offline {
            background-color: var(--danger);
            box-shadow: 0 0 10px var(--danger);
            animation-duration: 2.8s;
        }

        .status-dot.warning {
            background-color: var(--warning);
            box-shadow: 0 0 10px var(--warning);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 24px;
            margin-bottom: 30px;
        }

        .glass-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
            animation: panelEnter 0.42s ease both;
        }

        .glass-card:hover {
            border-color: rgba(0, 240, 255, 0.15);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }

        .stat-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .stat-info h3 {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 400;
            margin-bottom: 6px;
        }

        .stat-info p {
            font-size: 26px;
            font-weight: 700;
        }

        #stat-net-speed {
            white-space: nowrap;
            font-size: clamp(16px, 1.6vw, 24px);
            letter-spacing: 0;
        }

        .stat-icon {
            width: 48px;
            height: 48px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.03);
            display: flex;
            justify-content: center;
            align-items: center;
            color: var(--accent-blue);
        }

        .charts-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 30px;
        }

        .table-wrap {
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            overscroll-behavior-inline: contain;
            scrollbar-gutter: stable;
        }

        .link-actions {
            flex-wrap: wrap;
            justify-content: flex-end;
        }

        .btn-purple {
            background: #8b5cf6 !important;
            color: #fff !important;
            box-shadow: 0 0 12px rgba(139, 92, 246, 0.34);
        }

        .btn-cyan {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple)) !important;
            color: #fff !important;
            box-shadow: 0 0 12px rgba(0, 240, 255, 0.22);
        }

        .btn-smart {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple)) !important;
            color: #fff !important;
            border: 1px solid color-mix(in srgb, var(--accent-blue) 55%, var(--border-card));
            box-shadow: 0 10px 22px rgba(0, 0, 0, 0.14), 0 0 14px color-mix(in srgb, var(--accent-blue) 28%, transparent);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-smart:hover {
            border-color: var(--accent-blue);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.18), 0 0 0 3px color-mix(in srgb, var(--accent-blue) 16%, transparent);
        }

        .ssh-terminal {
            background: #050b0f;
            color: #d1fae5;
            border: 1px solid rgba(6, 182, 212, 0.35);
            border-radius: 8px;
            min-height: 360px;
            max-height: 52vh;
            overflow: auto;
            padding: 14px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
            font-size: 13px;
            line-height: 1.45;
            direction: ltr;
            text-align: left;
            white-space: pre-wrap;
            outline: none;
        }

        .ssh-terminal:focus {
            border-color: #06b6d4;
            box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.16);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: right;
            margin-top: 15px;
            min-width: 800px;
            table-layout: auto;
        }
        #table-nodes {
            min-width: 1800px;
            white-space: nowrap;
        }

        #table-nodes th,
        #table-nodes td {
            white-space: nowrap;
            vertical-align: middle;
        }

        #table-nodes .node-name-line,
        #table-nodes .node-actions-line {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            flex-wrap: nowrap;
        }

        #table-nodes .tag-row {
            display: inline-flex;
            flex-wrap: nowrap;
            margin-top: 0;
            vertical-align: middle;
        }

        #table-nodes .tag-pill {
            overflow-wrap: normal;
            white-space: nowrap;
        }

        th, td {
            padding: 16px;
            border-bottom: 1px solid var(--border-card);
        }

        th {
            font-weight: 500;
            color: var(--text-secondary);
            font-size: 14px;
        }

        td {
            font-size: 15px;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.01);
        }

        .modal {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(5px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            padding: max(12px, env(safe-area-inset-top)) max(12px, env(safe-area-inset-right)) max(12px, env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left));
        }

        .modal-content {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            width: 90%;
            max-width: 500px;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
            animation: modalIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            max-height: 90vh;
            max-height: 90dvh;
            overflow-y: auto;
            overscroll-behavior: contain;
        }

        @keyframes modalIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }

        .modal-header h2 {
            font-size: 20px;
            font-weight: 600;
        }

        .modal-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
        }

        .hidden { display: none !important; }
        .text-success { color: var(--success) !important; }
        .text-danger { color: var(--danger) !important; }
        .text-warning { color: var(--warning) !important; }
        .flex-between { display: flex; justify-content: space-between; align-items: center; }
        .gap-10 { gap: 10px; }
        .mt-20 { margin-top: 20px; }
        .mb-20 { margin-bottom: 20px; }
        .w-auto { width: auto !important; }
        .p-10 { padding: 10px; }

        .tag-pill {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-card);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            display: inline-block;
            color: var(--text-primary);
            text-decoration: none;
            overflow-wrap: anywhere;
        }

        .tag-color-0 { background: rgba(32, 199, 181, 0.14); border-color: rgba(32, 199, 181, 0.42); }
        .tag-color-1 { background: rgba(124, 92, 255, 0.14); border-color: rgba(124, 92, 255, 0.42); }
        .tag-color-2 { background: rgba(245, 158, 11, 0.14); border-color: rgba(245, 158, 11, 0.42); }
        .tag-color-3 { background: rgba(16, 185, 129, 0.14); border-color: rgba(16, 185, 129, 0.42); }
        .tag-color-4 { background: rgba(239, 68, 68, 0.14); border-color: rgba(239, 68, 68, 0.42); }
        .tag-color-5 { background: rgba(59, 130, 246, 0.14); border-color: rgba(59, 130, 246, 0.42); }
        .tag-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
        .rating-chip-good { background: rgba(16, 185, 129, 0.18); border-color: rgba(16, 185, 129, 0.52); color: var(--text-primary); }
        .rating-chip-normal { background: rgba(245, 158, 11, 0.18); border-color: rgba(245, 158, 11, 0.58); color: var(--text-primary); }
        .rating-chip-poor { background: rgba(239, 68, 68, 0.18); border-color: rgba(239, 68, 68, 0.58); color: var(--text-primary); }
        .rating-icons { display: inline-flex; align-items: center; gap: 6px; flex-wrap: nowrap; }
        .rating-icon {
            width: 30px;
            height: 30px;
            border-radius: 8px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 1px solid currentColor;
            background: rgba(255, 255, 255, 0.04);
            color: var(--warning);
        }
        .rating-icon svg { width: 16px; height: 16px; }
        .rating-icon.good { color: var(--success); background: rgba(16, 185, 129, 0.14); }
        .rating-icon.normal { color: var(--warning); background: rgba(245, 158, 11, 0.14); }
        .rating-icon.poor { color: var(--danger); background: rgba(239, 68, 68, 0.14); }
        .profile-catalog-grid { display: grid; gap: 10px; margin-top: 14px; }
        .profile-catalog-group { border: 1px solid var(--border-card); border-radius: 8px; background: rgba(255,255,255,0.025); overflow: hidden; }
        .profile-catalog-group summary { cursor: pointer; list-style: none; padding: 12px; }
        .profile-catalog-group summary::-webkit-details-marker { display: none; }
        .profile-catalog-group-body { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; padding: 0 12px 12px; }
        .profile-card-mini { border: 1px solid var(--border-card); border-radius: 8px; padding: 12px; background: rgba(255,255,255,0.03); display: grid; gap: 8px; cursor: pointer; transition: transform .18s ease, border-color .18s ease, background .18s ease; }
        .profile-card-mini:hover { transform: translateY(-2px); border-color: var(--accent-blue); background: rgba(76, 201, 240, 0.08); }
        .profile-builder-panel { margin-top: 30px; padding-top: 22px; border-top: 1px solid var(--border-card); display: grid; gap: 16px; }
        .profile-builder-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
        .profile-builder-head p { color: var(--text-secondary); line-height: 1.75; margin-top: 6px; max-width: 820px; }
        .profile-builder-grid { align-items: start; }
        .field-hint { display: block; margin-top: 6px; color: var(--text-secondary); font-size: 12px; line-height: 1.7; }
        .profile-native-select { display: none; }
        .profile-picker { position: relative; }
        .profile-picker-button { width: 100%; min-height: 56px; text-align: start; display: flex; justify-content: space-between; align-items: center; gap: 12px; border: 1px solid var(--border-card); background: var(--bg-input); color: var(--text-primary); border-radius: 8px; padding: 10px 12px; cursor: pointer; font-family: inherit; }
        .profile-picker-button:hover { border-color: var(--accent-blue); box-shadow: 0 0 0 3px rgba(76, 201, 240, 0.12); }
        .profile-picker-selected { display: grid; gap: 6px; min-width: 0; }
        .profile-picker-selected strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .profile-picker-selected small { color: var(--text-secondary); }
        .profile-picker-menu { position: absolute; inset-inline: 0; top: calc(100% + 8px); z-index: 3000; max-height: min(58vh, 560px); overflow: auto; background: var(--dropdown-bg); color: var(--text-primary); border: 1px solid var(--border-card); border-radius: 8px; box-shadow: 0 24px 70px rgba(0,0,0,.38); padding: 8px; }
        .profile-picker-category { padding: 8px 10px 6px; color: var(--text-secondary); font-size: 12px; font-weight: 700; }
        .profile-picker-option { width: 100%; border: 1px solid transparent; background: transparent; color: var(--text-primary); border-radius: 8px; padding: 10px; display: grid; gap: 8px; text-align: start; cursor: pointer; font-family: inherit; }
        .profile-picker-option:hover, .profile-picker-option.active { background: rgba(76, 201, 240, 0.10); border-color: rgba(76, 201, 240, 0.42); }
        .profile-picker-option-title { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
        .profile-picker-option-title small { white-space: nowrap; color: var(--text-secondary); }
        .direction-example-card { margin-top: 10px; border: 1px solid var(--border-card); background: rgba(255,255,255,0.03); border-radius: 8px; padding: 12px; display: grid; gap: 10px; }
        .direction-example-flow { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; gap: 10px; }
        .direction-example-node { border: 1px solid var(--border-card); background: var(--bg-card); border-radius: 8px; padding: 10px; min-width: 0; }
        .direction-example-node strong, .direction-example-node small { display: block; overflow-wrap: anywhere; }
        .direction-example-arrow { color: var(--accent-blue); font-weight: 800; white-space: nowrap; }
        .direction-example-note { color: var(--text-secondary); line-height: 1.75; }
        .flow-diagram { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 10px; padding: 12px; border: 1px solid var(--border-card); border-radius: 8px; background: rgba(255,255,255,0.03); }
        .flow-node { border: 1px solid var(--border-card); border-radius: 8px; padding: 10px; text-align: center; background: var(--bg-card); }
        .flow-arrow { color: var(--accent-blue); font-weight: 800; }
        .link-category summary { cursor: pointer; list-style: none; }
        .link-category summary::-webkit-details-marker { display: none; }
        .link-category-chart-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; align-items: stretch; }
        .category-metrics { display: grid; grid-template-columns: repeat(2, minmax(120px, 1fr)); gap: 10px; margin: 12px 0; }
        .category-metric { border: 1px solid var(--border-card); border-radius: 8px; padding: 10px; background: rgba(255,255,255,0.03); }
        .category-metric span { display: block; color: var(--text-secondary); font-size: 12px; margin-bottom: 4px; }
        .category-metric strong { display: block; white-space: nowrap; font-size: clamp(13px, 1.4vw, 18px); line-height: 1.25; letter-spacing: 0; }
        .category-metric.active { border-color: rgba(16,185,129,0.42); }
        .category-metric.download { border-color: rgba(59,130,246,0.42); }
        .category-metric.upload { border-color: rgba(124,92,255,0.42); }
        .category-metric.active strong { color: #10b981; }
        .category-metric.download strong { color: #3b82f6; }
        .category-metric.upload strong { color: #7c5cff; }
        .category-chart-frame { height: 180px; min-height: 180px; overflow: hidden; }

        #tab-about a.tag-pill {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.12);
        }




        .settings-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
        }

        #tab-settings .settings-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            align-items: start;
        }

        #tab-settings .settings-wide {
            grid-column: 1 / -1;
        }

        #engine-manager-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .compact-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
        }

        .help-list {
            display: grid;
            gap: 12px;
            color: var(--text-secondary);
            line-height: 1.8;
        }

        .node-role {
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .mini-metric {
            display: grid;
            gap: 6px;
            min-width: 150px;
        }

        .metric-bar {
            height: 7px;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
        }

        .metric-bar span {
            display: block;
            height: 100%;
            width: 0%;
            max-width: 100%;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
            transition: width 0.45s ease;
        }

        .resource-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .tunnel-guardian-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
        }

        .tunnel-guardian-card {
            border: 1px solid var(--border-card);
            border-radius: 8px;
            background: rgba(255,255,255,0.03);
            padding: 14px;
            display: grid;
            gap: 10px;
        }

        .tunnel-guardian-card h4 {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            font-size: 15px;
        }

        .tunnel-guardian-status {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            min-width: 58px;
            white-space: nowrap;
            overflow-wrap: normal;
            word-break: keep-all;
            text-align: center;
            flex: 0 0 auto;
        }

        .guardian-action-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }

        .guardian-result {
            min-height: 20px;
            color: var(--text-secondary);
            font-size: 12px;
            line-height: 1.6;
        }

        .ops-intel-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 14px;
        }

        .ops-intel-card {
            border: 1px solid var(--border-card);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.035);
            padding: 12px;
            display: grid;
            gap: 8px;
            min-height: 104px;
        }

        .ops-intel-card strong {
            font-size: 22px;
            line-height: 1.2;
        }

        .ops-recommendation-row,
        .ops-radar-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
        }

        .ops-radar-row .tag-pill,
        .ops-recommendation-row .tag-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            overflow-wrap: normal;
            white-space: nowrap;
        }

        .mini-icon-btn {
            width: 24px;
            height: 24px;
            border-radius: 6px;
            border: 1px solid var(--border-card);
            background: color-mix(in srgb, var(--accent-blue) 18%, transparent);
            color: var(--text-primary);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            padding: 0;
        }

        .mini-icon-btn svg {
            width: 14px;
            height: 14px;
        }

        .order-control {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 5px;
            border: 1px solid color-mix(in srgb, var(--accent-blue) 45%, var(--border-card));
            border-radius: 12px;
            background: linear-gradient(145deg, rgba(0, 240, 255, 0.12), rgba(124, 92, 255, 0.08));
            box-shadow: inset 0 1px 0 rgba(255,255,255,.07), 0 6px 18px rgba(0,0,0,.12);
            flex: 0 0 auto;
        }

        .order-control.vertical {
            flex-direction: column;
        }

        .order-button {
            width: 31px;
            height: 31px;
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 9px;
            background: rgba(4, 18, 30, .72);
            color: var(--text-primary);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: transform .16s ease, border-color .16s ease, background .16s ease;
        }

        .order-button:hover:not(:disabled) {
            transform: translateY(-1px);
            border-color: var(--accent-blue);
            background: color-mix(in srgb, var(--accent-blue) 22%, rgba(4,18,30,.8));
        }

        .order-button:disabled { opacity: .28; cursor: not-allowed; }
        .order-button svg { width: 17px; height: 17px; }
        .order-cell { width: 88px; min-width: 88px; }
        .link-card-head { display: flex; align-items: flex-start; gap: 12px; }
        .link-card-main { flex: 1 1 auto; min-width: 0; }

        .smart-test-panel {
            display: grid;
            gap: 12px;
            width: 100%;
            padding: 14px;
            border: 1px solid var(--border-card);
            border-radius: 12px;
            background: rgba(255,255,255,.025);
        }

        .smart-test-summary,
        .smart-profile-grid,
        .speed-summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 10px;
        }

        .smart-metric,
        .speed-metric {
            display: grid;
            gap: 5px;
            padding: 11px;
            border-radius: 10px;
            border: 1px solid var(--border-card);
            background: rgba(255,255,255,.035);
        }

        .smart-metric span,
        .speed-metric span { color: var(--text-secondary); font-size: 12px; }
        .smart-metric strong,
        .speed-metric strong { font-size: 17px; overflow-wrap: anywhere; }
        .smart-profile-card { border: 1px solid var(--border-card); border-radius: 10px; padding: 11px; display: grid; gap: 7px; }
        .smart-profile-card.is-selected { border-color: var(--accent-blue); background: color-mix(in srgb, var(--accent-blue) 10%, transparent); }
        .smart-profile-score { display: flex; gap: 7px; flex-wrap: wrap; color: var(--text-secondary); font-size: 12px; }

        .speed-config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 12px;
        }

        .speed-node-picker {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 8px;
            max-height: 240px;
            overflow: auto;
            padding: 10px;
            border: 1px solid var(--border-card);
            border-radius: 10px;
        }

        .speed-node-choice {
            display: flex;
            align-items: center;
            gap: 8px;
            border: 1px solid var(--border-card);
            border-radius: 9px;
            padding: 9px;
            background: rgba(255,255,255,.025);
        }

        .speed-progress {
            height: 10px;
            border-radius: 999px;
            overflow: hidden;
            background: rgba(255,255,255,.08);
        }

        .speed-progress > span {
            display: block;
            height: 100%;
            width: 0;
            background: linear-gradient(90deg, #10b981, #22d3ee, #7c5cff);
            transition: width .25s ease;
        }

        .speed-result-bar { height: 7px; border-radius: 999px; background: rgba(255,255,255,.08); overflow: hidden; }
        .speed-result-bar span { display: block; height: 100%; background: linear-gradient(90deg, #22d3ee, #7c5cff); }

        .audit-summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 12px;
            margin: 16px 0;
        }

        .audit-summary-item {
            border: 1px solid var(--border-card);
            border-radius: 8px;
            background: rgba(255,255,255,0.03);
            padding: 12px;
            display: grid;
            gap: 6px;
        }

        .audit-summary-item span {
            color: var(--text-secondary);
            font-size: 12px;
        }

        .audit-list {
            display: grid;
            gap: 8px;
            margin-top: 12px;
        }

        .audit-list-item {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            align-items: center;
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 9px 10px;
            background: rgba(255,255,255,0.025);
        }

        .resource-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 10px;
        }

        .resource-summary .tag-pill {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }

        .node-resource-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }

        .node-resource-card {
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 12px;
            background: rgba(255,255,255,0.03);
        }

        .node-resource-card h4 {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 10px;
            font-size: 15px;
        }

        .node-resource-charts {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 12px;
        }

        .node-resource-chart {
            height: 150px;
            min-height: 150px;
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 8px;
            background: rgba(255,255,255,0.025);
            overflow: hidden;
        }

        .node-resource-chart canvas {
            display: block;
            width: 100%;
            height: 100%;
        }

        @keyframes panelEnter {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes logoPulse {
            0%, 100% { transform: translateY(0) scale(1); filter: drop-shadow(0 14px 28px rgba(32, 199, 181, 0.22)); }
            50% { transform: translateY(-2px) scale(1.025); filter: drop-shadow(0 18px 34px rgba(124, 92, 255, 0.25)); }
        }

        @keyframes statusPulse {
            0%, 100% { transform: scale(1); opacity: 0.82; }
            50% { transform: scale(1.35); opacity: 1; }
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.001ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.001ms !important;
                scroll-behavior: auto !important;
            }
        }

        @media (max-width: 1180px) {
            body { display: block; min-width: 0; }
            body.menu-open { overflow: hidden; }
            aside {
                width: min(320px, 92vw);
                position: fixed;
                top: 0;
                bottom: 0;
                right: 0;
                display: none;
                flex-direction: column;
                gap: 8px;
                padding: 18px;
                overflow-y: auto;
                box-shadow: -16px 0 40px rgba(0, 0, 0, 0.28);
                padding-bottom: max(18px, env(safe-area-inset-bottom));
            }
            body.menu-open aside { display: flex; }
            .mobile-menu-btn { display: inline-flex; align-items: center; gap: 8px; }
            .brand { width: 100%; margin-bottom: 8px; }
            .nav-item { margin-bottom: 0; padding: 10px 12px; }
            main { width: 100%; min-width: 0; padding: 18px; }
            header { align-items: flex-start; gap: 14px; flex-direction: column; }
            .header-actions { width: 100%; gap: 10px; }
            .toolbar-select { flex: 1 1 140px; min-width: 0; }
            .charts-grid, #tab-settings > div { grid-template-columns: 1fr !important; }
            .modal-content { max-height: calc(100dvh - 24px); overflow-y: auto; }
            .link-actions { align-items: center; justify-content: flex-start; }
            .glass-card { padding: 18px; }
            table { min-width: 620px; }
            #table-nodes { min-width: 1500px; }
            .stats-grid { grid-template-columns: 1fr; }
            .link-category-chart-grid { grid-template-columns: 1fr; }
            .category-metrics { grid-template-columns: 1fr 1fr; }
            .node-resource-grid { grid-template-columns: 1fr; }
            .tunnel-guardian-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            #tab-settings .settings-grid { grid-template-columns: 1fr; }
        }

        @media (max-width: 760px) {
            :root { scroll-padding-top: 12px; }
            main {
                padding: 12px;
                padding-left: max(12px, env(safe-area-inset-left));
                padding-right: max(12px, env(safe-area-inset-right));
            }
            header { margin-bottom: 20px; }
            header h1 { font-size: clamp(22px, 7vw, 30px); }
            .mobile-menu-btn { width: 100%; justify-content: center; }
            .header-actions {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                align-items: stretch;
            }
            .header-actions > *,
            .toolbar-select,
            .header-actions .status-pill {
                width: 100%;
                min-width: 0;
            }
            .status-pill { justify-content: center; padding: 8px 10px; }
            .glass-card { padding: 14px; border-radius: 10px; }
            .glass-card:hover { transform: none; }
            .stats-grid, .charts-grid { gap: 12px; margin-bottom: 16px; }
            .stat-card { gap: 12px; }
            .stat-info p { font-size: 22px; }
            .charts-grid .glass-card > div[style*="height"] { height: 220px !important; }
            .node-resource-charts { grid-template-columns: 1fr; }
            .node-resource-chart { height: 180px; min-height: 180px; }
            .category-chart-frame { height: 160px; min-height: 160px; }
            .category-metrics,
            .speed-summary-grid,
            .speed-config-grid,
            .speed-node-picker,
            .audit-summary-grid,
            .resource-summary,
            .compact-grid,
            .profile-catalog-group-body {
                grid-template-columns: 1fr !important;
            }
            .tunnel-guardian-grid { grid-template-columns: 1fr; }
            .flow-diagram,
            .direction-example-flow {
                grid-template-columns: 1fr;
                text-align: center;
            }
            .flow-arrow,
            .direction-example-arrow { transform: rotate(90deg); justify-self: center; }
            .profile-picker-menu { position: fixed; inset: auto 12px 12px; max-height: 70dvh; }
            .modal { align-items: flex-end; padding: 0; }
            .modal-content {
                width: 100% !important;
                max-width: none !important;
                max-height: 94dvh !important;
                border-radius: 16px 16px 0 0;
                padding: 18px 14px max(18px, env(safe-area-inset-bottom));
            }
            .modal-header { position: sticky; top: -18px; z-index: 4; margin: -18px -14px 18px; padding: 16px 14px; background: var(--bg-card); border-bottom: 1px solid var(--border-card); }
            .modal-header h2 { font-size: 18px; overflow-wrap: anywhere; }
            .modal-content [style*="grid-template-columns"] { grid-template-columns: 1fr !important; }
            .modal-content .btn { min-height: 44px; }
            .ssh-terminal { min-height: 280px; max-height: 48dvh; font-size: 12px; }
            .smart-test-panel .flex-between,
            .profile-builder-head,
            .audit-list-item {
                align-items: stretch;
                flex-direction: column;
            }
            .tab-content > .flex-between {
                align-items: stretch;
                flex-direction: column;
                gap: 12px;
            }
            .tab-content > .flex-between > .flex-between {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                width: 100%;
            }
            .tab-content > .flex-between > .flex-between > * {
                width: 100% !important;
                min-width: 0;
                min-height: 44px;
                white-space: normal;
            }
            .smart-test-panel .btn,
            .smart-test-panel .form-input,
            .resource-actions .btn { width: 100% !important; }
            .link-card-head { align-items: flex-start; gap: 10px; }
            .link-card-head > .order-control { order: -1; }
            .link-card-main { min-width: 0; width: 100%; }
            .link-card-main > .flex-between {
                align-items: stretch;
                flex-direction: column;
                gap: 12px;
            }
            .link-actions {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                width: 100%;
                gap: 8px;
            }
            .link-actions > * { width: 100% !important; min-width: 0; justify-content: center; text-align: center; }
            .link-actions > .tag-pill,
            .link-actions > .status-pill { grid-column: 1 / -1; }
            .order-control.vertical { flex-direction: row; }
            .order-button { width: 38px; height: 38px; }
            .table-wrap { margin-inline: -4px; width: calc(100% + 8px); }
            table { min-width: 680px; }

            #table-nodes {
                min-width: 0;
                display: block;
                margin-top: 8px;
                white-space: normal;
            }
            #table-nodes thead { display: none; }
            #table-nodes tbody { display: grid; gap: 12px; }
            #table-nodes tr {
                display: grid;
                grid-template-columns: 1fr;
                border: 1px solid var(--border-card);
                border-radius: 12px;
                padding: 10px;
                background: rgba(255,255,255,.025);
            }
            #table-nodes td {
                display: grid;
                grid-template-columns: minmax(92px, 34%) minmax(0, 1fr);
                align-items: start;
                gap: 10px;
                padding: 10px 4px;
                white-space: normal;
                overflow-wrap: anywhere;
            }
            #table-nodes td::before {
                content: attr(data-label);
                color: var(--text-secondary);
                font-size: 12px;
                font-weight: 700;
            }
            #table-nodes td.order-cell {
                display: flex;
                justify-content: flex-end;
                padding: 0 0 6px;
                border-bottom: 0;
            }
            #table-nodes td.order-cell::before { display: none; }
            #table-nodes .node-name-line,
            #table-nodes .node-actions-line,
            #table-nodes .tag-row {
                display: flex;
                flex-wrap: wrap;
                white-space: normal;
            }
            #table-nodes .node-actions-line {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            #table-nodes .node-actions-line .btn { width: 100% !important; min-height: 40px; }
            .link-port-wrap { overflow: visible; }
            .link-port-table {
                min-width: 0;
                display: block;
            }
            .link-port-table thead { display: none; }
            .link-port-table tbody { display: grid; gap: 10px; }
            .link-port-table tr { display: grid; border: 1px solid var(--border-card); border-radius: 10px; padding: 8px; }
            .link-port-table td {
                display: grid;
                grid-template-columns: minmax(96px, 38%) minmax(0, 1fr);
                gap: 8px;
                padding: 9px 4px;
                overflow-wrap: anywhere;
            }
            .link-port-table td::before {
                content: attr(data-label);
                color: var(--text-secondary);
                font-size: 12px;
                font-weight: 700;
            }
            .link-port-table .flex-between { align-items: stretch; flex-direction: column; }
            .link-port-table .btn { width: 100% !important; }
        }

        @media (max-width: 430px) {
            .header-actions,
            .link-actions,
            #table-nodes .node-actions-line,
            .tab-content > .flex-between > .flex-between { grid-template-columns: 1fr; }
            .category-metrics { grid-template-columns: 1fr !important; }
            .login-card { width: calc(100% - 20px); padding: 22px 16px; }
            .logo-wordmark { font-size: 19px; }
            #link-data-plane-architecture { font-size: 13px; }
        }

        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-main);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-blue);
        }
    </style>
</head>
<body>
    <div class="ambient-glow" id="glow-1"></div>
    <div class="ambient-glow" id="glow-2"></div>

    <div id="login-screen">
        <div class="login-card">
            <div class="login-logo">
                <img class="brand-logo" src="/icon.svg" alt="P00RIJA TUNNEL logo">
                <div class="logo-wordmark">P00RIJA TUNNEL</div>
            </div>
            <div class="compact-grid mb-20">
                <select id="login-language-select" class="form-input" onchange="setLanguage(this.value)">
                    <option value="fa">فارسی</option>
                    <option value="en">English</option>
                </select>
                <select id="login-theme-select" class="form-input" onchange="setTheme(this.value)">
                    <option value="dark">تیره</option>
                    <option value="light">روشن</option>
                    <option value="cyberpunk">سایبرپانک</option>
                    <option value="forest">جنگل</option>
                    <option value="ocean">اقیانوس</option>
                </select>
            </div>
            <form id="login-form">
                <div class="form-group">
                    <label>نام کاربری</label>
                    <input type="text" id="username" class="form-input" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label>کلمه عبور</label>
                    <input type="password" id="password" class="form-input" required autocomplete="current-password">
                </div>
                <div class="form-group hidden" id="otp-group">
                    <label>کد دو مرحله‌ای (اختیاری)</label>
                    <input type="text" id="otp" class="form-input" inputmode="numeric" autocomplete="one-time-code" placeholder="123456">
                </div>
                <button type="submit" class="btn">ورود به پنل</button>
            </form>
        </div>
    </div>

    <aside id="main-sidebar" class="hidden">
        <div class="brand">
            <img class="brand-logo small" src="/icon.svg" alt="P00RIJA TUNNEL logo">
            <span>P00RIJA Panel</span>
        </div>
        <div class="nav-item active" onclick="switchTab('dashboard')">
            <i data-lucide="gauge"></i>
            <span>داشبورد</span>
        </div>
        <div class="nav-item" onclick="switchTab('nodes')">
            <i data-lucide="server"></i>
            <span>مدیریت سرورها</span>
        </div>
        <div class="nav-item" onclick="switchTab('links')">
            <i data-lucide="split"></i>
            <span>مدیریت تانل‌ها</span>
        </div>
        <div class="nav-item" onclick="switchTab('speedtest')">
            <i data-lucide="gauge-circle"></i>
            <span>مرکز تست سرعت</span>
        </div>
        <div class="nav-item" onclick="switchTab('logs')">
            <i data-lucide="terminal"></i>
            <span>لاگ‌های سیستم</span>
        </div>
        <div class="nav-item" onclick="switchTab('monitor')">
            <i data-lucide="activity"></i>
            <span>مانیتورینگ</span>
        </div>
        <div class="nav-item" onclick="switchTab('appearance')">
            <i data-lucide="palette"></i>
            <span>ظاهر و زبان</span>
        </div>
        <div class="nav-item" onclick="switchTab('settings')">
            <i data-lucide="settings"></i>
            <span>تنظیمات</span>
        </div>
        <div class="nav-item" onclick="switchTab('help')">
            <i data-lucide="book-open"></i>
            <span>راهنما</span>
        </div>
        <div class="nav-item" onclick="switchTab('about')">
            <i data-lucide="info"></i>
            <span>درباره من</span>
        </div>
        <div class="nav-item mt-20" onclick="logout()" style="margin-top: auto; border-top: 1px solid var(--border-card); padding-top: 20px;">
            <i data-lucide="log-out" class="text-danger"></i>
            <span class="text-danger">خروج</span>
        </div>
    </aside>

    <main id="main-workspace" class="hidden">
        <header>
            <div class="page-title">
                <button class="mobile-menu-btn" onclick="toggleMobileMenu()"><i data-lucide="menu"></i><span>منو</span></button>
                <h1 id="tab-title">داشبورد</h1>
            </div>
            <div class="header-actions">
                <select id="auto-refresh-select" class="form-input toolbar-select" onchange="setAutoRefresh()">
                    <option value="0">رفرش: خاموش</option>
                    <option value="1">رفرش: 1s</option>
                    <option value="3" selected>رفرش: 3s</option>
                    <option value="5">رفرش: 5s</option>
                    <option value="10">رفرش: 10s</option>
                    <option value="30">رفرش: 30s</option>
                    <option value="60">رفرش: 60s</option>
                </select>
                <select id="font-select" class="form-input toolbar-select" onchange="setFont(this.value)">
                    <option value="system">سیستم</option>
                    <option value="vazirmatn">Vazirmatn</option>
                    <option value="sahel">Sahel</option>
                    <option value="shabnam">Shabnam</option>
                    <option value="inter">Inter</option>
                    <option value="byekan">Byekan</option>
                </select>
                <select id="language-select" class="form-input toolbar-select" onchange="setLanguage(this.value)">
                    <option value="fa">فارسی</option>
                    <option value="en">English</option>
                </select>
                <select id="theme-select" class="form-input toolbar-select" onchange="setTheme(this.value)">
                    <option value="dark">تیره</option>
                    <option value="light">روشن</option>
                    <option value="cyberpunk">سایبرپانک</option>
                    <option value="forest">جنگل</option>
                    <option value="ocean">اقیانوس</option>
                </select>
                <div class="status-pill">
                    <img class="brand-logo tiny" src="/icon.svg" alt="P00RIJA TUNNEL logo">
                    <div class="status-dot"></div>
                    <span>P00RIJA PANEL فعال است</span>
                </div>
            </div>
        </header>

        <div id="tab-dashboard" class="tab-content">
            <div class="stats-grid">
                <div class="glass-card stat-card">
                    <div class="stat-info">
                        <h3>سرورها / نودها</h3>
                        <p id="stat-nodes-count">۰</p>
                    </div>
                    <div class="stat-icon"><i data-lucide="server"></i></div>
                </div>
                <div class="glass-card stat-card">
                    <div class="stat-info">
                        <h3>تانل‌های فعال</h3>
                        <p id="stat-links-count">۰</p>
                    </div>
                    <div class="stat-icon" style="color: var(--accent-purple);"><i data-lucide="git-commit"></i></div>
                </div>
                <div class="glass-card stat-card">
                    <div class="stat-info">
                        <h3>ترافیک شبکه (Rx/Tx)</h3>
                        <p id="stat-net-speed">0 MB/s</p>
                    </div>
                    <div class="stat-icon" style="color: var(--success);"><i data-lucide="activity"></i></div>
                </div>
                <div class="glass-card stat-card">
                    <div class="stat-info">
                        <h3>تردهای فعال</h3>
                        <p id="stat-threads-count">۰</p>
                    </div>
                    <div class="stat-icon" style="color: var(--warning);"><i data-lucide="cpu"></i></div>
                </div>
            </div>

            <div class="glass-card mb-20" style="padding: 15px;">
                <h2 style="margin-bottom: 15px; font-size: 16px;">وضعیت سیستم میزبان پنل</h2>
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">هسته‌های CPU</span>
                        <div id="host-cpu" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">RAM (آزاد / کل)</span>
                        <div id="host-ram" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">Swap (آزاد / کل)</span>
                        <div id="host-swap" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">دیسک (آزاد / کل)</span>
                        <div id="host-disk" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">بار سیستم / آپ‌تایم</span>
                        <div id="host-load" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">پروسس پنل</span>
                        <div id="host-process" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <span style="color: var(--text-secondary); font-size: 13px;">Docker</span>
                        <div id="host-docker" style="font-size: 18px; font-weight: 500;">-</div>
                    </div>
                </div>
            </div>

            <div class="charts-grid">
                <div class="glass-card">
                    <h2 class="mb-20">ترافیک عبوری شبکه (Live)</h2>
                    <div style="height: 300px;"><canvas id="chart-traffic"></canvas></div>
                </div>
                <div class="glass-card">
                    <h2 class="mb-20">اتصالات فعال تانل</h2>
                    <div style="height: 300px;"><canvas id="chart-connections"></canvas></div>
                </div>
            </div>
            <div class="charts-grid">
                <div class="glass-card">
                    <h2 class="mb-20">منابع سیستم پنل</h2>
                    <div style="height: 260px;"><canvas id="chart-panel-system"></canvas></div>
                </div>
                <div class="glass-card">
                    <h2 class="mb-20">Runtime پنل</h2>
                    <div style="height: 260px;"><canvas id="chart-panel-runtime"></canvas></div>
                </div>
            </div>
        </div>

        <div id="tab-nodes" class="tab-content hidden">
            <div class="flex-between mb-20">
                <h2>لیست نودها</h2>
                <div class="flex-between gap-10">
                    <button class="btn w-auto p-10 btn-cyan" onclick="checkNodeVersions('')">بررسی نسخه نودها</button>
                    <button class="btn w-auto p-10 btn-purple" onclick="queueNodeUpdate('')">آپدیت همه نودها</button>
                    <button class="btn w-auto p-10" onclick="openNodeSshModal()">اتصال و کنترل SSH نود</button>
                    <button id="add-panel-node-btn" class="btn w-auto p-10 btn-smart" onclick="addPanelAsNode()">افزودن پنل به‌عنوان نود</button>
                    <button class="btn w-auto p-10" onclick="openNewNodeModal()">افزودن نود جدید</button>
                </div>
            </div>
            <div class="glass-card">
                <div class="table-wrap">
                    <table id="table-nodes">
                        <thead>
                            <tr>
                                <th class="order-cell">ترتیب</th>
                                <th>نام سرور</th>
                                <th>نقش</th>
                                <th>آدرس IP</th>
                                <th>وضعیت</th>
                                <th>منابع سرور</th>
                                <th>ترافیک</th>
                                <th>تردها/کانکشن</th>
                                <th>عملیات</th>
                            </tr>
                        </thead>
                        <tbody>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="tab-links" class="tab-content hidden">
            <div class="flex-between mb-20">
                <h2>لیست تانل‌ها (لینک‌ها)</h2>
                <button class="btn w-auto p-10" onclick="openNewLinkModal()">افزودن تانل جدید</button>
            </div>
            <details class="glass-card mb-20 link-category">
                <summary class="flex-between mb-20">
                    <h2>پروفایل‌های تانل</h2>
                    <span class="tag-pill">آماده + شخصی</span>
                </summary>
                <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 14px;">پروفایل‌ها قالب آماده برای پر کردن Engine، Transport، TLS، SNI، Pool و پارامترهای پیشرفته هستند. سه آیکون رنگی وضعیت سرعت، امنیت و پایداری را نشان می‌دهند تا قبل از ساخت تانل سریع‌تر انتخاب کنید.</p>
                <div id="profile-catalog" class="profile-catalog-grid"></div>
                <div class="profile-builder-panel">
                    <div class="profile-builder-head">
                        <div>
                            <h3>ساخت پروفایل شخصی</h3>
                            <p>این بخش برای ساخت قالب اختصاصی است. بعد از ذخیره، همین پروفایل در افزودن تانل با آیکون‌های سرعت، امنیت و پایداری نمایش داده می‌شود.</p>
                        </div>
                        <span class="tag-pill">Custom Profile</span>
                    </div>
                    <div class="compact-grid profile-builder-grid">
                        <div class="form-group">
                            <label>نام پروفایل</label>
                            <input id="profile-name" class="form-input" placeholder="نام پروفایل">
                            <small class="field-hint">نامی که بعداً در لیست پروفایل‌ها و picker تانل می‌بینید.</small>
                        </div>
                        <div class="form-group">
                            <label>هسته اجرا</label>
                            <select id="profile-engine" class="form-input" onchange="syncProfileModeOptions()">
                                <option value="builtin">Built-in Reverse</option>
                                <option value="gost">GOST</option>
                                <option value="backhaul">Backhaul</option>
                                <option value="rathole">Rathole</option>
                                <option value="chisel">Chisel</option>
                                <option value="frp">FRP</option>
                                <option value="xray">Xray</option>
                                <option value="muxquantum">Mux/Quantum</option>
                                <option value="hysteria2">Hysteria 2</option>
                                <option value="singbox">sing-box</option>
                                <option value="tuic">TUIC</option>
                                <option value="masque">MASQUE</option>
                                <option value="naiveproxy">NaiveProxy</option>
                                <option value="shadowtls">ShadowTLS</option>
                                <option value="brook">Brook</option>
                                <option value="mieru">Mieru</option>
                                <option value="amneziawg">AmneziaWG v2</option>
                                <option value="wireguard">WireGuard</option>
                            </select>
                            <small class="field-hint">Core یا ابزار اصلی که کانفیگ تانل بر اساس آن ساخته و روی نودها اجرا می‌شود.</small>
                        </div>
                        <div class="form-group">
                            <label>مود تانل</label>
                            <select id="profile-mode" class="form-input">
                                <option value="websocket">WebSocket</option>
                                <option value="http_obfs">HTTP Obfs</option>
                                <option value="tcp">TCP Raw</option>
                            </select>
                            <small class="field-hint">الگوی ارتباطی و پوشش ترافیک؛ مثل WebSocket، gRPC، REALITY، XHTTP یا MASQUE.</small>
                        </div>
                        <div class="form-group">
                            <label>Pool رزرو</label>
                            <input id="profile-pool" type="number" class="form-input" value="120" placeholder="Pool">
                            <small class="field-hint">تعداد اتصال آماده. روی سرور کم‌منبع عدد کمتر فشار RAM و thread را پایین‌تر نگه می‌دارد.</small>
                        </div>
                        <div class="form-group">
                            <label>Host / SNI</label>
                            <input id="profile-host" class="form-input" value="speedtest.net" placeholder="Host / SNI">
                            <small class="field-hint">نام دامنه‌ای که برای TLS، SNI یا ظاهر ترافیک وب استفاده می‌شود.</small>
                        </div>
                        <div class="form-group">
                            <label>Path</label>
                            <input id="profile-path" class="form-input" value="/tunnel" placeholder="Path">
                            <small class="field-hint">مسیر HTTP/WebSocket/gRPC که برای پوشش ترافیک و routing سمت وب استفاده می‌شود.</small>
                        </div>
                        <div class="form-group">
                            <label>Jitter ms</label>
                            <input id="profile-jitter" type="number" class="form-input" value="0" placeholder="Jitter ms">
                            <small class="field-hint">تاخیر تصادفی کوچک برای کم کردن الگوی ثابت بسته‌ها؛ مقدار زیاد روی سرعت اثر می‌گذارد.</small>
                        </div>
                    </div>
                </div>
                <div class="flex-between gap-10 mt-20">
                    <button class="btn w-auto p-10" onclick="saveProfile()">ذخیره پروفایل</button>
                    <button class="btn w-auto p-10" onclick="exportProfiles()">خروجی پروفایل‌ها</button>
                </div>
                <textarea id="profile-import" class="form-input mt-20" rows="4" placeholder="Paste exported profiles JSON"></textarea>
                <button class="btn w-auto p-10 mt-20" onclick="importProfiles()">ورود پروفایل‌ها</button>
            </details>
            <div id="link-category-charts" class="link-category-chart-grid mb-20"></div>
            <div id="links-container" style="display: flex; flex-direction: column; gap: 24px;">
            </div>
        </div>

        <div id="tab-speedtest" class="tab-content hidden">
            <div class="flex-between mb-20">
                <div>
                    <h2>مرکز تست سرعت iperf3</h2>
                    <p style="color:var(--text-secondary);margin-top:7px;line-height:1.8;">سنجش واقعی TCP/UDP بین نودها یا از نودها به یک سرور iperf3 اینترنتی، همراه با JSON، loss، jitter، retransmit و مصرف CPU.</p>
                </div>
                <button class="btn w-auto p-10 btn-cyan" onclick="installIperfOnSelectedNodes()">نصب/بررسی iperf3</button>
            </div>
            <div class="glass-card mb-20">
                <div class="speed-config-grid">
                    <div class="form-group">
                        <label>نوع تست</label>
                        <select id="speedtest-mode" class="form-input" onchange="syncSpeedTestMode()">
                            <option value="pair">بین دو نود انتخابی</option>
                            <option value="mesh">Mesh بین تمام نودهای انتخابی</option>
                            <option value="internet">هر نود به سرور اینترنتی iperf3</option>
                        </select>
                    </div>
                    <div class="form-group speed-internet-only" style="display:none;">
                        <label>هاست سرور اینترنتی iperf3</label>
                        <input id="speedtest-internet-host" class="form-input" placeholder="iperf.example.com">
                    </div>
                    <div class="form-group">
                        <label>پروتکل</label>
                        <select id="speedtest-protocol" class="form-input">
                            <option value="tcp">TCP</option>
                            <option value="udp">UDP</option>
                        </select>
                    </div>
                    <div class="form-group"><label>پورت</label><input id="speedtest-port" type="number" class="form-input" value="5201" min="1" max="65535"></div>
                    <div class="form-group"><label>مدت تست (ثانیه)</label><input id="speedtest-duration" type="number" class="form-input" value="8" min="1" max="30"></div>
                    <div class="form-group"><label>Parallel streams</label><input id="speedtest-parallel" type="number" class="form-input" value="2" min="1" max="16"></div>
                    <div class="form-group"><label>Omit warm-up (ثانیه)</label><input id="speedtest-omit" type="number" class="form-input" value="1" min="0" max="10"></div>
                    <div class="form-group"><label>UDP bitrate</label><input id="speedtest-bitrate" class="form-input" value="100M" placeholder="100M"></div>
                    <div class="form-group"><label>Block length (byte، اختیاری)</label><input id="speedtest-block-length" type="number" class="form-input" value="0" min="0"></div>
                    <div class="form-group"><label>TCP window (اختیاری)</label><input id="speedtest-window" class="form-input" placeholder="2M"></div>
                    <div class="form-group"><label>Congestion control</label><input id="speedtest-congestion" class="form-input" placeholder="bbr / cubic"></div>
                </div>
                <div class="tag-row mt-20">
                    <label class="tag-pill"><input id="speedtest-reverse" type="checkbox"> Reverse</label>
                    <label class="tag-pill"><input id="speedtest-bidir" type="checkbox"> Bidirectional</label>
                    <label class="tag-pill"><input id="speedtest-zerocopy" type="checkbox"> Zero-copy</label>
                    <label class="tag-pill"><input id="speedtest-mptcp" type="checkbox"> MPTCP</label>
                </div>
                <h3 class="mt-20 mb-20">انتخاب نودها</h3>
                <div id="speedtest-node-picker" class="speed-node-picker"></div>
                <div class="flex-between gap-10 mt-20" style="justify-content:flex-start;flex-wrap:wrap;">
                    <button class="btn w-auto p-10" onclick="selectAllSpeedNodes(true)">انتخاب همه</button>
                    <button class="btn w-auto p-10" onclick="selectAllSpeedNodes(false)">پاک کردن انتخاب</button>
                    <button id="speedtest-start-btn" class="btn w-auto p-10 btn-smart" onclick="startSpeedTest()">شروع تست واقعی</button>
                </div>
            </div>
            <div class="glass-card">
                <div class="flex-between">
                    <h2>نتیجه تست</h2>
                    <span id="speedtest-state" class="tag-pill">آماده</span>
                </div>
                <div class="speed-progress mt-20"><span id="speedtest-progress-bar"></span></div>
                <div id="speedtest-summary" class="speed-summary-grid mt-20"></div>
                <div class="table-wrap mt-20">
                    <table>
                        <thead><tr><th>مسیر</th><th>پروتکل</th><th>آپلود</th><th>دانلود</th><th>Loss/Jitter</th><th>Retransmit</th><th>CPU</th><th>وضعیت</th></tr></thead>
                        <tbody id="speedtest-results-body"></tbody>
                    </table>
                </div>
                <details class="mt-20"><summary>خطاها و جزئیات</summary><pre id="speedtest-details" class="terminal-output mt-20"></pre></details>
            </div>
        </div>

        <div id="tab-logs" class="tab-content hidden">
            <div class="flex-between mb-20">
                <h2>لاگ‌های سیستم</h2>
                <button class="btn w-auto p-10" onclick="exportLogsCSV()">خروجی CSV</button>
            </div>
            <div class="glass-card" style="max-height: 600px; overflow-y: auto;">
                <div class="table-wrap">
                    <table id="table-logs">
                        <thead>
                            <tr>
                                <th>زمان ثبت</th>
                                <th>منبع</th>
                                <th>سطح لاگ</th>
                                <th>شرح لاگ</th>
                            </tr>
                        </thead>
                        <tbody>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="tab-monitor" class="tab-content hidden">
            <div class="flex-between mb-20">
                <h2>مانیتورینگ سشن‌ها، تردها و پروسس‌ها</h2>
                <button class="btn w-auto p-10" onclick="fetchRuntime()">بروزرسانی دستی</button>
            </div>
            <div class="settings-grid">
                <div class="glass-card">
                    <button type="button" id="sessions-toggle" class="profile-picker-button mb-20" onclick="toggleSessionsPanel()">
                        <span class="profile-picker-selected">
                            <strong>سشن‌های فعال تانل</strong>
                            <small id="sessions-toggle-hint">برای مشاهده و بروزرسانی، منو را باز کنید</small>
                        </span>
                        <span class="tag-pill"><span id="sessions-dropdown-count">0</span></span>
                        <i data-lucide="chevron-down"></i>
                    </button>
                    <div id="sessions-panel" class="table-wrap hidden">
                        <table id="table-sessions">
                            <thead><tr><th>شناسه</th><th>تانل</th><th>مقصد</th><th>عمر</th><th>بیکاری</th><th>عملیات</th></tr></thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
                <div class="glass-card">
                    <button type="button" id="threads-toggle" class="profile-picker-button mb-20" onclick="toggleThreadsPanel()">
                        <span class="profile-picker-selected">
                            <strong>تردهای فعال</strong>
                            <small id="threads-toggle-hint">برای مشاهده و بروزرسانی تردها، منو را باز کنید</small>
                        </span>
                        <span class="tag-pill"><span id="threads-dropdown-count">0</span></span>
                        <i data-lucide="chevron-down"></i>
                    </button>
                    <div id="threads-panel" class="table-wrap hidden">
                        <table id="table-threads">
                            <thead><tr><th>TID</th><th>PID</th><th>پروسس</th><th>منبع</th><th>وضعیت</th><th>RSS</th><th>CPU</th></tr></thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
                <div class="glass-card">
                    <h3 class="mb-20">پروسس‌های سیستم</h3>
                    <div class="table-wrap">
                        <table id="table-processes">
                            <thead><tr><th>PID</th><th>نام</th><th>RSS</th><th>تردها</th><th>زمان CPU</th><th>عملیات</th></tr></thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
                <div class="glass-card">
                    <h3 class="mb-20">مدیریت منابع سرور</h3>
                    <div id="resource-summary" class="resource-summary mb-20">
                        <span class="tag-pill">تردها <strong id="resource-threads">0</strong></span>
                        <span class="tag-pill">سشن‌ها <strong id="resource-sessions">0</strong></span>
                        <span class="tag-pill">RSS <strong id="resource-rss">0 MB</strong></span>
                    </div>
                    <div class="form-group">
                        <label>محدوده بهینه‌سازی</label>
                        <select id="resource-scope" class="form-input">
                            <option value="all">پنل و همه نودهای آنلاین</option>
                            <option value="panel">فقط پنل</option>
                            <option value="nodes">فقط نودهای آنلاین</option>
                        </select>
                    </div>
                    <div class="resource-actions">
                        <button class="btn w-auto p-10 btn-smart" onclick="optimizeResources('thread_guard')"><i data-lucide="shield-check"></i><span>مدیریت هوشمند تردها</span></button>
                        <button class="btn w-auto p-10" onclick="optimizeResources('idle')">پاک‌سازی سشن‌های Idle</button>
                        <button class="btn w-auto p-10" onclick="optimizeResources('gc')">پاک‌سازی RAM/GC</button>
                        <button class="btn w-auto p-10" onclick="optimizeResources('pressure')" style="background: var(--accent-purple);">کاهش فشار ترد/RAM</button>
                        <button class="btn w-auto p-10" onclick="optimizeResources('all')" style="background: var(--warning);">بهینه‌سازی کامل منابع</button>
                    </div>
                    <p id="resource-result" class="mt-20" style="color: var(--text-secondary); line-height: 1.8;"></p>
                </div>
                <div class="glass-card">
                    <div class="flex-between gap-10 mb-20">
                        <h3>مرکز هوشمند عملیات ۲۰۲۶</h3>
                        <button id="auto-guardian-toggle" class="btn w-auto p-10 btn-smart" onclick="toggleAutoGuardian()"><i data-lucide="timer-reset"></i><span>نگهبان خودکار: خاموش</span></button>
                    </div>
                    <div id="ops-intelligence-grid" class="ops-intel-grid"></div>
                    <div class="mb-20">
                        <h4 class="mb-20">پیشنهادهای اجرایی</h4>
                        <div id="ops-recommendations" class="ops-recommendation-row"></div>
                    </div>
                    <div>
                        <h4 class="mb-20">رادار تانلینگ ۲۰۲۶</h4>
                        <div id="ops-transport-radar" class="ops-radar-row"></div>
                    </div>
                </div>
                <div class="glass-card">
                    <h3 class="mb-20">نگهبان هوشمند تانل‌ها</h3>
                    <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 14px;">این بخش همه تانل‌ها را از نظر سشن فعال، worker آماده، فشار thread و وضعیت engine پایش می‌کند و برای هر لینک اقدام پیشنهادی می‌دهد.</p>
                    <div id="tunnel-guardian-grid" class="tunnel-guardian-grid"></div>
                </div>
                <div class="glass-card">
                    <h3 class="mb-20">منابع زنده نودها</h3>
                    <div id="node-resource-grid" class="node-resource-grid"></div>
                </div>
            </div>
        </div>

        <div id="tab-appearance" class="tab-content hidden">
            <div class="settings-grid">
                <div class="glass-card">
                    <h2 class="mb-20">ظاهر، فونت و زبان</h2>
                    <div class="compact-grid">
                        <div class="form-group">
                            <label>زبان پنل</label>
                            <select id="appearance-language" class="form-input" onchange="setLanguage(this.value)">
                                <option value="fa">فارسی</option>
                                <option value="en">English</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>تم رنگی</label>
                            <select id="appearance-theme" class="form-input" onchange="setTheme(this.value)">
                                <option value="dark">تیره</option>
                                <option value="light">روشن</option>
                                <option value="cyberpunk">سایبرپانک</option>
                                <option value="forest">جنگل</option>
                                <option value="ocean">اقیانوس</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>فونت برنامه</label>
                            <select id="appearance-font" class="form-input" onchange="setFont(this.value)">
                                <option value="system">سیستم</option>
                                <option value="vazirmatn">Vazirmatn</option>
                                <option value="sahel">Sahel</option>
                                <option value="shabnam">Shabnam</option>
                                <option value="inter">Inter</option>
                                <option value="byekan">Byekan</option>
                            </select>
                        </div>
                    </div>
                </div>
                </div>
            </div>
        </div>

        <div id="tab-settings" class="tab-content hidden">
            <h2>تنظیمات پنل</h2>
            <div class="settings-grid">
                <div class="glass-card mt-20">
                    <form id="form-settings-pass" class="mb-20">
                        <h3 class="mb-20">تغییر مشخصات مدیریت</h3>
                        <div class="form-group">
                            <label>نام کاربری</label>
                            <input type="text" id="setting-username" class="form-input" required autocomplete="username">
                        </div>
                        <div class="form-group">
                            <label>کلمه عبور جدید</label>
                            <input type="password" id="setting-password" class="form-input" required autocomplete="new-password">
                        </div>
                        <button type="submit" class="btn w-auto p-10">بروزرسانی مشخصات ورود</button>
                    </form>
                </div>

                <div class="glass-card mt-20">
                    <h3 class="mb-20">امنیت ورود</h3>
                    <form id="form-settings-security">
                        <div class="form-group">
                            <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="setting-two-factor" style="width: 18px; height: 18px;">
                                فعال‌سازی ورود دو مرحله‌ای TOTP
                            </label>
                        </div>
                        <div class="form-group">
                            <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="setting-biometric" style="width: 18px; height: 18px;">
                                فعال‌سازی بایومتریک مرورگر برای Quick Unlock
                            </label>
                        </div>
                        <button type="submit" class="btn w-auto p-10">ثبت تنظیمات امنیتی</button>
                    </form>
                    <p id="totp-secret-box" class="tag-pill mt-20 hidden" style="direction:ltr; text-align:left;"></p>
                </div>

                <div class="glass-card mt-20">
                    <h3 class="mb-20">مسیر مخفی مدیریت پنل</h3>
                    <p style="color:var(--text-secondary); line-height:1.8;">
                        در حالت فعال، صفحه ورود فقط از مسیر تصادفی زیر باز می‌شود و درخواست مستقیم Login بدون Gate معتبر با 404 پاسخ داده می‌شود. این قابلیت جلوی اسکن‌های عمومی را می‌گیرد، اما جایگزین محافظت IP/SNI نیست.
                    </p>
                    <form id="form-panel-hidden-path">
                        <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer;">
                            <input type="checkbox" id="setting-hidden-path-enabled">
                            فعال‌سازی مسیر مخفی
                        </label>
                        <div class="form-group mt-20">
                            <label>مسیر مدیریت</label>
                            <div style="display:flex; gap:8px;">
                                <input type="text" id="setting-hidden-panel-path" class="form-input" dir="ltr" placeholder="/manage-random-token">
                                <button type="button" class="btn w-auto p-10" onclick="generateHiddenPanelPath()">ساخت مسیر تصادفی</button>
                            </div>
                        </div>
                        <button type="submit" class="btn w-auto p-10 btn-smart">ذخیره مسیر مدیریت</button>
                        <div id="hidden-path-result" class="mt-20" style="color:var(--text-secondary); word-break:break-all;"></div>
                    </form>
                </div>

                <div class="glass-card mt-20">
                    <h3 class="mb-20">تنظیمات نمایش</h3>
                    <form id="form-settings-display" class="mb-20">
                        <div class="form-group">
                            <label>واحد نمایش ترافیک در داشبورد و جدول نودها</label>
                            <select id="setting-traffic-unit" class="form-input">
                                <option value="MB">مگابایت بر ثانیه (MB/s)</option>
                                <option value="KB">کیلوبایت بر ثانیه (KB/s)</option>
                            </select>
                        </div>
                        <button type="submit" class="btn w-auto p-10">اعمال تنظیمات نمایش</button>
                    </form>
                </div>

                <div class="glass-card mt-20">
                    <h3 class="mb-20">تنظیمات شبکه</h3>
                    <form id="form-settings-network" class="mb-20">
                        <div class="form-group">
                            <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="setting-disable-ipv6" style="width: 18px; height: 18px;">
                                غیرفعال‌سازی سراسری IPv6 (توصیه شده در ایران)
                            </label>
                            <small style="display:block; margin-top:5px; opacity:0.8;">در صورت اختلال و بسته شدن IPV6 این گزینه را فعال کنید تا ارتباط شبکه قطع نشود.</small>
                        </div>
                        <div class="form-group">
                            <label>زمان اعمال و ریست مجدد هسته (به دقیقه، 0 برای غیرفعال کردن)</label>
                            <input type="number" id="setting-engine-restart-interval" class="form-input" min="0" value="0">
                            <small style="display:block; margin-top:5px; opacity:0.8;">برای پایداری بیشتر، هسته‌ها می‌توانند به صورت زمان‌بندی شده ریست شوند تا حافظه و منابع آزاد شود.</small>
                        </div>
                        <button type="submit" class="btn w-auto p-10">اعمال تنظیمات شبکه</button>
                    </form>
                </div>

                <div class="glass-card mt-20">
                    <h3 class="mb-20">پورت‌های پنل و API نودها</h3>
                    <p style="color:var(--text-secondary); line-height:1.8;">
                        تغییر پورت، Docker mapping را روی میزبان بازسازی می‌کند. اگر پورت API تغییر کند، ابتدا آدرس جدید به نودهای آنلاین اعلام می‌شود.
                    </p>
                    <form id="form-panel-ports">
                        <div class="compact-grid">
                            <div class="form-group">
                                <label>پورت وب پنل</label>
                                <input type="number" id="setting-panel-port" class="form-input" min="1" max="65535" required>
                            </div>
                            <div class="form-group">
                                <label>پورت API نودها</label>
                                <input type="number" id="setting-api-port" class="form-input" min="1" max="65535" required>
                            </div>
                            <div class="form-group">
                                <label>Host عمومی پنل</label>
                                <input type="text" id="setting-panel-host" class="form-input" placeholder="panel.example.com" required>
                            </div>
                        </div>
                        <button type="submit" class="btn w-auto p-10" style="background:var(--accent-purple);">اعمال پورت‌ها و بازسازی پنل</button>
                        <div id="panel-port-result" class="mt-20" style="color:var(--text-secondary);"></div>
                    </form>
                </div>

                <div class="glass-card mt-20 settings-wide">
                    <h3 class="mb-20">بکاپ کامل و انتقال پنل</h3>
                    <p style="color:var(--text-secondary); line-height:1.8;">
                        بکاپ شامل دیتابیس، همه نودها و تانل‌ها، توکن‌ها، کلیدها، Certificateها، تنظیمات و فایل‌های برنامه است و با AES-256 رمزگذاری می‌شود.
                    </p>
                    <div class="compact-grid mt-20">
                        <div>
                            <h4 class="mb-20">دانلود بکاپ رمزگذاری‌شده</h4>
                            <div class="form-group">
                                <label>رمز بکاپ (حداقل ۸ کاراکتر)</label>
                                <input type="password" id="backup-password" class="form-input" autocomplete="new-password">
                            </div>
                            <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer;">
                                <input type="checkbox" id="backup-include-engines" checked>
                                هسته‌های آفلاین نیز داخل بکاپ قرار بگیرند
                            </label>
                            <button class="btn w-auto p-10 mt-20" onclick="createAndDownloadBackup()">ساخت و دانلود بکاپ</button>
                            <div id="backup-result" class="mt-20" style="color:var(--text-secondary);"></div>
                        </div>
                        <form id="form-panel-migration">
                            <h4 class="mb-20">انتقال مستقیم به هاست جدید</h4>
                            <div class="compact-grid">
                                <div class="form-group">
                                    <label>Host یا IP مقصد</label>
                                    <input type="text" id="migration-host" class="form-input" required placeholder="203.0.113.10">
                                </div>
                                <div class="form-group">
                                    <label>پورت SSH</label>
                                    <input type="number" id="migration-port" class="form-input" value="22" min="1" max="65535">
                                </div>
                                <div class="form-group">
                                    <label>نام کاربری SSH</label>
                                    <input type="text" id="migration-username" class="form-input" value="root" required>
                                </div>
                                <div class="form-group">
                                    <label>رمز SSH مقصد</label>
                                    <input type="password" id="migration-password" class="form-input" required autocomplete="new-password">
                                </div>
                            </div>
                            <div class="form-group">
                                <label>آدرس API پنل جدید برای نودها</label>
                                <input type="url" id="migration-panel-url" class="form-input" required placeholder="https://panel.example.com:8000">
                                <small style="display:block; margin-top:5px; opacity:.8;">این آدرس قبل از cutover به تمام نودهای آنلاین اعلام می‌شود. آدرس پنل فعلی به‌عنوان fallback روی نود باقی می‌ماند.</small>
                            </div>
                            <div class="form-group">
                                <label>رمز بکاپ انتقال</label>
                                <input type="password" id="migration-backup-password" class="form-input" required autocomplete="new-password">
                            </div>
                            <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer; margin-left:18px;">
                                <input type="checkbox" id="migration-include-engines" checked>
                                انتقال هسته‌های آفلاین
                            </label>
                            <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer;">
                                <input type="checkbox" id="migration-regenerate-cert" checked>
                                ساخت Certificate جدید برای Host مقصد
                            </label>
                            <button type="submit" class="btn w-auto p-10 mt-20" style="background:var(--accent-purple);">شروع مهاجرت مرحله‌ای</button>
                            <div id="migration-result" class="mt-20" style="white-space:pre-wrap; color:var(--text-secondary);"></div>
                        </form>
                    </div>
                    <form id="form-panel-restore" class="mt-20" style="border-top:1px solid var(--border); padding-top:20px;">
                        <h4 class="mb-20">بازیابی پنل از بکاپ رمزگذاری‌شده</h4>
                        <p style="color:var(--text-secondary); line-height:1.8;">
                            پیش از Restore یک Snapshot بازگشت از وضعیت فعلی ساخته می‌شود. پس از بازیابی، پنل به‌صورت خودکار Restart خواهد شد.
                        </p>
                        <div class="compact-grid">
                            <div class="form-group">
                                <label>منبع فایل بکاپ</label>
                                <select id="restore-source" class="form-input">
                                    <option value="upload">بارگذاری مستقیم از سیستم من</option>
                                    <option value="server">انتخاب فایل موجود داخل سرور</option>
                                </select>
                            </div>
                            <div class="form-group" id="restore-upload-wrap">
                                <label>فایل بکاپ از سیستم</label>
                                <input type="file" id="restore-upload-file" class="form-input" accept=".enc,.tar.gz.enc,application/octet-stream">
                            </div>
                            <div class="form-group" id="restore-server-wrap" style="display:none;">
                                <label>بکاپ موجود در سرور</label>
                                <div style="display:flex; gap:8px;">
                                    <select id="restore-server-backup" class="form-input"></select>
                                    <button type="button" class="btn w-auto p-10" onclick="loadServerBackups()">بازخوانی</button>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>رمز بکاپ</label>
                                <input type="password" id="restore-password" class="form-input" required autocomplete="new-password">
                            </div>
                            <div class="form-group">
                                <label>آدرس جدید پنل (اختیاری)</label>
                                <input type="url" id="restore-panel-url" class="form-input" placeholder="https://panel.example.com:8000">
                            </div>
                        </div>
                        <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer;">
                            <input type="checkbox" id="restore-regenerate-cert">
                            ساخت Certificate جدید بر اساس آدرس واردشده
                        </label>
                        <button type="submit" class="btn w-auto p-10 mt-20" style="background:var(--accent-purple);">اعتبارسنجی و Restore</button>
                        <div id="restore-result" class="mt-20" style="white-space:pre-wrap; color:var(--text-secondary);"></div>
                    </form>
                </div>

                <div class="glass-card mt-20 settings-wide">
                    <div class="flex-between gap-10" style="align-items:flex-start; flex-wrap:wrap;">
                        <div>
                            <h3 class="mb-20">ممیزی ماژولار و آمادگی نصب</h3>
                            <p style="color: var(--text-secondary); line-height: 1.8;">این بخش ساختار ماژول‌ها، فایل‌های ضروری پکیج، وضعیت engineهای آفلاین و پیشنهادهای refactor بعدی را بررسی می‌کند.</p>
                        </div>
                        <button class="btn w-auto p-10" onclick="fetchSystemAudit()">اجرای ممیزی</button>
                    </div>
                    <div id="system-audit-result" class="mt-20">
                        <span class="tag-pill">برای بررسی ساختار و آمادگی پکیج، ممیزی را اجرا کنید.</span>
                    </div>
                </div>
                
                <div class="glass-card mt-20 settings-wide">
                    <div class="flex-between mb-20" style="flex-wrap:wrap; gap:10px;">
                        <h3>مدیریت هسته‌ها (Engine Management)</h3>
                        <button class="btn w-auto p-10 btn-cyan" onclick="checkEngineUpdates('')">بررسی آپدیت همه هسته‌ها</button>
                    </div>
                    <div id="engine-update-summary" class="mb-20" style="color:var(--text-secondary);"></div>
                    <div id="engine-manager-grid" class="compact-grid"></div>
                    <small style="display:block; margin-top:10px; opacity:0.8;">هسته‌ها از پوشه آفلاین engines داخل image استفاده می‌کنند. نصب از GitHub فقط وقتی لازم است که اینترنت در دسترس باشد.</small>
                </div>
                
                <div class="glass-card mt-20 settings-wide">
                    <h3 class="mb-20">تنظیمات SSL/TLS وب پنل (HTTPS)</h3>
                    <form id="form-settings-tls" class="mb-20">
                        <div class="form-group">
                            <label style="display: inline-flex; align-items: center; gap: 8px;">
                                <input type="checkbox" id="setting-panel-tls" style="width: 18px; height: 18px;" checked disabled>
                                HTTPS اجباری برای وب پنل
                            </label>
                            <small style="display:block; margin-top:5px; opacity:0.8;">در صورت نبود certificate معتبر، پنل به صورت خودکار certificate محلی می‌سازد.</small>
                        </div>
                        <div class="form-group">
                            <label>مسیر Certificate (.pem)</label>
                            <input type="text" id="setting-cert-path" class="form-input" placeholder="/opt/p00rija/certs/cert.pem">
                        </div>
                        <div class="form-group">
                            <label>مسیر Private Key (.pem)</label>
                            <input type="text" id="setting-key-path" class="form-input" placeholder="/opt/p00rija/certs/key.pem">
                        </div>
                        <button type="submit" class="btn w-auto p-10" style="margin-bottom: 10px;">ثبت تنظیمات SSL</button>
                    </form>
                    <hr style="border: 0; border-top: 1px solid var(--border-card); margin: 20px 0;">

                    <h4 class="mb-20">ساخت Certificate محلی برای IP یا Hostname</h4>
                    <form id="form-local-cert" class="mb-20">
                        <div class="form-group">
                            <label>IP یا Hostname پنل</label>
                            <input type="text" id="local-cert-host" class="form-input" placeholder="127.0.0.1 یا panel.local" required>
                        </div>
                        <button type="submit" class="btn w-auto p-10" style="background: var(--accent-blue);">ساخت و اعمال Certificate محلی</button>
                    </form>
                    <hr style="border: 0; border-top: 1px solid var(--border-card); margin: 20px 0;">
                    
                    <h4 class="mb-20">دریافت Certificate خودکار Let's Encrypt</h4>
                    <form id="form-acme-cert" class="mb-20">
                        <div class="form-group">
                            <label>آدرس دامنه (مثال: panel.yourdomain.com)</label>
                            <input type="text" id="acme-domain" class="form-input" placeholder="panel.yourdomain.com" required>
                        </div>
                        <div class="form-group">
                            <label>ایمیل (جهت ثبت‌نام در Let's Encrypt)</label>
                            <input type="email" id="acme-email" class="form-input" placeholder="admin@yourdomain.com" required>
                        </div>
                        <div class="compact-grid">
                            <div class="form-group">
                                <label>روش اعتبارسنجی ACME</label>
                                <select id="acme-challenge" class="form-input" onchange="toggleAcmeDnsFields()">
                                    <option value="http-01">HTTP-01 — نیازمند پورت ۸۰</option>
                                    <option value="dns-01">DNS-01 — بدون نیاز به پورت ۸۰</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label style="display:inline-flex;align-items:center;gap:8px;">
                                    <input type="checkbox" id="acme-wildcard" onchange="toggleAcmeDnsFields()">
                                    صدور Wildcard برای *.domain
                                </label>
                            </div>
                        </div>
                        <div id="acme-dns-fields" class="hidden">
                            <div class="form-group">
                                <label>ارائه‌دهنده DNS</label>
                                <select id="acme-dns-provider" class="form-input">
                                    <option value="cloudflare">Cloudflare</option>
                                    <option value="digitalocean">DigitalOcean</option>
                                    <option value="route53">AWS Route53 (IAM/Environment)</option>
                                    <option value="rfc2136">RFC2136 Dynamic DNS</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>محتوای فایل Credentials افزونه Certbot</label>
                                <textarea id="acme-dns-credentials" class="form-input" rows="5" dir="ltr" placeholder="dns_cloudflare_api_token = ..."></textarea>
                                <small class="field-hint">فایل با سطح دسترسی 0600 روی Host نگهداری می‌شود. برای Route53 می‌توان از IAM role یا متغیرهای محیطی سرویس استفاده کرد.</small>
                            </div>
                            <div class="form-group">
                                <label>زمان انتظار انتشار DNS (ثانیه)</label>
                                <input type="number" id="acme-dns-propagation" class="form-input" min="10" max="600" value="30">
                            </div>
                        </div>
                        <button type="submit" class="btn w-auto p-10" style="background: var(--accent-purple);">دریافت و نصب گواهینامه SSL</button>
                    </form>
                    
                    <button class="btn w-auto p-10 mt-20" onclick="restartPanel()" style="background: var(--danger);">اعمال تغییرات و ریستارت وب پنل</button>
                </div>
            </div>
        </div>

        <div id="tab-help" class="tab-content hidden">
            <div class="glass-card">
                <div style="text-align: center;">
                    <img src="/icon.svg" style="width: 120px; height: 120px; display: block; margin: 0 auto 20px;" alt="P00RIJA Logo">
                    <h2 class="mb-20">راهنمای سریع داشبورد</h2>
                </div>
                <div class="compact-grid mb-20">
                    <div>
                        <h3 class="mb-20">سناریو ۱: خارجی به داخلی</h3>
                        <div class="flow-diagram">
                            <div class="flow-node">External Node<br><small>Client / Dialer</small></div>
                            <div class="flow-arrow">====&gt;</div>
                            <div class="flow-node">Internal Node<br><small>Server / Listener</small></div>
                        </div>
                        <p style="color: var(--text-secondary); line-height: 1.8; margin-top: 10px;">این حالت پیش‌فرض است. نود داخلی Bridge/Sync را گوش می‌دهد و نود خارجی اتصال‌های رزرو را به سمت داخلی می‌سازد.</p>
                    </div>
                    <div>
                        <h3 class="mb-20">سناریو ۲: داخلی به خارجی</h3>
                        <div class="flow-diagram">
                            <div class="flow-node">Internal Node<br><small>Client / Dialer</small></div>
                            <div class="flow-arrow">====&gt;</div>
                            <div class="flow-node">External Node<br><small>Server / Listener</small></div>
                        </div>
                        <p style="color: var(--text-secondary); line-height: 1.8; margin-top: 10px;">اگر خروجی گرفتن از نود داخلی بهتر از ورودی گرفتن روی آن است، این جهت را انتخاب کنید تا نود داخلی اتصال اولیه را به خارجی بزند.</p>
                    </div>
                </div>
                <div class="help-list">
                    <p>۱. در مدیریت سرورها، ابتدا نودهای داخلی و خارجی را ثبت کنید. اگر یک سرور هم پنل است و هم نود داخلی، همان سرور را به عنوان Internal Node هم اضافه کنید تا در ساخت تانل قابل انتخاب باشد.</p>
                    <p>۲. در مدیریت تانل‌ها، از پروفایل‌های آماده برای شروع سریع استفاده کنید. بعد از انتخاب پروفایل، Engine، Transport، Network، TLS، SNI، Path و Pool همچنان قابل تغییر هستند.</p>
                    <p>۳. برای هر تانل Bridge Port و Sync Port روی نود داخلی باید آزاد و یکتا باشد. اگر پورت تکراری باشد، پنل قبل از ذخیره خطا می‌دهد.</p>
                    <p>۴. بعد از ساخت تانل، Port Forwarding را اضافه کنید. User/Internal Port همان پورتی است که روی نود داخلی باز می‌شود و Target Port به سرویس سمت نود خارجی اشاره می‌کند.</p>
                    <p>۵. دکمه توقف تانل، تانل را از کانفیگ نودها خارج می‌کند و با ادامه دوباره به نودها تحویل داده می‌شود. برای اعمال عملی، چند ثانیه تا polling بعدی نود صبر کنید.</p>
                    <p>۶. اگر TLS تانل فعال است، SNI و Host را هماهنگ انتخاب کنید. برای وب پنل، تنظیمات HTTPS در Settings فقط با مسیر Certificate و Key معتبر و ریستارت پنل کامل اعمال می‌شود.</p>
                    <p>۷. نمودارهای Dashboard و وضعیت منابع/ترافیک مدیریت سرورها با Refresh Time بالای صفحه به صورت زنده به‌روزرسانی می‌شوند. برای تست فوری، مقدار ۳ ثانیه را انتخاب کنید.</p>
                    <p>۸. در Monitor می‌توانید sessionهای فعال، مصرف RSS و تعداد threadها را ببینید و پاک‌سازی idle یا GC را اجرا کنید.</p>
                    <p>۹. نام کاربری و رمز پیش‌فرض دیتابیس تازه admin/admin است؛ در نصب wizard رمز جدید بگذارید و بعد از ورود آن را تغییر دهید.</p>
                </div>
            </div>
        </div>

        <div id="tab-about" class="tab-content hidden">
            <div class="glass-card">
                <div style="text-align: center;">
                    <img src="/icon.svg" style="width: 120px; height: 120px; display: block; margin: 0 auto 20px;" alt="P00RIJA Logo">
                    <h2 class="mb-20">درباره من</h2>
                </div>
                <p class="mb-20" style="color: var(--text-secondary); line-height: 1.9; text-align: center;">P00RIJA TUNNEL برای مدیریت متمرکز تانل‌های معکوس در سناریوهای چندنودی ساخته شده است؛ جایی که پنل باید هم وضعیت سرورها را زنده ببیند، هم پروفایل‌های مختلف تانلینگ را کنترل کند، و هم امکان توقف، ادامه، و ویرایش عملیاتی تانل‌ها را بدون دستکاری دستی کانفیگ‌ها بدهد.</p>
                <div class="compact-grid mb-20">
                    <div style="padding: 16px; border: 1px solid var(--border-card); border-radius: 8px;">
                        <h3 class="mb-20">تمرکز پروژه</h3>
                        <p style="color: var(--text-secondary); line-height: 1.8;">پایداری ارتباط، انتخاب هوشمند پروفایل، مانیتورینگ منابع، و مدیریت امن نودها با توکن و امضای درخواست.</p>
                    </div>
                    <div style="padding: 16px; border: 1px solid var(--border-card); border-radius: 8px;">
                        <h3 class="mb-20">برای چه سناریویی؟</h3>
                        <p style="color: var(--text-secondary); line-height: 1.8;">پنل مرکزی، نودهای داخلی، نودهای خارجی، شبکه‌های جدا، و تانل‌هایی که باید زیر بار واقعی قابل مشاهده و قابل کنترل باشند.</p>
                    </div>
                </div>
                <div class="compact-grid">
                    <div class="tag-pill">نسخه: <span id="about-version">1.9.95</span></div>
                    <div class="tag-pill">لایسنس: <span id="about-license">GPL-3.0</span></div>
                    <a class="tag-pill" href="https://github.com/Poorija" target="_blank" rel="noopener">گیت‌هاب: github.com/Poorija</a>
                    <a class="tag-pill" href="mailto:mohammadmahdi.farhadianfard@gmail.com">mohammadmahdi.farhadianfard@gmail.com</a>
                </div>
            </div>
        </div>
    </main>

    <div id="modal-add-node" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="node-modal-title">افزودن نود جدید</h2>
                <button class="modal-close" onclick="closeModal('modal-add-node')"><i data-lucide="x"></i></button>
            </div>
            <form id="form-add-node">
                <div class="form-group">
                    <label>نام نود (مثال: INTERNAL-Node-1)</label>
                    <input type="text" id="node-name" class="form-input" required>
                </div>
                <div class="form-group">
                    <label>نقش نود</label>
                    <select id="node-role" class="form-input">
                        <option value="internal">نود داخلی (Internal Node)</option>
                        <option value="external">نود خارجی (External Node)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>آدرس IP سرور</label>
                    <input type="text" id="node-ip" class="form-input" placeholder="1.2.3.4" required>
                </div>
                <div class="form-group">
                    <label>تگ‌های نود</label>
                    <input type="text" id="node-tags" class="form-input" placeholder="iran, edge, vip">
                </div>
                <div class="form-group">
                    <label>دسته‌بندی نود</label>
                    <input type="text" id="node-category" class="form-input" placeholder="Iran / Europe / Panel">
                </div>
                <button type="submit" id="node-submit-btn" class="btn">ثبت نود جدید</button>
            </form>
        </div>
    </div>

    <div id="loading-overlay" class="modal" style="z-index: 9999; background: rgba(0, 0, 0, 0.8);">
        <div class="modal-content" style="max-width: 300px; text-align: center; background: transparent; border: none; box-shadow: none;">
            <div class="spinner" style="border: 4px solid rgba(255, 255, 255, 0.3); border-radius: 50%; border-top: 4px solid var(--primary); width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 15px auto;"></div>
            <h3 style="color: white;" data-tx="در حال آزمایش، صبر کنید...|Testing, please wait...">در حال آزمایش، صبر کنید...</h3>
        </div>
    </div>
    <div id="modal-node-test" class="modal">
        <div class="modal-content" style="max-width: 720px;">
            <div class="modal-header">
                <h2>تست ارتباط سرور</h2>
                <button class="modal-close" onclick="closeModal('modal-node-test')"><i data-lucide="x"></i></button>
            </div>
            <div id="node-test-loading" class="mb-20" style="display:flex; align-items:center; gap:12px;">
                <div class="spinner" style="border: 3px solid rgba(255,255,255,0.18); border-top-color: var(--accent-blue); width: 28px; height: 28px; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <strong>در حال تست ارتباط، چند لحظه صبر کنید...</strong>
            </div>
            <pre id="node-test-result" class="form-input" style="min-height: 220px; white-space: pre-wrap; direction:ltr; text-align:left;"></pre>
        </div>
    </div>
    
    <div id="modal-show-token" class="modal">
        <div class="modal-content" style="text-align: center;">
            <div class="modal-header">
                <h2>توکن امنیتی نود ایجاد شده</h2>
                <button class="modal-close" onclick="closeModal('modal-show-token')"><i data-lucide="x"></i></button>
            </div>
            <p class="mb-20 text-warning" style="font-size: 14px;">توکن و کلید خصوصی را هر دو در نصب نود وارد کنید. این اطلاعات حساس می‌باشد، در حفظ و افشا نشدن آنها دقت کنید.</p>
            <div class="form-group">
                <label>Node Token</label>
                <div style="display:flex; gap:8px; align-items:center;">
                    <input type="text" id="generated-token-input" class="form-input" readonly style="text-align: center; font-size: 14px; font-weight: bold; border-color: var(--accent-blue);">
                    <button type="button" class="btn w-auto p-10 btn-purple" onclick="copyFieldValue('generated-token-input')">کپی</button>
                </div>
            </div>
            <div class="form-group">
                <label>Node Private Key</label>
                <div style="display:flex; gap:8px; align-items:center;">
                    <input type="text" id="generated-private-key-input" class="form-input" readonly style="text-align: center; font-size: 13px; font-weight: bold; border-color: var(--accent-purple); direction:ltr;">
                    <button type="button" class="btn w-auto p-10 btn-purple" onclick="copyFieldValue('generated-private-key-input')">کپی</button>
                </div>
            </div>
            <div class="form-group">
                <label>Installer Values</label>
                <div style="display:flex; gap:8px; align-items:flex-start;">
                    <textarea id="generated-node-setup-input" class="form-input" readonly rows="5" style="font-family: monospace; font-size: 13px; direction:ltr; text-align:left; resize: vertical;"></textarea>
                    <button type="button" class="btn w-auto p-10 btn-purple" onclick="copyFieldValue('generated-node-setup-input')">کپی</button>
                </div>
            </div>
            <button class="btn mt-20" onclick="closeModal('modal-show-token')">تایید و بستن</button>
        </div>
    </div>
    <div id="modal-show-config" class="modal">
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2>کانفیگ موتور تانلینگ (Engine Config)</h2>
                <button class="modal-close" onclick="closeModal('modal-show-config')"><i data-lucide="x"></i></button>
            </div>
            <div class="form-group">
                <textarea id="engine-config-content" class="form-input" readonly rows="15" style="font-family: monospace; font-size: 13px; text-align: left; direction: ltr; resize: none;"></textarea>
            </div>
            <button class="btn" onclick="closeModal('modal-show-config')">بستن</button>
        </div>
    </div>
    <div id="modal-node-ssh" class="modal">
        <div class="modal-content" style="max-width: 980px;">
            <div class="modal-header">
                <h2>اتصال و کنترل SSH نود</h2>
                <button class="modal-close" onclick="closeSshTerminal(true); closeModal('modal-node-ssh')"><i data-lucide="x"></i></button>
            </div>
            <form id="form-node-ssh">
                <div class="compact-grid">
                    <div class="form-group">
                        <label>نود</label>
                        <select id="ssh-node-id" class="form-input" onchange="fillSshFromNode()"></select>
                    </div>
                    <div class="form-group">
                        <label>هاست / IP</label>
                        <input id="ssh-host" class="form-input" placeholder="192.0.2.10">
                    </div>
                    <div class="form-group">
                        <label>پورت</label>
                        <input id="ssh-port" type="number" class="form-input" value="22">
                    </div>
                    <div class="form-group">
                        <label>نام کاربری</label>
                        <input id="ssh-username" class="form-input" value="root">
                    </div>
                    <div class="form-group">
                        <label>روش احراز هویت</label>
                        <select id="ssh-auth-method" class="form-input" onchange="toggleSshAuthFields()">
                            <option value="password">رمز عبور</option>
                            <option value="key">کلید خصوصی</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Timeout ثانیه</label>
                        <input id="ssh-timeout" type="number" class="form-input" value="15">
                    </div>
                </div>
                <div id="ssh-password-group" class="form-group">
                    <label>رمز عبور</label>
                    <input id="ssh-password" type="password" class="form-input" autocomplete="new-password">
                </div>
                <div id="ssh-key-group" class="form-group hidden">
                    <label>کلید خصوصی</label>
                    <textarea id="ssh-private-key" class="form-input" rows="5" style="font-family: monospace; direction:ltr; text-align:left;"></textarea>
                </div>
                <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer;">
                    <input id="ssh-save" type="checkbox" style="width:18px;height:18px;">
                    ذخیره رمزنگاری‌شده مشخصات اتصال برای این نود
                </label>
                <div class="flex-between gap-10 mt-20" style="justify-content:flex-start; flex-wrap:wrap;">
                    <button type="submit" class="btn w-auto btn-cyan">اتصال ترمینال</button>
                    <button type="button" class="btn w-auto p-10" onclick="sendSshTerminalInput('\u0003')">Ctrl+C</button>
                    <button type="button" class="btn w-auto p-10 btn-danger" onclick="closeSshTerminal()">قطع اتصال</button>
                    <button type="button" class="btn w-auto p-10" onclick="saveSshOnly()">فقط ذخیره مشخصات</button>
                    <span id="ssh-status" class="tag-pill">آماده اتصال</span>
                </div>
                <div id="ssh-output" class="ssh-terminal mt-20" tabindex="0" spellcheck="false"></div>
            </form>
        </div>
    </div>
    <div id="modal-add-link" class="modal">
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2 id="link-modal-title">ایجاد تانل (لینک) جدید</h2>
                <button class="modal-close" onclick="closeModal('modal-add-link')"><i data-lucide="x"></i></button>
            </div>
            <form id="form-add-link">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div class="form-group">
                        <label>نام تانل</label>
                        <input type="text" id="link-name" class="form-input" placeholder="Tunnel-Tehran-Frankfurt" required>
                    </div>
                    <div class="form-group">
                        <label>تعداد اتصالات رزرو (Pool Size)</label>
                        <input type="number" id="link-pool-size" class="form-input" value="150" required>
                    </div>
                </div>

                <div class="glass-card advanced-link-field" style="padding:14px; margin-bottom:16px;">
                    <h3 class="mb-20">Transport Intelligence 2026</h3>
                    <div class="compact-grid">
                        <div class="form-group">
                            <label style="display:inline-flex;align-items:center;gap:8px;">
                                <input type="checkbox" id="link-adaptive-smux" checked>
                                Adaptive SMux
                            </label>
                            <small class="field-hint">Carrierها براساس stream فعال و فشار RAM/Thread بین حداقل و حداکثر تغییر می‌کنند.</small>
                        </div>
                        <div class="form-group">
                            <label>حداقل / حداکثر SMux connections</label>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                                <input type="number" id="link-smux-min-connections" class="form-input" min="1" max="16" value="2">
                                <input type="number" id="link-smux-max-connections" class="form-input" min="1" max="16" value="8">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>stream لازم برای افزایش Carrier</label>
                            <input type="number" id="link-smux-min-streams" class="form-input" min="1" max="1024" value="8">
                        </div>
                        <div class="form-group">
                            <label style="display:inline-flex;align-items:center;gap:8px;">
                                <input type="checkbox" id="link-smux-padding" checked>
                                Padding روی SMux
                            </label>
                        </div>
                        <div class="form-group">
                            <label style="display:inline-flex;align-items:center;gap:8px;">
                                <input type="checkbox" id="link-ech-enabled">
                                ECH برای sing-box
                            </label>
                            <input type="text" id="link-ech-query-server-name" class="form-input mt-20" placeholder="public-name.example.com">
                            <textarea id="link-ech-config" class="form-input mt-20" rows="3" dir="ltr" placeholder="ECHConfigList (optional when DNS HTTPS/SVCB is available)"></textarea>
                        </div>
                        <div class="form-group">
                            <label>XHTTP + REALITY mode</label>
                            <select id="link-xhttp-mode" class="form-input">
                                <option value="auto">Auto based on path quality</option>
                                <option value="packet-up">packet-up — سازگاری بیشتر</option>
                                <option value="stream-up">stream-up</option>
                                <option value="stream-one">stream-one</option>
                            </select>
                            <label style="display:inline-flex;align-items:center;gap:8px;margin-top:10px;">
                                <input type="checkbox" id="link-xhttp-auto-select" checked>
                                انتخاب خودکار mode
                            </label>
                        </div>
                        <div class="form-group">
                            <label>MASQUE mode</label>
                            <select id="link-masque-mode" class="form-input">
                                <option value="connect-udp">CONNECT-UDP — RFC 9298</option>
                                <option value="connect-ip">CONNECT-IP — RFC 9484 (experimental / capability-gated)</option>
                            </select>
                            <input type="text" id="link-masque-token" class="form-input mt-20" placeholder="Bearer token (auto if empty)">
                        </div>
                        <div class="form-group">
                            <label style="display:inline-flex;align-items:center;gap:8px;">
                                <input type="checkbox" id="link-tcp-brutal-enabled">
                                TCP Brutal (opt-in)
                            </label>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px;">
                                <input type="number" id="link-tcp-brutal-up" class="form-input" min="1" value="50" placeholder="Up Mbps">
                                <input type="number" id="link-tcp-brutal-down" class="form-input" min="1" value="100" placeholder="Down Mbps">
                            </div>
                            <small class="field-hint">فقط در صورت وجود ماژول brutal روی Linux فعال می‌شود؛ وضعیت در telemetry نود گزارش می‌شود.</small>
                        </div>
                    </div>
                </div>

                <div class="form-group">
                    <label>پروفایل آماده یا شخصی</label>
                    <select id="link-profile" class="form-input profile-native-select" onchange="applySelectedProfile()">
                        <option value="custom">شخصی / پیشرفته</option>
                    </select>
                    <div id="link-profile-picker" class="profile-picker">
                        <button type="button" id="profile-picker-button" class="profile-picker-button" onclick="toggleProfilePicker(event)">
                            <span class="profile-picker-selected">
                                <strong>شخصی / پیشرفته</strong>
                                <small>تنظیم دستی هسته، ترنسپورت و پارامترها</small>
                            </span>
                            <i data-lucide="chevron-down"></i>
                        </button>
                        <div id="profile-picker-menu" class="profile-picker-menu hidden"></div>
                    </div>
                </div>

                <div class="form-group">
                    <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="checkbox" id="link-easy-mode" style="width: 18px; height: 18px;" onchange="toggleEasyMode()">
                        Easy Mode برای ساخت سریع تانل
                    </label>
                    <small id="link-auto-port-status" style="display:block; margin-top:8px; color:var(--text-secondary);"></small>
                    <label id="link-easy-custom-ports-row" class="hidden" style="align-items:center;gap:8px;margin-top:12px;cursor:pointer;">
                        <input type="checkbox" id="link-easy-custom-ports" style="width:18px;height:18px;" onchange="toggleEasyCustomPorts()">
                        تغییر دستی Bridge/Sync Port در Easy Mode
                    </label>
                    <small id="link-easy-custom-ports-hint" class="field-hint hidden">پورت‌های دستی نیز پیش از ذخیره روی هر دو نود بررسی می‌شوند و در صورت اشغال بودن پذیرفته نخواهند شد.</small>
                </div>

                <div class="glass-card" style="padding:14px; margin-bottom:16px;">
                    <div class="compact-grid">
                        <div class="form-group">
                            <label>معماری انتقال دیتا</label>
                            <select id="link-data-plane-architecture" class="form-input" onchange="toggleDataPlaneOptions()">
                                <option value="per_user">Per-user Classic — یک اتصال برای هر کاربر</option>
                                <option value="adaptive_bonding">Adaptive Bonding — چند lane برای هر انتقال</option>
                                <option value="shared_mux">Shared Mux Pool — کاربران روی carrierهای مشترک</option>
                                <option value="smart_hybrid">Smart Hybrid — Mux + Bonding (پیشنهادی)</option>
                            </select>
                            <input type="checkbox" id="link-bonding-enabled" style="display:none;">
                            <small class="field-hint">3X-UI همچنان احراز هویت را انجام می‌دهد؛ پنل فقط streamهای جدا را از مسیر انتخاب‌شده عبور می‌دهد.</small>
                        </div>
                        <div class="form-group" id="link-mux-carriers-group">
                            <label>Carrierهای پایدار Shared Mux</label>
                            <select id="link-mux-carriers" class="form-input">
                                <option value="2">۲ carrier — کم‌مصرف</option>
                                <option value="3">۳ carrier — سبک</option>
                                <option value="4" selected>۴ carrier — متعادل</option>
                                <option value="6">۶ carrier — پیشنهادی Smart Hybrid</option>
                                <option value="8">۸ carrier — ظرفیت و افزونگی بالا</option>
                            </select>
                            <small class="field-hint">صدها stream منطقی روی این اتصال‌های سرور‌به‌سرور توزیع می‌شوند؛ قطع یک carrier فقط streamهای همان carrier را متاثر می‌کند.</small>
                        </div>
                        <div class="form-group" id="link-bonding-lanes-group">
                            <label>حداکثر lane برای هر session</label>
                            <select id="link-bonding-max-lanes" class="form-input">
                                <option value="2">۲ lane — کم‌مصرف</option>
                                <option value="4" selected>۴ lane — متعادل</option>
                                <option value="6">۶ lane — سریع</option>
                                <option value="8">۸ lane — پرسرعت</option>
                                <option value="10">۱۰ lane — تهاجمی</option>
                                <option value="12">۱۲ lane — بسیار تهاجمی</option>
                                <option value="16">۱۶ lane — حداکثر</option>
                            </select>
                            <small class="field-hint">در مسیر خلوت همین تعداد اتصال آماده می‌شود؛ با افزایش کاربران scheduler خودکار به ۱۲/۱۰/۸/۶/۴/۲/۱ lane کاهش می‌دهد.</small>
                        </div>
                    </div>
                </div>

                <div class="form-group">
                    <label>تگ‌های تانل</label>
                    <input type="text" id="link-tags" class="form-input" placeholder="video, vip, tehran">
                </div>
                <div class="form-group">
                    <label>دسته‌بندی نمایشی تانل</label>
                    <input type="text" id="link-category" class="form-input" placeholder="Production / Backup / Streaming">
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div class="form-group">
                        <label>انتخاب نود داخلی (Internal Node)</label>
                        <select id="link-iran-node" class="form-input" onchange="suggestNextLinkPorts()"></select>
                    </div>
                    <div class="form-group">
                        <label>انتخاب نود خارجی (External Node)</label>
                        <select id="link-foreign-node" class="form-input" onchange="suggestNextLinkPorts()"></select>
                    </div>
                </div>
                <div class="form-group">
                    <label>جهت برقراری تانل</label>
                    <select id="link-direction" class="form-input" onchange="updateDirectionExample(); suggestNextLinkPorts();">
                        <option value="external_to_internal">نود خارجی به نود داخلی (External -> Internal)</option>
                        <option value="internal_to_external">نود داخلی به نود خارجی (Internal -> External)</option>
                    </select>
                    <div id="direction-example" class="direction-example-card"></div>
                </div>
                <div class="form-group">
                    <div class="smart-test-panel">
                        <div class="flex-between gap-10" style="justify-content:flex-start; flex-wrap:wrap;">
                            <select id="smart-test-objective" class="form-input w-auto" style="min-width:190px;">
                                <option value="balanced">متعادل</option>
                                <option value="speed">اولویت سرعت</option>
                                <option value="stability">اولویت پایداری</option>
                                <option value="security">اولویت امنیت</option>
                            </select>
                            <button type="button" class="btn w-auto p-10" onclick="smartTestSelectedNodes()">تست هوشمند واقعی و پیشنهاد پروفایل</button>
                            <button type="button" class="btn w-auto p-10" onclick="quickSpaceTunnel()" style="background: linear-gradient(135deg, #10b981, #3b82f6);">بزن بریم فضا !</button>
                        </div>
                        <div id="smart-test-result" style="color:var(--text-secondary);">آماده تست مسیر واقعی بین دو نود</div>
                    </div>
                </div>
                <div class="compact-grid advanced-link-field">
                    <div class="form-group">
                        <label>هسته تانل</label>
                        <select id="link-engine" class="form-input" onchange="syncTunnelOptions()">
                            <option value="builtin">Built-in Reverse</option>
                            <option value="gost">GOST</option>
                            <option value="backhaul">Backhaul</option>
                            <option value="rathole">Rathole</option>
                            <option value="chisel">Chisel</option>
                            <option value="frp">FRP</option>
                            <option value="xray">Xray</option>
                            <option value="muxquantum">Mux/Quantum</option>
                            <option value="hysteria2">Hysteria 2 (UDP)</option>
                            <option value="singbox">sing-box</option>
                            <option value="tuic">TUIC</option>
                            <option value="masque">MASQUE / CONNECT-UDP</option>
                            <option value="naiveproxy">NaiveProxy</option>
                            <option value="shadowtls">ShadowTLS</option>
                            <option value="brook">Brook</option>
                            <option value="mieru">Mieru</option>
                            <option value="amneziawg">AmneziaWG v2</option>
                            <option value="wireguard">WireGuard</option>
                            <option value="ssh">SSH Forwarding</option>
                            <option value="stunnel">Stunnel TLS Wrap</option>
                            <option value="aead">AEAD Egress</option>
                            <option value="rawsock">Raw Socket</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>ترنسپورت</label>
                        <select id="link-transport" class="form-input" onchange="syncTransportTls()">
                            <option value="tcp">TCP</option>
                            <option value="udp">UDP</option>
                            <option value="ws">WebSocket</option>
                            <option value="wss">WebSocket TLS</option>
                            <option value="wsmux">WSMux</option>
                            <option value="grpc">gRPC</option>
                            <option value="tcpmux">TCPMux</option>
                            <option value="kcp">KCP</option>
                            <option value="quic">QUIC</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>شبکه</label>
                        <select id="link-network" class="form-input" onchange="syncNetworkMode()">
                            <option value="tcp">TCP</option>
                            <option value="udp">UDP</option>
                            <option value="tcp_udp">TCP + UDP</option>
                        </select>
                    </div>
                </div>
                
                <div id="link-port-fields" class="advanced-link-field" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div class="form-group">
                        <label>پورت پل ارتباطی (Bridge Port)</label>
                        <input type="number" id="link-bridge-port" class="form-input" value="7000" required>
                    </div>
                    <div class="form-group">
                        <label>پورت هماهنگ‌سازی (Sync Port)</label>
                        <input type="number" id="link-sync-port" class="form-input" value="7001" required>
                    </div>
                </div>

                <div class="form-group advanced-link-field">
                    <label>روش تانلینگ (Tunnel Mode)</label>
                    <select id="link-tunnel-mode" class="form-input" onchange="syncModeTransport()">
                        <option value="tcp">TCP Tunnel (پیشفرض و خام)</option>
                        <option value="udp">UDP Tunnel</option>
                        <option value="websocket">WebSocket Tunnel (شبیه‌ساز وب)</option>
                        <option value="http_obfs">HTTP Obfuscation (پوشش ترافیک معمولی)</option>
                        <option value="grpc">gRPC Tunnel</option>
                        <option value="tcpmux">TCPMux</option>
                        <option value="wsmux">WSMux</option>
                        <option value="kcp">KCP</option>
                        <option value="quic">QUIC</option>
                        <option value="vless_reality">Xray VLESS Reality</option>
                    </select>
                </div>
                
                <div class="form-group advanced-link-field">
                    <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="checkbox" id="link-tls-enabled" style="width: 18px; height: 18px;" onchange="toggleObfsOptions()">
                        امن‌سازی با پروتکل TLS (Secure Connection)
                    </label>
                </div>
                
                <!-- Advanced Parameters Section -->
                <div id="obfs-advanced-section" class="hidden" style="border-top: 1px solid var(--border-card); padding-top: 15px; margin-top: 15px;">
                    <h4 class="mb-20">تنظیمات پیشرفته مبهم‌سازی (Advanced Obfuscation)</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div class="form-group">
                            <label>آدرس Host هدر (مبهم‌سازی)</label>
                            <input type="text" id="link-obfs-host" class="form-input" value="speedtest.net">
                        </div>
                        <div class="form-group">
                            <label>مسیر درخواست (Path)</label>
                            <input type="text" id="link-obfs-path" class="form-input" value="/tunnel">
                        </div>
                    </div>
                    <div class="form-group" id="tls-sni-group">
                        <label>مقدار SNI در پروتکل TLS</label>
                        <input type="text" id="link-tls-sni" class="form-input" value="speedtest.net">
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
                        <div class="form-group">
                            <label>Padding Min</label>
                            <input type="number" id="link-padding-min" class="form-input" value="0">
                        </div>
                        <div class="form-group">
                            <label>Padding Max</label>
                            <input type="number" id="link-padding-max" class="form-input" value="0">
                        </div>
                        <div class="form-group">
                            <label>Jitter ms</label>
                            <input type="number" id="link-jitter-ms" class="form-input" value="0">
                        </div>
                        <div class="form-group">
                            <label>Keepalive sec</label>
                            <input type="number" id="link-keepalive" class="form-input" value="25">
                        </div>
                    </div>
                    <div id="xray-options" class="hidden">
                        <h4 class="mb-20">تنظیمات Xray (VLESS Reality)</h4>
                        <div class="compact-grid">
                            <input id="link-xray-protocol" class="form-input" value="vless" placeholder="Protocol (vless)">
                            <input id="link-xray-security" class="form-input" value="reality" placeholder="Security (reality)">
                            <input id="link-xray-flow" class="form-input" value="xtls-rprx-vision" placeholder="Flow (xtls-rprx-vision)">
                            <input id="link-xray-uuid" class="form-input" placeholder="UUID (auto if empty)">
                            <input id="link-xray-sni" class="form-input" value="www.microsoft.com" placeholder="SNI / ServerName (e.g. microsoft.com)">
                            <input id="link-xray-shortid" class="form-input" placeholder="ShortId (auto if empty)">
                            <input id="link-xray-public-key" class="form-input" placeholder="Public Key (auto if empty)">
                            <input id="link-xray-private-key" class="form-input" placeholder="Private Key (auto if empty)">
                        </div>
                    </div>
                </div>

                <div id="engine-advanced-section" class="advanced-link-field hidden" style="border-top: 1px solid var(--border-card); padding-top: 15px; margin-top: 15px;">
                    <div class="form-group">
                        <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="link-native-engine-enabled" style="width: 18px; height: 18px;">
                            اجرای واقعی موتور انتخاب‌شده (برای Hysteria2: QUIC/UDP پرسرعت)
                        </label>
                        <small class="field-hint">اگر خاموش باشد، مسیر سازگار قدیمی Built-in استفاده می‌شود. برای مهاجرت امن ابتدا روی یک تانل فعال کنید.</small>
                    </div>
                    <div class="compact-grid">
                        <input id="link-hysteria-up-mbps" class="form-input" type="number" min="1" max="1000" value="30" placeholder="Hysteria upload Mbps">
                        <input id="link-hysteria-down-mbps" class="form-input" type="number" min="1" max="1000" value="50" placeholder="Hysteria download Mbps">
                    </div>
                    <div id="ssh-options" class="hidden">
                        <h4 class="mb-20">تنظیمات SSH Forwarding</h4>
                        <div class="compact-grid">
                            <input id="link-ssh-user" class="form-input" value="root" placeholder="SSH User">
                            <input id="link-ssh-port" class="form-input" type="number" value="22" placeholder="SSH Port">
                            <input id="link-ssh-bind-host" class="form-input" value="0.0.0.0" placeholder="Bind Host">
                            <input id="link-ssh-identity-file" class="form-input" value="/opt/p00rija/ssh/id_ed25519" placeholder="Identity File">
                            <input id="link-ssh-target-host" class="form-input" value="127.0.0.1" placeholder="Target Host">
                            <input id="link-ssh-target-port" class="form-input" type="number" value="443" placeholder="Target Port">
                        </div>
                        <div class="form-group">
                            <label>Jump Hosts / Bastions (-J)</label>
                            <input id="link-ssh-jump-hosts" class="form-input" placeholder="bastion1.example.com,bastion2.example.com">
                            <small class="field-hint">برای Multi-Hop چند Bastion را با کاما جدا کن.</small>
                        </div>
                    </div>
                    <div id="stunnel-options" class="hidden">
                        <h4 class="mb-20">تنظیمات Stunnel TLS Wrapping</h4>
                        <div class="compact-grid">
                            <input id="link-stunnel-cert-path" class="form-input" value="/opt/p00rija/certs/stunnel.crt" placeholder="Certificate Path">
                            <input id="link-stunnel-key-path" class="form-input" value="/opt/p00rija/certs/stunnel.key" placeholder="Private Key Path">
                            <label class="inline-check"><input id="link-stunnel-verify" type="checkbox"> Verify peer certificate</label>
                        </div>
                    </div>
                    <div id="wireguard-options" class="hidden">
                        <h4 class="mb-20">تنظیمات WireGuard سریع</h4>
                        <div class="compact-grid">
                            <input id="link-wg-address" class="form-input" value="10.77.0.1/24" placeholder="Server Address">
                            <input id="link-wg-client-address" class="form-input" value="10.77.0.2/32" placeholder="Client Address">
                            <input id="link-wg-mtu" class="form-input" type="number" value="1420" placeholder="MTU">
                            <input id="link-wg-allowed-ips" class="form-input" value="0.0.0.0/0, ::/0" placeholder="Allowed IPs">
                            <input id="link-wg-interface" class="form-input" placeholder="Interface name (auto)">
                        </div>
                        <small class="field-hint">برای بیشترین سرعت خام روی مسیر UDP تمیز. اگر UDP محدود یا پر Packet Loss است، Hysteria2/TUIC/AmneziaWG را تست کن.</small>
                    </div>
                    <div id="aead-options" class="hidden">
                        <h4 class="mb-20">تنظیمات AEAD و خروجی کلاینت</h4>
                        <div class="compact-grid">
                            <select id="link-aead-cipher" class="form-input">
                                <option value="aes-128-gcm">AES-128-GCM</option>
                                <option value="aes-256-gcm">AES-256-GCM</option>
                                <option value="chacha20-poly1305">ChaCha20-Poly1305</option>
                            </select>
                            <input id="link-aead-key" class="form-input" placeholder="AEAD Key Hex (auto if empty)">
                            <select id="link-egress-mode" class="form-input">
                                <option value="port_forward">Port Forwarding</option>
                                <option value="socks5">SOCKS5 Proxy</option>
                            </select>
                            <input id="link-socks5-username" class="form-input" placeholder="SOCKS5 Username (optional)">
                            <input id="link-socks5-password" class="form-input" type="password" placeholder="SOCKS5 Password (optional)">
                        </div>
                    </div>
                    <div id="rawsock-options" class="hidden">
                        <h4 class="mb-20">تنظیمات Raw Socket</h4>
                        <div class="compact-grid">
                            <input id="link-raw-protocol" class="form-input" type="number" value="253" placeholder="IP Protocol Number">
                            <input id="link-raw-mtu" class="form-input" type="number" value="1200" placeholder="MTU">
                            <input id="link-raw-packet-mark" class="form-input" placeholder="Packet Mark">
                        </div>
                        <small class="field-hint">این حالت به root یا CAP_NET_RAW نیاز دارد و بهتر است فقط بعد از تست لَب و محدودسازی firewall فعال شود.</small>
                    </div>
                </div>
                
                <button type="submit" id="link-submit-button" class="btn mt-20">ایجاد تانل</button>
            </form>
        </div>
    </div>

    <div id="modal-sync-xui" class="modal">
        <div class="modal-content" style="max-width: 500px;">
            <div class="modal-header">
                <h2>همگام‌سازی از X-UI</h2>
                <button class="modal-close" onclick="closeModal('modal-sync-xui')"><i data-lucide="x"></i></button>
            </div>
            <form id="form-sync-xui">
                <input type="hidden" id="sync-xui-link-id">
                <div class="form-group">
                    <label>آدرس پنل (مثال: http://192.168.1.10:2053)</label>
                    <input type="url" id="sync-xui-url" class="form-input" required>
                </div>
                <div class="compact-grid">
                    <div class="form-group">
                        <label>نام کاربری</label>
                        <input type="text" id="sync-xui-username" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label>رمز عبور</label>
                        <input type="password" id="sync-xui-password" class="form-input" required>
                    </div>
                </div>
                <button type="submit" class="btn mt-20">شروع همگام‌سازی پورت‌ها</button>
            </form>
        </div>
    </div>
    <script>
        let token = localStorage.getItem('token');
        let currentTab = 'dashboard';
        let charts = {};
        let categoryCharts = {};
        let nodeResourceCharts = {};
        let linkGuardianMessages = {};
        let autoGuardianTimer = null;
        let sessionsPanelOpen = false;
        let sessionsLastRefresh = 0;
        let threadsPanelOpen = false;
        let threadsLastRefresh = 0;
        let lastLinksSignature = '';
        let lastProfilesSignature = '';
        let autoRefreshTimer = null;
        let autoRefreshInFlight = false;
        const COLOR_ACTIVE = '#10b981';
        const COLOR_DOWNLOAD = '#3b82f6';
        const COLOR_UPLOAD = '#7c5cff';
        let linkCategoryOpenStates = {};
        try {
            linkCategoryOpenStates = JSON.parse(localStorage.getItem('p00rija_link_category_open') || '{}') || {};
        } catch (err) {
            linkCategoryOpenStates = {};
        }
        let profileCategoryOpenStates = {};
        try {
            profileCategoryOpenStates = JSON.parse(localStorage.getItem('p00rija_profile_category_open') || '{}') || {};
        } catch (err) {
            profileCategoryOpenStates = {};
        }
        let statusInterval = null;
        let latestStatus = {};
        let currentSpeedTestJobId = '';
        let speedTestPollTimer = null;
        let engineUpdateStatuses = {};
        let nodeVersionChecks = {};
        let currentLang = localStorage.getItem('p00rija_lang') || 'fa';
        let currentTheme = localStorage.getItem('p00rija_theme') || 'dark';
        let currentFont = localStorage.getItem('p00rija_font') || 'vazirmatn';
        let sshTerminalSessionId = null;
        let sshTerminalPoller = null;

        const translations = {
            dashboard: { fa: 'داشبورد', en: 'Dashboard' },
            nodes: { fa: 'مدیریت سرورها', en: 'Nodes' },
            links: { fa: 'مدیریت تانل‌ها', en: 'Tunnels' },
            logs: { fa: 'لاگ‌های سیستم', en: 'Logs' },
            settings: { fa: 'تنظیمات', en: 'Settings' },
            monitor: { fa: 'مانیتورینگ', en: 'Monitor' },
            appearance: { fa: 'ظاهر و زبان', en: 'Appearance' },
            help: { fa: 'راهنما', en: 'Help' },
            about: { fa: 'درباره من', en: 'About' },
            online: { fa: 'آنلاین', en: 'Online' },
            offline: { fa: 'آفلاین', en: 'Offline' },
            connected: { fa: 'برقرار', en: 'Connected' },
            disconnected: { fa: 'قطع', en: 'Disconnected' },
            internal: { fa: 'داخلی', en: 'Internal' },
            external: { fa: 'خارجی', en: 'External' },
            delete: { fa: 'حذف', en: 'Delete' },
            close: { fa: 'قطع', en: 'Close' }
        };

        function t(key) {
            return translations[key]?.[currentLang] || key;
        }

        function tx(fa, en) {
            return currentLang === 'en' ? en : fa;
        }

        function applyPreferences() {
            document.body.classList.remove('theme-light', 'theme-cyberpunk', 'theme-forest', 'theme-ocean', 'font-vazirmatn', 'font-sahel', 'font-shabnam', 'font-inter', 'font-system', 'font-byekan');
            if (currentTheme !== 'dark') document.body.classList.add(`theme-${currentTheme}`);
            document.body.classList.add(`font-${currentFont}`);
            document.documentElement.lang = currentLang;
            document.documentElement.dir = currentLang === 'fa' ? 'rtl' : 'ltr';
            document.title = tx('پنل مدیریت P00RIJA TUNNEL', 'P00RIJA TUNNEL Management Panel');
            ['language-select', 'appearance-language', 'login-language-select'].forEach(id => { const el = document.getElementById(id); if (el) el.value = currentLang; });
            ['theme-select', 'appearance-theme', 'login-theme-select'].forEach(id => { const el = document.getElementById(id); if (el) el.value = currentTheme; });
            ['font-select', 'appearance-font'].forEach(id => { const el = document.getElementById(id); if (el) el.value = currentFont; });
            applyStaticTranslations();
            applyAttributeTranslations();
        }

        const staticEnglish = {
            'پنل مدیریت P00RIJA TUNNEL': 'P00RIJA TUNNEL Management Panel',
            'فارسی': 'Persian',
            'تیره': 'Dark',
            'روشن': 'Light',
            'سایبرپانک': 'Cyberpunk',
            'جنگل': 'Forest',
            'اقیانوس': 'Ocean',
            'سیستم': 'System',
            'منو': 'Menu',
            'رفرش: خاموش': 'Refresh: Off',
            'رفرش: 1s': 'Refresh: 1s',
            'رفرش: 3s': 'Refresh: 3s',
            'رفرش: 5s': 'Refresh: 5s',
            'رفرش: 10s': 'Refresh: 10s',
            'رفرش: 30s': 'Refresh: 30s',
            'رفرش: 60s': 'Refresh: 60s',
            'نام کاربری': 'Username',
            'کلمه عبور': 'Password',
            'کد دو مرحله‌ای (اختیاری)': 'Two-factor code (optional)',
            'ورود به پنل': 'Sign in',
            'داشبورد': 'Dashboard',
            'مدیریت سرورها': 'Nodes',
            'مدیریت تانل‌ها': 'Tunnels',
            'لاگ‌های سیستم': 'Logs',
            'مانیتورینگ': 'Monitor',
            'ظاهر و زبان': 'Appearance',
            'تنظیمات': 'Settings',
            'راهنما': 'Help',
            'درباره من': 'About',
            'خروج': 'Logout',
            'کل سرورها': 'Total nodes',
            'تانل‌های فعال': 'Active tunnels',
            'ترافیک شبکه (Rx/Tx)': 'Network traffic (Rx/Tx)',
            'تردهای فعال': 'Active threads',
            'وضعیت سیستم میزبان پنل': 'Panel host system status',
            'ترافیک عبوری شبکه (Live)': 'Live network traffic',
            'اتصالات فعال تانل': 'Active tunnel connections',
            'P00RIJA PANEL فعال است': 'P00RIJA PANEL is active',
            'لیست نودها': 'Node list',
            'افزودن خودکار نودهای نمونه': 'Auto add starter nodes',
            'افزودن نود جدید': 'Add node',
            'آپدیت همه نودها': 'Update all nodes',
            'اتصال و کنترل SSH نود': 'Node SSH control',
            'ویرایش نود': 'Edit node',
            'ذخیره تغییرات': 'Save changes',
            'آپدیت نود': 'Update node',
            'آخرین آپدیت': 'Last update',
            'موفق': 'Success',
            'ناموفق': 'Failed',
            'اعمال‌شده': 'Applied',
            'AmneziaWG v2': 'AmneziaWG v2',
            'Reverse TCP Tunnel': 'Reverse TCP Tunnel',
            'تانل معکوس TCP': 'Reverse TCP',
            'نام سرور': 'Server name',
            'نقش': 'Role',
            'آدرس IP': 'IP address',
            'وضعیت': 'Status',
            'منابع سرور': 'Server resources',
            'ترافیک': 'Traffic',
            'تردها/کانکشن': 'Threads/connections',
            'عملیات': 'Actions',
            'لیست تانل‌ها (لینک‌ها)': 'Tunnel links',
            'افزودن تانل جدید': 'Add tunnel',
            'خروجی CSV': 'Export CSV',
            'زمان ثبت': 'Time',
            'منبع': 'Source',
            'سطح لاگ': 'Log level',
            'شرح لاگ': 'Log message',
            'مانیتورینگ سشن‌ها، تردها و پروسس‌ها': 'Sessions, threads and process monitoring',
            'بروزرسانی': 'Refresh',
            'سشن‌های فعال تانل': 'Active tunnel sessions',
            'برای مشاهده و بروزرسانی، منو را باز کنید': 'Open to view and refresh sessions',
            'برای مشاهده و بروزرسانی تردها، منو را باز کنید': 'Open to view and refresh threads',
            'در حال بروزرسانی سشن‌ها...': 'Refreshing sessions...',
            'خطا در بروزرسانی سشن‌ها': 'Session refresh failed',
            'سشن فعالی وجود ندارد': 'No active sessions',
            'در حال بروزرسانی تردها...': 'Refreshing threads...',
            'خطا در بروزرسانی تردها': 'Thread refresh failed',
            'ترد فعالی وجود ندارد': 'No active threads',
            'گروه ترد': 'Thread group',
            'پروسس‌های سیستم': 'System processes',
            'مدیریت منابع سرور': 'Server resource management',
            'مدیریت هوشمند تردها': 'Smart thread management',
            'نگهبان هوشمند تانل‌ها': 'Smart tunnel guardian',
            'این بخش همه تانل‌ها را از نظر سشن فعال، worker آماده، فشار thread و وضعیت engine پایش می‌کند و برای هر لینک اقدام پیشنهادی می‌دهد.': 'This section monitors every tunnel for active sessions, ready workers, thread pressure, and engine state, then suggests an action per link.',
            'مرکز هوشمند عملیات ۲۰۲۶': '2026 Smart Operations Center',
            'نگهبان خودکار: خاموش': 'Auto guardian: Off',
            'نگهبان خودکار: روشن': 'Auto guardian: On',
            'پیشنهادهای اجرایی': 'Operational recommendations',
            'رادار تانلینگ ۲۰۲۶': '2026 tunneling radar',
            'هماهنگی نسخه نودها': 'Node version sync',
            'امتیاز SLA تانل‌ها': 'Tunnel SLA score',
            'ریسک منابع': 'Resource risk',
            'نودهای آنلاین': 'Online nodes',
            'هماهنگ': 'Aligned',
            'نیازمند آپدیت': 'Needs update',
            'اجرای پیشنهاد': 'Run recommendation',
            'تحقیقاتی': 'Research',
            'کاندید اجرا': 'Implementation candidate',
            'پاک‌سازی سشن‌های Idle': 'Clean idle sessions',
            'پاک‌سازی RAM/GC': 'Clean RAM/GC',
            'کاهش فشار ترد/RAM': 'Reduce thread/RAM pressure',
            'بهینه‌سازی کامل منابع': 'Full resource optimization',
            'ظاهر، فونت و زبان': 'Appearance, font and language',
            'زبان پنل': 'Panel language',
            'تم رنگی': 'Theme',
            'فونت': 'Font',
            'پروفایل‌های تانل': 'Tunnel profiles',
            'آماده + شخصی': 'Preset + Custom',
            'پروفایل‌ها قالب آماده برای پر کردن Engine، Transport، TLS، SNI، Pool و پارامترهای پیشرفته هستند. سه آیکون رنگی وضعیت سرعت، امنیت و پایداری را نشان می‌دهند تا قبل از ساخت تانل سریع‌تر انتخاب کنید.': 'Profiles are templates that fill Engine, Transport, TLS, SNI, Pool, and advanced parameters. Three color-coded icons show speed, security, and stability so you can choose faster before creating a tunnel.',
            'ساخت پروفایل شخصی': 'Create custom profile',
            'این بخش برای ساخت قالب اختصاصی است. بعد از ذخیره، همین پروفایل در افزودن تانل با آیکون‌های سرعت، امنیت و پایداری نمایش داده می‌شود.': 'Use this section to create your own template. After saving, it appears in Add Tunnel with speed, security, and stability icons.',
            'نام پروفایل': 'Profile name',
            'نامی که بعداً در لیست پروفایل‌ها و picker تانل می‌بینید.': 'The name shown later in the profile list and tunnel picker.',
            'هسته اجرا': 'Runtime core',
            'Core یا ابزار اصلی که کانفیگ تانل بر اساس آن ساخته و روی نودها اجرا می‌شود.': 'The core/tool used to generate and run the tunnel config on nodes.',
            'مود تانل': 'Tunnel mode',
            'الگوی ارتباطی و پوشش ترافیک؛ مثل WebSocket، gRPC، REALITY، XHTTP یا MASQUE.': 'Connection and camouflage pattern, such as WebSocket, gRPC, REALITY, XHTTP, or MASQUE.',
            'Pool رزرو': 'Reserve pool',
            'تعداد اتصال آماده. روی سرور کم‌منبع عدد کمتر فشار RAM و thread را پایین‌تر نگه می‌دارد.': 'Number of ready connections. Lower values reduce RAM and thread pressure on low-resource servers.',
            'آماده': 'Ready',
            'هدف': 'Target',
            'زنده': 'Alive',
            'پاک‌شده': 'Reaped',
            'فشار': 'Pressure',
            'متوقف': 'Paused',
            'تانلی برای نمایش نیست': 'No tunnels to show',
            'پیشنهاد نگهبان': 'Guardian suggestion',
            'اجرای نگهبان لینک': 'Run link guardian',
            'نگهبان لینک اجرا شد': 'Link guardian queued',
            'در حال اجرای نگهبان لینک...': 'Running link guardian...',
            'workerهای پاک‌شده': 'reaped workers',
            'همه چیز عادی است': 'Everything looks normal',
            'تانل متوقف است': 'Tunnel is paused',
            'نودها یا engine را بررسی کنید': 'Check nodes or engine',
            'پاک‌سازی رزروهای idle': 'Clean idle reserves',
            'کاهش فشار ترد': 'Reduce thread pressure',
            'پایش پروسس engine': 'Watch engine process',
            'ارسال دستور بستن': 'Send close command',
            'دستور بسته شدن برای نود ارسال شد.': 'Close command was queued for the node.',
            'سشن بسته شد.': 'Session closed.',
            'نامی که در لیست پروفایل‌ها می‌بینید': 'Name shown in the profile list',
            'نام دامنه‌ای که برای TLS، SNI یا ظاهر ترافیک وب استفاده می‌شود.': 'Domain name used for TLS, SNI, or web-like traffic appearance.',
            'مسیر HTTP/WebSocket/gRPC که برای پوشش ترافیک و routing سمت وب استفاده می‌شود.': 'HTTP/WebSocket/gRPC path used for traffic cover and web-side routing.',
            'تاخیر تصادفی کوچک برای کم کردن الگوی ثابت بسته‌ها؛ مقدار زیاد روی سرعت اثر می‌گذارد.': 'Small random delay to reduce fixed packet patterns; high values affect speed.',
            'ورود پروفایل‌ها': 'Import profiles',
            'Profile name': 'Profile name',
            'ترنسپورت': 'Transport',
            'شبکه': 'Network',
            'رمز عبور': 'Password',
            'کلید خصوصی': 'Private key',
            'دستور': 'Command',
            'هاست / IP': 'Host / IP',
            'پورت': 'Port',
            'PID': 'PID',
            'هسته‌های CPU': 'CPU cores',
            'RAM (آزاد / کل)': 'RAM (Free / Total)',
            'Swap (آزاد / کل)': 'Swap (Free / Total)',
            'دیسک (آزاد / کل)': 'Disk (Free / Total)',
            'بار سیستم / آپ‌تایم': 'Load / Uptime',
            'پروسس پنل': 'Panel process',
            'نام': 'Name',
            'RSS': 'RSS',
            'تردها': 'Threads',
            'سشن‌ها': 'Sessions',
            'زمان CPU': 'CPU time',
            'CPU Cores': 'CPU cores',
            'RAM (Free / Total)': 'RAM (Free / Total)',
            'Swap (Free / Total)': 'Swap (Free / Total)',
            'Disk (Free / Total)': 'Disk (Free / Total)',
            'Load / Uptime': 'Load / Uptime',
            'Panel Process': 'Panel process',
            'Docker وضعیت': 'Docker status',
            'ذخیره پروفایل': 'Save profile',
            'خروجی پروفایل‌ها': 'Export profiles',
            'تنظیمات پنل': 'Panel settings',
            'تغییر مشخصات مدیریت': 'Admin credentials',
            'کلمه عبور جدید': 'New password',
            'بروزرسانی مشخصات ورود': 'Update login',
            'امنیت ورود': 'Login security',
            'فعال‌سازی ورود دو مرحله‌ای TOTP': 'Enable TOTP two-factor login',
            'فعال‌سازی بایومتریک مرورگر برای Quick Unlock': 'Enable browser biometric quick unlock',
            'ثبت تنظیمات امنیتی': 'Save security settings',
            'تنظیمات SSL/TLS وب پنل (HTTPS)': 'Panel SSL/TLS settings (HTTPS)',
            'فعال‌سازی HTTPS برای وب پنل': 'Enable HTTPS for panel',
            'ثبت تنظیمات SSL': 'Save SSL settings',
            "دریافت Certificate خودکار Let's Encrypt": "Automatic Let's Encrypt certificate",
            'مسیر Certificate (.pem)': 'Certificate path (.pem)',
            'مسیر Private Key (.pem)': 'Private key path (.pem)',
            'آدرس دامنه (مثال: panel.yourdomain.com)': 'Domain name (example: panel.yourdomain.com)',
            "ایمیل (جهت ثبت‌نام در Let's Encrypt)": "Email (for Let's Encrypt registration)",
            'دریافت و نصب گواهینامه SSL': 'Get and install SSL certificate',
            'اعمال تغییرات و ریستارت وب پنل': 'Apply changes and restart panel',
            '۱. در بخش مدیریت سرورها، نود داخلی و نود خارجی را ثبت کنید و توکن هر نود را در همان سرور وارد کنید.': '1. In Nodes, register an internal node and an external node, then enter each node token on that server.',
            '۲. در مدیریت تانل‌ها، یک پروفایل Easy/Hard/Resilient یا پروفایل شخصی انتخاب کنید، سپس Bridge/Sync port را بسازید.': '2. In Tunnels, choose an Easy/Hard/Resilient or custom profile, then create the Bridge/Sync ports.',
            '۳. در هر تانل، port forwarding اضافه کنید تا ورودی نود داخلی به سرویس مقصد روی نود خارجی وصل شود.': '3. Add port forwarding on each tunnel so internal-node input reaches the destination service on the external node.',
            '۴. در Monitor می‌توانید sessionهای تانل و پروسس‌های سیستم را ببینید و در صورت نیاز session یا process را قطع کنید.': '4. In Monitor, review tunnel sessions and system processes, then close a session or process when needed.',
            '۵. از Appearance می‌توانید زبان، تم، فونت و profile bundle را مدیریت کنید. PWA هم از همین پنل قابل install شدن است.': '5. In Appearance, manage language, theme, font, and profile bundles. The PWA can also be installed from the same panel.',
            '۶. نام کاربری و رمز پیش‌فرض دیتابیس تازه admin/admin است؛ در نصب wizard رمز جدید بگذارید و بعد از ورود آن را تغییر دهید.': '6. A fresh database defaults to admin/admin. Set a new password in the setup wizard and change it after login.',
            'P00RIJA TUNNEL یک پنل مدیریت تانل معکوس چندنودی برای اتصال پایدار نودهای داخلی و خارجی با پروفایل‌های قابل تنظیم، مانیتورینگ runtime و داشبورد دو زبانه است.': 'P00RIJA TUNNEL is a multi-node reverse tunnel control panel for stable internal/external node connectivity with configurable profiles, runtime monitoring, and a bilingual dashboard.',
            'توکن امنیتی نود ایجاد شده': 'Generated node security token',
            'این توکن فقط یکبار نمایش داده می‌شود. لطفاً آن را ذخیره کنید تا در راه‌اندازی کلاینت استفاده کنید.': 'This token is shown only once. Save it for node setup.',
            'توکن و کلید خصوصی را هر دو در نصب نود وارد کنید. این اطلاعات حساس می‌باشد، در حفظ و افشا نشدن آنها دقت کنید.': 'Enter both the token and private key during node installation. This information is sensitive; keep it protected and do not disclose it.',
            'تایید و بستن': 'Confirm and close',
            'ایجاد تانل': 'Create tunnel',
            'افزودن نود جدید': 'Add node',
            'نام نود (مثال: INTERNAL-Node-1)': 'Node name (example: INTERNAL-Node-1)',
            'نقش نود': 'Node role',
            'نود داخلی (Internal Node)': 'Internal node',
            'نود خارجی (External Node)': 'External node',
            'آدرس IP سرور': 'Server IP address',
            'ثبت نود جدید': 'Save node',
            'ویرایش نود': 'Edit node',
            'ذخیره تغییرات': 'Save changes',
            'ایجاد تانل (لینک) جدید': 'Create new tunnel link',
            'نام تانل': 'Tunnel name',
            'تعداد اتصالات رزرو (Pool Size)': 'Reserved connections (Pool Size)',
            'پروفایل آماده یا شخصی': 'Preset or custom profile',
            'انتخاب نود داخلی (Internal Node)': 'Select internal node',
            'انتخاب نود خارجی (External Node)': 'Select external node',
            'جهت برقراری تانل': 'Tunnel direction',
            'نود خارجی به نود داخلی (External -> Internal)': 'External node to internal node (External -> Internal)',
            'نود داخلی به نود خارجی (Internal -> External)': 'Internal node to external node (Internal -> External)',
            'این گزینه مشخص می‌کند کدام سمت اتصال اولیه را dial کند. برای مسیرهای بسته، جهتی را انتخاب کنید که سمت client امکان خروجی گرفتن دارد.': 'This option controls which side dials the initial connection. For restricted paths, choose the direction where the client side can make outbound connections.',
            'هسته تانل': 'Tunnel engine',
            'پورت پل ارتباطی (Bridge Port)': 'Bridge port',
            'پورت هماهنگ‌سازی (Sync Port)': 'Sync port',
            'روش تانلینگ (Tunnel Mode)': 'Tunnel mode',
            'TCP Tunnel (پیشفرض و خام)': 'TCP Tunnel (default raw mode)',
            'WebSocket Tunnel (شبیه‌ساز وب)': 'WebSocket Tunnel (web-like traffic)',
            'HTTP Obfuscation (پوشش ترافیک معمولی)': 'HTTP Obfuscation (normal traffic cover)',
            'امن‌سازی با پروتکل TLS (Secure Connection)': 'Secure with TLS protocol',
            'تنظیمات پیشرفته مبهم‌سازی (Advanced Obfuscation)': 'Advanced obfuscation settings',
            'آدرس Host هدر (مبهم‌سازی)': 'Header host address (obfuscation)',
            'مسیر درخواست (Path)': 'Request path',
            'مقدار SNI در پروتکل TLS': 'TLS SNI value',
            'تنظیمات Xray': 'Xray settings',
            'اتصال و کنترل SSH نود': 'Node SSH connection and control',
            'نود': 'Node',
            'روش احراز هویت': 'Authentication method',
            'Timeout ثانیه': 'Timeout seconds',
            'ذخیره رمزنگاری‌شده مشخصات اتصال برای این نود': 'Save encrypted connection details for this node',
            'اتصال و اجرا': 'Connect and run',
            'فقط ذخیره مشخصات': 'Save credentials only',
            'آماده اتصال': 'Ready to connect',
            'تگ‌های نود': 'Node tags',
            'تگ‌های تانل': 'Tunnel tags',
            'Easy Mode برای ساخت سریع تانل': 'Easy Mode for fast tunnel creation',
            'تغییر دستی Bridge/Sync Port در Easy Mode': 'Manually set Bridge/Sync ports in Easy Mode',
            'پورت‌های دستی نیز پیش از ذخیره روی هر دو نود بررسی می‌شوند و در صورت اشغال بودن پذیرفته نخواهند شد.': 'Manual ports are checked on both nodes before saving and are rejected if occupied.',
            'تست هوشمند و پیشنهاد پروفایل': 'Smart test and profile recommendation',
            'بزن بریم فضا !': 'Launch quick tunnel!',
            'آماده تست مسیر بین دو نود': 'Ready to test the path between two nodes',
            'کانفیگ موتور تانلینگ (Engine Config)': 'Tunneling engine config',
            'بستن': 'Close',
            'تست ارتباط سرور': 'Server connection test',
            'در حال تست ارتباط، چند لحظه صبر کنید...': 'Testing connection, please wait...',
            'مدیریت هسته‌ها (Engine Management)': 'Engine management',
            'هسته‌ها از پوشه آفلاین engines داخل image استفاده می‌کنند. نصب از GitHub فقط وقتی لازم است که اینترنت در دسترس باشد.': 'Engines are loaded from the offline engines folder inside the image. GitHub install is only needed when internet access is available.',
            'تنظیمات نمایش': 'Display settings',
            'تنظیمات شبکه': 'Network settings',
            'تنظیمات شبکه و هسته‌ها': 'Network and engine settings',
            'ممیزی ماژولار و آمادگی نصب': 'Modularity and install readiness audit',
            'این بخش ساختار ماژول‌ها، فایل‌های ضروری پکیج، وضعیت engineهای آفلاین و پیشنهادهای refactor بعدی را بررسی می‌کند.': 'This section checks module structure, required package files, offline engine status, and next refactor recommendations.',
            'اجرای ممیزی': 'Run audit',
            'برای بررسی ساختار و آمادگی پکیج، ممیزی را اجرا کنید.': 'Run the audit to check structure and package readiness.',
            'غیرفعال سازی IPv6 روی سیستم عامل': 'Disable IPv6 on the operating system',
            'زمان اعمال و ریست مجدد هسته (به دقیقه، 0 برای غیرفعال کردن)': 'Engine scheduled restart interval (minutes, 0 to disable)',
            'برای پایداری بیشتر، هسته‌ها می‌توانند به صورت زمان‌بندی شده ریست شوند تا حافظه و منابع آزاد شود.': 'For better stability, engines can be restarted on a schedule to release memory and resources.',
            'ثبت تنظیمات شبکه': 'Save network settings',
            'Runtime پنل': 'Panel runtime',
            'منابع نودها': 'Node resources',
            'پروسس‌های سیستم': 'System processes',
            'شناسه': 'ID',
            'تانل': 'Tunnel',
            'مقصد': 'Target',
            'پورت مقصد': 'Target port',
            'عمر': 'Age',
            'بیکاری': 'Idle',
            'نام': 'Name',
            'زمان CPU': 'CPU time',
            'بهینه‌سازی انجام شد': 'Optimization completed',
            'سشن‌های بسته‌شده': 'closed sessions',
            'فرمان نودها': 'node commands',
            'نودی برای نمایش نیست': 'No nodes to show',
            'نسخه:': 'Version:',
            'لایسنس:': 'License:',
            'گیت‌هاب: github.com/Poorija': 'GitHub: github.com/Poorija',
            'شخصی / پیشرفته': 'Custom / Advanced',
            'پاک‌سازی ثبت نشده': 'No cleanup yet',
            'آخرین پاک‌سازی': 'Last cleanup',
            'روی نود': 'On node',
            'ارسال دستور بستن': 'Send close command',
            'دستور بسته شدن برای نود ارسال شد.': 'Close command was queued for the node.',
            'پیشنهاد نگهبان': 'Guardian suggestion',
            'اجرای نگهبان لینک': 'Run link guardian',
            'نگهبان لینک اجرا شد': 'Link guardian queued',
            'در حال اجرای نگهبان لینک...': 'Running link guardian...',
            'workerهای پاک‌شده': 'reaped workers',
            'همه چیز عادی است': 'Everything looks normal',
            'تانل متوقف است': 'Tunnel is paused',
            'نودها یا engine را بررسی کنید': 'Check nodes or engine',
            'پاک‌سازی رزروهای idle': 'Clean idle reserves',
            'کاهش فشار ترد': 'Reduce thread pressure',
            'پایش پروسس engine': 'Watch engine process',
            'این سشن تانل بسته شود؟': 'Close this tunnel session?',
            'JSON پروفایل نامعتبر است.': 'Invalid profile JSON.',
            'پروفایل ذخیره شد.': 'Profile saved.',
            'پروفایل‌ها وارد شدند.': 'Profiles imported.',
            'آپدیت از گیت‌هاب': 'GitHub update',
            'آپدیت دستی از فایل': 'Manual file update',
            'انتخاب فایل': 'Choose file',
            'توقف': 'Stop',
            'ادامه': 'Resume',
            'ریست': 'Restart',
            'آماده': 'Ready',
            'غیرفعال': 'Disabled',
            'نصب نشده': 'Missing',
            'درباره من': 'About me',
            'راهنمای سریع داشبورد': 'Quick dashboard guide',
            'سناریو ۱: خارجی به داخلی': 'Scenario 1: External to Internal',
            'سناریو ۲: داخلی به خارجی': 'Scenario 2: Internal to External',
            'این حالت پیش‌فرض است. نود داخلی Bridge/Sync را گوش می‌دهد و نود خارجی اتصال‌های رزرو را به سمت داخلی می‌سازد.': 'This is the default mode. The internal node listens on Bridge/Sync, and the external node creates reserve connections toward the internal node.',
            'اگر خروجی گرفتن از نود داخلی بهتر از ورودی گرفتن روی آن است، این جهت را انتخاب کنید تا نود داخلی اتصال اولیه را به خارجی بزند.': 'If outbound connectivity from the internal node is more reliable than inbound connectivity to it, choose this direction so the internal node dials the external node.',
            'سمت listener تانل را اجرا نکرده است': 'The listener side has not started the tunnel',
            'سمت dialer تانل را اجرا نکرده است': 'The dialer side has not started the tunnel',
            'پورت ورودی روی سمت listener باز نشده است': 'Input port is not listening on the listener side',
            'نه اتصال رزرو آماده است و نه پل مستقیم سمت dialer باز است': 'No reserve worker is ready and dialer direct bridge is not listening',
            '۱. در مدیریت سرورها، ابتدا نودهای داخلی و خارجی را ثبت کنید. اگر یک سرور هم پنل است و هم نود داخلی، همان سرور را به عنوان Internal Node هم اضافه کنید تا در ساخت تانل قابل انتخاب باشد.': '1. In Nodes, register internal and external nodes first. If one server is both the panel and an internal node, add that same server as an Internal Node too so it can be selected when creating tunnels.',
            '۲. در مدیریت تانل‌ها، از پروفایل‌های آماده برای شروع سریع استفاده کنید. بعد از انتخاب پروفایل، Engine، Transport، Network، TLS، SNI، Path و Pool همچنان قابل تغییر هستند.': '2. In Tunnels, use preset profiles for a fast start. After choosing a profile, Engine, Transport, Network, TLS, SNI, Path, and Pool remain editable.',
            '۳. برای هر تانل Bridge Port و Sync Port روی نود داخلی باید آزاد و یکتا باشد. اگر پورت تکراری باشد، پنل قبل از ذخیره خطا می‌دهد.': '3. Each tunnel needs unique free Bridge and Sync ports on the internal node. The panel rejects duplicate ports before saving.',
            '۴. بعد از ساخت تانل، Port Forwarding را اضافه کنید. User/Internal Port همان پورتی است که روی نود داخلی باز می‌شود و Target Port به سرویس سمت نود خارجی اشاره می‌کند.': '4. After creating a tunnel, add port forwarding. User/Internal Port is opened on the internal node, and Target Port points to the service on the external node.',
            '۵. دکمه توقف تانل، تانل را از کانفیگ نودها خارج می‌کند و با ادامه دوباره به نودها تحویل داده می‌شود. برای اعمال عملی، چند ثانیه تا polling بعدی نود صبر کنید.': '5. Pause removes the tunnel from node configs; Resume sends it back to the nodes. Wait a few seconds for the next node polling cycle to apply it.',
            '۶. اگر TLS تانل فعال است، SNI و Host را هماهنگ انتخاب کنید. برای وب پنل، تنظیمات HTTPS در Settings فقط با مسیر Certificate و Key معتبر و ریستارت پنل کامل اعمال می‌شود.': '6. If tunnel TLS is enabled, keep SNI and Host aligned. For the web panel, HTTPS settings fully apply only with valid Certificate/Key paths and a panel restart.',
            '۷. نمودارهای Dashboard و وضعیت منابع/ترافیک مدیریت سرورها با Refresh Time بالای صفحه به صورت زنده به‌روزرسانی می‌شوند. برای تست فوری، مقدار ۳ ثانیه را انتخاب کنید.': '7. Dashboard charts and node resource/traffic status refresh live according to the Refresh Time at the top. Choose 3 seconds for quick testing.',
            '۸. در Monitor می‌توانید sessionهای فعال، مصرف RSS و تعداد threadها را ببینید و پاک‌سازی idle یا GC را اجرا کنید.': '8. In Monitor, review active sessions, RSS usage, and thread counts, then run idle cleanup or GC.',
            '۹. نام کاربری و رمز پیش‌فرض دیتابیس تازه admin/admin است؛ در نصب wizard رمز جدید بگذارید و بعد از ورود آن را تغییر دهید.': '9. A fresh database defaults to admin/admin. Set a new password in the setup wizard and change it after first login.',
            'P00RIJA TUNNEL برای مدیریت متمرکز تانل‌های معکوس در سناریوهای چندنودی ساخته شده است؛ جایی که پنل باید هم وضعیت سرورها را زنده ببیند، هم پروفایل‌های مختلف تانلینگ را کنترل کند، و هم امکان توقف، ادامه، و ویرایش عملیاتی تانل‌ها را بدون دستکاری دستی کانفیگ‌ها بدهد.': 'P00RIJA TUNNEL is built for centralized reverse-tunnel management in multi-node scenarios where the panel must watch server status live, control multiple tunneling profiles, and provide operational pause, resume, and editing without manual config edits.',
            'تمرکز پروژه': 'Project focus',
            'پایداری ارتباط، انتخاب هوشمند پروفایل، مانیتورینگ منابع، و مدیریت امن نودها با توکن و امضای درخواست.': 'Connection stability, smart profile selection, resource monitoring, and secure node management with tokens and signed requests.',
            'برای چه سناریویی؟': 'Designed for',
            'پنل مرکزی، نودهای داخلی، نودهای خارجی، شبکه‌های جدا، و تانل‌هایی که باید زیر بار واقعی قابل مشاهده و قابل کنترل باشند.': 'A central panel, internal nodes, external nodes, separate networks, and tunnels that must remain observable and controllable under real load.',
            'فونت‌ها به صورت stack داخلی تعریف شده‌اند و اگر فونت روی سیستم کاربر نصب باشد استفاده می‌شود؛ در غیر این صورت پنل به فونت امن سیستم برمی‌گردد.': 'Fonts are defined as local stacks. If a font exists on the user system it is used; otherwise the panel falls back to a safe system font.'
        };
        Object.assign(staticEnglish, {
            '3X-UI همچنان احراز هویت را انجام می‌دهد؛ پنل فقط streamهای جدا را از مسیر انتخاب‌شده عبور می‌دهد.': '3X-UI continues to handle authentication; the panel only carries isolated streams over the selected path.',
            'Adaptive Bonding — چند lane برای هر انتقال': 'Adaptive Bonding — multiple lanes per transfer',
            'Block length (byte، اختیاری)': 'Block length (bytes, optional)',
            'Carrierها براساس stream فعال و فشار RAM/Thread بین حداقل و حداکثر تغییر می‌کنند.': 'Carriers scale between the minimum and maximum based on active streams and RAM/thread pressure.',
            'Carrierهای پایدار Shared Mux': 'Stable Shared Mux carriers',
            'DNS-01 — بدون نیاز به پورت ۸۰': 'DNS-01 — no port 80 required',
            'ECH برای sing-box': 'ECH for sing-box',
            'HTTP-01 — نیازمند پورت ۸۰': 'HTTP-01 — requires port 80',
            'HTTPS اجباری برای وب پنل': 'Force HTTPS for the web panel',
            'Host عمومی پنل': 'Public panel host',
            'Host یا IP مقصد': 'Destination host or IP',
            'IP یا Hostname پنل': 'Panel IP or hostname',
            'Mesh بین تمام نودهای انتخابی': 'Mesh between all selected nodes',
            'Omit warm-up (ثانیه)': 'Omit warm-up (seconds)',
            'Padding روی SMux': 'SMux padding',
            'Per-user Classic — یک اتصال برای هر کاربر': 'Per-user Classic — one connection per user',
            'Shared Mux Pool — کاربران روی carrierهای مشترک': 'Shared Mux Pool — users share carriers',
            'Smart Hybrid — Mux + Bonding (پیشنهادی)': 'Smart Hybrid — Mux + Bonding (recommended)',
            'TCP window (اختیاری)': 'TCP window (optional)',
            'packet-up — سازگاری بیشتر': 'packet-up — better compatibility',
            'stream لازم برای افزایش Carrier': 'Streams required to add a carrier',
            'آدرس API پنل جدید برای نودها': 'New panel API address for nodes',
            'آدرس جدید پنل (اختیاری)': 'New panel address (optional)',
            'آدرس پنل (مثال: http://192.168.1.10:2053)': 'Panel address (example: http://192.168.1.10:2053)',
            'آماده تست مسیر واقعی بین دو نود': 'Ready to test the real path between two nodes',
            'آپلود': 'Upload',
            'اتصال ترمینال': 'Terminal connection',
            'اجرای واقعی موتور انتخاب‌شده (برای Hysteria2: QUIC/UDP پرسرعت)': 'Run the selected engine for real (Hysteria2: high-speed QUIC/UDP)',
            'ارائه‌دهنده DNS': 'DNS provider',
            'اعتبارسنجی و Restore': 'Validate and restore',
            'اعمال تنظیمات شبکه': 'Apply network settings',
            'اعمال تنظیمات نمایش': 'Apply display settings',
            'اعمال پورت‌ها و بازسازی پنل': 'Apply ports and rebuild panel',
            'افزودن پنل به‌عنوان نود': 'Add panel as a node',
            'انتخاب خودکار mode': 'Select mode automatically',
            'انتخاب فایل موجود داخل سرور': 'Select an existing server file',
            'انتخاب نودها': 'Select nodes',
            'انتخاب همه': 'Select all',
            'انتقال مستقیم به هاست جدید': 'Direct migration to a new host',
            'انتقال هسته‌های آفلاین': 'Transfer offline engines',
            'اولویت امنیت': 'Prioritize security',
            'اولویت سرعت': 'Prioritize speed',
            'اولویت پایداری': 'Prioritize stability',
            'اگر خاموش باشد، مسیر سازگار قدیمی Built-in استفاده می‌شود. برای مهاجرت امن ابتدا روی یک تانل فعال کنید.': 'When disabled, the legacy compatible Built-in path is used. Enable it on one tunnel first for a safe migration.',
            'این آدرس قبل از cutover به تمام نودهای آنلاین اعلام می‌شود. آدرس پنل فعلی به‌عنوان fallback روی نود باقی می‌ماند.': 'This address is announced to all online nodes before cutover. The current panel address remains on each node as a fallback.',
            'این حالت به root یا CAP_NET_RAW نیاز دارد و بهتر است فقط بعد از تست لَب و محدودسازی firewall فعال شود.': 'This mode requires root or CAP_NET_RAW and should only be enabled after lab testing and firewall restrictions.',
            'بارگذاری مستقیم از سیستم من': 'Upload directly from my device',
            'بازخوانی': 'Reload',
            'بازیابی پنل از بکاپ رمزگذاری‌شده': 'Restore panel from an encrypted backup',
            'برای Multi-Hop چند Bastion را با کاما جدا کن.': 'For Multi-Hop, separate multiple bastions with commas.',
            'برای بیشترین سرعت خام روی مسیر UDP تمیز. اگر UDP محدود یا پر Packet Loss است، Hysteria2/TUIC/AmneziaWG را تست کن.': 'Use this for maximum raw speed on a clean UDP path. If UDP is restricted or lossy, test Hysteria2, TUIC, or AmneziaWG.',
            'بررسی آپدیت همه هسته‌ها': 'Check all engine updates',
            'بررسی نسخه نودها': 'Check node versions',
            'بروزرسانی دستی': 'Manual update',
            'بکاپ شامل دیتابیس، همه نودها و تانل‌ها، توکن‌ها، کلیدها، Certificateها، تنظیمات و فایل‌های برنامه است و با AES-256 رمزگذاری می‌شود.': 'The backup includes the database, all nodes and tunnels, tokens, keys, certificates, settings, and application files, encrypted with AES-256.',
            'بکاپ موجود در سرور': 'Backup stored on the server',
            'بکاپ کامل و انتقال پنل': 'Full backup and panel migration',
            'بین دو نود انتخابی': 'Between two selected nodes',
            'ترتیب': 'Order',
            'تست هوشمند واقعی و پیشنهاد پروفایل': 'Real smart test and profile recommendation',
            'تغییر پورت، Docker mapping را روی میزبان بازسازی می‌کند. اگر پورت API تغییر کند، ابتدا آدرس جدید به نودهای آنلاین اعلام می‌شود.': 'Changing a port rebuilds the Docker mapping on the host. If the API port changes, the new address is announced to online nodes first.',
            'تنظیم دستی هسته، ترنسپورت و پارامترها': 'Manually configure the core, transport, and parameters',
            'تنظیمات AEAD و خروجی کلاینت': 'AEAD and client egress settings',
            'تنظیمات Raw Socket': 'Raw Socket settings',
            'تنظیمات SSH Forwarding': 'SSH forwarding settings',
            'تنظیمات Stunnel TLS Wrapping': 'Stunnel TLS wrapping settings',
            'تنظیمات WireGuard سریع': 'Fast WireGuard settings',
            'تنظیمات Xray (VLESS Reality)': 'Xray settings (VLESS Reality)',
            'حداقل / حداکثر SMux connections': 'Minimum / maximum SMux connections',
            'حداکثر lane برای هر session': 'Maximum lanes per session',
            'خطاها و جزئیات': 'Errors and details',
            'دانلود': 'Download',
            'دانلود بکاپ رمزگذاری‌شده': 'Download encrypted backup',
            'در حال آزمایش، صبر کنید...': 'Testing, please wait...',
            'در حالت فعال، صفحه ورود فقط از مسیر تصادفی زیر باز می‌شود و درخواست مستقیم Login بدون Gate معتبر با 404 پاسخ داده می‌شود. این قابلیت جلوی اسکن‌های عمومی را می‌گیرد، اما جایگزین محافظت IP/SNI نیست.': 'When enabled, the login page is available only at the random path below and direct login requests without a valid gate return 404. This reduces broad scanning but does not replace IP/SNI protection.',
            'در صورت اختلال و بسته شدن IPV6 این گزینه را فعال کنید تا ارتباط شبکه قطع نشود.': 'Enable this if IPv6 disruption or filtering causes network connectivity loss.',
            'در صورت نبود certificate معتبر، پنل به صورت خودکار certificate محلی می‌سازد.': 'If no valid certificate exists, the panel automatically creates a local certificate.',
            'در مسیر خلوت همین تعداد اتصال آماده می‌شود؛ با افزایش کاربران scheduler خودکار به ۱۲/۱۰/۸/۶/۴/۲/۱ lane کاهش می‌دهد.': 'On an uncongested path this many connections are prepared; as users increase, the scheduler automatically steps down through 12/10/8/6/4/2/1 lanes.',
            'دسته‌بندی نمایشی تانل': 'Tunnel display category',
            'دسته‌بندی نود': 'Node category',
            'ذخیره مسیر مدیریت': 'Save management path',
            'رمز SSH مقصد': 'Destination SSH password',
            'رمز بکاپ': 'Backup password',
            'رمز بکاپ (حداقل ۸ کاراکتر)': 'Backup password (at least 8 characters)',
            'رمز بکاپ انتقال': 'Migration backup password',
            'روش اعتبارسنجی ACME': 'ACME validation method',
            'زمان انتظار انتشار DNS (ثانیه)': 'DNS propagation wait time (seconds)',
            'ساخت Certificate جدید بر اساس آدرس واردشده': 'Create a new certificate for the entered address',
            'ساخت Certificate جدید برای Host مقصد': 'Create a new certificate for the destination host',
            'ساخت Certificate محلی برای IP یا Hostname': 'Create a local certificate for an IP or hostname',
            'ساخت مسیر تصادفی': 'Generate random path',
            'ساخت و اعمال Certificate محلی': 'Create and apply local certificate',
            'ساخت و دانلود بکاپ': 'Create and download backup',
            'سرورها / نودها': 'Servers / Nodes',
            'سنجش واقعی TCP/UDP بین نودها یا از نودها به یک سرور iperf3 اینترنتی، همراه با JSON، loss، jitter، retransmit و مصرف CPU.': 'Real TCP/UDP measurement between nodes or from nodes to an internet iperf3 server, including JSON, loss, jitter, retransmits, and CPU usage.',
            'شروع تست واقعی': 'Start real test',
            'شروع مهاجرت مرحله‌ای': 'Start staged migration',
            'شروع همگام‌سازی پورت‌ها': 'Start port synchronization',
            'صدها stream منطقی روی این اتصال‌های سرور‌به‌سرور توزیع می‌شوند؛ قطع یک carrier فقط streamهای همان carrier را متاثر می‌کند.': 'Hundreds of logical streams are distributed over these server-to-server connections; losing one carrier affects only its own streams.',
            'صدور Wildcard برای *.domain': 'Issue wildcard for *.domain',
            'غیرفعال‌سازی سراسری IPv6 (توصیه شده در ایران)': 'Disable IPv6 globally (recommended in Iran)',
            'فایل با سطح دسترسی 0600 روی Host نگهداری می‌شود. برای Route53 می‌توان از IAM role یا متغیرهای محیطی سرویس استفاده کرد.': 'The file is stored on the host with 0600 permissions. Route53 can use an IAM role or service environment variables.',
            'فایل بکاپ از سیستم': 'Backup file from device',
            'فعال‌سازی مسیر مخفی': 'Enable hidden path',
            'فقط در صورت وجود ماژول brutal روی Linux فعال می‌شود؛ وضعیت در telemetry نود گزارش می‌شود.': 'Enabled only when the Brutal module is available on Linux; its state is reported in node telemetry.',
            'فقط نودهای آنلاین': 'Online nodes only',
            'فقط پنل': 'Panel only',
            'فونت برنامه': 'Application font',
            'قطع اتصال': 'Disconnect',
            'متعادل': 'Balanced',
            'محتوای فایل Credentials افزونه Certbot': 'Certbot plugin credentials file contents',
            'محدوده بهینه‌سازی': 'Optimization scope',
            'مدت تست (ثانیه)': 'Test duration (seconds)',
            'مرکز تست سرعت': 'Speed test center',
            'مرکز تست سرعت iperf3': 'iperf3 speed test center',
            'مسیر': 'Path',
            'مسیر مخفی مدیریت پنل': 'Hidden panel management path',
            'مسیر مدیریت': 'Management path',
            'معماری انتقال دیتا': 'Data transfer architecture',
            'منابع زنده نودها': 'Live node resources',
            'منابع سیستم پنل': 'Panel system resources',
            'منبع فایل بکاپ': 'Backup file source',
            'مگابایت بر ثانیه (MB/s)': 'Megabytes per second (MB/s)',
            'نام کاربری SSH': 'SSH username',
            'نتیجه تست': 'Test result',
            'نصب/بررسی iperf3': 'Install/check iperf3',
            'نوع تست': 'Test type',
            'هاست سرور اینترنتی iperf3': 'Internet iperf3 server host',
            'هر نود به سرور اینترنتی iperf3': 'Each node to an internet iperf3 server',
            'هسته‌های آفلاین نیز داخل بکاپ قرار بگیرند': 'Include offline engines in the backup',
            'همگام‌سازی از X-UI': 'Synchronize from X-UI',
            'واحد نمایش ترافیک در داشبورد و جدول نودها': 'Traffic display unit in dashboard and node table',
            'پاک کردن انتخاب': 'Clear selection',
            'پروتکل': 'Protocol',
            'پروسس': 'Process',
            'پنل و همه نودهای آنلاین': 'Panel and all online nodes',
            'پورت API نودها': 'Node API port',
            'پورت SSH': 'SSH port',
            'پورت وب پنل': 'Panel web port',
            'پورت‌های پنل و API نودها': 'Panel and node API ports',
            'پیش از Restore یک Snapshot بازگشت از وضعیت فعلی ساخته می‌شود. پس از بازیابی، پنل به‌صورت خودکار Restart خواهد شد.': 'Before restore, a rollback snapshot of the current state is created. The panel restarts automatically after recovery.',
            'کپی': 'Copy',
            'کیلوبایت بر ثانیه (KB/s)': 'Kilobytes per second (KB/s)',
            '۰': '0',
            '۱۰ lane — تهاجمی': '10 lanes — aggressive',
            '۱۲ lane — بسیار تهاجمی': '12 lanes — very aggressive',
            '۱۶ lane — حداکثر': '16 lanes — maximum',
            '۲ carrier — کم‌مصرف': '2 carriers — low resource',
            '۲ lane — کم‌مصرف': '2 lanes — low resource',
            '۳ carrier — سبک': '3 carriers — light',
            '۴ carrier — متعادل': '4 carriers — balanced',
            '۴ lane — متعادل': '4 lanes — balanced',
            '۶ carrier — پیشنهادی Smart Hybrid': '6 carriers — Smart Hybrid recommended',
            '۶ lane — سریع': '6 lanes — fast',
            '۸ carrier — ظرفیت و افزونگی بالا': '8 carriers — high capacity and redundancy',
            '۸ lane — پرسرعت': '8 lanes — high speed',
            '127.0.0.1 یا panel.local': '127.0.0.1 or panel.local'
        });
        const originalTextNodes = new WeakMap();

        const attributeEnglish = {
            'node-name': 'INTERNAL-Node-1',
            'profile-import': 'Paste exported profiles JSON',
            'profile-name': 'Profile name',
            'profile-host': 'Host / SNI',
            'profile-path': 'Path',
            'ssh-host': 'Host or IP address',
            'ssh-command': 'uname -a && uptime && free -h',
            'link-name': 'Tunnel-Tehran-Frankfurt',
            'link-tags': 'video, vip, tehran'
        };

        function applyStaticTranslations() {
            document.querySelectorAll('[data-tx]').forEach(el => {
                const parts = String(el.dataset.tx || '').split('|');
                if (parts.length >= 2) el.textContent = currentLang === 'en' ? parts.slice(1).join('|') : parts[0];
            });
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            const nodes = [];
            while (walker.nextNode()) nodes.push(walker.currentNode);
            nodes.forEach(node => {
                if (!originalTextNodes.has(node)) originalTextNodes.set(node, node.nodeValue);
                const original = originalTextNodes.get(node);
                const raw = original.trim();
                if (!raw) return;
                if (currentLang === 'en' && staticEnglish[raw]) node.nodeValue = original.replace(raw, staticEnglish[raw]);
                if (currentLang === 'fa') node.nodeValue = original;
            });
        }

        function applyAttributeTranslations() {
            Object.keys(attributeEnglish).forEach(id => {
                const el = document.getElementById(id);
                if (!el) return;
                if (!el.dataset.faPlaceholder) el.dataset.faPlaceholder = el.getAttribute('placeholder') || '';
                el.setAttribute('placeholder', currentLang === 'en' ? attributeEnglish[id] : el.dataset.faPlaceholder);
            });
            document.querySelectorAll('[placeholder], [title], [aria-label]').forEach(el => {
                ['placeholder', 'title', 'aria-label'].forEach(name => {
                    if (!el.hasAttribute(name)) return;
                    const dataName = `fa${name.replace(/(^|-)([a-z])/g, (_, __, c) => c.toUpperCase())}`;
                    if (!el.dataset[dataName]) el.dataset[dataName] = el.getAttribute(name) || '';
                    const original = el.dataset[dataName];
                    if (currentLang === 'en' && staticEnglish[original]) el.setAttribute(name, staticEnglish[original]);
                    if (currentLang === 'fa') el.setAttribute(name, original);
                });
            });
        }

        function auditEnglishTranslation(root = document.body) {
            const persian = /[\u0600-\u06ff]/;
            const issues = [];
            const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {
                const node = walker.currentNode;
                const parent = node.parentElement;
                if (!parent || ['SCRIPT', 'STYLE'].includes(parent.tagName) || parent.closest('[hidden], .hidden')) continue;
                const text = node.nodeValue.trim();
                if (text && persian.test(text)) issues.push({ type: 'text', text: text.slice(0, 180) });
            }
            root.querySelectorAll('[placeholder], [title], [aria-label]').forEach(el => {
                ['placeholder', 'title', 'aria-label'].forEach(name => {
                    const value = el.getAttribute(name) || '';
                    if (persian.test(value)) issues.push({ type: name, text: value.slice(0, 180) });
                });
            });
            return issues;
        }
        window.auditEnglishTranslation = auditEnglishTranslation;

        function setLanguage(lang) {
            currentLang = lang;
            localStorage.setItem('p00rija_lang', lang);
            applyPreferences();
            switchTab(currentTab, true);
            if (latestStatus.nodes) {
                updateDashboard(latestStatus);
                renderCurrentTab(latestStatus);
            }
        }

        function setTheme(theme) {
            currentTheme = theme;
            localStorage.setItem('p00rija_theme', theme);
            applyPreferences();
        }

        function setFont(font) {
            currentFont = font;
            localStorage.setItem('p00rija_font', font);
            applyPreferences();
        }

        async function fetchSettings() {
            if (!token) return;
            try {
                const res = await fetch('/api/status', {
                    headers: { 'Authorization': `Bearer ${token}` },
                    cache: 'no-store'
                });
                if (!res.ok) return;
                latestStatus = await res.json();
                updateLoginSecurity(latestStatus);
            } catch (err) {
                console.warn('Settings bootstrap skipped:', err);
            }
        }

        function applyTheme() {
            applyPreferences();
        }

        function createInlineIcons(root = document) {
            const icons = {
                gauge: 'M4 13a8 8 0 0 1 16 0 M12 13l4-4',
                server: 'M4 6h16v5H4z M4 13h16v5H4z',
                split: 'M6 4v5a3 3 0 0 0 3 3h6 M15 7l3-3 3 3 M15 17l3 3 3-3',
                terminal: 'M4 6l5 5-5 5 M11 18h9',
                settings: 'M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8z M4 12h3 M17 12h3 M12 4v3 M12 17v3',
                'log-out': 'M5 4h8v4 M13 16v4H5V4 M12 12h9 M18 9l3 3-3 3',
                activity: 'M4 13h4l3-7 4 12 3-5h2',
                cpu: 'M8 8h8v8H8z M4 9h3 M4 15h3 M17 9h3 M17 15h3 M9 4v3 M15 4v3 M9 17v3 M15 17v3',
                x: 'M6 6l12 12 M18 6L6 18',
                'git-commit': 'M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8z M2 12h6 M16 12h6',
                'arrow-right': 'M5 12h14 M13 6l6 6-6 6',
                palette: 'M12 4a8 8 0 0 0 0 16h1.5a2 2 0 0 0 1.7-3h1.3A5.5 5.5 0 0 0 12 4z M7 10h.01 M10 7h.01 M14 7h.01 M17 10h.01',
                'book-open': 'M4 5h6a4 4 0 0 1 4 4v11a4 4 0 0 0-4-4H4z M20 5h-6a4 4 0 0 0-4 4v11a4 4 0 0 1 4-4h6z',
                info: 'M12 8h.01 M11 12h1v5h1 M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
                menu: 'M4 6h16 M4 12h16 M4 18h16',
                'chevron-up': 'M18 15l-6-6-6 6',
                'chevron-down': 'M6 9l6 6 6-6',
                zap: 'M13 2L3 14h8l-1 8 10-12h-8l1-8z',
                shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
                'check-circle': 'M22 11.08V12a10 10 0 1 1-5.93-9.14 M22 4L12 14.01l-3-3'
            };
            root.querySelectorAll('i[data-lucide]').forEach(el => {
                const name = el.getAttribute('data-lucide');
                const pathData = icons[name] || icons.activity;
                const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
                svg.setAttribute("viewBox", "0 0 24 24");
                svg.setAttribute("width", "20");
                svg.setAttribute("height", "20");
                svg.setAttribute("fill", "none");
                svg.setAttribute("stroke", "currentColor");
                svg.setAttribute("stroke-width", "2");
                svg.setAttribute("stroke-linecap", "round");
                svg.setAttribute("stroke-linejoin", "round");
                svg.setAttribute("aria-hidden", "true");
                const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
                path.setAttribute("d", pathData);
                svg.appendChild(path);
                while (el.firstChild) {
                    el.removeChild(el.firstChild);
                }
                el.appendChild(svg);
            });
        }

        function esc(value) {
            return String(value ?? '').replace(/[&<>"']/g, ch => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            }[ch]));
        }

        function cssEscape(value) {
            if (window.CSS && CSS.escape) return CSS.escape(String(value));
            return String(value).replace(/["\\\\]/g, '\\\\$&');
        }

        function formatBytes(value) {
            const bytes = Number(value || 0);
            if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
            if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
            if (bytes >= 1024) return `${(bytes / 1024).toFixed(2)} KB`;
            return `${bytes} B`;
        }

        function safeDomId(value) {
            return String(value || 'node').replace(/[^a-zA-Z0-9_-]/g, '_');
        }

        function parseTags(value) {
            if (Array.isArray(value)) return value.map(v => String(v).trim()).filter(Boolean).slice(0, 8);
            return String(value || '').replace(/،/g, ',').split(',').map(v => v.trim()).filter(Boolean).slice(0, 8);
        }

        function renderTags(tags = []) {
            return parseTags(tags).map((tag, idx) => `<span class="tag-pill tag-color-${idx % 6}">${esc(tag)}</span>`).join('');
        }

        applyPreferences();
        createInlineIcons();
        fetchPublicSettings();
        document.addEventListener('click', (event) => {
            if (!event.target.closest?.('#link-profile-picker')) closeProfilePicker();
        });

        if (token) {
            showPanel();
        }

        async function fetchPublicSettings() {
            try {
                const res = await fetch('/api/public-settings');
                if (!res.ok) return;
                updateLoginSecurity(await res.json());
            } catch (err) {
                updateLoginSecurity({ two_factor_enabled: false });
            }
        }

        function updateLoginSecurity(settings) {
            const group = document.getElementById('otp-group');
            const otp = document.getElementById('otp');
            const enabled = !!settings.two_factor_enabled;
            if (group) group.classList.toggle('hidden', !enabled);
            if (otp) {
                otp.required = enabled;
                if (!enabled) otp.value = '';
            }
        }

        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;
            const otp = document.getElementById('otp').value;
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: u, password: p, otp })
                });
                if (res.ok) {
                    const data = await res.json();
                    token = data.token;
                    localStorage.setItem('token', token);
                    await maybeRegisterBiometric();
                    showPanel();
                } else {
                    alert(tx('نام کاربری یا کلمه عبور نادرست است.', 'Username or password is incorrect.'));
                }
            } catch (err) {
                console.error("Login flow error:", err);
                alert(tx('خطا در پردازش ورود (کنسول مرورگر را بررسی کنید).', 'Error processing login (check browser console).'));
            }
        });

        async function maybeRegisterBiometric() {
            if (typeof latestStatus === 'undefined' || !latestStatus || !latestStatus.biometric_enabled || !window.PublicKeyCredential) return;
            if (localStorage.getItem('p00rija_bio_registered') === '1') return;
            try {
                await navigator.credentials.create({
                    publicKey: {
                        challenge: crypto.getRandomValues(new Uint8Array(32)),
                        rp: { name: 'P00RIJA TUNNEL' },
                        user: { id: crypto.getRandomValues(new Uint8Array(16)), name: 'admin', displayName: 'P00RIJA Admin' },
                        pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
                        authenticatorSelection: { authenticatorAttachment: 'platform', userVerification: 'preferred' },
                        timeout: 30000
                    }
                });
                localStorage.setItem('p00rija_bio_registered', '1');
            } catch (err) {
                console.warn('Biometric registration skipped:', err);
            }
        }

        async function fetchXrayVersions() {
            if (!document.getElementById('setting-xray-version')) return;
            try {
                let data = null;
                const cached = localStorage.getItem('xray_versions_cache');
                const cachedTime = localStorage.getItem('xray_versions_time');
                if (cached && cachedTime && (Date.now() - parseInt(cachedTime)) < 3600000) {
                    data = JSON.parse(cached);
                } else {
                    const res = await fetch('https://api.github.com/repos/XTLS/Xray-core/releases');
                    if (res.ok) {
                        data = await res.json();
                        localStorage.setItem('xray_versions_cache', JSON.stringify(data));
                        localStorage.setItem('xray_versions_time', Date.now().toString());
                    } else {
                        throw new Error('Rate limited');
                    }
                }
                populateXrayVersions(data);
                document.getElementById('xray-version-status').innerText = 'نسخه‌ها با موفقیت دریافت شدند.';
            } catch (err) {
                console.warn('Github fetch failed, using fallback.', err);
                const fallback = [
                    { tag_name: 'v1.8.24', prerelease: false, draft: false },
                    { tag_name: 'v1.8.23', prerelease: false, draft: false },
                    { tag_name: 'v1.8.1', prerelease: false, draft: false },
                    { tag_name: 'v1.8.0', prerelease: false, draft: false },
                    { tag_name: 'v1.7.5', prerelease: false, draft: false }
                ];
                populateXrayVersions(fallback);
                document.getElementById('xray-version-status').innerText = 'استفاده از لیست پشتیبان (محدودیت گیت‌هاب).';
            }
        }
        function populateXrayVersions(data) {
            const sel = document.getElementById('setting-xray-version');
            if (!sel) return;
            sel.innerHTML = '<option value="latest">آخرین نسخه (latest)</option>';
            let added = 0;
            for (const release of data) {
                if (release.prerelease || release.draft) continue;
                const opt = document.createElement('option');
                opt.value = release.tag_name;
                opt.innerText = release.tag_name;
                sel.appendChild(opt);
                added++;
                if (added >= 5) break;
            }
        }

        function showPanel() {
            document.getElementById('login-screen').classList.add('hidden');
            document.getElementById('main-sidebar').classList.remove('hidden');
            document.getElementById('main-workspace').classList.remove('hidden');
            try { initCharts(); } catch(e) { console.error('initCharts error:', e); }
            try { startPolling(); } catch(e) { console.error('startPolling error:', e); }
            try { switchTab('dashboard', true); } catch(e) { console.error('switchTab error:', e); }
            try { fetchStatus(); } catch(e) { console.error('fetchStatus error:', e); }
            try { updateDirectionExample(); } catch(e) { console.error('direction example error:', e); }
            try {
                if (localStorage.getItem('p00rija_auto_guardian') === '1' && !autoGuardianTimer) {
                    autoGuardianTimer = setInterval(runAutoGuardianCycle, 60000);
                }
                updateAutoGuardianButton();
            } catch(e) { console.error('auto guardian init error:', e); }
        }

        function toggleMobileMenu() {
            document.body.classList.toggle('menu-open');
        }

        function logout(reload = false) {
            token = null;
            localStorage.removeItem('token');
            if (autoRefreshTimer) {
                clearInterval(autoRefreshTimer);
                autoRefreshTimer = null;
            }
            if (autoGuardianTimer) {
                clearInterval(autoGuardianTimer);
                autoGuardianTimer = null;
            }
            document.getElementById('main-sidebar').classList.add('hidden');
            document.getElementById('main-workspace').classList.add('hidden');
            document.getElementById('login-screen').classList.remove('hidden');
            if (reload) location.reload();
        }

        function startPolling() {
            document.getElementById("auto-refresh-select").value = "3";
            setAutoRefresh();
        }

        function switchTab(tabId, skipFetch = false) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

            document.getElementById(`tab-${tabId}`).classList.remove('hidden');
            const navItems = Array.from(document.querySelectorAll('.nav-item'));
            const activeNav = navItems.find(el => el.getAttribute('onclick') && el.getAttribute('onclick').includes(`'${tabId}'`));
            if (activeNav) activeNav.classList.add('active');
            currentTab = tabId;

            const titles = {
                dashboard: t('dashboard'),
                nodes: t('nodes'),
                links: t('links'),
                speedtest: tx('مرکز تست سرعت', 'Speed Test Center'),
                logs: t('logs'),
                monitor: t('monitor'),
                appearance: t('appearance'),
                settings: t('settings'),
                help: t('help'),
                about: t('about')
            };
            document.getElementById('tab-title').innerText = titles[tabId];
            if (tabId === 'monitor') fetchRuntime();
            if (tabId === 'speedtest') renderSpeedTestNodePicker();
            if (tabId === 'settings' && latestStatus) {
                document.getElementById('setting-username').value = latestStatus.admin_username || 'admin';
                document.getElementById('setting-traffic-unit').value = localStorage.getItem('trafficUnit') || 'MB';
                document.getElementById('setting-panel-tls').checked = latestStatus.panel_tls || false;
                document.getElementById('setting-cert-path').value = latestStatus.cert_path || '';
                document.getElementById('setting-key-path').value = latestStatus.key_path || '';
                document.getElementById('setting-two-factor').checked = latestStatus.two_factor_enabled || false;
                document.getElementById('setting-biometric').checked = latestStatus.biometric_enabled || false;
                const disableIpv6El = document.getElementById('setting-disable-ipv6');
                if (disableIpv6El) disableIpv6El.checked = latestStatus.disable_ipv6 || false;
                const engineRestartIntervalEl = document.getElementById('setting-engine-restart-interval');
                if (engineRestartIntervalEl) engineRestartIntervalEl.value = latestStatus.engine_restart_interval || 0;
                const panelPortEl = document.getElementById('setting-panel-port');
                if (panelPortEl) panelPortEl.value = latestStatus.panel_port || location.port || 443;
                const apiPortEl = document.getElementById('setting-api-port');
                if (apiPortEl) apiPortEl.value = latestStatus.api_port || 8000;
                const panelHostEl = document.getElementById('setting-panel-host');
                if (panelHostEl) panelHostEl.value = latestStatus.panel_host || location.hostname;
                const hiddenEnabledEl = document.getElementById('setting-hidden-path-enabled');
                if (hiddenEnabledEl) hiddenEnabledEl.checked = Boolean(latestStatus.hidden_panel_path_enabled);
                const hiddenPathEl = document.getElementById('setting-hidden-panel-path');
                if (hiddenPathEl) hiddenPathEl.value = latestStatus.hidden_panel_path || '';
            }
            if (!skipFetch) fetchStatus();
            if (window.innerWidth <= 900) document.body.classList.remove('menu-open');
        }

        function initCharts() {
            if (charts.traffic) return;
            charts.traffic = { canvas: document.getElementById('chart-traffic'), series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_DOWNLOAD, COLOR_UPLOAD] };
            charts.connections = { canvas: document.getElementById('chart-connections'), series: [Array(20).fill(0)], colors: [COLOR_ACTIVE] };
            charts.panelSystem = { canvas: document.getElementById('chart-panel-system'), series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_ACTIVE, COLOR_UPLOAD] };
            charts.panelRuntime = { canvas: document.getElementById('chart-panel-runtime'), series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_ACTIVE, COLOR_DOWNLOAD] };
            drawChart(charts.traffic, 'MB/s', [tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
            drawChart(charts.connections, '', [tx('اتصالات', 'Connections')]);
            drawChart(charts.panelSystem, '%', ['CPU', 'RAM']);
            drawChart(charts.panelRuntime, '', ['Threads', 'Sessions']);
        }

        function drawChart(chart, unit = '', labels = []) {
            const canvas = chart.canvas;
            const parent = canvas.parentElement;
            const dpr = window.devicePixelRatio || 1;
            const width = Math.max(240, parent.clientWidth || canvas.clientWidth || 320);
            const height = Math.max(140, parent.clientHeight || canvas.clientHeight || 220);
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;

            const ctx = canvas.getContext('2d');
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, width, height);
            const pad = 24;
            const topPad = 35; // extra padding for legend
            let flatSeries = [];
            chart.series.forEach(arr => { flatSeries = flatSeries.concat(arr); });
            const max = Math.max(1, ...flatSeries);
            const isLightChart = document.body.classList.contains('theme-light');
            const gridColor = isLightChart ? 'rgba(15,23,42,0.16)' : 'rgba(255,255,255,0.07)';
            const axisTextColor = isLightChart ? 'rgba(15,23,42,0.72)' : 'rgba(255,255,255,0.56)';
            const legendTextColor = isLightChart ? 'rgba(15,23,42,0.88)' : 'rgba(255,255,255,0.86)';
            ctx.strokeStyle = gridColor;
            ctx.lineWidth = 1;
            for (let i = 0; i < 5; i++) {
                const y = topPad + ((height - topPad - pad) / 4) * i;
                ctx.beginPath();
                ctx.moveTo(pad, y);
                ctx.lineTo(width - pad, y);
                ctx.stroke();
                
                // Draw Y axis labels
                ctx.fillStyle = axisTextColor;
                ctx.font = '10px Vazirmatn, Tahoma, sans-serif';
                ctx.textAlign = 'right';
                const val = max - (max / 4) * i;
                ctx.fillText(val.toFixed(1) + (unit ? ' ' + unit : ''), width - pad, y - 5);
            }
            chart.series.forEach((points, idx) => {
                ctx.strokeStyle = chart.colors[idx];
                ctx.lineWidth = 2;
                ctx.beginPath();
                points.forEach((point, i) => {
                    const x = pad + ((width - pad * 2) / (points.length - 1)) * i;
                    const safePoint = Math.max(0, Math.min(Number(point) || 0, max));
                    const y = height - pad - ((height - topPad - pad) * safePoint / max);
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                });
                ctx.stroke();
            });
            
            // Draw Legends
            if (labels && labels.length > 0) {
                let currentX = pad;
                labels.forEach((label, idx) => {
                    ctx.fillStyle = chart.colors[idx];
                    ctx.fillRect(currentX, 10, 10, 10);
                    ctx.fillStyle = legendTextColor;
                    ctx.textAlign = 'left';
                    ctx.font = '12px Vazirmatn, Tahoma, sans-serif';
                    ctx.fillText(label, currentX + 15, 20);
                    currentX += ctx.measureText(label).width + 30;
                });
            }
        }

        async function fetchStatus(options = {}) {
            if (!token) return;
            try {
                const res = await fetch('/api/status', {
                    headers: { 'Authorization': `Bearer ${token}` },
                    cache: 'no-store'
                });
                if (res.status === 401) {
                    logout(false);
                    return;
                }
                if (!res.ok) return;
                const status = await res.json();
                latestStatus = status;
                updateDashboard(status);
                renderEngineManager(status.engines || {});
                populateProfiles(status.tunnel_profiles || {}, { preserveSelection: isModalVisible('modal-add-link') });
                renderProfileCatalog(status.tunnel_profiles || {});
                document.getElementById('about-version').innerText = status.version || '1.9.95';
                document.getElementById('about-license').innerText = status.license || 'GPL-3.0';
                updateLoginSecurity(status);
                if (status.biometric_enabled) maybeRegisterBiometric();

                renderCurrentTab(status, options);
                return status;
            } catch (err) {
                console.error("Fetch status failed:", err);
            }
        }

        function renderCurrentTab(status, options = {}) {
            if (currentTab === 'nodes') {
                renderNodes(status.nodes || {});
            } else if (currentTab === 'links') {
                renderLinksLive(status.links || {}, status.nodes || {});
            } else if (currentTab === 'logs') {
                renderLogs(status.logs || []);
            } else if (currentTab === 'monitor') {
                fetchRuntime();
            } else if (currentTab === 'speedtest') {
                renderSpeedTestNodePicker();
            } else if (currentTab === 'dashboard' && options.forceChartRedraw) {
                drawLiveCharts(status);
            }
        }

        function populateProfiles(profiles, options = {}) {
            const select = document.getElementById('link-profile');
            if (!select) return;
            ensureTunnelOptionMatrixCoversProfiles(profiles || {});
            const signature = JSON.stringify(Object.entries(profiles || {}).sort(([a], [b]) => a.localeCompare(b)).map(([id, profile]) => [id, profile?.name, profile?.engine, profile?.tunnel_mode]));
            if (options.preserveSelection && signature === lastProfilesSignature) {
                renderProfilePicker(profiles || {});
                return;
            }
            const current = select.value || 'custom';
            const focused = document.activeElement === select;
            select.innerHTML = `<option value="custom">${tx('شخصی / پیشرفته', 'Custom / Advanced')}</option>`;
            const groups = {};
            Object.entries(profiles).forEach(([id, profile]) => {
                const category = profileCategoryName(id, profile || {});
                groups[category] = groups[category] || [];
                groups[category].push([id, profile]);
            });
            Object.entries(groups).forEach(([category, items]) => {
                const group = document.createElement('optgroup');
                group.label = category;
                items.sort((a, b) => (a[1].name || a[0]).localeCompare(b[1].name || b[0])).forEach(([id, profile]) => {
                    const opt = document.createElement('option');
                    opt.value = id;
                    opt.innerText = profile.name || id;
                    group.appendChild(opt);
                });
                select.appendChild(group);
            });
            select.value = profiles[current] ? current : 'custom';
            lastProfilesSignature = signature;
            renderProfilePicker(profiles || {});
            if (focused) select.focus();
        }

        function titleFromToken(value) {
            return String(value || '')
                .replace(/_/g, ' ')
                .replace(/\\b\\w/g, ch => ch.toUpperCase());
        }

        function addUniqueOption(list, value, label) {
            if (!value) return;
            if (!list.some(([existing]) => existing === value)) list.push([value, label || titleFromToken(value)]);
        }

        function ensureSelectHasOptions(selectId, options, preferred) {
            const select = document.getElementById(selectId);
            if (!select) return;
            const current = preferred || select.value;
            const seen = new Set(Array.from(select.options).map(opt => opt.value));
            options.forEach(([value, label]) => {
                if (!seen.has(value)) {
                    const opt = document.createElement('option');
                    opt.value = value;
                    opt.innerText = label;
                    select.appendChild(opt);
                    seen.add(value);
                }
            });
            if (current && Array.from(select.options).some(opt => opt.value === current)) select.value = current;
        }

        function ensureTunnelOptionMatrixCoversProfiles(profiles = {}) {
            const engineOptions = [];
            Object.values(profiles || {}).forEach(profile => {
                if (!profile || typeof profile !== 'object') return;
                const engine = profile.engine || 'builtin';
                const mode = profile.tunnel_mode || profile.transport || 'tcp';
                const transport = profile.transport || modeTransportMap[mode] || mode;
                const network = profile.network || (udpTunnelModes.includes(mode) ? 'udp' : 'tcp');
                if (!tunnelOptionMatrix[engine]) {
                    tunnelOptionMatrix[engine] = { transports: [], modes: [], networks: [] };
                }
                addUniqueOption(tunnelOptionMatrix[engine].modes, mode, titleFromToken(mode));
                addUniqueOption(tunnelOptionMatrix[engine].transports, transport, titleFromToken(transport));
                addUniqueOption(tunnelOptionMatrix[engine].networks, network, network.toUpperCase());
                addUniqueOption(engineOptions, engine, engine === 'builtin' ? 'Built-in Reverse' : titleFromToken(engine));
            });
            Object.entries(tunnelOptionMatrix).forEach(([engine, config]) => addUniqueOption(engineOptions, engine, engine === 'builtin' ? 'Built-in Reverse' : titleFromToken(engine)));
            engineOptions.sort((a, b) => a[1].localeCompare(b[1]));
            ensureSelectHasOptions('link-engine', engineOptions);
            ensureSelectHasOptions('profile-engine', engineOptions);
            syncProfileModeOptions();
        }

        function profileCategoryName(id, profile) {
            if (id === 'easy' || id === 'hard' || id === 'resilient') return tx('ساده و پیشنهادی', 'Recommended');
            if ((profile.engine || '').includes('muxquantum') || id.includes('muxquantum')) return 'Mux/Quantum';
            if (profile.engine === 'amneziawg') return 'AmneziaWG';
            if (profile.engine === 'wireguard') return 'WireGuard / Fastest';
            if (profile.engine === 'masque') return 'MASQUE / HTTP/3';
            if (profile.engine === 'ssh') return 'SSH Forwarding';
            if (profile.engine === 'stunnel') return 'TLS Wrapping';
            if (profile.engine === 'aead' || ['client_port_forward', 'client_socks5'].includes(profile.tunnel_mode)) return 'AEAD / Client Egress';
            if (profile.engine === 'rawsock') return 'Raw Socket Lab';
            if (profile.tunnel_mode === 'reverse_tcp') return tx('تانل معکوس TCP', 'Reverse TCP');
            if (id.includes('ultra_stealth') || ['naiveproxy', 'shadowtls', 'singbox', 'tuic', 'hysteria2'].includes(profile.engine)) return tx('مخفی‌سازی و شرایط سخت', 'Stealth / strict filtering');
            if (['xray', 'gost', 'backhaul', 'rathole', 'chisel', 'frp'].includes(profile.engine)) return tx('کلاسیک و پایدار', 'Classic / stable');
            return tx('سایر', 'Other');
        }

        function ratingLevel(profile, key) {
            return profile?.ratings?.[key] || 'normal';
        }

        function ratingLabel(profile, key) {
            const level = ratingLevel(profile, key);
            if (level === 'good') return currentLang === 'en' ? 'Good' : 'خوب';
            if (level === 'poor') return currentLang === 'en' ? 'Poor' : 'ضعیف';
            return currentLang === 'en' ? 'Normal' : 'عادی';
        }

        function ratingChip(profile, key, labelFa, labelEn) {
            const level = ratingLevel(profile, key);
            return `<span class="tag-pill rating-chip-${level}">${tx(labelFa, labelEn)}: ${ratingLabel(profile, key)}</span>`;
        }

        function ratingIcon(profile, key, icon, labelFa, labelEn) {
            const level = ratingLevel(profile, key);
            const label = `${tx(labelFa, labelEn)}: ${ratingLabel(profile, key)}`;
            return `<span class="rating-icon ${level}" title="${esc(label)}" aria-label="${esc(label)}"><i data-lucide="${icon}"></i></span>`;
        }

        function ratingIcons(profile) {
            return `
                <span class="rating-icons">
                    ${ratingIcon(profile, 'speed', 'zap', 'سرعت', 'Speed')}
                    ${ratingIcon(profile, 'security', 'shield', 'امنیت', 'Security')}
                    ${ratingIcon(profile, 'stability', 'check-circle', 'پایداری', 'Stability')}
                </span>
            `;
        }

        function profilePickerSelectedMarkup(profileId, profiles = {}) {
            const profile = profiles[profileId];
            if (!profile) {
                return `
                    <span class="profile-picker-selected">
                        <strong>${tx('شخصی / پیشرفته', 'Custom / Advanced')}</strong>
                        <small>${tx('تنظیم دستی هسته، ترنسپورت و پارامترها', 'Manually tune engine, transport, and parameters')}</small>
                    </span>
                    <i data-lucide="chevron-down"></i>
                `;
            }
            return `
                <span class="profile-picker-selected">
                    <strong>${esc(profile.name || profileId)}</strong>
                    <small>${esc(profile.engine || 'builtin')} / ${esc(profile.tunnel_mode || profile.transport || 'tcp')}</small>
                    ${ratingIcons(profile)}
                </span>
                <i data-lucide="chevron-down"></i>
            `;
        }

        function renderProfilePicker(profiles = {}) {
            const select = document.getElementById('link-profile');
            const button = document.getElementById('profile-picker-button');
            const menu = document.getElementById('profile-picker-menu');
            if (!select || !button || !menu) return;
            const selected = select.value || 'custom';
            button.innerHTML = profilePickerSelectedMarkup(selected, profiles);
            createInlineIcons(button);
            const groups = {};
            Object.entries(profiles).forEach(([id, profile]) => {
                const category = profileCategoryName(id, profile || {});
                groups[category] = groups[category] || [];
                groups[category].push([id, profile]);
            });
            const customOption = `
                <button type="button" class="profile-picker-option ${selected === 'custom' ? 'active' : ''}" onclick="selectProfile('custom')">
                    <span class="profile-picker-option-title"><strong>${tx('شخصی / پیشرفته', 'Custom / Advanced')}</strong><span class="tag-pill">${tx('دستی', 'Manual')}</span></span>
                    <small class="field-hint">${tx('برای تنظیم کامل Engine، Transport، SNI و پارامترهای Advance.', 'For full control over engine, transport, SNI, and advanced parameters.')}</small>
                </button>
            `;
            const groupedMarkup = Object.entries(groups).map(([category, items]) => {
                const options = items.sort((a, b) => (a[1].name || a[0]).localeCompare(b[1].name || b[0])).map(([id, profile]) => `
                    <button type="button" class="profile-picker-option ${selected === id ? 'active' : ''}" onclick="selectProfile('${esc(id)}')">
                        <span class="profile-picker-option-title">
                            <strong>${esc(profile.name || id)}</strong>
                            <small>${esc(profile.engine || 'builtin')} / ${esc(profile.tunnel_mode || profile.transport || 'tcp')}</small>
                        </span>
                        ${ratingIcons(profile)}
                    </button>
                `).join('');
                return `<div class="profile-picker-category">${esc(category)}</div>${options}`;
            }).join('');
            menu.innerHTML = customOption + groupedMarkup;
            createInlineIcons(menu);
        }

        function selectProfile(profileId) {
            const select = document.getElementById('link-profile');
            if (!select) return;
            select.value = profileId;
            applySelectedProfile();
            renderProfilePicker(latestStatus.tunnel_profiles || {});
            closeProfilePicker();
        }

        function toggleProfilePicker(event) {
            event?.stopPropagation();
            const menu = document.getElementById('profile-picker-menu');
            if (!menu) return;
            menu.classList.toggle('hidden');
        }

        function closeProfilePicker() {
            document.getElementById('profile-picker-menu')?.classList.add('hidden');
        }

        function renderProfileCatalog(profiles = {}) {
            const box = document.getElementById('profile-catalog');
            if (!box) return;
            const groups = {};
            Object.entries(profiles || {}).forEach(([id, profile]) => {
                const category = profileCategoryName(id, profile || {});
                groups[category] = groups[category] || [];
                groups[category].push([id, profile]);
            });
            box.innerHTML = Object.entries(groups).sort(([a], [b]) => a.localeCompare(b)).map(([category, items], index) => {
                const cards = items.sort((a, b) => (a[1].name || a[0]).localeCompare(b[1].name || b[0])).map(([id, profile]) => `
                    <div class="profile-card-mini" onclick="selectProfile('${esc(id)}')" title="${esc(profile.recommendation_note || '')}">
                        <div class="flex-between gap-10">
                            <strong>${esc(profile.name || id)}</strong>
                            ${ratingIcons(profile)}
                        </div>
                        <small style="color: var(--text-secondary);">${esc(profile.engine || 'builtin')} / ${esc(profile.tunnel_mode || profile.transport || 'tcp')}</small>
                    </div>
                `).join('');
                const hasSavedState = Object.prototype.hasOwnProperty.call(profileCategoryOpenStates, category);
                const isOpen = hasSavedState ? !!profileCategoryOpenStates[category] : index < 2;
                return `
                    <details class="profile-catalog-group" data-category="${esc(category)}" ${isOpen ? 'open' : ''}>
                        <summary class="flex-between gap-10">
                            <strong>${esc(category)}</strong>
                            <span class="tag-pill">${items.length}</span>
                        </summary>
                        <div class="profile-catalog-group-body">${cards}</div>
                    </details>
                `;
            }).join('');
            box.querySelectorAll('.profile-catalog-group').forEach(details => {
                details.addEventListener('toggle', () => {
                    const category = details.dataset.category;
                    if (!category) return;
                    profileCategoryOpenStates[category] = details.open;
                    localStorage.setItem('p00rija_profile_category_open', JSON.stringify(profileCategoryOpenStates));
                });
            });
            createInlineIcons(box);
        }

        function updateDirectionExample() {
            const box = document.getElementById('direction-example');
            if (!box) return;
            const direction = document.getElementById('link-direction')?.value || 'external_to_internal';
            if (direction === 'internal_to_external') {
                box.innerHTML = `
                    <div class="direction-example-flow">
                        <div class="direction-example-node">
                            <strong>${tx('نود داخلی', 'Internal node')}</strong>
                            <small>${tx('پشت NAT یا فایروال، فقط خروجی اینترنت دارد', 'Behind NAT/firewall, outbound internet works')}</small>
                        </div>
                        <div class="direction-example-arrow">-- dial --&gt;</div>
                        <div class="direction-example-node">
                            <strong>${tx('نود خارجی VPS', 'External VPS node')}</strong>
                            <small>${tx('IP عمومی دارد و Listener را نگه می‌دارد', 'Has public IP and keeps the listener')}</small>
                        </div>
                    </div>
                    <div class="direction-example-note">
                        ${tx('مثال ملموس: اگر نود داخلی داخل شبکه بسته است و نمی‌توانید از بیرون به آن ورودی بگیرید، این حالت بهتر است. نود داخلی خودش به VPS خارجی وصل می‌شود، کانکشن رزرو می‌سازد و کاربر از سمت نود خارجی یا پورت‌های تعریف‌شده وارد سرویس می‌شود.', 'Concrete example: if the internal node sits in a restricted network and cannot accept inbound traffic, this direction is better. The internal node dials the external VPS, builds reserve connections, and users enter through the external side or mapped ports.')}
                    </div>
                `;
                return;
            }
            box.innerHTML = `
                <div class="direction-example-flow">
                    <div class="direction-example-node">
                        <strong>${tx('نود خارجی VPS', 'External VPS node')}</strong>
                        <small>${tx('Dialer است و اتصال اولیه را می‌زند', 'Acts as the dialer and starts the connection')}</small>
                    </div>
                    <div class="direction-example-arrow">-- dial --&gt;</div>
                    <div class="direction-example-node">
                        <strong>${tx('نود داخلی', 'Internal node')}</strong>
                        <small>${tx('Bridge/Sync port روی آن قابل دسترس است', 'Bridge/Sync ports are reachable on it')}</small>
                    </div>
                </div>
                <div class="direction-example-note">
                    ${tx('مثال ملموس: اگر نود داخلی IP/Port قابل دسترس دارد یا بین دو سمت route باز است، VPS خارجی به Bridge Port نود داخلی وصل می‌شود و ورودی‌های کاربر روی سمت داخلی listener می‌شوند. برای لَب داخلی یا دیتاسنترهایی که بین دو سمت route مستقیم دارند ساده‌تر است.', 'Concrete example: if the internal node has reachable IP/ports or routing is open between both sides, the external VPS dials the internal node Bridge Port and user-facing listeners stay on the internal side. This is simpler for labs or data centers with direct routing between both sides.')}
                </div>
            `;
        }

        function isModalVisible(id) {
            const modal = document.getElementById(id);
            return !!modal && modal.style.display !== 'none' && getComputedStyle(modal).display !== 'none';
        }

        function populateLinkNodeSelects(nodes, options = {}) {
            const selectIR = document.getElementById('link-iran-node');
            const selectForeign = document.getElementById('link-foreign-node');
            if (!selectIR || !selectForeign) return;
            const preserveSelection = options.preserveSelection !== false;
            const currentIR = preserveSelection ? selectIR.value : '';
            const currentForeign = preserveSelection ? selectForeign.value : '';
            const focusedId = document.activeElement?.id || '';

            selectIR.innerHTML = '';
            selectForeign.innerHTML = '';
            Object.entries(nodes || {}).forEach(([nid, n]) => {
                const opt = document.createElement('option');
                opt.value = nid;
                opt.innerText = `${n.name || nid} (${n.ip || '-'})`;
                if (n.role === 'internal' || n.role === 'iran') selectIR.appendChild(opt);
                else selectForeign.appendChild(opt);
            });

            if (currentIR && Array.from(selectIR.options).some(opt => opt.value === currentIR)) {
                selectIR.value = currentIR;
            }
            if (currentForeign && Array.from(selectForeign.options).some(opt => opt.value === currentForeign)) {
                selectForeign.value = currentForeign;
            }
            if (focusedId === 'link-iran-node') selectIR.focus();
            if (focusedId === 'link-foreign-node') selectForeign.focus();
        }

        function getTargetPortCheck(nodes, linkId, link, userPort) {
            const clientNodeId = (link.direction || 'external_to_internal') === 'internal_to_external'
                ? (link.internal_node_id || link.iran_node_id)
                : (link.external_node_id || link.foreign_node_id);
            const clientNode = (nodes || {})[clientNodeId] || {};
            const checks = clientNode.stats?.target_port_checks?.[linkId] || {};
            return checks[String(userPort)] || {};
        }

        function targetPortStatusMarkup(check) {
            const known = check && check.target_open !== undefined;
            if (!known) return `<span style="opacity:.75;">${tx('در انتظار گزارش سمت مقصد', 'Waiting for target-side report')}</span>`;
            if (check.target_open === true) return `<span class="text-success">${tx('مقصد باز است', 'Target open')}</span>`;
            return `<span class="text-danger">${tx('مقصد بسته است', 'Target closed')}</span>`;
        }

        function linkRuntimeHealth(nodes, linkId, link) {
            const irNode = (nodes || {})[link.internal_node_id || link.iran_node_id] || {};
            const foreignNode = (nodes || {})[link.external_node_id || link.foreign_node_id] || {};
            const internalStatus = irNode.stats?.link_statuses?.[linkId] || {};
            const externalStatus = foreignNode.stats?.link_statuses?.[linkId] || {};
            const reverseDirection = (link.direction || 'external_to_internal') === 'internal_to_external';
            const serverStatus = reverseDirection ? externalStatus : internalStatus;
            const clientStatus = reverseDirection ? internalStatus : externalStatus;
            const nodesOnline = irNode.status === 'online' && foreignNode.status === 'online';
            const anyUserPort = (link.ports || []).some(port => serverStatus.ports?.[String(port.user_port)]?.listening === true);
            const poolReady = Number(serverStatus.pool_available || 0) > 0 || Number(clientStatus.ready_workers || 0) > 0;
            const directReady = clientStatus.direct_bridge_listening === true;
            const runtimeKnown = serverStatus.running !== undefined || clientStatus.running !== undefined;
            const ready = nodesOnline && !link.paused && (!runtimeKnown || (serverStatus.running && clientStatus.running && anyUserPort && (poolReady || directReady)));
            let reason = '';
            if (!nodesOnline) reason = tx('یکی از نودها آفلاین است', 'One node is offline');
            else if (link.paused) reason = tx('تانل متوقف است', 'Tunnel is paused');
            else if (runtimeKnown && !serverStatus.running) reason = tx('سمت listener تانل را اجرا نکرده است', 'The listener side has not started the tunnel');
            else if (runtimeKnown && !clientStatus.running) reason = tx('سمت dialer تانل را اجرا نکرده است', 'The dialer side has not started the tunnel');
            else if (runtimeKnown && !anyUserPort) reason = tx('پورت ورودی روی سمت listener باز نشده است', 'Input port is not listening on the listener side');
            else if (runtimeKnown && !poolReady && !directReady) reason = tx('نه اتصال رزرو آماده است و نه پل مستقیم سمت dialer باز است', 'No reserve worker is ready and dialer direct bridge is not listening');
            if (!reason && clientStatus.last_worker_error) reason = clientStatus.last_worker_error;
            return { ready, reason, internalStatus, externalStatus, serverStatus, clientStatus };
        }

        function threadGuardianMarkup(health) {
            const server = health.serverStatus || {};
            const client = health.clientStatus || {};
            const desired = Number(client.desired_workers || server.desired_workers || 0);
            const maxWorkers = Number(client.max_workers || server.max_workers || 0);
            const alive = Number(client.worker_threads_alive || 0);
            const ready = Number(client.ready_workers || server.pool_available || 0);
            const reaped = Number(client.idle_workers_reaped || server.idle_workers_reaped || 0);
            const pressure = Number(client.thread_guardian?.thread_pressure || server.thread_guardian?.thread_pressure || 0);
            return `
                <div class="tag-row" data-thread-guardian>
                    <span class="tag-pill tag-color-3" title="${tx('worker آماده برای اتصال بعدی', 'worker ready for next connection')}"><i data-lucide="activity"></i> ${tx('آماده', 'Ready')}: ${ready}</span>
                    <span class="tag-pill tag-color-0" title="${tx('سقف هوشمند فعلی نسبت به سقف کل', 'current smart target versus maximum')}"><i data-lucide="sliders-horizontal"></i> ${tx('هدف', 'Target')}: ${desired}/${maxWorkers}</span>
                    <span class="tag-pill tag-color-5" title="${tx('تردهای worker زنده سمت dialer', 'live dialer worker threads')}"><i data-lucide="cpu"></i> ${tx('زنده', 'Alive')}: ${alive}</span>
                    <span class="tag-pill tag-color-1" title="${tx('workerهای idle که با بستن socket پاک شده‌اند', 'idle workers reaped by closing sockets')}"><i data-lucide="scissors"></i> ${tx('پاک‌شده', 'Reaped')}: ${reaped}</span>
                    <span class="tag-pill" title="${tx('تعداد کل thread در process نود گزارش‌دهنده', 'total threads in reporting node process')}"><i data-lucide="gauge"></i> ${tx('فشار', 'Pressure')}: ${pressure}</span>
                </div>
            `;
        }

        function updateDashboard(status) {
            const nodeList = Object.values(status.nodes || {});
            const totalNodes = nodeList.length;
            const onlineNodes = nodeList.filter(node => node.status === 'online').length;
            document.getElementById('stat-nodes-count').innerText = `${onlineNodes} / ${totalNodes}`;
            document.getElementById('stat-links-count').innerText = Object.keys(status.links || {}).length;
            
            let totalRx = 0, totalTx = 0, totalThreads = 0, totalConns = 0;
            nodeList.forEach(node => {
                if (node.status === 'online' && node.stats) {
                    totalRx += node.stats.rx_speed || 0;
                    totalTx += node.stats.tx_speed || 0;
                    totalThreads += node.stats.threads || 0;
                    totalConns += node.stats.connections || 0;
                }
            });

            const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
            const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
            const rxVal = (totalRx / divisor).toFixed(2);
            const txVal = (totalTx / divisor).toFixed(2);
            
            document.getElementById('stat-net-speed').innerText = `${rxVal} / ${txVal} ${trafficUnit}/s`;
            document.getElementById('stat-threads-count').innerText = totalThreads;

            pushLiveChartPoints(parseFloat(rxVal), parseFloat(txVal), totalConns, trafficUnit);
            
            if (status.host_info) {
                document.getElementById('host-cpu').innerText = status.host_info.cpu_cores + ' Cores';
                document.getElementById('host-ram').innerText = status.host_info.ram_free_gb + ' GB / ' + status.host_info.ram_total_gb + ' GB';
                document.getElementById('host-swap').innerText = status.host_info.swap_free_gb + ' GB / ' + status.host_info.swap_total_gb + ' GB';
                document.getElementById('host-disk').innerText = status.host_info.disk_free_gb + ' GB / ' + status.host_info.disk_total_gb + ' GB';
                const uptime = Number(status.host_info.uptime_seconds || 0);
                const uptimeText = uptime ? `${Math.floor(uptime / 86400)}d ${Math.floor((uptime % 86400) / 3600)}h` : '-';
                const load = (status.host_info.load_avg || []).join(' / ') || '-';
                document.getElementById('host-load').innerText = `${load} | ${uptimeText}`;
                document.getElementById('host-process').innerText = `PID ${status.host_info.panel_pid || '-'} | RSS ${status.host_info.panel_rss_mb || 0} MB`;
                const docker = status.host_info.docker || {};
                document.getElementById('host-docker').innerText = docker.available ? `${docker.containers_running}/${docker.containers_total} Containers | ${docker.images} Images` : tx('در دسترس نیست', 'Unavailable');
            }
            pushPanelSystemChart(status, totalThreads, totalConns);
        }

        function pushPanelSystemChart(status, totalThreads, totalConns) {
            const host = status.host_info || {};
            const cores = Math.max(1, Number(host.cpu_cores || 1));
            const load1 = Number((host.load_avg || [0])[0] || 0);
            const cpuLoadPercent = Math.min(100, (load1 / cores) * 100);
            const ramTotal = Number(host.ram_total_gb || 0);
            const ramFree = Number(host.ram_free_gb || 0);
            const ramUsedPercent = ramTotal > 0 ? Math.max(0, Math.min(100, ((ramTotal - ramFree) / ramTotal) * 100)) : 0;
            if (charts.panelSystem) {
                charts.panelSystem.series[0].shift();
                charts.panelSystem.series[0].push(parseFloat(cpuLoadPercent.toFixed(1)));
                charts.panelSystem.series[1].shift();
                charts.panelSystem.series[1].push(parseFloat(ramUsedPercent.toFixed(1)));
                drawChart(charts.panelSystem, '%', ['CPU', 'RAM']);
            }
            if (charts.panelRuntime) {
                charts.panelRuntime.series[0].shift();
                charts.panelRuntime.series[0].push(Number(totalThreads || 0));
                charts.panelRuntime.series[1].shift();
                charts.panelRuntime.series[1].push(Number(totalConns || 0));
                drawChart(charts.panelRuntime, '', ['Threads', 'Sessions']);
            }
        }

        function pushLiveChartPoints(rxVal, txVal, totalConns, trafficUnit) {
            if (charts.traffic) {
                charts.traffic.series[0].shift();
                charts.traffic.series[0].push(rxVal);
                charts.traffic.series[1].shift();
                charts.traffic.series[1].push(txVal);
                drawChart(charts.traffic, trafficUnit + '/s', [tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
            }

            if (charts.connections) {
                charts.connections.series[0].shift();
                charts.connections.series[0].push(totalConns);
                drawChart(charts.connections, '', [tx('اتصالات', 'Connections')]);
            }
        }

        function drawLiveCharts(status) {
            if (!status || !charts.traffic || !charts.connections) return;
            const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
            drawChart(charts.traffic, trafficUnit + '/s', [tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
            drawChart(charts.connections, '', [tx('اتصالات', 'Connections')]);
        }

        function renderNodes(nodes) {
            const tbody = document.querySelector('#table-nodes tbody');
            const existingRows = new Map(Array.from(tbody.querySelectorAll('tr[data-node-id]')).map(row => [row.dataset.nodeId, row]));
            const seen = new Set();
            
            const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
            const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
            const panelNodeButton = document.getElementById('add-panel-node-btn');
            const hasPanelNode = Object.values(nodes || {}).some(node => node.is_panel_node);
            if (panelNodeButton) panelNodeButton.style.display = hasPanelNode ? 'none' : '';
            
            const orderedNodeIds = Object.keys(nodes).sort((a, b) => {
                const ao = Number(nodes[a]?.display_order ?? 100000);
                const bo = Number(nodes[b]?.display_order ?? 100000);
                return ao - bo || String(nodes[a]?.name || a).localeCompare(String(nodes[b]?.name || b));
            });
            orderedNodeIds.forEach((nid, nodeIndex) => {
                seen.add(nid);
                const n = nodes[nid];
                const stats = n.stats || { cpu: 0, ram: 0, rx_speed: 0, tx_speed: 0, threads: 0, connections: 0 };
                const isOnline = n.status === 'online';
                const isPaused = n.paused;
                const statusClass = isPaused ? 'text-warning' : (isOnline ? 'text-success' : 'text-danger');
                const statusText = isPaused ? tx('متوقف', 'Paused') : (isOnline ? t('online') : t('offline'));
                const pingText = isPaused
                    ? `<span class="text-warning" title="${tx('نود متوقف است', 'Node is paused')}"> ! </span>`
                    : (!isOnline || stats.ping_status === 'failed'
                        ? `<span class="text-danger" title="${tx('قطع یا بدون پاسخ ping', 'Disconnected or ping failed')}">∞</span>`
                        : (stats.ping_ms !== undefined ? `<span class="text-success">${esc(stats.ping_ms)} ms</span>` : `<span style="opacity:.7;">...</span>`));
                const lastCommand = n.last_command_result || {};
                const lastUpdate = lastCommand.type === 'node_update' ? (lastCommand.result || {}) : null;
                const versionCheck = nodeVersionChecks[nid] || {};
                const nodeVersion = stats.app_version || '-';
                const versionClass = versionCheck.state === 'current'
                    ? 'text-success'
                    : (versionCheck.state ? 'text-danger' : '');
                const versionStatus = versionCheck.state
                    ? `<div class="${versionClass}" style="margin-top:6px;font-size:12px;">${tx('نسخه', 'Version')}: ${esc(nodeVersion)} | ${esc(versionCheck.state)} — ${esc(versionCheck.reason || '')}</div>`
                    : `<div style="margin-top:6px;font-size:12px;color:var(--text-secondary);">${tx('نسخه', 'Version')}: ${esc(nodeVersion)}</div>`;
                const networkMode = stats.network_mode || 'unknown';
                const networkWarning = networkMode === 'bridge'
                    ? `<div class="text-danger" style="margin-top:6px;font-size:12px;">${tx('هشدار: Docker bridge می‌تواند پورت‌های VPN و سرویس‌های Host را مسدود کند؛ Host network پیشنهاد می‌شود.', 'Warning: Docker bridge can block VPN entry ports and host services; host network is recommended.')}</div>`
                    : '';
                const updateStatus = lastUpdate
                    ? `<div style="margin-top:8px; font-size:12px; color: var(--text-secondary);">
                            ${tx('آخرین آپدیت', 'Last update')}: 
                            <span class="${lastUpdate.success ? 'text-success' : 'text-danger'}">${lastUpdate.success ? tx('موفق', 'Success') : tx('ناموفق', 'Failed')}</span>
                            ${lastUpdate.version ? ` | v${esc(lastUpdate.version)}` : ''}
                            ${Array.isArray(lastUpdate.applied) ? ` | ${tx('اعمال‌شده', 'Applied')}: ${lastUpdate.applied.length}` : ''}
                            ${lastUpdate.error ? ` | ${esc(lastUpdate.error)}` : ''}
                       </div>`
                    : '';
                
                const tr = existingRows.get(nid) || document.createElement('tr');
                tr.dataset.nodeId = nid;
                tr.innerHTML = `
                    <td class="order-cell" data-label="${tx('ترتیب', 'Order')}">
                        <div class="order-control" title="${tx('تغییر ترتیب نمایش', 'Change display order')}">
                            <button class="order-button" onclick="moveNode('${nid}', -1)" ${nodeIndex === 0 ? 'disabled' : ''} title="${tx('انتقال به بالا', 'Move up')}"><i data-lucide="chevron-up"></i></button>
                            <button class="order-button" onclick="moveNode('${nid}', 1)" ${nodeIndex === orderedNodeIds.length - 1 ? 'disabled' : ''} title="${tx('انتقال به پایین', 'Move down')}"><i data-lucide="chevron-down"></i></button>
                        </div>
                    </td>
                    <td data-label="${tx('نام سرور', 'Server name')}"><div class="node-name-line"><strong>${esc(n.name)}</strong><span class="tag-row">${n.category ? `<span class="tag-pill tag-color-4">${esc(n.category)}</span>` : ''}${renderTags(n.tags || [])}</span></div></td>
                    <td data-label="${tx('نقش', 'Role')}"><span class="tag-pill node-role"><span class="status-dot ${isOnline ? '' : 'offline'}"></span>${(n.role === 'internal' || n.role === 'iran') ? t('internal') : t('external')}</span></td>
                    <td data-label="${tx('آدرس IP', 'IP address')}"><code>${esc(n.ip)}</code></td>
                    <td data-label="${tx('وضعیت', 'Status')}"><span class="status-pill"><span class="status-dot ${isOnline ? (isPaused ? 'warning' : '') : 'offline'}"></span><span class="${statusClass}">${statusText}</span><span style="margin-inline-start:8px;">${pingText}</span></span></td>
                    <td data-label="${tx('منابع سرور', 'Server resources')}">${tx('پردازنده', 'CPU')}: ${esc(stats.cpu)}% | ${tx('رم', 'RAM')}: ${esc(stats.ram)}%</td>
                    <td data-label="${tx('ترافیک', 'Traffic')}">${tx('دانلود', 'Download')}: ${(stats.rx_speed / divisor).toFixed(1)} ${trafficUnit}/s | ${tx('آپلود', 'Upload')}: ${(stats.tx_speed / divisor).toFixed(1)} ${trafficUnit}/s</td>
                    <td data-label="${tx('تردها/کانکشن', 'Threads/connections')}">${tx('تردها', 'Threads')}: ${stats.threads} | ${tx('فعال', 'Active')}: ${stats.connections}<br><small>${tx('شبکه', 'Network')}: ${esc(networkMode)}</small>${networkWarning}</td>
                    <td data-label="${tx('عملیات', 'Actions')}">
                        <div class="node-actions-line">
                            <button class="btn w-auto p-10 btn-danger" onclick="deleteNode('${nid}')" style="background: var(--danger);">${t('delete')}</button>
                            <button class="btn w-auto p-10" onclick="togglePauseNode('${nid}')" style="background: var(--warning); color: #000;">${isPaused ? tx('فعال‌سازی', 'Resume') : tx('توقف', 'Pause')}</button>
                            <button class="btn w-auto p-10" onclick="editNode('${nid}')" style="background: #10b981; color: white; box-shadow: 0 0 10px #10b981;">${tx('ویرایش', 'Edit')}</button>
                            <button class="btn w-auto p-10" onclick="testNodeConnection('${nid}')">${tx('تست ارتباط', 'Test connection')}</button>
                            <button class="btn w-auto p-10 btn-purple" onclick="openNodeSecrets('${nid}')">${tx('توکن/کلید', 'Token/Key')}</button>
                            <button class="btn w-auto p-10 btn-purple" onclick="queueNodeUpdate('${nid}')">${tx('آپدیت نود', 'Update node')}</button>
                            <button class="btn w-auto p-10 btn-cyan" onclick="checkNodeVersions('${nid}')">${tx('بررسی نسخه', 'Check version')}</button>
                            <button class="btn w-auto p-10 btn-cyan" onclick="openNodeSshModal('${nid}')">SSH</button>
                        </div>
                        ${versionStatus}
                        ${updateStatus}
                    </td>
                `;
                // appendChild also moves an existing row, so order changes are
                // visible immediately without requiring a page refresh.
                tbody.appendChild(tr);
            });
            existingRows.forEach((row, nid) => {
                if (!seen.has(nid)) row.remove();
            });
            createInlineIcons(tbody);
        }

        function linkCategoryKey(link) {
            return link.category || `${link.engine || 'builtin'} / ${link.tunnel_mode || 'tcp'}`;
        }

        function estimateCategoryTraffic(items, nodes) {
            const nodeIds = new Set();
            items.forEach(({ link }) => {
                nodeIds.add(link.internal_node_id || link.iran_node_id);
                nodeIds.add(link.external_node_id || link.foreign_node_id);
            });
            let rx = 0, tx = 0;
            nodeIds.forEach(nid => {
                const stats = nodes[nid]?.stats || {};
                rx += Number(stats.rx_speed || 0);
                tx += Number(stats.tx_speed || 0);
            });
            return { rx, tx };
        }

        function linksStructureSignature(links) {
            return JSON.stringify(Object.entries(links || {}).sort(([a], [b]) => a.localeCompare(b)).map(([id, link]) => [
                id, link.name, link.engine, link.tunnel_mode, link.internal_node_id || link.iran_node_id,
                link.external_node_id || link.foreign_node_id, link.bridge_port, link.sync_port,
                link.direction || 'external_to_internal', link.category || '', Number(link.display_order ?? 100000),
                JSON.stringify(link.ports || []), JSON.stringify(link.tags || [])
            ]).concat([JSON.stringify(latestStatus?.link_category_order || [])]));
        }

        function renderLinksLive(links, nodes) {
            const signature = linksStructureSignature(links);
            if (signature !== lastLinksSignature || !document.querySelector('#links-container .link-category')) {
                renderLinks(links, nodes);
            } else {
                updateLinkLiveSections(links, nodes);
            }
        }

        function renderLinks(links, nodes) {
            const container = document.getElementById('links-container');
            const chartsContainer = document.getElementById('link-category-charts');
            const shouldRestoreScroll = currentTab === 'links';
            const scrollX = window.scrollX;
            const scrollY = window.scrollY;
            lastLinksSignature = linksStructureSignature(links);
            container.innerHTML = '';
            if (chartsContainer) chartsContainer.innerHTML = '';

            populateLinkNodeSelects(nodes || {}, { preserveSelection: isModalVisible('modal-add-link') });

            const grouped = {};
            Object.entries(links).forEach(([lid, link]) => {
                const key = linkCategoryKey(link);
                grouped[key] = grouped[key] || [];
                grouped[key].push({ id: lid, link });
            });

            const savedCategoryOrder = latestStatus?.link_category_order || [];
            const categoryRank = name => {
                const index = savedCategoryOrder.indexOf(name);
                return index >= 0 ? index : 100000;
            };
            Object.entries(grouped).sort(([a], [b]) => categoryRank(a) - categoryRank(b) || a.localeCompare(b)).forEach(([category, items], categoryIndex, categoryEntries) => {
                items.sort((a, b) => Number(a.link.display_order ?? 100000) - Number(b.link.display_order ?? 100000) || String(a.link.name || a.id).localeCompare(String(b.link.name || b.id)));
                const active = items.filter(({ id, link }) => {
                    return linkRuntimeHealth(nodes, id, link).ready;
                }).length;
                const traffic = estimateCategoryTraffic(items, nodes);
                const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
                const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
                const chartId = `category-chart-${categoryIndex}`;
                if (chartsContainer) {
                    const chartCard = document.createElement('div');
                    chartCard.className = 'glass-card';
                    chartCard.dataset.category = category;
                    chartCard.innerHTML = `
                        <div class="flex-between">
                            <h3 style="font-size: 16px;">${esc(category)}</h3>
                            <span class="tag-pill">${tx('گراف زنده دسته', 'Live category chart')}</span>
                        </div>
                        <div class="category-metrics">
                            <div class="category-metric active"><span>${tx('تانل فعال', 'Active tunnels')}</span><strong data-category-active>${active}</strong></div>
                            <div class="category-metric"><span>${tx('کل تانل‌ها', 'Total tunnels')}</span><strong data-category-total>${items.length}</strong></div>
                            <div class="category-metric download"><span>${tx('دانلود', 'Download')}</span><strong data-category-rx>${(traffic.rx / divisor).toFixed(2)} ${trafficUnit}/s</strong></div>
                            <div class="category-metric upload"><span>${tx('آپلود', 'Upload')}</span><strong data-category-tx>${(traffic.tx / divisor).toFixed(2)} ${trafficUnit}/s</strong></div>
                        </div>
                        <div class="category-chart-frame"><canvas id="${chartId}"></canvas></div>
                    `;
                    chartsContainer.appendChild(chartCard);
                }

                const details = document.createElement('details');
                details.className = 'glass-card link-category';
                details.dataset.category = category;
                details.open = !!linkCategoryOpenStates[category];
                details.addEventListener('toggle', () => {
                    linkCategoryOpenStates[category] = details.open;
                    localStorage.setItem('p00rija_link_category_open', JSON.stringify(linkCategoryOpenStates));
                });
                details.innerHTML = `
                    <summary>
                        <div class="link-card-head">
                            <div class="order-control" onclick="event.preventDefault(); event.stopPropagation();" title="${tx('ترتیب دسته', 'Category order')}">
                                <button class="order-button" onclick="moveLinkCategory(decodeURIComponent('${encodeURIComponent(category)}'), -1)" ${categoryIndex === 0 ? 'disabled' : ''}><i data-lucide="chevron-up"></i></button>
                                <button class="order-button" onclick="moveLinkCategory(decodeURIComponent('${encodeURIComponent(category)}'), 1)" ${categoryIndex === categoryEntries.length - 1 ? 'disabled' : ''}><i data-lucide="chevron-down"></i></button>
                            </div>
                            <div class="link-card-main">
                                <h3>${esc(category)}</h3>
                                <div class="tag-row">
                                    <span class="tag-pill tag-color-3">${tx('فعال', 'Active')}: ${active}</span>
                                    <span class="tag-pill tag-color-0">${tx('کل', 'Total')}: ${items.length}</span>
                                </div>
                            </div>
                            <span class="tag-pill">${tx('باز/بسته کردن دسته', 'Toggle category')}</span>
                        </div>
                    </summary>
                    <div style="display: flex; flex-direction: column; gap: 16px; margin-top: 16px;"></div>
                `;
                const inner = details.querySelector('summary + div');
                items.forEach(({ id: lid, link: l }, linkIndex) => {
                    const irNode = nodes[l.internal_node_id || l.iran_node_id] || { name: tx('نامشخص', 'Unknown') };
                    const foreignNode = nodes[l.external_node_id || l.foreign_node_id] || { name: tx('نامشخص', 'Unknown') };
                    const isPaused = !!l.paused;
                    const health = linkRuntimeHealth(nodes, lid, l);
                    const isLinked = health.ready;
                    const readableMode = l.tunnel_mode === 'reverse_tcp' ? 'Reverse TCP Tunnel' : (l.tunnel_mode === 'amneziawg_v2' ? 'AmneziaWG v2' : (l.tunnel_mode === 'websocket' ? 'WebSocket' : (l.tunnel_mode === 'http_obfs' ? 'HTTP Obfs' : l.tunnel_mode || 'TCP RAW')));
                    const modeText = `${l.engine || 'builtin'} / ${readableMode}`;
                    const tlsText = l.tls_enabled ? ' + TLS (Secure)' : '';
                    const directionText = (l.direction || 'external_to_internal') === 'internal_to_external'
                        ? tx('داخلی به خارجی', 'Internal to External')
                        : tx('خارجی به داخلی', 'External to Internal');
                    const portRows = (l.ports || []).map((port, index) => {
                        const targetStatus = targetPortStatusMarkup(getTargetPortCheck(nodes, lid, l, port.user_port));
                        return `<tr>
                            <td data-label="${tx('پورت ورودی', 'Input port')}"><code>${esc(port.user_port)}</code><br><small class="text-success">${tx('روی نود داخلی listen می‌شود', 'Listens on internal node')}</small></td>
                            <td data-label="${tx('پورت مقصد', 'Target port')}"><code>${esc(port.target_port)}</code><br><small data-target-port-status data-user-port="${esc(port.user_port)}">${targetStatus}</small></td>
                            <td data-label="${tx('وضعیت', 'Status')}" data-port-link-status data-user-port="${esc(port.user_port)}">${isLinked ? `<span class="text-success">${tx('تانل برقرار', 'Tunnel connected')}</span>` : `<span class="text-danger" title="${esc(health.reason)}">${tx('تانل آماده نیست', 'Tunnel not ready')}</span>`}</td>
                            <td data-label="${tx('عملیات', 'Actions')}">
                                <div class="flex-between gap-10" style="justify-content:flex-start; flex-wrap:wrap;">
                                    <button class="btn w-auto p-10" onclick="editPortMapping('${lid}', ${index}, ${esc(port.user_port)}, ${esc(port.target_port)})" style="background: #10b981; color: white; font-size: 12px; padding: 4px 8px;">${tx('ویرایش', 'Edit')}</button>
                                    <button class="btn w-auto p-10 btn-purple" onclick="testPortPayload('${lid}', ${index})" style="font-size: 12px; padding: 4px 8px;">${tx('تست پکیج', 'Payload test')}</button>
                                    <button class="btn w-auto p-10" onclick="deletePortMapping('${lid}', ${index})" style="background: var(--danger); font-size: 12px; padding: 4px 8px;">${t('delete')}</button>
                                </div>
                            </td>
                        </tr>`;
                    }).join('');
                    const card = document.createElement('div');
                    card.dataset.linkId = lid;
                    card.style.border = '1px solid var(--border-card)';
                    card.style.borderRadius = '8px';
                    card.style.padding = '16px';
                    card.innerHTML = `
                        <div class="link-card-head mb-20">
                            <div class="order-control vertical" title="${tx('تغییر ترتیب تانل', 'Change tunnel order')}">
                                <button class="order-button" onclick="moveLink('${lid}', -1)" ${linkIndex === 0 ? 'disabled' : ''}><i data-lucide="chevron-up"></i></button>
                                <button class="order-button" onclick="moveLink('${lid}', 1)" ${linkIndex === items.length - 1 ? 'disabled' : ''}><i data-lucide="chevron-down"></i></button>
                            </div>
                            <div class="link-card-main">
                              <div class="flex-between">
                               <div>
                                <h3 style="font-size: 18px; margin-bottom: 6px;">${esc(l.name)} <span class="tag-pill" style="background: rgba(0,240,255,0.1); border-color: var(--accent-blue);">${modeText}${tlsText}</span></h3>
                                <p style="font-size: 14px; color: var(--text-secondary);">
                                    ${tx('نود داخلی', 'Internal node')}: <strong>${esc(irNode.name)}</strong> <i data-lucide="arrow-right"></i> ${tx('نود خارجی', 'External node')}: <strong>${esc(foreignNode.name)}</strong>
                                </p>
                                <div class="tag-row"><span class="tag-pill tag-color-5">${tx('جهت', 'Direction')}: ${directionText}</span>${renderTags(l.tags || [])}</div>
                                ${threadGuardianMarkup(health)}
                               </div>
                            <div class="flex-between gap-10 link-actions">
                                <span class="tag-pill">${tx('پل', 'Bridge')}: ${l.bridge_port} | ${tx('همگام‌سازی', 'Sync')}: ${l.sync_port}</span>
                                <span class="status-pill" data-link-status-pill title="${esc(health.reason)}">
                                    <div class="status-dot" data-link-status-dot style="background-color: ${isPaused ? 'var(--warning)' : (isLinked ? 'var(--success)' : 'var(--danger)')}; box-shadow: 0 0 10px ${isPaused ? 'var(--warning)' : (isLinked ? 'var(--success)' : 'var(--danger)')};"></div>
                                    <span data-link-status-text>${isPaused ? tx('متوقف', 'Paused') : (isLinked ? t('connected') : t('disconnected'))}</span>
                                </span>
                                <button class="btn w-auto p-10 btn-danger" onclick="deleteLink('${lid}')" style="background: var(--danger);">${tx('حذف تانل', 'Delete tunnel')}</button>
                                <button class="btn w-auto p-10" onclick="togglePauseLink('${lid}')" style="background: var(--warning); color: #000;">${isPaused ? tx('ادامه', 'Resume') : tx('توقف', 'Pause')}</button>
                                <button class="btn w-auto p-10" onclick="editLink('${lid}')" style="background: #10b981; color: white; box-shadow: 0 0 10px #10b981;">${tx('ویرایش', 'Edit')}</button>
                                <button class="btn w-auto p-10" onclick="testLink('${lid}')">${tx('تست اتصال', 'Test connection')}</button>
                                <button class="btn w-auto p-10" onclick="showEngineConfig('${lid}')">${tx('نمایش کانفیگ موتور', 'Show engine config')}</button>
                            </div>
                              </div>
                            </div>
                        </div>
                        <div style="border-top: 1px solid var(--border-card); padding-top: 15px;">
                            <h4 class="mb-20">${tx('لیست پورت‌های هدایت شده (Port Forwarding)', 'Forwarded ports (Port Forwarding)')}</h4>
                            <div class="table-wrap link-port-wrap"><table class="link-port-table">
                                <thead><tr><th>${tx('پورت ورودی سمت listener', 'Listener input port')}</th><th>${tx('پورت مقصد سمت dialer', 'Dialer target port')}</th><th>${tx('وضعیت', 'Status')}</th><th>${tx('عملیات', 'Actions')}</th></tr></thead>
                                <tbody>
                                    ${portRows}
                                    <tr>
                                        <td data-label="${tx('پورت ورودی', 'Input port')}"><input type="text" id="add-user-port-${lid}" class="form-input" placeholder="${tx('پورت داخلی (یا بازه)', 'Internal port/range')}" style="padding: 6px; font-size: 14px;"></td>
                                        <td data-label="${tx('پورت مقصد', 'Target port')}"><input type="text" id="add-target-port-${lid}" class="form-input" placeholder="${tx('پورت خارجی (یا بازه)', 'External port/range')}" style="padding: 6px; font-size: 14px;"></td>
                                        <td data-label="${tx('وضعیت', 'Status')}">-</td>
                                        <td data-label="${tx('عملیات', 'Actions')}"><button class="btn w-auto p-10" onclick="addPortMapping('${lid}')" style="font-size: 12px; padding: 6px 12px;">${tx('افزودن پورت', 'Add port')}</button></td>
                                    </tr>
                                </tbody>
                            </table></div>
                        </div>
                    `;
                    inner.appendChild(card);
                    createInlineIcons(card);
                });
                container.appendChild(details);
                const canvas = document.getElementById(chartId);
                if (!canvas) return;
                categoryCharts[category] = categoryCharts[category] || { canvas, series: [Array(20).fill(0), Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_ACTIVE, COLOR_DOWNLOAD, COLOR_UPLOAD] };
                categoryCharts[category].canvas = canvas;
                categoryCharts[category].colors = [COLOR_ACTIVE, COLOR_DOWNLOAD, COLOR_UPLOAD];
                categoryCharts[category].series[0].shift();
                categoryCharts[category].series[0].push(active);
                categoryCharts[category].series[1].shift();
                categoryCharts[category].series[1].push(parseFloat((traffic.rx / divisor).toFixed(2)));
                categoryCharts[category].series[2].shift();
                categoryCharts[category].series[2].push(parseFloat((traffic.tx / divisor).toFixed(2)));
                drawChart(categoryCharts[category], '', [tx('فعال', 'Active'), tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
            });
            createInlineIcons(container);
            if (shouldRestoreScroll) {
                requestAnimationFrame(() => window.scrollTo(scrollX, scrollY));
            }
        }

        function updateLinkLiveSections(links, nodes) {
            const grouped = {};
            Object.entries(links || {}).forEach(([lid, link]) => {
                const key = linkCategoryKey(link);
                grouped[key] = grouped[key] || [];
                grouped[key].push({ id: lid, link });
            });
            const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
            const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
            Object.entries(grouped).forEach(([category, items]) => {
                const active = items.filter(({ id, link }) => {
                    return linkRuntimeHealth(nodes, id, link).ready;
                }).length;
                const traffic = estimateCategoryTraffic(items, nodes);
                const chartCard = document.querySelector(`#link-category-charts [data-category="${cssEscape(category)}"]`);
                if (chartCard) {
                    const activeEl = chartCard.querySelector('[data-category-active]');
                    const totalEl = chartCard.querySelector('[data-category-total]');
                    const rxEl = chartCard.querySelector('[data-category-rx]');
                    const txEl = chartCard.querySelector('[data-category-tx]');
                    if (activeEl) activeEl.innerText = active;
                    if (totalEl) totalEl.innerText = items.length;
                    if (rxEl) rxEl.innerText = `${(traffic.rx / divisor).toFixed(2)} ${trafficUnit}/s`;
                    if (txEl) txEl.innerText = `${(traffic.tx / divisor).toFixed(2)} ${trafficUnit}/s`;
                }
                const chart = categoryCharts[category];
                if (chart) {
                    chart.series[0].shift();
                    chart.series[0].push(active);
                    chart.series[1].shift();
                    chart.series[1].push(parseFloat((traffic.rx / divisor).toFixed(2)));
                    chart.series[2].shift();
                    chart.series[2].push(parseFloat((traffic.tx / divisor).toFixed(2)));
                    drawChart(chart, '', [tx('فعال', 'Active'), tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
                }
            });
            Object.entries(links || {}).forEach(([lid, link]) => {
                const card = document.querySelector(`[data-link-id="${cssEscape(lid)}"]`);
                if (!card) return;
                const isPaused = !!link.paused;
                const health = linkRuntimeHealth(nodes, lid, link);
                const isLinked = health.ready;
                const color = isPaused ? 'var(--warning)' : (isLinked ? 'var(--success)' : 'var(--danger)');
                const dot = card.querySelector('[data-link-status-dot]');
                const text = card.querySelector('[data-link-status-text]');
                if (dot) {
                    dot.style.backgroundColor = color;
                    dot.style.boxShadow = `0 0 10px ${color}`;
                }
                const pill = card.querySelector('[data-link-status-pill]');
                if (pill) pill.title = health.reason || '';
                if (text) text.innerText = isPaused ? tx('متوقف', 'Paused') : (isLinked ? t('connected') : t('disconnected'));
                const guardian = card.querySelector('[data-thread-guardian]');
                if (guardian) {
                    const wrapper = document.createElement('div');
                    wrapper.innerHTML = threadGuardianMarkup(health).trim();
                    guardian.replaceWith(wrapper.firstElementChild);
                    createInlineIcons(card);
                }
                (link.ports || []).forEach(port => {
                    const portStatusEl = card.querySelector(`[data-port-link-status][data-user-port="${cssEscape(port.user_port)}"]`);
                    if (portStatusEl) {
                        portStatusEl.innerHTML = isLinked
                            ? `<span class="text-success">${tx('تانل برقرار', 'Tunnel connected')}</span>`
                            : `<span class="text-danger" title="${esc(health.reason)}">${tx('تانل آماده نیست', 'Tunnel not ready')}</span>`;
                    }
                    const statusEl = card.querySelector(`[data-target-port-status][data-user-port="${cssEscape(port.user_port)}"]`);
                    if (statusEl) statusEl.innerHTML = targetPortStatusMarkup(getTargetPortCheck(nodes, lid, link, port.user_port));
                });
            });
        }

        function renderLogs(logs) {
            const tbody = document.querySelector('#table-logs tbody');
            tbody.innerHTML = '';
            
            const reversed = [...logs].reverse();
            reversed.forEach(entry => {
                let lvlClass = '';
                if (entry.level === 'error') lvlClass = 'text-danger';
                else if (entry.level === 'warning') lvlClass = 'text-warning';
                else lvlClass = 'text-success';

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="color: var(--text-secondary); font-size: 13px;">${esc(entry.timestamp)}</td>
                    <td><strong>${esc(entry.source)}</strong></td>
                    <td class="${lvlClass}">${esc(entry.level).toUpperCase()}</td>
                    <td><code>${esc(entry.message)}</code></td>
                `;
                tbody.appendChild(tr);
            });
        }

        const tunnelOptionMatrix = {
            builtin: {
                transports: [['reverse_tcp', 'Reverse TCP'], ['tcp', 'TCP'], ['websocket', 'WebSocket'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['reverse_tcp', 'Reverse TCP Tunnel'], ['tcp', 'TCP Tunnel'], ['websocket', 'WebSocket Tunnel'], ['http_obfs', 'HTTP Obfuscation']],
                networks: [['tcp', 'TCP']]
            },
            gost: {
                transports: [['tcp', 'TCP'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS'], ['grpc', 'gRPC']],
                modes: [['websocket', 'WebSocket Tunnel'], ['http_obfs', 'HTTP Obfuscation'], ['grpc', 'gRPC Tunnel']],
                networks: [['tcp', 'TCP']]
            },
            backhaul: {
                transports: [['tcp', 'TCP'], ['udp', 'UDP'], ['tcpmux', 'TCPMux'], ['wsmux', 'WSMux']],
                modes: [['tcp', 'TCP Tunnel'], ['udp', 'UDP Tunnel'], ['tcpmux', 'TCPMux'], ['wsmux', 'WSMux'], ['websocket', 'WebSocket Tunnel']],
                networks: [['tcp', 'TCP'], ['udp', 'UDP']]
            },
            rathole: {
                transports: [['tcp', 'TCP'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['tcp', 'TCP Tunnel'], ['websocket', 'WebSocket Tunnel']],
                networks: [['tcp', 'TCP']]
            },
            chisel: {
                transports: [['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['websocket', 'WebSocket Tunnel'], ['http_obfs', 'HTTP Obfuscation']],
                networks: [['tcp', 'TCP']]
            },
            frp: {
                transports: [['tcp', 'TCP'], ['udp', 'UDP'], ['kcp', 'KCP'], ['quic', 'QUIC']],
                modes: [['tcp', 'TCP Tunnel'], ['udp', 'UDP Tunnel'], ['tcp_udp', 'TCP + UDP'], ['kcp', 'KCP'], ['quic', 'QUIC']],
                networks: [['tcp', 'TCP'], ['udp', 'UDP'], ['tcp_udp', 'TCP + UDP']]
            },
            xray: {
                transports: [['tcp', 'TCP'], ['grpc', 'gRPC TLS'], ['h2', 'HTTP/2 TLS'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['vless_reality', 'Xray VLESS Reality'], ['reality_grpc', 'REALITY gRPC'], ['reality_h2', 'REALITY HTTP/2'], ['reality_ws', 'REALITY WebSocket']],
                networks: [['tcp', 'TCP']]
            },
            muxquantum: {
                transports: [['tcpmux', 'TCPMux'], ['httpsmux', 'HTTPSMux'], ['quantummux', 'QuantumMux'], ['tunmux', 'TunMux'], ['mux_wss', 'Mux WSS'], ['mux_h2', 'Mux HTTP/2 TLS'], ['mux_h3', 'Mux HTTP/3 QUIC'], ['mux_quic', 'Mux QUIC'], ['mux_grpc', 'Mux gRPC TLS'], ['mux_shadowtls', 'Mux ShadowTLS'], ['mux_reality', 'Mux REALITY'], ['mux_anytls', 'Mux AnyTLS'], ['mux_naive', 'Mux Naive HTTPS'], ['mux_kcp', 'Mux KCP']],
                modes: [['tcpmux', 'TCPMux'], ['httpsmux', 'HTTPSMux'], ['quantummux', 'QuantumMux'], ['tunmux', 'TunMux'], ['mux_wss', 'Mux WSS'], ['mux_h2', 'Mux HTTP/2 TLS'], ['mux_h3', 'Mux HTTP/3 QUIC'], ['mux_quic', 'Mux QUIC'], ['mux_grpc', 'Mux gRPC TLS'], ['mux_shadowtls', 'Mux ShadowTLS'], ['mux_reality', 'Mux REALITY'], ['mux_anytls', 'Mux AnyTLS'], ['mux_naive', 'Mux Naive HTTPS'], ['mux_kcp', 'Mux KCP UDP']],
                networks: [['tcp', 'TCP'], ['udp', 'UDP']]
            },
            hysteria2: {
                transports: [['quic', 'QUIC'], ['h3', 'HTTP/3 Masquerade']],
                modes: [['quic', 'QUIC'], ['http3_masquerade', 'HTTP/3 Masquerade'], ['hysteria2_salamander', 'Salamander Obfuscation'], ['hysteria2_gecko', 'Gecko Obfuscation']],
                networks: [['udp', 'UDP']]
            },
            singbox: {
                transports: [['tcp', 'TCP'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS'], ['grpc', 'gRPC'], ['h2', 'HTTP/2 TLS'], ['h3', 'HTTP/3 QUIC'], ['xhttp', 'XHTTP'], ['shadowtls', 'ShadowTLS'], ['tuic', 'TUIC'], ['anytls', 'AnyTLS'], ['naive', 'Naive HTTPS'], ['ech', 'ECH TLS'], ['turn_tls', 'TURN-like TLS Relay']],
                modes: [['vless_reality', 'VLESS REALITY'], ['reality_grpc', 'REALITY gRPC'], ['reality_h2', 'REALITY HTTP/2'], ['reality_ws', 'REALITY WS'], ['xhttp', 'XHTTP REALITY'], ['shadowtls', 'ShadowTLS'], ['shadowtls_ws', 'ShadowTLS + WS'], ['shadowtls_h2', 'ShadowTLS + HTTP/2'], ['tuic_quic', 'TUIC QUIC'], ['quic', 'Hysteria2 QUIC'], ['http3_masquerade', 'HTTP/3 Masquerade'], ['hysteria2_salamander', 'Hysteria2 Salamander'], ['hysteria2_gecko', 'Hysteria2 Gecko'], ['naive_https', 'Naive HTTPS'], ['naive_h2', 'Naive HTTP/2'], ['http2_tls', 'HTTP/2 TLS'], ['anytls', 'AnyTLS'], ['anytls_h2', 'AnyTLS HTTP/2'], ['anytls_ws', 'AnyTLS WebSocket'], ['ech_tls', 'ECH TLS'], ['ech_h2', 'ECH HTTP/2'], ['turn_tls', 'TURN-like TLS Relay'], ['websocket', 'WebSocket TLS'], ['grpc', 'gRPC TLS']],
                networks: [['tcp', 'TCP'], ['udp', 'UDP'], ['tcp_udp', 'TCP + UDP']]
            },
            tuic: {
                transports: [['tuic', 'TUIC'], ['quic', 'QUIC'], ['udp_over_stream', 'UDP over Stream']],
                modes: [['tuic_quic', 'TUIC QUIC'], ['tuic_udp_over_stream', 'TUIC UDP over Stream'], ['quic', 'QUIC']],
                networks: [['udp', 'UDP']]
            },
            masque: {
                transports: [['masque_h3', 'MASQUE HTTP/3'], ['connect_udp', 'CONNECT-UDP']],
                modes: [['masque_connect_udp', 'MASQUE CONNECT-UDP'], ['masque_quic_proxy', 'MASQUE QUIC-aware Proxy']],
                networks: [['udp', 'UDP']]
            },
            naiveproxy: {
                transports: [['naive', 'Naive HTTPS'], ['h2', 'HTTP/2 TLS']],
                modes: [['naive_https', 'Naive HTTPS Camouflage'], ['naive_h2', 'Naive HTTP/2 Chrome-like'], ['http2_tls', 'HTTP/2 TLS']],
                networks: [['tcp', 'TCP']]
            },
            shadowtls: {
                transports: [['shadowtls', 'ShadowTLS'], ['wss', 'WebSocket TLS'], ['h2', 'HTTP/2 TLS']],
                modes: [['shadowtls', 'ShadowTLS'], ['shadowtls_ws', 'ShadowTLS + WS'], ['shadowtls_h2', 'ShadowTLS + HTTP/2']],
                networks: [['tcp', 'TCP']]
            },
            brook: {
                transports: [['tcp', 'TCP'], ['ws', 'WebSocket'], ['wss', 'WebSocket TLS']],
                modes: [['tcp', 'Brook TCP'], ['websocket', 'Brook WS'], ['http_obfs', 'Brook Web-like']],
                networks: [['tcp', 'TCP']]
            },
            mieru: {
                transports: [['tcp', 'TCP'], ['h2', 'HTTP/2 TLS'], ['wss', 'WebSocket TLS']],
                modes: [['http2_tls', 'HTTP/2 TLS'], ['websocket', 'WebSocket TLS'], ['tcp', 'TCP']],
                networks: [['tcp', 'TCP']]
            },
            amneziawg: {
                transports: [['amneziawg_udp', 'AmneziaWG UDP']],
                modes: [['amneziawg_v2', 'AmneziaWG v2']],
                networks: [['udp', 'UDP']]
            },
            wireguard: {
                transports: [['wireguard_udp', 'WireGuard UDP']],
                modes: [['wireguard_kernel', 'WireGuard Kernel / wg-quick']],
                networks: [['udp', 'UDP']]
            },
            ssh: {
                transports: [['ssh_dynamic', 'SSH Dynamic SOCKS5'], ['ssh_local', 'SSH Local -L'], ['ssh_remote', 'SSH Remote -R'], ['ssh_jump', 'SSH Jump -J']],
                modes: [['ssh_socks5', 'SOCKS5 Dynamic (-D)'], ['ssh_local_forward', 'Local Port Forward (-L)'], ['ssh_remote_forward', 'Remote/Reverse Forward (-R)'], ['ssh_jump', 'Jump Hosts / Multi-Hop (-J)']],
                networks: [['tcp', 'TCP']]
            },
            stunnel: {
                transports: [['stunnel_tls', 'Stunnel TLS']],
                modes: [['stunnel_tls_wrap', 'TLS Wrapping']],
                networks: [['tcp', 'TCP']]
            },
            aead: {
                transports: [['aead_tcp', 'AEAD TCP'], ['port_forward', 'Port Forward'], ['socks5', 'SOCKS5']],
                modes: [['aead_port_forward', 'AEAD Port Forward'], ['aead_socks5', 'AEAD SOCKS5 Proxy'], ['client_port_forward', 'Client Port Forward'], ['client_socks5', 'Client SOCKS5 Proxy']],
                networks: [['tcp', 'TCP']]
            },
            rawsock: {
                transports: [['raw_ip', 'Raw IP Socket']],
                modes: [['raw_socket', 'Raw Socket']],
                networks: [['tcp_udp', 'TCP + UDP']]
            }
        };

        function setSelectOptions(select, options, preferred) {
            if (!select) return;
            const current = preferred || select.value;
            select.innerHTML = options.map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join('');
            select.value = options.some(([value]) => value === current) ? current : options[0]?.[0] || '';
        }

        const modeTransportMap = {
            websocket: 'ws', http_obfs: 'ws', grpc: 'grpc', tcpmux: 'tcpmux', httpsmux: 'httpsmux',
            quantummux: 'quantummux', tunmux: 'tunmux', kcp: 'kcp', quic: 'quic', udp: 'udp',
            tcp: 'tcp', reverse_tcp: 'reverse_tcp', tcp_udp: 'tcp', vless_reality: 'tcp', reality_grpc: 'grpc', reality_h2: 'h2',
            reality_ws: 'wss', shadowtls: 'shadowtls', shadowtls_ws: 'shadowtls', shadowtls_h2: 'shadowtls',
            tuic_quic: 'tuic', naive_https: 'naive', naive_h2: 'h2', http2_tls: 'h2',
            http3_masquerade: 'h3', hysteria2_salamander: 'quic', hysteria2_gecko: 'h3',
            anytls: 'anytls', anytls_h2: 'anytls', anytls_ws: 'anytls', ech_tls: 'ech', ech_h2: 'ech',
            masque_connect_udp: 'masque_h3', masque_quic_proxy: 'connect_udp', xhttp: 'xhttp',
            tuic_udp_over_stream: 'udp_over_stream', turn_tls: 'turn_tls',
            mux_wss: 'mux_wss', mux_h2: 'mux_h2', mux_h3: 'mux_h3', mux_quic: 'mux_quic',
            mux_grpc: 'mux_grpc', mux_shadowtls: 'mux_shadowtls', mux_reality: 'mux_reality',
            mux_anytls: 'mux_anytls', mux_naive: 'mux_naive', mux_kcp: 'mux_kcp',
            amneziawg_v2: 'amneziawg_udp',
            wireguard_kernel: 'wireguard_udp',
            ssh_socks5: 'ssh_dynamic', ssh_local_forward: 'ssh_local', ssh_remote_forward: 'ssh_remote',
            ssh_jump: 'ssh_jump', stunnel_tls_wrap: 'stunnel_tls', raw_socket: 'raw_ip',
            aead_port_forward: 'aead_tcp', aead_socks5: 'socks5',
            client_port_forward: 'port_forward', client_socks5: 'socks5'
        };
        const udpTunnelModes = ['udp', 'kcp', 'quic', 'tuic_quic', 'tuic_udp_over_stream', 'http3_masquerade', 'hysteria2_salamander', 'hysteria2_gecko', 'masque_connect_udp', 'masque_quic_proxy', 'mux_h3', 'mux_quic', 'mux_kcp', 'amneziawg_v2', 'wireguard_kernel'];
        const tlsTunnelModes = ['websocket', 'http_obfs', 'grpc', 'wss', 'httpsmux', 'mux_wss', 'mux_h2', 'mux_h3', 'mux_quic', 'mux_grpc', 'mux_shadowtls', 'mux_reality', 'mux_anytls', 'mux_naive', 'quic', 'vless_reality', 'reality_grpc', 'reality_h2', 'reality_ws', 'xhttp', 'shadowtls', 'shadowtls_ws', 'shadowtls_h2', 'tuic_quic', 'tuic_udp_over_stream', 'naive_https', 'naive_h2', 'http2_tls', 'http3_masquerade', 'hysteria2_salamander', 'hysteria2_gecko', 'masque_connect_udp', 'masque_quic_proxy', 'anytls', 'anytls_h2', 'anytls_ws', 'ech_tls', 'ech_h2', 'turn_tls', 'stunnel_tls_wrap'];
        const tlsTransports = ['wss', 'httpsmux', 'quic', 'h2', 'h3', 'grpc', 'xhttp', 'shadowtls', 'tuic', 'udp_over_stream', 'naive', 'anytls', 'ech', 'masque_h3', 'connect_udp', 'turn_tls', 'mux_wss', 'mux_h2', 'mux_h3', 'mux_quic', 'mux_grpc', 'mux_shadowtls', 'mux_reality', 'mux_anytls', 'mux_naive', 'stunnel_tls'];

        function syncTunnelOptions(preferred = {}) {
            const engine = document.getElementById('link-engine').value;
            const config = tunnelOptionMatrix[engine] || tunnelOptionMatrix.builtin;
            setSelectOptions(document.getElementById('link-transport'), config.transports, preferred.transport);
            setSelectOptions(document.getElementById('link-network'), config.networks, preferred.network);
            setSelectOptions(document.getElementById('link-tunnel-mode'), config.modes, preferred.mode);
            syncTransportTls();
            toggleEngineOptions();
            toggleObfsOptions();
        }

        function syncProfileModeOptions() {
            const engine = document.getElementById('profile-engine')?.value || 'builtin';
            const config = tunnelOptionMatrix[engine] || tunnelOptionMatrix.builtin;
            setSelectOptions(document.getElementById('profile-mode'), config.modes);
        }

        function syncTransportTls() {
            const transport = document.getElementById('link-transport').value;
            const tlsEl = document.getElementById('link-tls-enabled');
            if (tlsTransports.includes(transport)) tlsEl.checked = true;
            if (transport === 'udp') tlsEl.checked = false;
            toggleObfsOptions();
            toggleEngineOptions();
        }

        function syncNetworkMode() {
            const network = document.getElementById('link-network').value;
            const mode = document.getElementById('link-tunnel-mode');
            if (network === 'udp' && !udpTunnelModes.includes(mode.value)) mode.value = 'udp';
            if (network === 'tcp_udp' && Array.from(mode.options).some(o => o.value === 'tcp_udp')) mode.value = 'tcp_udp';
            toggleObfsOptions();
        }

        function syncModeTransport() {
            const mode = document.getElementById('link-tunnel-mode').value;
            const transport = document.getElementById('link-transport');
            const network = document.getElementById('link-network');
            if (modeTransportMap[mode] && Array.from(transport.options).some(o => o.value === modeTransportMap[mode])) transport.value = modeTransportMap[mode];
            if (udpTunnelModes.includes(mode) && Array.from(network.options).some(o => o.value === 'udp')) network.value = 'udp';
            if (mode === 'tcp_udp' && Array.from(network.options).some(o => o.value === 'tcp_udp')) network.value = 'tcp_udp';
            syncTransportTls();
            toggleEngineOptions();
        }

        function toggleObfsOptions() {
            const mode = document.getElementById('link-tunnel-mode').value;
            const tls = document.getElementById('link-tls-enabled').checked;
            const section = document.getElementById('obfs-advanced-section');
            const tlsGroup = document.getElementById('tls-sni-group');
            const obfsModes = tlsTunnelModes.concat(['wsmux']);
            
            if (obfsModes.includes(mode) || tls) {
                section.classList.remove('hidden');
            } else {
                section.classList.add('hidden');
            }
            
            if (tls) {
                tlsGroup.classList.remove('hidden');
            } else {
                tlsGroup.classList.add('hidden');
            }
        }

        async function toggleEasyMode() {
            const enabled = document.getElementById('link-easy-mode')?.checked;
            document.querySelectorAll('.advanced-link-field').forEach(el => el.classList.toggle('hidden', !!enabled));
            const customRow = document.getElementById('link-easy-custom-ports-row');
            customRow?.classList.toggle('hidden', !enabled);
            if (customRow) customRow.style.display = enabled ? 'flex' : 'none';
            document.getElementById('link-easy-custom-ports-hint')?.classList.toggle('hidden', !enabled);
            if (enabled) {
                const profileSelect = document.getElementById('link-profile');
                if (latestStatus.tunnel_profiles?.easy && profileSelect.value !== 'easy') {
                    selectProfile('easy');
                }
                document.getElementById('link-engine').value = 'builtin';
                syncTunnelOptions({ transport: 'websocket', network: 'tcp', mode: 'websocket' });
                document.getElementById('link-tls-enabled').checked = true;
                document.getElementById('link-pool-size').value = 16;
                document.getElementById('link-padding-min').value = 8;
                document.getElementById('link-padding-max').value = 48;
                document.getElementById('link-jitter-ms').value = 5;
                document.getElementById('link-data-plane-architecture').value = 'per_user';
                toggleDataPlaneOptions();
                await toggleEasyCustomPorts();
            } else {
                document.getElementById('link-port-fields')?.classList.remove('hidden');
            }
            toggleObfsOptions();
        }

        async function toggleEasyCustomPorts() {
            const easy = !!document.getElementById('link-easy-mode')?.checked;
            const manual = easy && !!document.getElementById('link-easy-custom-ports')?.checked;
            document.getElementById('link-port-fields')?.classList.toggle('hidden', easy && !manual);
            ['link-bridge-port', 'link-sync-port'].forEach(id => {
                const input = document.getElementById(id);
                if (input) input.readOnly = easy && !manual;
            });
            if (easy && !manual) await suggestNextLinkPorts(true);
            const status = document.getElementById('link-auto-port-status');
            if (status && manual) {
                status.innerText = tx(
                    'انتخاب دستی فعال است؛ آزاد بودن هر دو پورت هنگام ذخیره دوباره بررسی می‌شود.',
                    'Manual selection is enabled; both ports are checked again when saving.'
                );
            }
        }

        function toggleDataPlaneOptions() {
            const architecture = document.getElementById('link-data-plane-architecture')?.value || 'per_user';
            const usesBonding = ['adaptive_bonding', 'smart_hybrid'].includes(architecture);
            const usesMux = ['shared_mux', 'smart_hybrid'].includes(architecture);
            const bondingCompat = document.getElementById('link-bonding-enabled');
            if (bondingCompat) bondingCompat.checked = usesBonding;
            document.getElementById('link-bonding-lanes-group')?.classList.toggle('hidden', !usesBonding);
            document.getElementById('link-mux-carriers-group')?.classList.toggle('hidden', !usesMux);
        }

        function applySelectedProfile() {
            const profileId = document.getElementById('link-profile').value;
            const profile = latestStatus.tunnel_profiles?.[profileId];
            if (!profile) {
                syncTunnelOptions();
                renderProfilePicker(latestStatus.tunnel_profiles || {});
                return;
            }
            document.getElementById('link-engine').value = profile.engine || 'builtin';
            syncTunnelOptions({ transport: profile.transport || profile.tunnel_mode || 'tcp', network: profile.network || 'tcp', mode: profile.tunnel_mode || 'websocket' });
            document.getElementById('link-tls-enabled').checked = !!profile.tls_enabled;
            document.getElementById('link-pool-size').value = profile.pool_size || 4;
            document.getElementById('link-data-plane-architecture').value = profile.data_plane_architecture || (profile.bonding_enabled ? 'adaptive_bonding' : 'per_user');
            document.getElementById('link-mux-carriers').value = String(profile.mux_carriers || 4);
            document.getElementById('link-bonding-enabled').checked = !!profile.bonding_enabled;
            document.getElementById('link-bonding-max-lanes').value = String(profile.bonding_max_lanes || 4);
            document.getElementById('link-bridge-port').value = profile.bridge_port || document.getElementById('link-bridge-port').value || 7000;
            document.getElementById('link-sync-port').value = profile.sync_port || document.getElementById('link-sync-port').value || 7001;
            document.getElementById('link-obfs-host').value = profile.obfs_host || 'speedtest.net';
            document.getElementById('link-obfs-path').value = profile.obfs_path || '/tunnel';
            document.getElementById('link-tls-sni').value = profile.tls_sni || profile.obfs_host || 'speedtest.net';
            document.getElementById('link-padding-min').value = profile.padding_min || 0;
            document.getElementById('link-padding-max').value = profile.padding_max || 0;
            document.getElementById('link-jitter-ms').value = profile.jitter_ms || 0;
            document.getElementById('link-keepalive').value = profile.keepalive_interval || 25;
            document.getElementById('link-xray-protocol').value = profile.xray_protocol || 'vless';
            document.getElementById('link-xray-security').value = profile.xray_security || 'reality';
            document.getElementById('link-xray-flow').value = profile.xray_flow || 'xtls-rprx-vision';
            document.getElementById('link-xray-uuid').value = profile.xray_uuid || '';
            document.getElementById('link-xray-sni').value = profile.xray_sni || 'www.microsoft.com';
            document.getElementById('link-xray-shortid').value = profile.xray_shortid || '';
            document.getElementById('link-xray-public-key').value = profile.xray_public_key || '';
            document.getElementById('link-xray-private-key').value = profile.xray_private_key || '';
            document.getElementById('link-ssh-user').value = profile.ssh_user || 'root';
            document.getElementById('link-ssh-port').value = profile.ssh_port || 22;
            document.getElementById('link-ssh-bind-host').value = profile.ssh_bind_host || '0.0.0.0';
            document.getElementById('link-ssh-identity-file').value = profile.ssh_identity_file || '/opt/p00rija/ssh/id_ed25519';
            document.getElementById('link-ssh-target-host').value = profile.ssh_target_host || '127.0.0.1';
            document.getElementById('link-ssh-target-port').value = profile.ssh_target_port || 443;
            document.getElementById('link-ssh-jump-hosts').value = profile.ssh_jump_hosts || '';
            document.getElementById('link-stunnel-cert-path').value = profile.stunnel_cert_path || '/opt/p00rija/certs/stunnel.crt';
            document.getElementById('link-stunnel-key-path').value = profile.stunnel_key_path || '/opt/p00rija/certs/stunnel.key';
            document.getElementById('link-stunnel-verify').checked = !!profile.stunnel_verify;
            document.getElementById('link-wg-address').value = profile.wg_address || '10.77.0.1/24';
            document.getElementById('link-wg-client-address').value = profile.wg_client_address || '10.77.0.2/32';
            document.getElementById('link-wg-mtu').value = profile.wg_mtu || 1420;
            document.getElementById('link-wg-allowed-ips').value = profile.wg_allowed_ips || '0.0.0.0/0, ::/0';
            document.getElementById('link-wg-interface').value = profile.wg_interface || '';
            document.getElementById('link-aead-cipher').value = profile.aead_cipher || 'aes-128-gcm';
            document.getElementById('link-aead-key').value = profile.aead_key || '';
            document.getElementById('link-egress-mode').value = profile.egress_mode || (String(profile.tunnel_mode || '').includes('socks5') ? 'socks5' : 'port_forward');
            document.getElementById('link-socks5-username').value = profile.socks5_username || '';
            document.getElementById('link-socks5-password').value = profile.socks5_password || '';
            document.getElementById('link-raw-protocol').value = profile.raw_protocol || 253;
            document.getElementById('link-raw-mtu').value = profile.raw_mtu || 1200;
            document.getElementById('link-raw-packet-mark').value = profile.raw_packet_mark || '';
            toggleObfsOptions();
            toggleEngineOptions();
            toggleDataPlaneOptions();
            renderProfilePicker(latestStatus.tunnel_profiles || {});
        }

        function toggleEngineOptions() {
            const engine = document.getElementById('link-engine').value;
            const mode = document.getElementById('link-tunnel-mode').value;
            document.getElementById('xray-options').classList.toggle('hidden', engine !== 'xray');
            const engineSection = document.getElementById('engine-advanced-section');
            const showSsh = engine === 'ssh';
            const showStunnel = engine === 'stunnel';
            const showWireGuard = engine === 'wireguard';
            const showAead = engine === 'aead' || ['client_port_forward', 'client_socks5'].includes(mode);
            const showRaw = engine === 'rawsock';
            document.getElementById('ssh-options').classList.toggle('hidden', !showSsh);
            document.getElementById('stunnel-options').classList.toggle('hidden', !showStunnel);
            document.getElementById('wireguard-options').classList.toggle('hidden', !showWireGuard);
            document.getElementById('aead-options').classList.toggle('hidden', !showAead);
            document.getElementById('rawsock-options').classList.toggle('hidden', !showRaw);
            engineSection.classList.toggle('hidden', !(showSsh || showStunnel || showWireGuard || showAead || showRaw));
        }

        async function fetchRuntime() {
            if (!token) return;
            try {
                const [processesRes, resourcesRes] = await Promise.all([
                    fetch('/api/runtime/processes', { headers: { 'Authorization': `Bearer ${token}` } }),
                    fetch('/api/runtime/resources', { headers: { 'Authorization': `Bearer ${token}` } })
                ]);
                if (processesRes.ok) renderProcesses((await processesRes.json()).processes || []);
                if (resourcesRes.ok) renderResources(await resourcesRes.json());
                if (sessionsPanelOpen) await fetchRuntimeSessions();
                if (threadsPanelOpen) await fetchRuntimeThreads();
            } catch (err) {
                console.error('Runtime fetch failed', err);
            }
        }

        async function fetchRuntimeSessions() {
            if (!token || !sessionsPanelOpen) return;
            const hint = document.getElementById('sessions-toggle-hint');
            if (hint) hint.innerText = tx('در حال بروزرسانی سشن‌ها...', 'Refreshing sessions...');
            try {
                const res = await fetch('/api/runtime/sessions', { headers: { 'Authorization': `Bearer ${token}` } });
                const data = await res.json();
                if (res.ok) {
                    sessionsLastRefresh = Date.now();
                    renderSessions(data.sessions || []);
                }
            } catch (err) {
                console.error('Session refresh failed', err);
                if (hint) hint.innerText = tx('خطا در بروزرسانی سشن‌ها', 'Session refresh failed');
            }
        }

        function toggleSessionsPanel(forceOpen) {
            const panel = document.getElementById('sessions-panel');
            const button = document.getElementById('sessions-toggle');
            if (!panel) return;
            sessionsPanelOpen = typeof forceOpen === 'boolean' ? forceOpen : panel.classList.contains('hidden');
            panel.classList.toggle('hidden', !sessionsPanelOpen);
            button?.classList.toggle('active', sessionsPanelOpen);
            const icon = button?.querySelector('i[data-lucide]');
            if (icon) icon.setAttribute('data-lucide', sessionsPanelOpen ? 'chevron-up' : 'chevron-down');
            const hint = document.getElementById('sessions-toggle-hint');
            if (!sessionsPanelOpen && hint) hint.innerText = tx('برای مشاهده و بروزرسانی، منو را باز کنید', 'Open to view and refresh sessions');
            createInlineIcons(button || document);
            if (sessionsPanelOpen) fetchRuntimeSessions();
        }

        async function fetchRuntimeThreads() {
            if (!token || !threadsPanelOpen) return;
            const hint = document.getElementById('threads-toggle-hint');
            if (hint) hint.innerText = tx('در حال بروزرسانی تردها...', 'Refreshing threads...');
            try {
                const res = await fetch('/api/runtime/threads', { headers: { 'Authorization': `Bearer ${token}` } });
                const data = await res.json();
                if (res.ok) {
                    threadsLastRefresh = Date.now();
                    renderThreads(data.threads || []);
                }
            } catch (err) {
                console.error('Thread refresh failed', err);
                if (hint) hint.innerText = tx('خطا در بروزرسانی تردها', 'Thread refresh failed');
            }
        }

        function toggleThreadsPanel(forceOpen) {
            const panel = document.getElementById('threads-panel');
            const button = document.getElementById('threads-toggle');
            if (!panel) return;
            threadsPanelOpen = typeof forceOpen === 'boolean' ? forceOpen : panel.classList.contains('hidden');
            panel.classList.toggle('hidden', !threadsPanelOpen);
            button?.classList.toggle('active', threadsPanelOpen);
            const icon = button?.querySelector('i[data-lucide]');
            if (icon) icon.setAttribute('data-lucide', threadsPanelOpen ? 'chevron-up' : 'chevron-down');
            const hint = document.getElementById('threads-toggle-hint');
            if (!threadsPanelOpen && hint) hint.innerText = tx('برای مشاهده و بروزرسانی تردها، منو را باز کنید', 'Open to view and refresh threads');
            createInlineIcons(button || document);
            if (threadsPanelOpen) fetchRuntimeThreads();
        }

        function intelLevelClass(level) {
            if (level === 'good') return 'rating-chip-good';
            if (level === 'poor') return 'rating-chip-poor';
            return 'rating-chip-normal';
        }

        function renderOperationIntelligence(intel) {
            const grid = document.getElementById('ops-intelligence-grid');
            const recBox = document.getElementById('ops-recommendations');
            const radarBox = document.getElementById('ops-transport-radar');
            updateAutoGuardianButton();
            if (!intel) {
                if (grid) grid.innerHTML = `<span class="tag-pill">${tx('داده‌ای برای نمایش نیست', 'No data to show')}</span>`;
                return;
            }
            const version = intel.version_sync || {};
            const sla = intel.sla || {};
            const risk = intel.resource_risk || {};
            const drift = Number(version.drift || 0);
            const unknown = Number(version.unknown || 0);
            const versionClass = drift ? 'rating-chip-poor' : (unknown ? 'rating-chip-normal' : 'rating-chip-good');
            if (grid) {
                grid.innerHTML = `
                    <div class="ops-intel-card">
                        <span>${tx('هماهنگی نسخه نودها', 'Node version sync')}</span>
                        <strong class="${versionClass}">${esc(version.ok || 0)}/${esc(version.online || 0)}</strong>
                        <small>${tx('هدف', 'Target')}: v${esc(intel.target_version || '1.9.95')} | ${tx('نیازمند آپدیت', 'Needs update')}: ${esc(drift + unknown)}</small>
                    </div>
                    <div class="ops-intel-card">
                        <span>${tx('امتیاز SLA تانل‌ها', 'Tunnel SLA score')}</span>
                        <strong class="${intelLevelClass(sla.level)}">${esc(sla.score ?? 100)}/100</strong>
                        <small>${tx('پایین‌ترین موارد برای بررسی اولویت دارند.', 'Lowest scoring tunnels are prioritized for review.')}</small>
                    </div>
                    <div class="ops-intel-card">
                        <span>${tx('ریسک منابع', 'Resource risk')}</span>
                        <strong class="${intelLevelClass(risk.level)}">${esc(risk.score || 0)}/100</strong>
                        <small>${tx('تردها', 'Threads')}: ${esc(risk.threads || 0)} | RSS ${esc(risk.rss_mb || 0)} MB</small>
                    </div>
                    <div class="ops-intel-card">
                        <span>${tx('نگهبان خودکار', 'Auto guardian')}</span>
                        <strong class="${autoGuardianTimer ? 'rating-chip-good' : 'rating-chip-normal'}">${autoGuardianTimer ? tx('روشن', 'On') : tx('خاموش', 'Off')}</strong>
                        <small>${tx('هر ۶۰ ثانیه مدیریت هوشمند تردها را اجرا می‌کند.', 'Runs smart thread management every 60 seconds.')}</small>
                    </div>
                `;
            }
            if (recBox) {
                recBox.innerHTML = (intel.recommendations || []).map(item => {
                    const label = currentLang === 'en' ? (item.label || item.label_fa || item.id) : (item.label_fa || item.label || item.id);
                    const action = item.action || 'none';
                    const canRun = ['pressure', 'thread_guard', 'node_update'].includes(action);
                    return `
                        <span class="tag-pill ${intelLevelClass(item.severity)}" title="${esc(item.detail || '')}">
                            <i data-lucide="${item.severity === 'poor' ? 'alert-triangle' : (item.severity === 'good' ? 'check-circle' : 'sparkles')}"></i>
                            ${esc(label)}
                            ${canRun ? `<button class="mini-icon-btn" onclick="runOpsRecommendation('${esc(action)}')" title="${tx('اجرای پیشنهاد', 'Run recommendation')}"><i data-lucide="play"></i></button>` : ''}
                        </span>
                    `;
                }).join('') || `<span class="tag-pill rating-chip-good">${tx('همه چیز هماهنگ است', 'Everything is aligned')}</span>`;
            }
            if (radarBox) {
                radarBox.innerHTML = (intel.transport_radar || []).map(item => `
                    <span class="tag-pill ${item.level === 'candidate' ? 'rating-chip-good' : 'rating-chip-normal'}" title="${esc(item.why || '')}">
                        <i data-lucide="${item.level === 'candidate' ? 'rocket' : 'radar'}"></i>
                        ${esc(item.name)}
                        <small>${item.level === 'candidate' ? tx('کاندید اجرا', 'Implementation candidate') : tx('تحقیقاتی', 'Research')}</small>
                    </span>
                `).join('');
            }
            createInlineIcons(document.getElementById('tab-monitor'));
        }

        function updateAutoGuardianButton() {
            const btn = document.getElementById('auto-guardian-toggle');
            if (!btn) return;
            const label = autoGuardianTimer ? tx('نگهبان خودکار: روشن', 'Auto guardian: On') : tx('نگهبان خودکار: خاموش', 'Auto guardian: Off');
            btn.innerHTML = `<i data-lucide="timer-reset"></i><span>${label}</span>`;
            btn.classList.toggle('rating-chip-good', Boolean(autoGuardianTimer));
            createInlineIcons(btn);
        }

        function toggleAutoGuardian() {
            if (autoGuardianTimer) {
                clearInterval(autoGuardianTimer);
                autoGuardianTimer = null;
                localStorage.setItem('p00rija_auto_guardian', '0');
            } else {
                localStorage.setItem('p00rija_auto_guardian', '1');
                autoGuardianTimer = setInterval(runAutoGuardianCycle, 60000);
                runAutoGuardianCycle();
            }
            updateAutoGuardianButton();
        }

        async function runAutoGuardianCycle() {
            try {
                const response = await fetch('/api/runtime/resources', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const resources = await response.json().catch(() => ({}));
                if (!response.ok) return;
                const risk = Number(resources.intelligence?.resource_risk?.score || 0);
                if (risk >= 65) {
                    await optimizeResources('pressure', true);
                    return;
                }
                const candidates = (resources.links || []).filter(link =>
                    ['reap_idle_reserve', 'reduce_thread_pressure'].includes(link.action)
                );
                for (const link of candidates.slice(0, 4)) {
                    await optimizeLinkGuardian(link.id, true);
                }
            } catch (error) {
                console.error('auto guardian cycle failed:', error);
            }
        }

        function runOpsRecommendation(action) {
            if (action === 'node_update') queueNodeUpdate('');
            else if (action === 'pressure' || action === 'thread_guard') optimizeResources(action);
        }

        function renderResources(resources) {
            const threads = document.getElementById('resource-threads');
            const sessions = document.getElementById('resource-sessions');
            const rss = document.getElementById('resource-rss');
            if (threads) threads.innerText = resources.threads ?? 0;
            if (sessions) sessions.innerText = resources.active_tunnel_sessions ?? 0;
            const sessionCount = document.getElementById('sessions-dropdown-count');
            if (sessionCount) sessionCount.innerText = resources.active_tunnel_sessions ?? 0;
            const threadCount = document.getElementById('threads-dropdown-count');
            if (threadCount && !threadsPanelOpen) threadCount.innerText = resources.threads ?? 0;
            if (rss) rss.innerText = `${((resources.rss_kb || 0) / 1024).toFixed(1)} MB`;
            renderOperationIntelligence(resources.intelligence || null);
            renderTunnelGuardians(resources.links || []);
            const grid = document.getElementById('node-resource-grid');
            if (grid) {
                const trafficUnit = localStorage.getItem('trafficUnit') || 'MB';
                const divisor = trafficUnit === 'MB' ? (1024 * 1024) : 1024;
                grid.innerHTML = (resources.nodes || []).map(node => {
                    const safeId = safeDomId(node.id || node.name || 'node');
                    const result = node.last_command_result?.result;
                    const resultText = result ? `${tx('آخرین پاک‌سازی', 'Last cleanup')}: ${esc(node.last_command_result.action)} | RSS ${((result.rss_kb || 0) / 1024).toFixed(1)} MB` : tx('پاک‌سازی ثبت نشده', 'No cleanup yet');
                    return `
                        <div class="node-resource-card" data-resource-node-id="${esc(node.id || node.name || '')}">
                            <h4><span>${esc(node.name)}</span><span class="status-pill"><span class="status-dot ${node.status === 'online' ? '' : 'offline'}"></span>${node.status === 'online' ? t('online') : t('offline')}</span></h4>
                            <div class="tag-row">
                                <span class="tag-pill">CPU ${esc(node.cpu)}%</span>
                                <span class="tag-pill">RAM ${esc(node.ram)}%</span>
                                <span class="tag-pill">${tx('تردها', 'Threads')} ${esc(node.threads)}</span>
                                <span class="tag-pill">${tx('فعال', 'Active')} ${esc(node.connections)}</span>
                            </div>
                            <div class="tag-row">
                                <span class="tag-pill tag-color-5">${tx('دانلود', 'Download')} ${(Number(node.rx_speed || 0) / divisor).toFixed(2)} ${trafficUnit}/s</span>
                                <span class="tag-pill tag-color-1">${tx('آپلود', 'Upload')} ${(Number(node.tx_speed || 0) / divisor).toFixed(2)} ${trafficUnit}/s</span>
                            </div>
                            <div class="node-resource-charts">
                                <div class="node-resource-chart"><canvas id="node-load-chart-${safeId}"></canvas></div>
                                <div class="node-resource-chart"><canvas id="node-traffic-chart-${safeId}"></canvas></div>
                            </div>
                            <small style="display:block; margin-top:10px; color: var(--text-secondary);">${resultText}</small>
                        </div>
                    `;
                }).join('') || `<span class="tag-pill">${tx('نودی برای نمایش نیست', 'No nodes to show')}</span>`;
                (resources.nodes || []).forEach(node => drawNodeResourceCharts(node, divisor, trafficUnit));
            }
        }

        function guardianActionMeta(action) {
            const map = {
                ok: [tx('همه چیز عادی است', 'Everything looks normal'), 'rating-chip-good', 'check-circle'],
                paused: [tx('تانل متوقف است', 'Tunnel is paused'), 'rating-chip-normal', 'pause-circle'],
                start_or_check_nodes: [tx('نودها یا engine را بررسی کنید', 'Check nodes or engine'), 'rating-chip-poor', 'alert-triangle'],
                reap_idle_reserve: [tx('پاک‌سازی رزروهای idle', 'Clean idle reserves'), 'rating-chip-normal', 'scissors'],
                reduce_thread_pressure: [tx('کاهش فشار ترد', 'Reduce thread pressure'), 'rating-chip-poor', 'gauge'],
                engine_process_watch: [tx('پایش پروسس engine', 'Watch engine process'), 'rating-chip-normal', 'cpu']
            };
            return map[action] || map.ok;
        }

        function renderTunnelGuardians(links) {
            const grid = document.getElementById('tunnel-guardian-grid');
            if (!grid) return;
            grid.innerHTML = links.map(link => {
                const [label, cls, icon] = guardianActionMeta(link.action);
                const runningClass = link.running && !link.paused ? 'rating-chip-good' : (link.paused ? 'rating-chip-normal' : 'rating-chip-poor');
                return `
                    <div class="tunnel-guardian-card" data-link-id="${esc(link.id)}">
                        <h4>
                            <span>${esc(link.name || link.id)}</span>
                            <span class="tag-pill tunnel-guardian-status ${runningClass}"><span class="status-dot ${link.running && !link.paused ? '' : (link.paused ? 'warning' : 'offline')}"></span>${link.running && !link.paused ? t('online') : (link.paused ? tx('متوقف', 'Paused') : t('offline'))}</span>
                        </h4>
                        <div class="tag-row">
                            <span class="tag-pill">${esc(link.engine)} / ${esc(link.mode)}</span>
                            <span class="tag-pill">${tx('سشن‌ها', 'Sessions')} ${esc(link.sessions)}</span>
                            <span class="tag-pill">${tx('آماده', 'Ready')} ${esc(link.ready_workers)}</span>
                            <span class="tag-pill">${tx('هدف', 'Target')} ${esc(link.desired_workers)}/${esc(link.max_workers)}</span>
                            <span class="tag-pill">${tx('فشار', 'Pressure')} ${esc(link.thread_pressure)}</span>
                        </div>
                        <small style="color: var(--text-secondary); line-height: 1.7;">${esc(link.client_node)} -> ${esc(link.server_node)}</small>
                        <div class="guardian-action-row">
                            <span class="tag-pill ${cls}"><i data-lucide="${icon}"></i>${tx('پیشنهاد نگهبان', 'Guardian suggestion')}: ${label}</span>
                            <button class="btn w-auto p-10 btn-smart" onclick="optimizeLinkGuardian('${esc(link.id)}')"><i data-lucide="shield-check"></i><span>${tx('اجرای نگهبان لینک', 'Run link guardian')}</span></button>
                        </div>
                        <small class="guardian-result" data-guardian-result="${esc(link.id)}">${esc(linkGuardianMessages[link.id] || '')}</small>
                    </div>
                `;
            }).join('') || `<span class="tag-pill">${tx('تانلی برای نمایش نیست', 'No tunnels to show')}</span>`;
            createInlineIcons(grid);
        }

        async function fetchSystemAudit() {
            const box = document.getElementById('system-audit-result');
            if (!box) return;
            box.innerHTML = `<span class="tag-pill">${tx('در حال اجرای ممیزی...', 'Running audit...')}</span>`;
            try {
                const res = await fetch('/api/system/audit', {
                    headers: { 'Authorization': `Bearer ${token}` },
                    cache: 'no-store'
                });
                const data = await res.json();
                if (!res.ok) {
                    box.innerHTML = `<span class="tag-pill rating-chip-poor">${esc(data.error || tx('ممیزی ناموفق بود', 'Audit failed'))}</span>`;
                    return;
                }
                renderSystemAudit(data);
            } catch (err) {
                box.innerHTML = `<span class="tag-pill rating-chip-poor">${tx('خطا در دریافت ممیزی', 'Could not fetch audit')}</span>`;
            }
        }

        function renderSystemAudit(data) {
            const box = document.getElementById('system-audit-result');
            if (!box) return;
            const score = Number(data.score || 0);
            const scoreClass = score >= 80 ? 'rating-chip-good' : (score >= 55 ? 'rating-chip-normal' : 'rating-chip-poor');
            const missingFiles = (data.package_files || []).filter(item => !item.present).map(item => item.path);
            const missingModules = (data.modules || []).filter(item => !item.present).map(item => item.path);
            const capabilities = (data.capabilities || []).map(item => `
                <div class="audit-list-item">
                    <span>${esc(item.label || item.id)}</span>
                    <span class="tag-pill ${item.ready ? 'rating-chip-good' : 'rating-chip-poor'}">${item.ready ? tx('آماده', 'Ready') : tx('نیازمند بررسی', 'Needs check')}</span>
                </div>
            `).join('');
            const recommendations = (data.recommendations || []).map(item => `<li>${esc(item)}</li>`).join('');
            const nextFeatures = (data.next_feature_candidates || []).map(item => `<span class="tag-pill tag-color-5">${esc(item)}</span>`).join('');
            const responsibilities = (data.module_responsibilities || []).map(item => `
                <div class="audit-list-item">
                    <span><strong>${esc(item.module || '')}</strong><br><small>${esc(item.responsibility || '')}</small></span>
                    <span class="tag-pill ${item.status === 'extracted' ? 'rating-chip-good' : 'rating-chip-normal'}">${item.status === 'extracted' ? tx('جدا شده', 'Extracted') : tx('در صف جداسازی', 'Pending')}</span>
                </div>
            `).join('');
            box.innerHTML = `
                <div class="audit-summary-grid">
                    <div class="audit-summary-item"><span>${tx('امتیاز ساختار', 'Structure score')}</span><strong class="tag-pill ${scoreClass}">${score}/100</strong></div>
                    <div class="audit-summary-item"><span>${tx('خط فایل اصلی', 'Main file lines')}</span><strong>${esc(data.main_file?.lines || 0)}</strong></div>
                    <div class="audit-summary-item"><span>${tx('ماژول‌های هسته', 'Core modules')}</span><strong>${(data.modules || []).filter(x => x.present).length}/${(data.modules || []).length}</strong></div>
                    <div class="audit-summary-item"><span>${tx('هسته‌های نصب‌شده', 'Installed engines')}</span><strong>${esc(data.engines?.installed || 0)}/${esc(data.engines?.total || 0)}</strong></div>
                    <div class="audit-summary-item"><span>${tx('نود/تانل/پروفایل', 'Nodes/links/profiles')}</span><strong>${esc(data.stats?.nodes || 0)} / ${esc(data.stats?.links || 0)} / ${esc(data.stats?.profiles || 0)}</strong></div>
                    <div class="audit-summary-item"><span>${tx('مسیرهای API', 'API routes')}</span><strong>${esc(data.api_surface?.route_count || 0)}</strong></div>
                </div>
                <div class="audit-list">${capabilities}</div>
                <div class="mt-20">
                    <h4>${tx('نقشه معماری ماژولار', 'Modular architecture map')}</h4>
                    <div class="audit-list">${responsibilities}</div>
                </div>
                <div class="tag-row mt-20">
                    ${missingFiles.length ? `<span class="tag-pill rating-chip-poor">${tx('فایل‌های ناقص', 'Missing files')}: ${esc(missingFiles.join(', '))}</span>` : `<span class="tag-pill rating-chip-good">${tx('فایل‌های پکیج کامل است', 'Package files are complete')}</span>`}
                    ${missingModules.length ? `<span class="tag-pill rating-chip-poor">${tx('ماژول ناقص', 'Missing module')}: ${esc(missingModules.join(', '))}</span>` : `<span class="tag-pill rating-chip-good">${tx('ماژول‌های پایه حاضر هستند', 'Base modules are present')}</span>`}
                </div>
                <div class="mt-20">
                    <h4>${tx('پیشنهادهای بعدی', 'Next recommendations')}</h4>
                    <ul style="color: var(--text-secondary); line-height: 1.8; margin-top: 8px; padding-inline-start: 22px;">${recommendations}</ul>
                </div>
                <div class="tag-row mt-20">${nextFeatures}</div>
            `;
        }

        function drawNodeResourceCharts(node, divisor, trafficUnit) {
            const rawId = String(node.id || node.name || 'node');
            const safeId = safeDomId(rawId);
            const loadCanvas = document.getElementById(`node-load-chart-${safeId}`);
            const trafficCanvas = document.getElementById(`node-traffic-chart-${safeId}`);
            nodeResourceCharts[rawId] = nodeResourceCharts[rawId] || {
                load: { canvas: loadCanvas, series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_ACTIVE, COLOR_UPLOAD] },
                traffic: { canvas: trafficCanvas, series: [Array(20).fill(0), Array(20).fill(0)], colors: [COLOR_DOWNLOAD, COLOR_UPLOAD] }
            };
            const item = nodeResourceCharts[rawId];
            item.load.canvas = loadCanvas;
            item.traffic.canvas = trafficCanvas;
            item.load.series[0].shift();
            item.load.series[0].push(Number(node.cpu || 0));
            item.load.series[1].shift();
            item.load.series[1].push(Number(node.ram || 0));
            item.traffic.series[0].shift();
            item.traffic.series[0].push(Number(node.rx_speed || 0) / divisor);
            item.traffic.series[1].shift();
            item.traffic.series[1].push(Number(node.tx_speed || 0) / divisor);
            if (loadCanvas) drawChart(item.load, '%', ['CPU', 'RAM']);
            if (trafficCanvas) drawChart(item.traffic, `${trafficUnit}/s`, [tx('دانلود', 'Download'), tx('آپلود', 'Upload')]);
        }

        function renderSessions(sessions) {
            const tbody = document.querySelector('#table-sessions tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            const countEl = document.getElementById('sessions-dropdown-count');
            if (countEl) countEl.innerText = sessions.length;
            const hint = document.getElementById('sessions-toggle-hint');
            if (hint) {
                const timeText = sessionsLastRefresh ? new Date(sessionsLastRefresh).toLocaleTimeString() : new Date().toLocaleTimeString();
                hint.innerText = currentLang === 'en' ? `Last refresh: ${timeText}` : `آخرین بروزرسانی: ${timeText}`;
            }
            if (!sessions.length) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td colspan="6"><span class="tag-pill">${tx('سشن فعالی وجود ندارد', 'No active sessions')}</span></td>`;
                tbody.appendChild(tr);
                return;
            }
            sessions.forEach(s => {
                const tr = document.createElement('tr');
                const remote = (s.source || 'panel') !== 'panel';
                const label = remote ? tx('ارسال دستور بستن', 'Send close command') : t('close');
                tr.innerHTML = `<td><code>${esc(s.id)}</code><br><small>${esc(s.node_name || 'Panel')}</small></td><td>${esc(s.link_id)}</td><td>${esc(s.target_port)}</td><td>${esc(s.age_seconds)}s</td><td>${esc(s.idle_seconds)}s</td><td><button class="btn w-auto p-10 btn-smart" onclick="closeSession('${esc(s.id)}')">${label}</button></td>`;
                tbody.appendChild(tr);
            });
        }

        function renderThreads(threads) {
            const tbody = document.querySelector('#table-threads tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            const countEl = document.getElementById('threads-dropdown-count');
            if (countEl) countEl.innerText = threads.length;
            const hint = document.getElementById('threads-toggle-hint');
            if (hint) {
                const timeText = threadsLastRefresh ? new Date(threadsLastRefresh).toLocaleTimeString() : new Date().toLocaleTimeString();
                hint.innerText = currentLang === 'en' ? `Last refresh: ${timeText}` : `آخرین بروزرسانی: ${timeText}`;
            }
            if (!threads.length) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td colspan="7"><span class="tag-pill">${tx('ترد فعالی وجود ندارد', 'No active threads')}</span></td>`;
                tbody.appendChild(tr);
                return;
            }
            threads.forEach(th => {
                const tr = document.createElement('tr');
                const isGroup = th.kind === 'process_group';
                const threadLabel = isGroup ? `${esc(th.threads || 0)} ${tx('تردها', 'Threads')}` : esc(th.tid || '-');
                const sourceLabel = (th.source || 'panel') === 'panel' ? 'Panel' : esc(th.node_name || th.node_id || 'Node');
                tr.title = isGroup
                    ? tx('این ردیف خلاصه تردهای گزارش‌شده از پروسس نود است.', 'This row summarizes threads reported by a node process.')
                    : '';
                tr.innerHTML = `
                    <td>${isGroup ? `<span class="tag-pill">${tx('گروه ترد', 'Thread group')}</span><br><small>${threadLabel}</small>` : `<code>${threadLabel}</code>`}</td>
                    <td><code>${esc(th.pid || '-')}</code></td>
                    <td>${esc(th.process || th.name || '-')}<br><small>${esc(th.name || '')}</small></td>
                    <td>${sourceLabel}</td>
                    <td><span class="tag-pill">${esc(th.state || '-')}</span></td>
                    <td>${(Number(th.rss_kb || 0) / 1024).toFixed(1)} MB</td>
                    <td>${esc(th.cpu_seconds || 0)}s</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function renderProcesses(processes) {
            const tbody = document.querySelector('#table-processes tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            processes.forEach(p => {
                const tr = document.createElement('tr');
                tr.title = p.cmd || '';
                const isPanelProcess = (p.source || 'panel') === 'panel';
                tr.innerHTML = `<td><code>${esc(p.pid)}</code><br><small>${esc(p.node_name || 'Panel')}</small></td><td>${esc(p.name)}</td><td>${(Number(p.rss_kb || 0) / 1024).toFixed(1)} MB</td><td>${esc(p.threads)}</td><td>${esc(p.cpu_seconds)}s</td><td>${isPanelProcess ? `<button class="btn w-auto p-10" style="background: var(--danger);" onclick="terminateProcess(${Number(p.pid)})">SIGTERM</button>` : `<span class="tag-pill">${tx('نود', 'Node')}</span>`}</td>`;
                tbody.appendChild(tr);
            });
        }

        async function closeSession(id) {
            if (!confirm(tx('این سشن تانل بسته شود؟', 'Close this tunnel session?'))) return;
            const res = await fetch(`/api/runtime/sessions?id=${encodeURIComponent(id)}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                const box = document.getElementById('resource-result');
                if (box) box.innerText = data.queued ? tx('دستور بسته شدن برای نود ارسال شد.', 'Close command was queued for the node.') : tx('سشن بسته شد.', 'Session closed.');
                fetchRuntime();
                if (sessionsPanelOpen) fetchRuntimeSessions();
            }
        }

        async function terminateProcess(pid) {
            if (!confirm(`Send SIGTERM to process ${pid}?`)) return;
            const res = await fetch(`/api/runtime/processes?pid=${encodeURIComponent(pid)}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) fetchRuntime();
        }

        async function optimizeResources(action, quiet = false) {
            const scope = document.getElementById('resource-scope')?.value || 'all';
            const res = await fetch('/api/runtime/optimize', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, scope })
            });
            const data = await res.json();
            const box = document.getElementById('resource-result');
            if (box && !quiet) {
                box.innerText = res.ok
                    ? `${tx('بهینه‌سازی انجام شد', 'Optimization completed')}: ${tx('سشن‌های بسته‌شده', 'closed sessions')} ${data.closed_idle_sessions || 0}, GC ${data.gc_collected || 0}, ${tx('فرمان نودها', 'node commands')} ${data.queued_nodes || 0}, ${tx('فشار', 'Pressure')} ${data.pressure_level || 'normal'}, ${tx('RAM آزادشده', 'RAM reclaimed')} ${((data.rss_reclaimed_kb || 0) / 1024).toFixed(1)} MB, RSS ${((data.rss_kb || 0) / 1024).toFixed(1)} MB`
                    : `${tx('خطا', 'Error')}: ${data.error || tx('ناشناخته', 'Unknown')}`;
            }
            if (!quiet) {
                fetchRuntime();
                if (sessionsPanelOpen) fetchRuntimeSessions();
            }
        }

        async function optimizeLinkGuardian(linkId, quiet = false) {
            const resultEl = document.querySelector(`[data-guardian-result="${cssEscape(linkId)}"]`);
            linkGuardianMessages[linkId] = tx('در حال اجرای نگهبان لینک...', 'Running link guardian...');
            if (resultEl && !quiet) resultEl.innerText = linkGuardianMessages[linkId];
            const res = await fetch('/api/runtime/optimize', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'thread_guard', scope: 'all', link_id: linkId })
            });
            const data = await res.json().catch(() => ({}));
            const box = document.getElementById('resource-result');
            const reapedWorkers = data.link_idle_workers_reaped ?? data.result?.link_idle_workers_reaped ?? 0;
            const message = res.ok
                ? `${tx('نگهبان لینک اجرا شد', 'Link guardian queued')}: ${tx('فرمان نودها', 'node commands')} ${data.queued_nodes || 0}, ${tx('workerهای پاک‌شده', 'reaped workers')} ${reapedWorkers}`
                : `${tx('خطا', 'Error')}: ${data.error || tx('ناشناخته', 'Unknown')}`;
            linkGuardianMessages[linkId] = message;
            if (box && !quiet) box.innerText = message;
            if (resultEl && !quiet) resultEl.innerText = message;
            if (!quiet) fetchRuntime();
        }

        async function testLink(lid) {
            const res = await fetch(`/api/links/test?id=${encodeURIComponent(lid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) {
                const data = await res.json();
                alert(`${tx('تست اتصال', 'Connection test')}: ${data.success ? tx('فعال', 'LIVE') : tx('آماده نیست', 'NOT READY')}\\n${tx('نود داخلی', 'Internal')}: ${data.internal_live}\\n${tx('نود خارجی', 'External')}: ${data.external_live}\\n${tx('هسته', 'Engine')}: ${data.engine}`);
            }
        }

        async function showEngineConfig(lid) {
            const res = await fetch(`/api/links/engine-config?id=${encodeURIComponent(lid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) {
                const data = await res.json();
                document.getElementById('engine-config-content').value = JSON.stringify(data, null, 2);
                openModal('modal-show-config');
            }
        }

        document.getElementById('form-sync-xui')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.innerText = tx('در حال اتصال و همگام‌سازی...', 'Syncing...');

            const payload = {
                link_id: document.getElementById('sync-xui-link-id').value,
                url: document.getElementById('sync-xui-url').value,
                username: document.getElementById('sync-xui-username').value,
                password: document.getElementById('sync-xui-password').value
            };

            try {
                const res = await fetch('/api/sync/xui', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                const data = await res.json();
                if (res.ok) {
                    alert(`${tx('همگام‌سازی موفق!', 'Sync Successful!')}\n${data.added} ${tx('پورت جدید از مجموع', 'new ports added from total')} ${data.total} ${tx('پورت فعال پنل شما اضافه شد.', 'active ports in your panel.')}`);
                    closeModal('modal-sync-xui');
                    fetchStatus();
                } else {
                    alert(`${tx('خطا', 'Error')}: ${data.error || tx('شکست در ارتباط', 'Connection failed')}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            } finally {
                btn.disabled = false;
                btn.innerText = tx('شروع همگام‌سازی پورت‌ها', 'Start Syncing');
            }
        });

        async function testNodeConnection(nid) {
            const loading = document.getElementById('node-test-loading');
            const result = document.getElementById('node-test-result');
            if (loading) loading.style.display = 'flex';
            if (result) result.textContent = '';
            openModal('modal-node-test');
            try {
                const res = await fetch(`/api/nodes/test?id=${encodeURIComponent(nid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
                const data = await res.json();
                if (loading) loading.style.display = 'none';
                if (res.ok) {
                    if (result) result.textContent = data.result || 'No output';
                } else {
                    if (result) result.textContent = data.error || tx('خطا در تست ارتباط', 'Test failed');
                }
            } catch (err) { 
                if (loading) loading.style.display = 'none';
                if (result) result.textContent = tx('خطا در ارتباط', 'Connection error');
            }
        }

        async function queueNodeUpdate(nid = '') {
            const scope = (prompt(
                tx('نوع آپدیت را وارد کنید: app، engines یا app_engines', 'Enter update scope: app, engines, or app_engines'),
                'app_engines'
            ) || '').trim();
            if (!['app', 'engines', 'app_engines'].includes(scope)) {
                alert(tx('نوع آپدیت نامعتبر است.', 'Invalid update scope.'));
                return;
            }
            const restart = confirm(tx('بعد از آپدیت، نود ریستارت شود؟', 'Restart node after the update?'));
            const target = nid ? tx('این نود', 'this node') : tx('همه نودهای آنلاین', 'all online nodes');
            if (!confirm(`${tx('آپدیت برای', 'Queue update for')} ${target}?`)) return;
            try {
                const res = await fetch('/api/nodes/update', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ node_id: nid || undefined, scope, restart })
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    alert(data.error || tx('صف‌کردن آپدیت ناموفق بود.', 'Failed to queue update.'));
                    return;
                }
                const first = (data.queued || [])[0] || {};
                const sizeKb = Math.max(1, Math.ceil((first.package_size || 0) / 1024));
                alert(`${tx('آپدیت افزایشی صف شد', 'Delta update queued')}: ${data.queued_count || 0}\n${tx('فایل تغییرکرده', 'Changed files')}: ${first.changed_files ?? '-'}\n${tx('حجم انتقال', 'Transfer size')}: ${sizeKb} KB`);
                fetchStatus();
            } catch (err) {
                alert(`${tx('صف‌کردن آپدیت ناموفق بود', 'Failed to queue update')}: ${err.message || err}`);
            }
        }

        async function checkNodeVersions(nid = '') {
            try {
                const suffix = nid ? `?id=${encodeURIComponent(nid)}` : '';
                const res = await fetch(`/api/nodes/version-check${suffix}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) throw new Error(data.error || 'Version check failed');
                nodeVersionChecks = { ...nodeVersionChecks, ...(data.nodes || {}) };
                renderNodes(latestStatus?.nodes || {});
                const summary = data.summary || {};
                alert(`${tx('بررسی نسخه نودها', 'Node version check')}: ${summary.current || 0}/${summary.total || 0} ${tx('کاملاً هماهنگ', 'fully current')}\n`
                    + `${tx('قدیمی/ناهماهنگ', 'Outdated/mismatched')}: ${(summary.outdated || 0) + (summary.incompatible || 0)}`);
            } catch (error) {
                alert(`${tx('بررسی نسخه ناموفق بود', 'Version check failed')}: ${error.message || error}`);
            }
        }

        function showGeneratedNodeCredentials(created) {
            const list = Array.isArray(created) ? created : [created];
            const first = list[0] || {};
            const tokenEl = document.getElementById('generated-token-input');
            const keyEl = document.getElementById('generated-private-key-input');
            const setupEl = document.getElementById('generated-node-setup-input');
            if (tokenEl) tokenEl.value = first.token || '';
            if (keyEl) keyEl.value = first.private_key || '';
            if (setupEl) {
                setupEl.value = list.map(n => [
                    `Node: ${n.name || n.node_id || 'node'}`,
                    `Node token: ${n.token || ''}`,
                    `Node private key: ${n.private_key || ''}`
                ].join('\\n')).join('\\n\\n');
            }
            openModal('modal-show-token');
        }

        async function copyFieldValue(id) {
            const el = document.getElementById(id);
            const value = el?.value || el?.textContent || '';
            if (!value) return;
            try {
                await navigator.clipboard.writeText(value);
                alert(tx('کپی شد.', 'Copied.'));
            } catch (err) {
                if (el?.select) {
                    el.select();
                    document.execCommand('copy');
                    alert(tx('کپی شد.', 'Copied.'));
                }
            }
        }

        async function openNodeSecrets(nid) {
            try {
                const res = await fetch(`/api/nodes/secrets?id=${encodeURIComponent(nid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
                const data = await res.json();
                if (!res.ok) {
                    alert(data.error || tx('امکان دریافت مشخصات نود نیست.', 'Could not load node credentials.'));
                    return;
                }
                showGeneratedNodeCredentials({
                    node_id: data.node_id,
                    name: data.name,
                    token: data.token,
                    private_key: data.private_key
                });
            } catch (err) {
                alert(tx('خطا در دریافت مشخصات نود', 'Node credential loading failed'));
            }
        }

        async function autoAddNodes() {
            const res = await fetch('/api/nodes/auto', { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) {
                const data = await res.json();
                if (data.created.length) {
                    showGeneratedNodeCredentials(data.created);
                } else {
                    alert('Starter nodes already exist.');
                }
                fetchStatus();
            }
        }

        async function addPanelAsNode() {
            if (!confirm(tx(
                'یک نود داخلی واقعی روی همین سرور پنل با Host Network ساخته می‌شود. ادامه می‌دهید؟',
                'A real internal node will be started on this panel server using host networking. Continue?'
            ))) return;
            const button = document.getElementById('add-panel-node-btn');
            if (button) button.disabled = true;
            try {
                const response = await fetch('/api/nodes/panel-local', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: tx('نود داخلی سرور پنل', 'Panel Server Internal Node'),
                        host: latestStatus.panel_host || location.hostname
                    })
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.error || 'Panel node creation failed');
                alert(data.already_exists
                    ? tx('پنل قبلاً به‌عنوان نود ثبت شده است.', 'The panel is already registered as a node.')
                    : tx('نود محلی پنل ساخته شد و تا چند ثانیه دیگر Online می‌شود.', 'The local panel node was created and will be online shortly.'));
                setTimeout(fetchStatus, 4000);
            } catch (error) {
                alert(`${tx('خطا', 'Error')}: ${error.message || error}`);
                if (button) button.disabled = false;
            }
        }

        async function saveProfile() {
            const engine = document.getElementById('profile-engine')?.value || 'builtin';
            const mode = document.getElementById('profile-mode').value;
            const profileConfig = tunnelOptionMatrix[engine] || tunnelOptionMatrix.builtin;
            const mappedTransport = modeTransportMap[mode];
            const transport = (mappedTransport && profileConfig.transports.some(([value]) => value === mappedTransport)) ? mappedTransport : profileConfig.transports[0]?.[0] || 'tcp';
            const network = udpTunnelModes.includes(mode) ? 'udp' : (mode === 'tcp_udp' ? 'tcp_udp' : 'tcp');
            const payload = {
                name: document.getElementById('profile-name').value || 'Custom Profile',
                engine,
                tunnel_mode: mode,
                transport,
                network,
                pool_size: parseInt(document.getElementById('profile-pool').value || '120'),
                obfs_host: document.getElementById('profile-host').value,
                obfs_path: document.getElementById('profile-path').value,
                jitter_ms: parseInt(document.getElementById('profile-jitter').value || '0'),
                tls_enabled: tlsTunnelModes.includes(mode) || tlsTransports.includes(transport),
                padding_min: 0,
                padding_max: 96,
                keepalive_interval: 25
            };
            const res = await fetch('/api/profiles', { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            if (res.ok) {
                latestStatus.tunnel_profiles = (await res.json()).profiles;
                populateProfiles(latestStatus.tunnel_profiles);
                renderProfileCatalog(latestStatus.tunnel_profiles);
                alert(tx('پروفایل ذخیره شد.', 'Profile saved.'));
            }
        }

        function exportProfiles() {
            window.location.href = `/api/profiles/export?token=${token}`;
        }

        async function importProfiles() {
            try {
                const payload = JSON.parse(document.getElementById('profile-import').value);
                const res = await fetch('/api/profiles/import', { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (res.ok) {
                    latestStatus.tunnel_profiles = (await res.json()).profiles;
                    populateProfiles(latestStatus.tunnel_profiles);
                    renderProfileCatalog(latestStatus.tunnel_profiles);
                    alert(tx('پروفایل‌ها وارد شدند.', 'Profiles imported.'));
                }
            } catch (err) {
                alert(tx('JSON پروفایل نامعتبر است.', 'Invalid profile JSON.'));
            }
        }

        async function deleteNode(nid) {
            if (!confirm(tx('آیا مایل به حذف این نود هستید؟ تمام تانل‌های مربوطه نیز حذف خواهند شد.', 'Delete this node? All related tunnels will also be removed.'))) return;
            const res = await fetch(`/api/nodes?id=${nid}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) fetchStatus();
        }

        async function deleteLink(lid) {
            if (!confirm(tx('آیا مایل به حذف این تانل هستید؟', 'Delete this tunnel?'))) return;
            const res = await fetch(`/api/links?id=${lid}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) fetchStatus();
        }

        async function addPortMapping(lid) {
            const userPort = document.getElementById(`add-user-port-${lid}`).value;
            const targetPort = document.getElementById(`add-target-port-${lid}`).value;
            if (!userPort || !targetPort) {
                alert(tx('لطفا هر دو پورت یا بازه را وارد کنید.', 'Please enter both ports or ranges.'));
                return;
            }
            const res = await fetch(`/api/links/ports?id=${lid}`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_port: userPort.trim(), target_port: targetPort.trim() })
            });
            if (res.ok) {
                fetchStatus();
            } else {
                const data = await res.json();
                alert(`${tx('خطا', 'Error')}: ${data.error || data.message || tx('ثبت ناموفق', 'Save failed')}`);
            }
        }

        async function editPortMapping(lid, index, currentUserPort, currentTargetPort) {
            const userPort = prompt(tx('پورت ورودی داخلی جدید را وارد کنید:', 'Enter the new internal input port:'), currentUserPort);
            if (userPort === null) return;
            const targetPort = prompt(tx('پورت مقصد خارجی جدید را وارد کنید:', 'Enter the new external target port:'), currentTargetPort);
            if (targetPort === null) return;
            const res = await fetch(`/api/links/ports/edit?id=${encodeURIComponent(lid)}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ index, user_port: userPort.trim(), target_port: targetPort.trim() })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                fetchStatus();
            } else {
                alert(`${tx('خطا در ویرایش پورت', 'Port edit failed')}: ${data.error || data.message || tx('ثبت ناموفق', 'Save failed')}`);
            }
        }

        async function testPortPayload(lid, index) {
            if (!latestStatus?.capabilities?.payload_test_client) {
                alert(tx('پنل در حال اجرا هنوز نسخه جدید تست پکیج را ندارد. پنل را با آخرین پکیج آفلاین آپدیت و container را restart کنید.', 'The running panel does not have the new payload test backend yet. Update the panel with the latest offline package and restart the container.'));
                return;
            }
            const currentLink = latestStatus?.links?.[lid];
            if (!currentLink || !Array.isArray(currentLink.ports) || index < 0 || index >= currentLink.ports.length) {
                alert(`${tx('اطلاعات تانل یا پورت در صفحه قدیمی است. وضعیت را دوباره دریافت می‌کنم؛ چند ثانیه بعد دوباره تست کنید.', 'The tunnel or port data on this screen is stale. Refreshing status; try again in a few seconds.')}\\nlink=${lid || '-'} index=${index}`);
                fetchStatus();
                return;
            }
            const sizeInput = prompt(tx('حجم پکیج تست را به مگابایت وارد کنید:', 'Enter payload test size in MB:'), '4');
            if (sizeInput === null) return;
            const sizeMb = Math.max(1, Math.min(32, parseInt(sizeInput, 10) || 4));
            openModal('loading-overlay');
            const loadingText = document.querySelector('#loading-overlay h3');
            const oldLoadingText = loadingText?.innerText;
            if (loadingText) loadingText.innerText = tx('در حال انتقال پکیج تست از مسیر تانل...', 'Transferring test payload through the tunnel...');
            try {
                const res = await fetch('/api/links/payload-test', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ id: lid, link_id: lid, index, size_mb: sizeMb })
                });
                const raw = await res.text();
                let data = {};
                try {
                    data = raw ? JSON.parse(raw) : {};
                } catch (err) {
                    data = { error: `${tx('پاسخ غیر JSON از سرور', 'Non-JSON server response')}: ${raw.slice(0, 500)}` };
                }
                if (res.ok && data.success) {
                    const transfer = data.transfer || {};
                    alert(`${tx('تست واقعی تانل موفق بود', 'Real tunnel payload test succeeded')}\\n${tx('مسیر اصلی', 'Main mapping')}: ${data.user_port} -> ${data.target_port}\\n${tx('مسیر تست موقت', 'Temporary test path')}: ${data.test_user_port} -> ${data.test_target_port}\\n${tx('حجم', 'Size')}: ${data.size_mb} MB\\n${tx('دریافت شده', 'Received')}: ${formatBytes(transfer.bytes_received || 0)}\\n${tx('زمان', 'Time')}: ${transfer.elapsed_seconds}s\\n${tx('سرعت', 'Speed')}: ${transfer.mbps} Mbps`);
                } else {
                    const transfer = data.transfer || {};
                    const detail = transfer.bytes_sent !== undefined
                        ? `\\n${tx('ارسال', 'Sent')}: ${formatBytes(transfer.bytes_sent || 0)} | ${tx('دریافت', 'Received')}: ${formatBytes(transfer.bytes_received || 0)}\\nSHA sent: ${(transfer.sha256_sent || '').slice(0, 16)}...\\nSHA recv: ${(transfer.sha256_received || '').slice(0, 16)}...`
                        : '';
                    const hint = data.hint ? `\\n${data.hint}` : '';
                    const available = Array.isArray(data.available_links) && data.available_links.length
                        ? `\\n${tx('تانل‌های موجود روی سرور', 'Available server tunnels')}: ${data.available_links.map(l => `${l.name || l.id} (${l.id})`).join(', ')}`
                        : '';
                    const httpInfo = res.ok ? '' : `\\nHTTP ${res.status} ${res.statusText || ''}`;
                    alert(`${tx('تست واقعی تانل ناموفق بود', 'Real tunnel payload test failed')}${httpInfo}\\n${data.error || tx('خطای نامشخص', 'Unknown error')}\\n${data.echo_result?.error || ''}${detail}${hint}${available}`);
                }
            } catch (err) {
                alert(`${tx('تست واقعی تانل ناموفق بود', 'Real tunnel payload test failed')}\\n${err.message || err}`);
            } finally {
                if (loadingText && oldLoadingText) loadingText.innerText = oldLoadingText;
                closeModal('loading-overlay');
                fetchStatus();
            }
        }

        async function deletePortMapping(lid, index) {
            if (!confirm(tx('آیا مایل به حذف این پورت فورواردینگ هستید؟', 'Delete this port forwarding rule?'))) return;
            const res = await fetch(`/api/links/ports?id=${lid}&index=${index}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) fetchStatus();
        }

        let currentEditNodeId = null;
        let currentEditLinkId = null;

        function setNodeFormMode(mode) {
            const editing = mode === 'edit';
            const title = document.getElementById('node-modal-title');
            const submit = document.getElementById('node-submit-btn');
            if (title) title.innerText = editing ? tx('ویرایش نود', 'Edit node') : tx('افزودن نود جدید', 'Add node');
            if (submit) submit.innerText = editing ? tx('ذخیره تغییرات', 'Save changes') : tx('ثبت نود جدید', 'Save node');
        }

        function openNewNodeModal() {
            currentEditNodeId = null;
            document.getElementById('form-add-node').reset();
            setNodeFormMode('add');
            openModal('modal-add-node');
        }

        function editNode(nid) {
            const nodes = latestStatus?.nodes || {};
            if (!nodes[nid]) return;
            const n = nodes[nid];
            currentEditNodeId = nid;
            document.getElementById('node-name').value = n.name || '';
            document.getElementById('node-role').value = n.role || 'internal';
            document.getElementById('node-ip').value = n.ip || '';
            document.getElementById('node-tags').value = parseTags(n.tags || []).join(', ');
            document.getElementById('node-category').value = n.category || '';
            setNodeFormMode('edit');
            openModal('modal-add-node');
        }

        async function persistOrder(url, order) {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ order })
            });
            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.error || tx('ذخیره ترتیب ناموفق بود', 'Could not save order'));
            }
            return response.json().catch(() => ({ success: true, order }));
        }

        async function moveNode(nid, delta) {
            const nodes = latestStatus?.nodes || {};
            const order = Object.keys(nodes).sort((a, b) =>
                Number(nodes[a]?.display_order ?? 100000) - Number(nodes[b]?.display_order ?? 100000)
            );
            const index = order.indexOf(nid);
            const target = index + delta;
            if (index < 0 || target < 0 || target >= order.length) return;
            [order[index], order[target]] = [order[target], order[index]];
            order.forEach((id, position) => { if (nodes[id]) nodes[id].display_order = position; });
            renderNodes(nodes);
            try {
                await persistOrder('/api/nodes/reorder', order);
            } catch (error) {
                await fetchStatus();
                alert(error.message || error);
            }
        }

        async function moveLink(lid, delta) {
            const links = latestStatus?.links || {};
            const category = linkCategoryKey(links[lid] || {});
            const all = Object.keys(links).sort((a, b) =>
                Number(links[a]?.display_order ?? 100000) - Number(links[b]?.display_order ?? 100000)
            );
            const categoryOrder = all
                .filter(id => linkCategoryKey(links[id]) === category)
            const index = categoryOrder.indexOf(lid);
            const target = index + delta;
            if (index < 0 || target < 0 || target >= categoryOrder.length) return;
            const other = categoryOrder[target];
            const left = all.indexOf(lid);
            const right = all.indexOf(other);
            [all[left], all[right]] = [all[right], all[left]];
            all.forEach((id, position) => { if (links[id]) links[id].display_order = position; });
            lastLinksSignature = '';
            renderLinks(links, latestStatus?.nodes || {});
            try {
                await persistOrder('/api/links/reorder', all);
            } catch (error) {
                await fetchStatus();
                alert(error.message || error);
            }
        }

        async function moveLinkCategory(category, delta) {
            const categories = Array.from(new Set(
                Object.values(latestStatus?.links || {}).map(linkCategoryKey)
            ));
            const saved = latestStatus?.link_category_order || [];
            categories.sort((a, b) => {
                const ai = saved.indexOf(a), bi = saved.indexOf(b);
                return (ai < 0 ? 100000 : ai) - (bi < 0 ? 100000 : bi) || a.localeCompare(b);
            });
            const index = categories.indexOf(category);
            const target = index + delta;
            if (index < 0 || target < 0 || target >= categories.length) return;
            [categories[index], categories[target]] = [categories[target], categories[index]];
            latestStatus.link_category_order = categories;
            lastLinksSignature = '';
            renderLinks(latestStatus?.links || {}, latestStatus?.nodes || {});
            try {
                await persistOrder('/api/links/categories/reorder', categories);
            } catch (error) {
                await fetchStatus();
                alert(error.message || error);
            }
        }

        async function togglePauseNode(nid) {
            const res = await fetch(`/api/nodes/toggle-pause?id=${encodeURIComponent(nid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) fetchStatus();
            else alert(tx('عملیات ناموفق بود.', 'Operation failed.'));
        }

        function populateSshNodeSelect(selected = '') {
            const select = document.getElementById('ssh-node-id');
            if (!select) return;
            select.innerHTML = '';
            Object.entries(latestStatus?.nodes || {}).forEach(([nid, node]) => {
                const opt = document.createElement('option');
                opt.value = nid;
                opt.innerText = `${node.name || nid} (${node.ip || '-'})`;
                select.appendChild(opt);
            });
            if (selected && latestStatus?.nodes?.[selected]) select.value = selected;
        }

        function openNodeSshModal(nid = '') {
            populateSshNodeSelect(nid);
            fillSshFromNode();
            closeSshTerminal(true);
            document.getElementById('ssh-output').textContent = '';
            document.getElementById('ssh-status').innerText = tx('آماده اتصال', 'Ready');
            openModal('modal-node-ssh');
            setTimeout(() => document.getElementById('ssh-output')?.focus(), 120);
        }

        function fillSshFromNode() {
            const nid = document.getElementById('ssh-node-id')?.value;
            const node = latestStatus?.nodes?.[nid] || {};
            const saved = latestStatus?.ssh_saved_nodes?.[nid] || {};
            document.getElementById('ssh-host').value = saved.host || node.ip || '';
            document.getElementById('ssh-port').value = saved.port || 22;
            document.getElementById('ssh-username').value = saved.username || 'root';
            document.getElementById('ssh-auth-method').value = saved.auth_method || 'password';
            document.getElementById('ssh-password').placeholder = saved.has_password ? tx('رمز ذخیره شده است؛ برای تغییر وارد کنید', 'Saved; enter to change') : '';
            document.getElementById('ssh-private-key').placeholder = saved.has_private_key ? tx('کلید ذخیره شده است؛ برای تغییر وارد کنید', 'Saved; enter to change') : '';
            document.getElementById('ssh-password').value = '';
            document.getElementById('ssh-private-key').value = '';
            toggleSshAuthFields();
        }

        function toggleSshAuthFields() {
            const method = document.getElementById('ssh-auth-method')?.value || 'password';
            document.getElementById('ssh-password-group')?.classList.toggle('hidden', method !== 'password');
            document.getElementById('ssh-key-group')?.classList.toggle('hidden', method !== 'key');
        }

        function sshPayloadBase() {
            return {
                node_id: document.getElementById('ssh-node-id').value,
                host: document.getElementById('ssh-host').value,
                port: parseInt(document.getElementById('ssh-port').value || '22'),
                username: document.getElementById('ssh-username').value,
                auth_method: document.getElementById('ssh-auth-method').value,
                password: document.getElementById('ssh-password').value,
                private_key: document.getElementById('ssh-private-key').value,
                timeout: parseInt(document.getElementById('ssh-timeout').value || '15')
            };
        }

        async function saveSshOnly() {
            const res = await fetch('/api/nodes/ssh/save', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(sshPayloadBase())
            });
            document.getElementById('ssh-status').innerText = res.ok ? tx('ذخیره شد', 'Saved') : tx('ذخیره ناموفق بود', 'Save failed');
            if (res.ok) fetchStatus();
        }

        function appendSshOutput(text) {
            if (!text) return;
            const terminal = document.getElementById('ssh-output');
            terminal.textContent += text;
            terminal.scrollTop = terminal.scrollHeight;
        }

        async function pollSshTerminal() {
            if (!sshTerminalSessionId) return;
            try {
                const res = await fetch('/api/nodes/ssh/read', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sshTerminalSessionId })
                });
                const data = await res.json().catch(() => ({}));
                if (res.ok) {
                    appendSshOutput(data.output || '');
                    if (!data.alive) {
                        document.getElementById('ssh-status').innerText = tx('اتصال بسته شد', 'Session closed');
                        closeSshTerminal(true);
                    }
                }
            } catch (err) {}
        }

        async function sendSshTerminalInput(data) {
            if (!sshTerminalSessionId || !data) return;
            try {
                const res = await fetch('/api/nodes/ssh/write', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sshTerminalSessionId, data })
                });
                const result = await res.json().catch(() => ({}));
                if (res.ok) {
                    appendSshOutput(result.output || '');
                    if (!result.alive) closeSshTerminal(true);
                } else {
                    appendSshOutput(`\\n${result.error || 'SSH write failed'}\\n`);
                }
            } catch (err) {
                appendSshOutput(`\\n${err.message}\\n`);
            }
        }

        async function closeSshTerminal(silent = false) {
            const sessionId = sshTerminalSessionId;
            sshTerminalSessionId = null;
            if (sshTerminalPoller) {
                clearInterval(sshTerminalPoller);
                sshTerminalPoller = null;
            }
            if (sessionId) {
                try {
                    await fetch('/api/nodes/ssh/close', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: sessionId })
                    });
                } catch (err) {}
            }
            if (!silent) document.getElementById('ssh-status').innerText = tx('قطع شد', 'Disconnected');
        }

        document.getElementById('ssh-output')?.addEventListener('keydown', (e) => {
            if (!sshTerminalSessionId) return;
            e.preventDefault();
            const specialKeys = {
                ArrowUp: '\\x1b[A',
                ArrowDown: '\\x1b[B',
                ArrowRight: '\\x1b[C',
                ArrowLeft: '\\x1b[D',
                Home: '\\x1b[H',
                End: '\\x1b[F',
                Delete: '\\x1b[3~',
                PageUp: '\\x1b[5~',
                PageDown: '\\x1b[6~',
            };
            if (e.key === 'Enter') sendSshTerminalInput('\\r');
            else if (e.key === 'Backspace') sendSshTerminalInput('\\x7f');
            else if (e.key === 'Tab') sendSshTerminalInput('\\t');
            else if (specialKeys[e.key]) sendSshTerminalInput(specialKeys[e.key]);
            else if (e.ctrlKey && e.key.toLowerCase() === 'c') sendSshTerminalInput('\\u0003');
            else if (e.ctrlKey && e.key.toLowerCase() === 'd') sendSshTerminalInput('\\u0004');
            else if (e.ctrlKey && e.key.toLowerCase() === 'l') {
                document.getElementById('ssh-output').textContent = '';
                sendSshTerminalInput('\\f');
            } else if (e.key.length === 1) sendSshTerminalInput(e.key);
        });

        document.getElementById('ssh-output')?.addEventListener('paste', (e) => {
            if (!sshTerminalSessionId) return;
            e.preventDefault();
            const text = e.clipboardData?.getData('text') || '';
            if (text) sendSshTerminalInput(text.replace(/\\n/g, '\\r'));
        });

        async function suggestNextLinkPorts(force = false) {
            const easyManual = !!document.getElementById('link-easy-mode')?.checked
                && !!document.getElementById('link-easy-custom-ports')?.checked;
            if (easyManual && !force) return;
            const internalId = document.getElementById('link-iran-node')?.value || '';
            const externalId = document.getElementById('link-foreign-node')?.value || '';
            const status = document.getElementById('link-auto-port-status');
            if (token && internalId && externalId) {
                if (status) status.innerText = tx('در حال بررسی پورت‌های آزاد روی هر دو نود...', 'Checking free ports on both nodes...');
                try {
                    const response = await fetch('/api/links/next-ports', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            internal_node_id: internalId,
                            external_node_id: externalId,
                            exclude_link_id: currentEditLinkId || undefined,
                            start: 7000
                        })
                    });
                    const data = await response.json().catch(() => ({}));
                    if (response.ok) {
                        setLinkFormValue('link-bridge-port', data.bridge_port);
                        setLinkFormValue('link-sync-port', data.sync_port);
                        if (status) status.innerText = `${tx('جفت پورت آزاد تأیید شد', 'Free port pair verified')}: ${data.bridge_port} / ${data.sync_port}`;
                        return data;
                    }
                    if (status) status.innerText = data.error || tx('پورت آزاد پیدا نشد', 'No free port pair found');
                } catch (error) {
                    if (status) status.innerText = tx('بررسی API ناموفق بود؛ انتخاب محلی استفاده شد', 'API check failed; local fallback was used');
                }
            }
            const used = new Set();
            Object.values(latestStatus?.links || {}).forEach(link => {
                [link.bridge_port, link.sync_port].forEach(port => {
                    const numericPort = parseInt(port);
                    if (numericPort > 0) used.add(numericPort);
                });
                (link.ports || []).forEach(mapping => {
                    const numericPort = parseInt(mapping.user_port);
                    if (numericPort > 0) used.add(numericPort);
                });
            });
            let bridgePort = 7000;
            while (used.has(bridgePort) || used.has(bridgePort + 1)) bridgePort += 2;
            setLinkFormValue('link-bridge-port', bridgePort);
            setLinkFormValue('link-sync-port', bridgePort + 1);
            return { bridge_port: bridgePort, sync_port: bridgePort + 1, fallback: true };
        }

        async function smartTestSelectedNodes() {
            const internalId = document.getElementById('link-iran-node').value;
            const externalId = document.getElementById('link-foreign-node').value;
            const direction = document.getElementById('link-direction')?.value || 'external_to_internal';
            const objective = document.getElementById('smart-test-objective')?.value || 'balanced';
            const resultEl = document.getElementById('smart-test-result');
            if (!internalId || !externalId) {
                alert(tx('ابتدا دو نود را انتخاب کنید.', 'Choose both nodes first.'));
                return;
            }
            resultEl.innerHTML = `<span class="spinner"></span> ${tx('در حال اجرای Ping/TCP و تست واقعی iperf3 بین نودها...', 'Running Ping/TCP and a real inter-node iperf3 test...')}`;
            const res = await fetch('/api/links/smart-test', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ internal_node_id: internalId, external_node_id: externalId, direction, objective })
            });
            const data = await res.json();
            if (!res.ok) {
                resultEl.innerText = data.error || tx('تست ناموفق بود', 'Test failed');
                return;
            }
            if (data.recommended_profile_id && latestStatus.tunnel_profiles?.[data.recommended_profile_id]) {
                selectProfile(data.recommended_profile_id);
            }
            const adaptive = data.adaptive_transport_settings || {};
            if (adaptive.xhttp_mode) setLinkFormValue('link-xhttp-mode', adaptive.xhttp_mode);
            if (adaptive.smux_min_connections) setLinkFormValue('link-smux-min-connections', adaptive.smux_min_connections);
            if (adaptive.smux_max_connections) setLinkFormValue('link-smux-max-connections', adaptive.smux_max_connections);
            if (adaptive.smux_min_streams) setLinkFormValue('link-smux-min-streams', adaptive.smux_min_streams);
            setLinkFormValue('link-tcp-brutal-enabled', !!adaptive.tcp_brutal_recommended);
            if (adaptive.masque_mode) setLinkFormValue('link-masque-mode', adaptive.masque_mode);
            const bestSpeed = data.best_by_speed?.name || '-';
            const bestStable = data.best_by_stability?.name || '-';
            const bestSecurity = data.best_by_security?.name || '-';
            const avg = data.path_quality?.avg_ms ?? '∞';
            const loss = data.path_quality?.loss ?? '?';
            const throughput = data.path_quality?.throughput_mbps ?? 0;
            const realProbe = data.path_quality?.node_path_probe?.success;
            const realThroughput = data.throughput_probe?.success;
            const probeLabel = realProbe
                ? tx('Probe واقعی بین نودها انجام شد', 'Real node-to-node probe completed')
                : tx('Probe بین نودها ناموفق بود؛ از داده‌های پنل و نود استفاده شد', 'Node-to-node probe failed; panel and node telemetry were used');
            const objectiveLabels = {
                balanced: tx('متعادل', 'Balanced'),
                speed: tx('سرعت', 'Speed'),
                stability: tx('پایداری', 'Stability'),
                security: tx('امنیت', 'Security')
            };
            const topRows = (data.ranked_profiles || []).slice(0, 6).map((item, index) => `
                <div class="smart-profile-card ${index === 0 ? 'is-selected' : ''}" title="${esc(item.note || '')}">
                    <div class="flex-between"><strong>${index + 1}. ${esc(item.name || item.profile_id)}</strong><span class="tag-pill">${esc(item.total_score)}</span></div>
                    <div class="smart-profile-score">
                        <span>⚡ ${esc(item.scores?.speed ?? '-')}</span>
                        <span>✓ ${esc(item.scores?.stability ?? '-')}</span>
                        <span>🛡 ${esc(item.scores?.security ?? '-')}</span>
                        <span>${esc(item.engine || '-')} / ${esc(item.tunnel_mode || '-')}</span>
                    </div>
                </div>
            `).join('');
            resultEl.innerHTML = `
                <div class="smart-test-summary">
                    <div class="smart-metric"><span>${tx('پیشنهاد بر اساس معیار', 'Recommendation objective')}: ${esc(objectiveLabels[objective])}</span><strong>${esc(data.recommended_profile?.name || data.recommended_profile_id || '-')}</strong></div>
                    <div class="smart-metric"><span>${tx('تاخیر مسیر واقعی', 'Real path latency')}</span><strong>${esc(avg)} ms</strong></div>
                    <div class="smart-metric"><span>Loss</span><strong>${esc(loss)}%</strong></div>
                    <div class="smart-metric"><span>iperf3 throughput</span><strong>${realThroughput ? `${esc(throughput)} Mbps` : tx('ناموفق', 'Failed')}</strong></div>
                    <div class="smart-metric"><span>${tx('پروفایل‌های سازگار بررسی‌شده', 'Compatible profiles evaluated')}</span><strong>${esc(data.evaluated_profiles ?? 0)}</strong></div>
                </div>
                <div class="tag-row">
                    <span class="tag-pill ${realProbe ? 'rating-chip-good' : 'rating-chip-normal'}">${esc(probeLabel)}</span>
                    <span class="tag-pill ${realThroughput ? 'rating-chip-good' : 'rating-chip-normal'}">${realThroughput ? tx('تست پهنای‌باند واقعی انجام شد', 'Real throughput test completed') : esc(data.throughput_probe?.error || tx('تست پهنای‌باند ناموفق بود', 'Throughput test failed'))}</span>
                    <span class="tag-pill">⚡ ${esc(bestSpeed)}</span>
                    <span class="tag-pill">✓ ${esc(bestStable)}</span>
                    <span class="tag-pill">🛡 ${esc(bestSecurity)}</span>
                </div>
                <div class="smart-profile-grid">${topRows}</div>
            `;
            createInlineIcons(resultEl);
        }

        function renderSpeedTestNodePicker() {
            const picker = document.getElementById('speedtest-node-picker');
            if (!picker) return;
            const checked = new Set(Array.from(picker.querySelectorAll('input:checked')).map(input => input.value));
            const nodes = latestStatus?.nodes || {};
            picker.innerHTML = Object.entries(nodes)
                .sort(([, a], [, b]) => Number(a.display_order ?? 100000) - Number(b.display_order ?? 100000))
                .map(([id, node]) => `
                    <label class="speed-node-choice">
                        <input type="checkbox" value="${esc(id)}" ${checked.has(id) ? 'checked' : ''} ${node.status !== 'online' ? 'disabled' : ''}>
                        <span><strong>${esc(node.name || id)}</strong><br><small>${esc(node.ip || '-')} · ${esc(node.status || 'offline')}</small></span>
                    </label>
                `).join('');
        }

        function selectAllSpeedNodes(selected) {
            document.querySelectorAll('#speedtest-node-picker input:not(:disabled)').forEach(input => { input.checked = selected; });
        }

        function syncSpeedTestMode() {
            const internet = document.getElementById('speedtest-mode')?.value === 'internet';
            document.querySelectorAll('.speed-internet-only').forEach(el => { el.style.display = internet ? '' : 'none'; });
        }

        function speedTestOptions() {
            return {
                protocol: document.getElementById('speedtest-protocol')?.value || 'tcp',
                port: Number(document.getElementById('speedtest-port')?.value || 5201),
                duration: Number(document.getElementById('speedtest-duration')?.value || 8),
                parallel: Number(document.getElementById('speedtest-parallel')?.value || 2),
                omit: Number(document.getElementById('speedtest-omit')?.value || 1),
                bitrate: document.getElementById('speedtest-bitrate')?.value || '100M',
                block_length: Number(document.getElementById('speedtest-block-length')?.value || 0),
                window: document.getElementById('speedtest-window')?.value || '',
                congestion: document.getElementById('speedtest-congestion')?.value || '',
                reverse: !!document.getElementById('speedtest-reverse')?.checked,
                bidir: !!document.getElementById('speedtest-bidir')?.checked,
                zerocopy: !!document.getElementById('speedtest-zerocopy')?.checked,
                mptcp: !!document.getElementById('speedtest-mptcp')?.checked
            };
        }

        async function installIperfOnSelectedNodes() {
            const selected = Array.from(document.querySelectorAll('#speedtest-node-picker input:checked')).map(input => input.value);
            const nodeIds = selected.length ? selected : Object.keys(latestStatus?.nodes || {});
            const response = await fetch('/api/speedtest/install', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ node_ids: nodeIds })
            });
            const data = await response.json().catch(() => ({}));
            alert(response.ok
                ? `${tx('فرمان نصب/بررسی iperf3 ارسال شد', 'iperf3 install/check queued')}: ${data.queued_count || 0}`
                : (data.error || tx('عملیات ناموفق بود', 'Operation failed')));
        }

        async function startSpeedTest() {
            const mode = document.getElementById('speedtest-mode')?.value || 'pair';
            const nodeIds = Array.from(document.querySelectorAll('#speedtest-node-picker input:checked')).map(input => input.value);
            if ((mode === 'pair' && nodeIds.length !== 2) || (mode === 'mesh' && nodeIds.length < 2) || (mode === 'internet' && nodeIds.length < 1)) {
                alert(mode === 'pair'
                    ? tx('برای تست دو نودی دقیقاً دو نود را انتخاب کنید.', 'Select exactly two nodes for a pair test.')
                    : tx('تعداد نود انتخاب‌شده کافی نیست.', 'Not enough nodes are selected.'));
                return;
            }
            const internetHost = document.getElementById('speedtest-internet-host')?.value?.trim() || '';
            if (mode === 'internet' && !internetHost) {
                alert(tx('آدرس سرور اینترنتی iperf3 را وارد کنید.', 'Enter an Internet iperf3 server.'));
                return;
            }
            const button = document.getElementById('speedtest-start-btn');
            if (button) button.disabled = true;
            const response = await fetch('/api/speedtest/start', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode, node_ids: nodeIds, internet_host: internetHost, options: speedTestOptions() })
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                if (button) button.disabled = false;
                alert(data.error || tx('شروع تست ناموفق بود', 'Could not start speed test'));
                return;
            }
            currentSpeedTestJobId = data.job?.id || '';
            renderSpeedTestJob(data.job || {});
            if (speedTestPollTimer) clearInterval(speedTestPollTimer);
            speedTestPollTimer = setInterval(pollSpeedTestJob, 1000);
        }

        async function pollSpeedTestJob() {
            if (!currentSpeedTestJobId) return;
            const response = await fetch(`/api/speedtest/status?id=${encodeURIComponent(currentSpeedTestJobId)}`, {
                headers: { 'Authorization': `Bearer ${token}` },
                cache: 'no-store'
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) return;
            renderSpeedTestJob(data.job || {});
            if (['completed', 'failed'].includes(data.job?.state)) {
                clearInterval(speedTestPollTimer);
                speedTestPollTimer = null;
                const button = document.getElementById('speedtest-start-btn');
                if (button) button.disabled = false;
            }
        }

        function renderSpeedTestJob(job) {
            const results = job.results || [];
            const errors = job.errors || [];
            const total = Number(job.total || 0);
            const completed = Number(job.completed || 0);
            const percent = total ? Math.min(100, completed * 100 / total) : (job.state === 'completed' ? 100 : 4);
            const state = document.getElementById('speedtest-state');
            const bar = document.getElementById('speedtest-progress-bar');
            const phaseLabels = {
                queued: tx('در صف', 'Queued'),
                preflight: tx('بررسی و آماده‌سازی iperf3', 'Checking/installing iperf3'),
                testing: tx('در حال اندازه‌گیری', 'Measuring'),
                completed: tx('تکمیل‌شده', 'Completed'),
                failed: tx('ناموفق', 'Failed')
            };
            if (state) state.innerText = `${phaseLabels[job.phase] || job.state || 'running'} · ${completed}/${total || '?'}`;
            if (bar) bar.style.width = `${percent}%`;
            const valid = results.filter(item => item.success);
            const maxRate = Math.max(1, ...valid.map(item => Math.max(Number(item.upload_mbps || 0), Number(item.download_mbps || 0))));
            const average = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
            const uploads = valid.map(item => Number(item.upload_mbps || 0));
            const downloads = valid.map(item => Number(item.download_mbps || 0));
            const summary = document.getElementById('speedtest-summary');
            if (summary) summary.innerHTML = `
                <div class="speed-metric"><span>${tx('تست موفق', 'Successful tests')}</span><strong>${valid.length}</strong></div>
                <div class="speed-metric"><span>${tx('میانگین آپلود', 'Average upload')}</span><strong>${average(uploads).toFixed(2)} Mbps</strong></div>
                <div class="speed-metric"><span>${tx('میانگین دانلود', 'Average download')}</span><strong>${average(downloads).toFixed(2)} Mbps</strong></div>
                <div class="speed-metric"><span>${tx('خطا', 'Errors')}</span><strong>${errors.length}</strong></div>
            `;
            const tbody = document.getElementById('speedtest-results-body');
            if (tbody) tbody.innerHTML = results.map(item => {
                const route = item.scope === 'internet'
                    ? `${item.node_name || item.node_id} → ${item.host || '-'}`
                    : `${item.source_name || item.source_node_id} → ${item.target_name || item.target_node_id}`;
                const rate = Math.max(Number(item.upload_mbps || 0), Number(item.download_mbps || 0));
                return `<tr>
                    <td><strong>${esc(route)}</strong><div class="speed-result-bar mt-20"><span style="width:${Math.max(2, rate * 100 / maxRate)}%"></span></div></td>
                    <td>${esc(String(item.protocol || '-').toUpperCase())} · P${esc(item.parallel || '-')}</td>
                    <td>${esc(item.upload_mbps ?? 0)} Mbps</td>
                    <td>${esc(item.download_mbps ?? 0)} Mbps</td>
                    <td>${esc(item.loss_percent ?? 0)}% / ${esc(item.jitter_ms ?? 0)} ms</td>
                    <td>${esc(item.retransmits ?? 0)}</td>
                    <td>${esc(item.cpu_local ?? 0)}% / ${esc(item.cpu_remote ?? 0)}%</td>
                    <td class="${item.success ? 'text-success' : 'text-danger'}">${item.success ? tx('موفق', 'Success') : esc(item.error || tx('ناموفق', 'Failed'))}</td>
                </tr>`;
            }).join('');
            const details = document.getElementById('speedtest-details');
            if (details) details.textContent = JSON.stringify({ job: { id: job.id, state: job.state, mode: job.mode, error: job.error }, errors, results }, null, 2);
        }

        async function quickSpaceTunnel() {
            const internalId = document.getElementById('link-iran-node').value;
            const externalId = document.getElementById('link-foreign-node').value;
            if (!internalId || !externalId) {
                alert(tx('ابتدا دو نود را انتخاب کنید.', 'Choose both nodes first.'));
                return;
            }
            await suggestNextLinkPorts();
            const internalNode = latestStatus.nodes?.[internalId] || {};
            const externalNode = latestStatus.nodes?.[externalId] || {};
            const payload = {
                name: `Space-${internalNode.name || 'internal'}-${externalNode.name || 'external'}`.slice(0, 90),
                profile_id: 'easy',
                tags: ['space', 'quick'],
                internal_node_id: internalId,
                external_node_id: externalId,
                direction: document.getElementById('link-direction')?.value || 'external_to_internal',
                engine: 'builtin',
                transport: 'websocket',
                network: 'tcp',
                bridge_port: parseInt(document.getElementById('link-bridge-port').value || '7000'),
                sync_port: parseInt(document.getElementById('link-sync-port').value || '7001'),
                pool_size: 16,
                tunnel_mode: 'websocket',
                tls_enabled: true,
                tls_sni: 'speedtest.net',
                obfs_host: 'speedtest.net',
                obfs_path: '/assets/ws',
                padding_min: 0,
                padding_max: 32,
                jitter_ms: 0,
                keepalive_interval: 25,
                easy_mode: true,
                auto_allocate_ports: true
            };
            const res = await fetch('/api/links', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                closeModal('modal-add-link');
                fetchStatus();
            } else {
                alert(`${tx('خطا در ایجاد تانل', 'Tunnel creation error')}: ${data.error || data.message || tx('ثبت ناموفق', 'Save failed')}`);
            }
        }

        async function openNewLinkModal() {
            currentEditLinkId = null;
            const form = document.getElementById('form-add-link');
            form.reset();
            populateLinkNodeSelects(latestStatus?.nodes || {}, { preserveSelection: false });
            document.getElementById('link-modal-title').innerText = tx('ایجاد تانل (لینک) جدید', 'Create new tunnel link');
            document.getElementById('link-submit-button').innerText = tx('ایجاد تانل', 'Create tunnel');
            document.getElementById('link-profile').value = 'custom';
            renderProfilePicker(latestStatus.tunnel_profiles || {});
            document.getElementById('link-tags').value = '';
            document.getElementById('link-category').value = '';
            setLinkFormValue('link-direction', 'external_to_internal');
            setLinkFormValue('link-data-plane-architecture', 'per_user');
            setLinkFormValue('link-mux-carriers', 4);
            setLinkFormValue('link-adaptive-smux', true);
            setLinkFormValue('link-smux-min-connections', 2);
            setLinkFormValue('link-smux-max-connections', 8);
            setLinkFormValue('link-smux-min-streams', 8);
            setLinkFormValue('link-smux-padding', true);
            setLinkFormValue('link-ech-enabled', false);
            setLinkFormValue('link-ech-config', '');
            setLinkFormValue('link-ech-query-server-name', '');
            setLinkFormValue('link-xhttp-mode', 'auto');
            setLinkFormValue('link-xhttp-auto-select', true);
            setLinkFormValue('link-masque-mode', 'connect-udp');
            setLinkFormValue('link-masque-token', '');
            setLinkFormValue('link-tcp-brutal-enabled', false);
            setLinkFormValue('link-tcp-brutal-up', 50);
            setLinkFormValue('link-tcp-brutal-down', 100);
            setLinkFormValue('link-bonding-enabled', false);
            setLinkFormValue('link-bonding-max-lanes', 4);
            setLinkFormValue('link-easy-custom-ports', false);
            toggleDataPlaneOptions();
            updateDirectionExample();
            document.getElementById('link-easy-mode').checked = true;
            syncTunnelOptions({ transport: 'tcp', network: 'tcp', mode: 'tcp' });
            await suggestNextLinkPorts();
            await toggleEasyMode();
            openModal('modal-add-link');
        }

        function setLinkFormValue(id, value) {
            const el = document.getElementById(id);
            if (!el) return;
            if (el.type === 'checkbox') el.checked = !!value;
            else el.value = value ?? '';
        }

        function editLink(lid) {
            const link = latestStatus?.links?.[lid];
            if (!link) return;
            currentEditLinkId = lid;
            document.getElementById('link-modal-title').innerText = tx('ویرایش تانل', 'Edit tunnel');
            document.getElementById('link-submit-button').innerText = tx('ذخیره تغییرات تانل', 'Save tunnel changes');
            populateLinkNodeSelects(latestStatus?.nodes || {}, { preserveSelection: false });
            setLinkFormValue('link-name', link.name || '');
            setLinkFormValue('link-profile', link.profile_id || 'custom');
            renderProfilePicker(latestStatus.tunnel_profiles || {});
            setLinkFormValue('link-tags', parseTags(link.tags || []).join(', '));
            setLinkFormValue('link-category', link.category || '');
            setLinkFormValue('link-easy-mode', false);
            setLinkFormValue('link-easy-custom-ports', false);
            setLinkFormValue('link-iran-node', link.internal_node_id || link.iran_node_id || '');
            setLinkFormValue('link-foreign-node', link.external_node_id || link.foreign_node_id || '');
            setLinkFormValue('link-direction', link.direction || 'external_to_internal');
            updateDirectionExample();
            setLinkFormValue('link-engine', link.engine || 'builtin');
            setLinkFormValue('link-native-engine-enabled', !!link.native_engine_enabled);
            setLinkFormValue('link-hysteria-up-mbps', link.hysteria_up_mbps || 30);
            setLinkFormValue('link-hysteria-down-mbps', link.hysteria_down_mbps || 50);
            syncTunnelOptions({ transport: link.transport || link.tunnel_mode || 'tcp', network: link.network || 'tcp', mode: link.tunnel_mode || 'tcp' });
            setLinkFormValue('link-bridge-port', link.bridge_port || 7000);
            setLinkFormValue('link-sync-port', link.sync_port || 7001);
            setLinkFormValue('link-pool-size', link.pool_size || 4);
            setLinkFormValue('link-data-plane-architecture', link.data_plane_architecture || (link.bonding_enabled ? 'adaptive_bonding' : 'per_user'));
            setLinkFormValue('link-mux-carriers', link.mux_carriers || 4);
            setLinkFormValue('link-adaptive-smux', link.adaptive_smux_enabled !== false);
            setLinkFormValue('link-smux-min-connections', link.smux_min_connections || 2);
            setLinkFormValue('link-smux-max-connections', link.smux_max_connections || 8);
            setLinkFormValue('link-smux-min-streams', link.smux_min_streams || 8);
            setLinkFormValue('link-smux-padding', link.smux_padding !== false);
            setLinkFormValue('link-ech-enabled', !!link.ech_enabled);
            setLinkFormValue('link-ech-config', link.ech_config || '');
            setLinkFormValue('link-ech-query-server-name', link.ech_query_server_name || '');
            setLinkFormValue('link-xhttp-mode', link.xhttp_mode || 'auto');
            setLinkFormValue('link-xhttp-auto-select', link.xhttp_auto_select !== false);
            setLinkFormValue('link-masque-mode', link.masque_mode || 'connect-udp');
            setLinkFormValue('link-masque-token', link.masque_token || '');
            setLinkFormValue('link-tcp-brutal-enabled', !!link.tcp_brutal_enabled);
            setLinkFormValue('link-tcp-brutal-up', link.tcp_brutal_up_mbps || 50);
            setLinkFormValue('link-tcp-brutal-down', link.tcp_brutal_down_mbps || 100);
            setLinkFormValue('link-bonding-enabled', !!link.bonding_enabled);
            setLinkFormValue('link-bonding-max-lanes', link.bonding_max_lanes || 4);
            toggleDataPlaneOptions();
            setLinkFormValue('link-tls-enabled', !!link.tls_enabled);
            setLinkFormValue('link-tls-sni', link.tls_sni || link.obfs_host || 'speedtest.net');
            setLinkFormValue('link-obfs-host', link.obfs_host || 'speedtest.net');
            setLinkFormValue('link-obfs-path', link.obfs_path || '/tunnel');
            setLinkFormValue('link-padding-min', link.padding_min || 0);
            setLinkFormValue('link-padding-max', link.padding_max || 0);
            setLinkFormValue('link-jitter-ms', link.jitter_ms || 0);
            setLinkFormValue('link-keepalive', link.keepalive_interval || 25);
            setLinkFormValue('link-xray-protocol', link.xray_protocol || 'vless');
            setLinkFormValue('link-xray-security', link.xray_security || 'reality');
            setLinkFormValue('link-xray-flow', link.xray_flow || 'xtls-rprx-vision');
            setLinkFormValue('link-xray-uuid', link.xray_uuid || '');
            setLinkFormValue('link-xray-sni', link.xray_sni || 'www.microsoft.com');
            setLinkFormValue('link-xray-shortid', link.xray_shortid || '');
            setLinkFormValue('link-xray-public-key', link.xray_public_key || '');
            setLinkFormValue('link-xray-private-key', link.xray_private_key || '');
            setLinkFormValue('link-ssh-user', link.ssh_user || 'root');
            setLinkFormValue('link-ssh-port', link.ssh_port || 22);
            setLinkFormValue('link-ssh-bind-host', link.ssh_bind_host || '0.0.0.0');
            setLinkFormValue('link-ssh-identity-file', link.ssh_identity_file || '/opt/p00rija/ssh/id_ed25519');
            setLinkFormValue('link-ssh-target-host', link.ssh_target_host || '127.0.0.1');
            setLinkFormValue('link-ssh-target-port', link.ssh_target_port || 443);
            setLinkFormValue('link-ssh-jump-hosts', link.ssh_jump_hosts || '');
            setLinkFormValue('link-stunnel-cert-path', link.stunnel_cert_path || '/opt/p00rija/certs/stunnel.crt');
            setLinkFormValue('link-stunnel-key-path', link.stunnel_key_path || '/opt/p00rija/certs/stunnel.key');
            setLinkFormValue('link-stunnel-verify', !!link.stunnel_verify);
            setLinkFormValue('link-wg-address', link.wg_address || '10.77.0.1/24');
            setLinkFormValue('link-wg-client-address', link.wg_client_address || '10.77.0.2/32');
            setLinkFormValue('link-wg-mtu', link.wg_mtu || 1420);
            setLinkFormValue('link-wg-allowed-ips', link.wg_allowed_ips || '0.0.0.0/0, ::/0');
            setLinkFormValue('link-wg-interface', link.wg_interface || '');
            setLinkFormValue('link-aead-cipher', link.aead_cipher || 'aes-128-gcm');
            setLinkFormValue('link-aead-key', link.aead_key || '');
            setLinkFormValue('link-egress-mode', link.egress_mode || (String(link.tunnel_mode || '').includes('socks5') ? 'socks5' : 'port_forward'));
            setLinkFormValue('link-socks5-username', link.socks5_username || '');
            setLinkFormValue('link-socks5-password', link.socks5_password || '');
            setLinkFormValue('link-raw-protocol', link.raw_protocol || 253);
            setLinkFormValue('link-raw-mtu', link.raw_mtu || 1200);
            setLinkFormValue('link-raw-packet-mark', link.raw_packet_mark || '');
            toggleObfsOptions();
            toggleEngineOptions();
            toggleEasyMode();
            openModal('modal-add-link');
        }

        async function togglePauseLink(lid) {
            const res = await fetch(`/api/links/toggle-pause?id=${encodeURIComponent(lid)}`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) fetchStatus();
            else alert(tx('عملیات ناموفق بود.', 'Operation failed.'));
        }

        document.getElementById('form-add-node').addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                name: document.getElementById('node-name').value,
                role: document.getElementById('node-role').value,
                ip: document.getElementById('node-ip').value,
                tags: parseTags(document.getElementById('node-tags').value)
                ,category: document.getElementById('node-category').value
            };
            
            let url = '/api/nodes';
            if (currentEditNodeId) {
                url = '/api/nodes/edit';
                payload.id = currentEditNodeId;
            }

            const res = await fetch(url, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                const data = await res.json();
                closeModal('modal-add-node');
                document.getElementById('form-add-node').reset();
                
                if (!currentEditNodeId) {
                    showGeneratedNodeCredentials(data);
                }
                currentEditNodeId = null;
                setNodeFormMode('add');
                fetchStatus();
            } else {
                alert(tx('عملیات ناموفق بود.', 'Operation failed.'));
            }
        });

        document.getElementById('form-node-ssh').addEventListener('submit', async (e) => {
            e.preventDefault();
            const statusEl = document.getElementById('ssh-status');
            const outEl = document.getElementById('ssh-output');
            await closeSshTerminal(true);
            statusEl.innerText = tx('در حال اتصال ترمینال...', 'Opening terminal...');
            outEl.textContent = '';
            const payload = {
                ...sshPayloadBase(),
                save: document.getElementById('ssh-save').checked
            };
            const res = await fetch('/api/nodes/ssh/start', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                sshTerminalSessionId = data.session_id;
                statusEl.innerText = data.alive ? tx('ترمینال متصل است', 'Terminal connected') : tx('اتصال بسته شد', 'Session closed');
                appendSshOutput(data.output || '');
                sshTerminalPoller = setInterval(pollSshTerminal, 900);
                outEl.focus();
                fetchStatus();
            } else {
                statusEl.innerText = tx('اتصال ناموفق بود', 'Connection failed');
                outEl.textContent = data.error || tx('خطا در ارتباط SSH', 'SSH error');
            }
        });

        document.getElementById('form-add-link').addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!document.getElementById('link-iran-node').value || !document.getElementById('link-foreign-node').value) {
                alert(tx('برای ساخت تانل باید حداقل یک نود داخلی و یک نود خارجی ثبت شده باشد.', 'At least one internal node and one external node are required to create a tunnel.'));
                return;
            }
            const payload = {
                name: document.getElementById('link-name').value,
                profile_id: document.getElementById('link-profile').value,
                tags: parseTags(document.getElementById('link-tags').value),
                category: document.getElementById('link-category').value,
                internal_node_id: document.getElementById('link-iran-node').value,
                external_node_id: document.getElementById('link-foreign-node').value,
                direction: document.getElementById('link-direction').value,
                engine: document.getElementById('link-engine').value,
                native_engine_enabled: document.getElementById('link-native-engine-enabled').checked,
                hysteria_up_mbps: parseInt(document.getElementById('link-hysteria-up-mbps').value || '30'),
                hysteria_down_mbps: parseInt(document.getElementById('link-hysteria-down-mbps').value || '50'),
                transport: document.getElementById('link-transport').value,
                network: document.getElementById('link-network').value,
                bridge_port: parseInt(document.getElementById('link-bridge-port').value),
                sync_port: parseInt(document.getElementById('link-sync-port').value),
                pool_size: parseInt(document.getElementById('link-pool-size').value),
                data_plane_architecture: document.getElementById('link-data-plane-architecture').value,
                mux_carriers: parseInt(document.getElementById('link-mux-carriers').value || '4'),
                adaptive_smux_enabled: document.getElementById('link-adaptive-smux').checked,
                smux_min_connections: parseInt(document.getElementById('link-smux-min-connections').value || '2'),
                smux_max_connections: parseInt(document.getElementById('link-smux-max-connections').value || '8'),
                smux_min_streams: parseInt(document.getElementById('link-smux-min-streams').value || '8'),
                smux_padding: document.getElementById('link-smux-padding').checked,
                bonding_enabled: document.getElementById('link-bonding-enabled').checked,
                bonding_max_lanes: parseInt(document.getElementById('link-bonding-max-lanes').value || '4'),
                tunnel_mode: document.getElementById('link-tunnel-mode').value,
                tls_enabled: document.getElementById('link-tls-enabled').checked,
                tls_sni: document.getElementById('link-tls-sni').value,
                obfs_host: document.getElementById('link-obfs-host').value,
                obfs_path: document.getElementById('link-obfs-path').value,
                padding_min: parseInt(document.getElementById('link-padding-min').value || '0'),
                padding_max: parseInt(document.getElementById('link-padding-max').value || '0'),
                jitter_ms: parseInt(document.getElementById('link-jitter-ms').value || '0'),
                keepalive_interval: parseInt(document.getElementById('link-keepalive').value || '25'),
                xray_protocol: document.getElementById('link-xray-protocol').value,
                xray_security: document.getElementById('link-xray-security').value,
                xray_flow: document.getElementById('link-xray-flow').value,
                xray_uuid: document.getElementById('link-xray-uuid').value,
                xray_sni: document.getElementById('link-xray-sni').value,
                xray_shortid: document.getElementById('link-xray-shortid').value,
                xray_public_key: document.getElementById('link-xray-public-key').value,
                xray_private_key: document.getElementById('link-xray-private-key').value,
                ech_enabled: document.getElementById('link-ech-enabled').checked,
                ech_config: document.getElementById('link-ech-config').value,
                ech_query_server_name: document.getElementById('link-ech-query-server-name').value,
                xhttp_mode: document.getElementById('link-xhttp-mode').value,
                xhttp_auto_select: document.getElementById('link-xhttp-auto-select').checked,
                masque_mode: document.getElementById('link-masque-mode').value,
                masque_token: document.getElementById('link-masque-token').value,
                tcp_brutal_enabled: document.getElementById('link-tcp-brutal-enabled').checked,
                tcp_brutal_up_mbps: parseInt(document.getElementById('link-tcp-brutal-up').value || '50'),
                tcp_brutal_down_mbps: parseInt(document.getElementById('link-tcp-brutal-down').value || '100'),
                ssh_user: document.getElementById('link-ssh-user').value,
                ssh_port: parseInt(document.getElementById('link-ssh-port').value || '22'),
                ssh_bind_host: document.getElementById('link-ssh-bind-host').value,
                ssh_identity_file: document.getElementById('link-ssh-identity-file').value,
                ssh_target_host: document.getElementById('link-ssh-target-host').value,
                ssh_target_port: parseInt(document.getElementById('link-ssh-target-port').value || '443'),
                ssh_jump_hosts: document.getElementById('link-ssh-jump-hosts').value,
                stunnel_cert_path: document.getElementById('link-stunnel-cert-path').value,
                stunnel_key_path: document.getElementById('link-stunnel-key-path').value,
                stunnel_verify: document.getElementById('link-stunnel-verify').checked,
                wg_address: document.getElementById('link-wg-address').value,
                wg_client_address: document.getElementById('link-wg-client-address').value,
                wg_mtu: parseInt(document.getElementById('link-wg-mtu').value || '1420'),
                wg_allowed_ips: document.getElementById('link-wg-allowed-ips').value,
                wg_interface: document.getElementById('link-wg-interface').value,
                aead_cipher: document.getElementById('link-aead-cipher').value,
                aead_key: document.getElementById('link-aead-key').value,
                egress_mode: document.getElementById('link-egress-mode').value,
                socks5_username: document.getElementById('link-socks5-username').value,
                socks5_password: document.getElementById('link-socks5-password').value,
                raw_protocol: parseInt(document.getElementById('link-raw-protocol').value || '253'),
                raw_mtu: parseInt(document.getElementById('link-raw-mtu').value || '1200'),
                raw_packet_mark: document.getElementById('link-raw-packet-mark').value
            };
            payload.easy_mode = Boolean(document.getElementById('link-easy-mode').checked);
            payload.auto_allocate_ports = payload.easy_mode
                && !document.getElementById('link-easy-custom-ports').checked
                && !currentEditLinkId;
            let url = '/api/links';
            if (currentEditLinkId) {
                url = '/api/links/edit';
                payload.id = currentEditLinkId;
            }
            const res = await fetch(url, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                closeModal('modal-add-link');
                document.getElementById('form-add-link').reset();
                currentEditLinkId = null;
                fetchStatus();
            } else {
                const data = await res.json();
                alert(`${tx('خطا در ایجاد تانل', 'Tunnel creation error')}: ${data.error || data.message || tx('ثبت ناموفق', 'Save failed')}`);
            }
        });

        document.getElementById('form-settings-pass').addEventListener('submit', async (e) => {
            e.preventDefault();
            const u = document.getElementById('setting-username').value;
            const p = document.getElementById('setting-password').value;
            const res = await fetch('/api/settings/password', {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username: u, password: p })
            });
            if (res.ok) {
                alert(tx('مشخصات ورود با موفقیت بروزرسانی شد.', 'Login credentials updated successfully.'));
                document.getElementById('setting-password').value = '';
            } else {
                alert(tx('خطا در ثبت مشخصات.', 'Could not save credentials.'));
            }
        });

        document.getElementById('form-settings-network').addEventListener('submit', async (e) => {
            e.preventDefault();
            const disable_ipv6 = document.getElementById('setting-disable-ipv6').checked;
            const engine_restart_interval = parseInt(document.getElementById('setting-engine-restart-interval').value) || 0;
            
            const res = await fetch('/api/settings/network', {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ disable_ipv6, engine_restart_interval })
            });
            if (res.ok) {
                alert(tx('تنظیمات شبکه با موفقیت بروزرسانی و بر روی سرور اعمال شد.', 'Network settings applied successfully.'));
                fetchStatus();
            } else {
                alert(tx('خطا در ثبت تنظیمات.', 'Could not save settings.'));
            }
        });

        document.getElementById('form-panel-ports')?.addEventListener('submit', async (event) => {
            event.preventDefault();
            const webPort = parseInt(document.getElementById('setting-panel-port').value || '0');
            const apiPort = parseInt(document.getElementById('setting-api-port').value || '0');
            const panelHost = document.getElementById('setting-panel-host').value.trim();
            if (!confirm(tx(
                `پنل روی پورت ${webPort} بازسازی می‌شود و اتصال فعلی قطع خواهد شد. ادامه می‌دهید؟`,
                `The panel will be recreated on port ${webPort} and this connection will close. Continue?`
            ))) return;
            const result = document.getElementById('panel-port-result');
            result.innerText = tx('در حال هماهنگ‌سازی نودها و اعمال پورت جدید...', 'Coordinating nodes and applying the new ports...');
            try {
                const response = await fetch('/api/settings/panel-ports', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ web_port: webPort, api_port: apiPort, panel_host: panelHost })
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.error || 'Panel port change failed');
                result.innerText = `${tx('درخواست اعمال شد', 'Change queued')}: ${data.new_panel_url}`;
                setTimeout(() => { window.location.href = data.new_panel_url; }, 9000);
            } catch (error) {
                result.innerText = `${tx('خطا', 'Error')}: ${error.message || error}`;
            }
        });

        function generateHiddenPanelPath() {
            const bytes = new Uint8Array(18);
            crypto.getRandomValues(bytes);
            const tokenValue = Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
            document.getElementById('setting-hidden-panel-path').value = `/manage-${tokenValue}`;
        }

        document.getElementById('form-panel-hidden-path')?.addEventListener('submit', async (event) => {
            event.preventDefault();
            const enabled = document.getElementById('setting-hidden-path-enabled').checked;
            const path = document.getElementById('setting-hidden-panel-path').value.trim();
            if (enabled && path.length < 20) {
                alert(tx('مسیر مخفی باید حداقل ۲۰ کاراکتر باشد.', 'The hidden path must be at least 20 characters.'));
                return;
            }
            const response = await fetch('/api/settings/panel-path', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled, path })
            });
            const data = await response.json().catch(() => ({}));
            const result = document.getElementById('hidden-path-result');
            if (!response.ok) {
                result.innerText = `${tx('خطا', 'Error')}: ${data.error || tx('ناشناخته', 'Unknown')}`;
                return;
            }
            result.innerText = `${tx('آدرس جدید مدیریت', 'New management URL')}: ${data.access_url}`;
            setTimeout(() => { window.location.href = data.access_url; }, 1500);
        });

        async function createAndDownloadBackup() {
            const password = document.getElementById('backup-password').value;
            const result = document.getElementById('backup-result');
            if ((password || '').length < 8) {
                alert(tx('رمز بکاپ باید حداقل ۸ کاراکتر باشد.', 'Backup password must be at least 8 characters.'));
                return;
            }
            result.innerText = tx('در حال ساخت و رمزگذاری بکاپ...', 'Creating and encrypting backup...');
            try {
                const createRes = await fetch('/api/backup/create', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        backup_password: password,
                        include_engines: document.getElementById('backup-include-engines').checked
                    })
                });
                const data = await createRes.json().catch(() => ({}));
                if (!createRes.ok) throw new Error(data.error || 'Backup creation failed');
                const downloadRes = await fetch(data.download_url, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (!downloadRes.ok) throw new Error('Backup download failed');
                const blob = await downloadRes.blob();
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = data.filename;
                document.body.appendChild(link);
                link.click();
                link.remove();
                URL.revokeObjectURL(url);
                result.innerText = `${tx('بکاپ دانلود شد', 'Backup downloaded')}: ${data.filename}\\nSHA-256: ${data.sha256}`;
                document.getElementById('backup-password').value = '';
            } catch (error) {
                result.innerText = `${tx('خطا', 'Error')}: ${error.message || error}`;
            }
        }

        function utf8Base64(value) {
            const bytes = new TextEncoder().encode(value);
            let binary = '';
            for (const byte of bytes) binary += String.fromCharCode(byte);
            return btoa(binary);
        }

        async function loadServerBackups() {
            const select = document.getElementById('restore-server-backup');
            if (!select) return;
            select.innerHTML = `<option value="">${tx('در حال خواندن بکاپ‌ها...', 'Loading backups...')}</option>`;
            try {
                const response = await fetch('/api/backup/list', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.error || 'Could not list backups');
                const backups = data.backups || [];
                select.innerHTML = backups.length
                    ? backups.map(item => `<option value="${escapeHtml(item.backup_id)}">${escapeHtml(item.filename)} (${formatBytes(item.size || 0)})</option>`).join('')
                    : `<option value="">${tx('بکاپی در سرور وجود ندارد', 'No server backups found')}</option>`;
            } catch (error) {
                select.innerHTML = `<option value="">${escapeHtml(error.message || String(error))}</option>`;
            }
        }

        document.getElementById('restore-source')?.addEventListener('change', (event) => {
            const serverMode = event.target.value === 'server';
            document.getElementById('restore-upload-wrap').style.display = serverMode ? 'none' : '';
            document.getElementById('restore-server-wrap').style.display = serverMode ? '' : 'none';
            if (serverMode) loadServerBackups();
        });

        document.getElementById('form-panel-restore')?.addEventListener('submit', async (event) => {
            event.preventDefault();
            const source = document.getElementById('restore-source').value;
            const password = document.getElementById('restore-password').value;
            const newPanelUrl = document.getElementById('restore-panel-url').value.trim();
            const regenerate = document.getElementById('restore-regenerate-cert').checked;
            const result = document.getElementById('restore-result');
            if ((password || '').length < 8) {
                alert(tx('رمز بکاپ باید حداقل ۸ کاراکتر باشد.', 'Backup password must be at least 8 characters.'));
                return;
            }
            if (regenerate && !newPanelUrl) {
                alert(tx('برای ساخت Certificate، آدرس پنل را وارد کنید.', 'Enter the panel URL to regenerate its certificate.'));
                return;
            }
            let file = null;
            let backupId = '';
            if (source === 'upload') {
                file = document.getElementById('restore-upload-file').files?.[0];
                if (!file) {
                    alert(tx('فایل بکاپ را انتخاب کنید.', 'Choose a backup file.'));
                    return;
                }
            } else {
                backupId = document.getElementById('restore-server-backup').value;
                if (!backupId) {
                    alert(tx('یک بکاپ موجود در سرور را انتخاب کنید.', 'Choose a server backup.'));
                    return;
                }
            }
            if (!confirm(tx(
                'اطلاعات فعلی با محتوای بکاپ جایگزین می‌شود و پنل Restart خواهد شد. Snapshot بازگشت ساخته می‌شود. ادامه می‌دهید؟',
                'Current panel data will be replaced and the panel will restart. A rollback snapshot will be created. Continue?'
            ))) return;
            const button = event.target.querySelector('button[type="submit"]');
            button.disabled = true;
            result.innerText = tx('در حال اعتبارسنجی، بازیابی و ساخت Snapshot بازگشت...', 'Validating and restoring the backup...');
            try {
                let response;
                if (source === 'upload') {
                    response = await fetch('/api/backup/restore-upload', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/octet-stream',
                            'X-Backup-Password-B64': utf8Base64(password),
                            'X-Backup-Filename': encodeURIComponent(file.name),
                            'X-New-Panel-Url': newPanelUrl,
                            'X-Regenerate-Certificate': regenerate ? '1' : '0'
                        },
                        body: file
                    });
                } else {
                    response = await fetch('/api/backup/restore', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            backup_id: backupId,
                            backup_password: password,
                            new_panel_url: newPanelUrl,
                            regenerate_certificate: regenerate
                        })
                    });
                }
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.error || 'Backup restore failed');
                result.innerText = `${tx('Restore موفق بود؛ پنل در حال Restart است.', 'Restore succeeded; the panel is restarting.')}\\n`
                    + `${tx('مسیر بازگشت', 'Rollback path')}: ${data.rollback_path || '-'}\\nSHA-256: ${data.sha256 || '-'}`;
                document.getElementById('restore-password').value = '';
                setTimeout(() => window.location.reload(), 7000);
            } catch (error) {
                result.innerText = `${tx('Restore ناموفق بود', 'Restore failed')}: ${error.message || error}`;
                button.disabled = false;
            }
        });

        document.getElementById('form-panel-migration')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const result = document.getElementById('migration-result');
            const backupPassword = document.getElementById('migration-backup-password').value;
            if ((backupPassword || '').length < 8) {
                alert(tx('رمز بکاپ باید حداقل ۸ کاراکتر باشد.', 'Backup password must be at least 8 characters.'));
                return;
            }
            if (!confirm(tx(
                'ابتدا مقصد نصب و تست می‌شود، سپس آدرس جدید به نودها اعلام می‌شود. پنل فعلی برای Rollback روشن می‌ماند. ادامه می‌دهید؟',
                'The destination will be installed and verified first, then nodes will receive the new endpoint. The current panel stays online for rollback. Continue?'
            ))) return;
            const button = e.target.querySelector('button[type="submit"]');
            button.disabled = true;
            result.innerText = tx('در حال ساخت بکاپ، نصب مقصد و هماهنگ‌سازی نودها؛ این مرحله ممکن است چند دقیقه طول بکشد...', 'Building backup, installing destination, and coordinating nodes; this can take several minutes...');
            try {
                const response = await fetch('/api/migration/start', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        host: document.getElementById('migration-host').value.trim(),
                        port: parseInt(document.getElementById('migration-port').value || '22'),
                        username: document.getElementById('migration-username').value.trim(),
                        password: document.getElementById('migration-password').value,
                        new_panel_url: document.getElementById('migration-panel-url').value.trim(),
                        backup_password: backupPassword,
                        include_engines: document.getElementById('migration-include-engines').checked,
                        regenerate_certificate: document.getElementById('migration-regenerate-cert').checked
                    })
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.error || 'Migration failed');
                const handoff = data.node_handoff || {};
                result.innerText = `${tx('مهاجرت مقصد موفق بود', 'Destination migration succeeded')}\\n`
                    + `${tx('آدرس جدید', 'New URL')}: ${data.destination?.new_panel_url || '-'}\\n`
                    + `${tx('تأیید نودها', 'Node acknowledgements')}: ${handoff.acknowledged || 0}/${handoff.queued || 0}\\n`
                    + `SHA-256: ${data.backup?.sha256 || '-'}\\n`
                    + tx('پنل فعلی برای بازگشت اضطراری روشن نگه داشته شده است.', 'The current panel remains online for emergency rollback.');
                document.getElementById('migration-password').value = '';
                document.getElementById('migration-backup-password').value = '';
            } catch (error) {
                result.innerText = `${tx('مهاجرت ناموفق بود', 'Migration failed')}: ${error.message || error}`;
            } finally {
                button.disabled = false;
            }
        });

        document.getElementById('form-settings-display').addEventListener('submit', (e) => {
            e.preventDefault();
            const unit = document.getElementById('setting-traffic-unit').value;
            localStorage.setItem('trafficUnit', unit);
            alert(tx('تنظیمات نمایش ذخیره شد.', 'Display settings saved.'));
            updateDashboard(latestStatus);
            renderNodes(latestStatus?.nodes || {});
        });

        function renderEngineManager(engines) {
            const grid = document.getElementById('engine-manager-grid');
            if (!grid) return;
            const order = [
                'wireguard', 'amneziawg', 'xray', 'singbox', 'hysteria2', 'tuic',
                'masque', 'naiveproxy', 'shadowtls', 'gost', 'backhaul', 'rathole',
                'chisel', 'frp', 'brook', 'mieru', 'ssh', 'stunnel', 'rawsock',
                'aead', 'muxquantum'
            ];
            grid.innerHTML = order.map(engine => {
                const info = engines?.[engine] || {};
                const status = info.installed ? (info.enabled ? tx('آماده', 'Ready') : tx('غیرفعال', 'Disabled')) : tx('نصب نشده', 'Missing');
                const color = info.installed ? (info.enabled ? 'text-success' : 'text-warning') : 'text-danger';
                const update = engineUpdateStatuses[engine] || {};
                const sourceType = update.source_type || '';
                const githubReleaseEngines = new Set([
                    'amneziawg', 'xray', 'singbox', 'hysteria2', 'tuic', 'masque',
                    'naiveproxy', 'shadowtls', 'gost', 'backhaul', 'rathole',
                    'chisel', 'frp', 'brook', 'mieru'
                ]);
                const githubInstallable = githubReleaseEngines.has(engine) && (!sourceType || sourceType === 'github_release');
                const updateMarkup = sourceType
                    ? `<div class="${update.reachable ? (update.update_available ? 'text-warning' : 'text-success') : 'text-danger'}" style="margin-top:10px;font-size:12px;">
                        ${update.reachable
                            ? `${tx('نصب‌شده', 'Installed')}: ${esc(update.installed_version || info.version || '-')} | ${tx('آخرین', 'Latest')}: ${esc(update.latest_version || '-')} | ${update.update_available ? tx('آپدیت موجود است', 'Update available') : (update.up_to_date === true ? tx('به‌روز است', 'Up to date') : tx('مدیریت سیستمی', 'System managed'))}`
                            : `${tx('عدم دسترسی به منبع', 'Source unreachable')}: ${esc(update.error || '')}`}
                       </div>`
                    : '';
                return `
                    <div style="padding:14px; border:1px solid var(--border-card); border-radius:8px;">
                        <div class="flex-between mb-20">
                            <h4>${esc(engine)}</h4>
                            <span class="${color}">${status}</span>
                        </div>
                        <div class="tag-row">
                            <span class="tag-pill">${esc(info.version || '-')}</span>
                            <span class="tag-pill">${esc(info.repo || 'builtin')}</span>
                        </div>
                        ${updateMarkup}
                        <div class="flex-between gap-10 mt-20" style="justify-content:flex-start; flex-wrap:wrap;">
                            <button class="btn w-auto p-10 btn-cyan" onclick="checkEngineUpdates('${engine}')">${tx('بررسی آپدیت', 'Check update')}</button>
                            <button class="btn w-auto p-10" onclick="installEngine('${engine}')" ${githubInstallable && engine !== 'muxquantum' ? '' : 'disabled'}>${tx('آپدیت از گیت‌هاب', 'GitHub update')}</button>
                            <button class="btn w-auto p-10" onclick="controlEngine('${engine}', 'stop')" ${engine === 'muxquantum' ? 'disabled' : ''}>${tx('توقف', 'Stop')}</button>
                            <button class="btn w-auto p-10" onclick="controlEngine('${engine}', 'start')" ${engine === 'muxquantum' ? 'disabled' : ''}>${tx('ادامه', 'Resume')}</button>
                            <button class="btn w-auto p-10" onclick="controlEngine('${engine}', 'restart')" ${engine === 'muxquantum' ? 'disabled' : ''}>${tx('ریست', 'Restart')}</button>
                            <button class="btn w-auto p-10" onclick="healthCheckEngine('${engine}')">${tx('تست سلامت', 'Health test')}</button>
                        </div>
                        <input id="engine-upload-${engine}" type="file" class="form-input mt-20" accept=".zip,.gz,.tgz,.xz,.txz,.tar.gz,.tar.xz">
                        <button class="btn w-auto p-10 mt-20" onclick="uploadEngine('${engine}')" ${engine === 'muxquantum' ? 'disabled' : ''}>${tx('آپدیت دستی از فایل', 'Manual file update')}</button>
                        <small id="engine-health-${engine}" style="display:block; margin-top:10px; color: var(--text-secondary); line-height:1.7;"></small>
                    </div>
                `;
            }).join('');
        }

        async function checkEngineUpdates(engineType = '') {
            const summaryEl = document.getElementById('engine-update-summary');
            if (summaryEl) summaryEl.innerText = tx('در حال اتصال به GitHub و بررسی نسخه‌ها...', 'Connecting to GitHub and checking releases...');
            try {
                const suffix = engineType ? `?engine=${encodeURIComponent(engineType)}` : '';
                const res = await fetch(`/api/engines/check-updates${suffix}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) throw new Error(data.error || 'Update check failed');
                engineUpdateStatuses = { ...engineUpdateStatuses, ...(data.engines || {}) };
                renderEngineManager(latestStatus?.engines || {});
                const summary = data.summary || {};
                if (summaryEl) {
                    summaryEl.innerText = `${tx('قابل دسترس', 'Reachable')}: ${summary.reachable || 0}/${summary.total || 0} | `
                        + `${tx('آپدیت موجود', 'Updates available')}: ${summary.updates_available || 0} | `
                        + `${tx('مدیریت سیستمی', 'System managed')}: ${summary.system_managed || 0} | `
                        + `${tx('خطا', 'Failed')}: ${summary.failed || 0}`;
                }
            } catch (error) {
                if (summaryEl) {
                    summaryEl.className = 'text-danger mb-20';
                    summaryEl.innerText = `${tx('بررسی آپدیت ناموفق بود', 'Update check failed')}: ${error.message || error}`;
                }
            }
        }

        async function installEngine(engineType) {
            const version = 'latest';
            
            if (!confirm(tx(`آیا از نصب/بروزرسانی هسته ${engineType} نسخه ${version} اطمینان دارید؟\nاین عملیات ممکن است چند دقیقه زمان ببرد.`, `Are you sure you want to install/update ${engineType} to version ${version}?\nThis may take a few minutes.`))) return;
            
            const res = await fetch(`/api/engines/install`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ engine: engineType, version: version })
            });
            if (res.ok) {
                alert(tx('درخواست نصب/آپدیت هسته ثبت شد. وضعیت را از لاگ‌ها دنبال کنید.', 'Engine install/update queued. Check logs for progress.'));
            } else {
                alert(tx('خطا در نصب هسته.', 'Failed to install engine.'));
            }
        }

        async function controlEngine(engineType, action) {
            const statusEl = document.getElementById(`engine-health-${engineType}`);
            if (statusEl) {
                statusEl.className = '';
                statusEl.innerText = tx('در حال انجام عملیات هسته...', 'Running engine operation...');
            }
            const res = await fetch('/api/engines/control', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ engine: engineType, action })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                renderEngineManager(data.engines || {});
                const health = data.result?.health || {};
                const ok = health.healthy !== false;
                const detail = (health.results || []).map(r => `${r.path || '-'} ${r.executable ? 'OK' : 'NOEXEC'} ${r.version || r.error || ''}`.trim()).join(' | ');
                const refreshedStatusEl = document.getElementById(`engine-health-${engineType}`);
                if (refreshedStatusEl) {
                    refreshedStatusEl.className = ok ? 'text-success' : 'text-danger';
                    refreshedStatusEl.innerText = `${data.result?.message || tx('عملیات هسته انجام شد.', 'Engine operation completed.')}${detail ? ' | ' + detail : ''}`;
                }
                fetchStatus();
            } else {
                alert(data.error || tx('عملیات هسته ناموفق بود.', 'Engine operation failed.'));
                if (statusEl) {
                    statusEl.className = 'text-danger';
                    statusEl.innerText = data.error || tx('عملیات هسته ناموفق بود.', 'Engine operation failed.');
                }
            }
        }

        async function healthCheckEngine(engineType) {
            const statusEl = document.getElementById(`engine-health-${engineType}`);
            if (statusEl) statusEl.innerText = tx('در حال تست سلامت هسته...', 'Checking engine health...');
            const res = await fetch('/api/engines/health', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ engine: engineType })
            });
            const data = await res.json().catch(() => ({}));
            const ok = res.ok && data.healthy;
            const detail = (data.results || []).map(r => `${r.path || '-'} ${r.executable ? 'OK' : 'NOEXEC'} ${r.version || ''}`.trim()).join(' | ');
            if (statusEl) {
                statusEl.className = ok ? 'text-success' : 'text-danger';
                statusEl.innerText = `${ok ? tx('سالم', 'Healthy') : tx('نیازمند بررسی', 'Needs attention')}: ${data.message || data.error || ''}${detail ? ' | ' + detail : ''}`;
            } else {
                alert(data.message || data.error || tx('نتیجه تست سلامت دریافت نشد.', 'No health result returned.'));
            }
        }

        async function uploadEngine(engineType) {
            const input = document.getElementById(`engine-upload-${engineType}`);
            const file = input?.files?.[0];
            if (!file) {
                alert(tx('ابتدا فایل هسته را انتخاب کنید.', 'Choose an engine archive first.'));
                return;
            }
            const buffer = await file.arrayBuffer();
            let binary = '';
            const bytes = new Uint8Array(buffer);
            for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
            const content_base64 = btoa(binary);
            const res = await fetch('/api/engines/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ engine: engineType, filename: file.name, content_base64 })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                alert(tx('هسته با فایل دستی آپدیت شد.', 'Engine manually updated.'));
                renderEngineManager(data.engines || {});
                fetchStatus();
            } else {
                alert(data.error || tx('آپدیت دستی ناموفق بود.', 'Manual update failed.'));
            }
        }

        document.getElementById('form-settings-tls').addEventListener('submit', async (e) => {
            e.preventDefault();
            const cert = document.getElementById('setting-cert-path').value;
            const key = document.getElementById('setting-key-path').value;
            
            const res = await fetch('/api/settings/tls', {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ panel_tls: true, cert_path: cert, key_path: key })
            });
            if (res.ok) {
                alert(tx('تنظیمات SSL ثبت شد. جهت اعمال نهایی روی دکمه "اعمال تغییرات و ریستارت وب پنل" کلیک کنید.', 'SSL settings were saved. Click "Apply changes and restart panel" to apply them.'));
                fetchStatus();
            } else {
                const data = await res.json().catch(() => ({}));
                alert(`${tx('خطا در ثبت تنظیمات SSL', 'Could not save SSL settings')}: ${data.error || tx('مسیر گواهی و کلید را بررسی کنید.', 'Check certificate and key paths.')}`);
            }
        });

        document.getElementById('form-settings-security').addEventListener('submit', async (e) => {
            e.preventDefault();
            const biometricRequested = document.getElementById('setting-biometric').checked;
            if (biometricRequested && !window.PublicKeyCredential) {
                alert(tx('این مرورگر یا محیط فعلی از WebAuthn/بایومتریک پشتیبانی نمی‌کند.', 'This browser/environment does not support WebAuthn/biometric login.'));
                return;
            }
            const res = await fetch('/api/settings/security', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    two_factor_enabled: document.getElementById('setting-two-factor').checked,
                    biometric_enabled: biometricRequested
                })
            });
            if (res.ok) {
                const data = await res.json();
                const box = document.getElementById('totp-secret-box');
                if (data.two_factor_secret) {
                    box.innerText = `TOTP Secret: ${data.two_factor_secret}`;
                    box.classList.remove('hidden');
                } else {
                    box.classList.add('hidden');
                }
                alert('Security options saved.');
                fetchStatus();
            } else {
                alert('Security settings failed.');
            }
        });

        document.getElementById('form-local-cert').addEventListener('submit', async (e) => {
            e.preventDefault();
            const host = document.getElementById('local-cert-host').value.trim();
            const res = await fetch('/api/certificates/local', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ host })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                document.getElementById('setting-panel-tls').checked = true;
                document.getElementById('setting-cert-path').value = data.cert_path || '';
                document.getElementById('setting-key-path').value = data.key_path || '';
                alert(tx('Certificate محلی ساخته و در تنظیمات اعمال شد. برای فعال شدن HTTPS پنل را ریستارت کنید.', 'Local certificate was generated and applied. Restart the panel to enable HTTPS.'));
                fetchStatus();
            } else {
                alert(`${tx('خطا در ساخت Certificate محلی', 'Local certificate error')}: ${data.error || tx('ناشناخته', 'Unknown')}`);
            }
        });

        function toggleAcmeDnsFields() {
            const challenge = document.getElementById('acme-challenge')?.value || 'http-01';
            const wildcard = !!document.getElementById('acme-wildcard')?.checked;
            if (wildcard && challenge !== 'dns-01') document.getElementById('acme-challenge').value = 'dns-01';
            document.getElementById('acme-dns-fields')?.classList.toggle(
                'hidden',
                (document.getElementById('acme-challenge')?.value || challenge) !== 'dns-01'
            );
        }

        document.getElementById('form-acme-cert').addEventListener('submit', async (e) => {
            e.preventDefault();
            const dom = document.getElementById('acme-domain').value;
            const mail = document.getElementById('acme-email').value;
            const challenge = document.getElementById('acme-challenge').value;
            const wildcard = document.getElementById('acme-wildcard').checked;
            const dnsProvider = document.getElementById('acme-dns-provider').value;
            const dnsCredentials = document.getElementById('acme-dns-credentials').value;
            const dnsPropagationSeconds = parseInt(document.getElementById('acme-dns-propagation').value || '30');
            
            alert(tx('دریافت گواهی ممکن است تا ۱ دقیقه طول بکشد. لطفا صبور باشید...', 'Certificate issuance can take up to 1 minute. Please wait...'));
            
            try {
                const res = await fetch('/api/certificates/generate', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        domain: dom,
                        email: mail,
                        challenge,
                        wildcard,
                        dns_provider: dnsProvider,
                        dns_credentials: dnsCredentials,
                        dns_propagation_seconds: dnsPropagationSeconds
                    })
                });
                if (res.ok) {
                    document.getElementById('acme-dns-credentials').value = '';
                    alert(tx("گواهینامه SSL با موفقیت از Let's Encrypt دریافت شد. برای بارگذاری گواهی جدید پنل را ریستارت کنید.", "SSL certificate was issued by Let's Encrypt. Restart the panel to load the new certificate."));
                    fetchStatus();
                } else {
                    const data = await res.json();
                    alert(`${tx('خطا در صدور گواهینامه', 'Certificate issuance error')}: ${data.error || tx('ناشناخته', 'Unknown')}`);
                }
            } catch (err) {
                alert(tx('خطا در ارتباط با سرور.', 'Could not connect to the server.'));
            }
        });

        async function restartPanel() {
            if (!confirm(tx('آیا مایل به ریستارت پنل جهت اعمال تغییرات SSL هستید؟ در حین ریستارت پنل برای لحظاتی از دسترس خارج می‌شود.', 'Restart the panel to apply SSL changes? The panel may be unavailable for a short time.'))) return;
            try {
                await fetch('/api/settings/restart', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                alert(tx('پنل در حال ریستارت است. صفحه را پس از ۱۰ ثانیه مجددا بارگذاری کنید.', 'The panel is restarting. Reload the page after 10 seconds.'));
                logout(true);
            } catch (err) {
                // Ignore as server exits
                alert(tx('درخواست ریستارت ارسال شد. صفحه را رفرش کنید.', 'Restart request sent. Refresh the page.'));
                logout(true);
            }
        }

        function exportLogsCSV() {
            window.location.href = `/api/logs/csv?token=${token}`;
        }

        function openModal(id) {
            document.getElementById(id).style.display = 'flex';
        }
        function closeModal(id) {
            document.getElementById(id).style.display = 'none';
        }

        async function cleanupLegacyBrowserCache() {
            try {
                if ('serviceWorker' in navigator) {
                    const regs = await navigator.serviceWorker.getRegistrations();
                    await Promise.all(regs.map(reg => reg.unregister()));
                }
                if ('caches' in window) {
                    const keys = await caches.keys();
                    await Promise.all(keys.filter(key => key.startsWith('p00rija-')).map(key => caches.delete(key)));
                }
            } catch (err) {
                console.warn('Legacy browser cache cleanup skipped:', err);
            }
        }
        cleanupLegacyBrowserCache();

        fetchSettings();
        applyTheme();

        async function runLiveRefreshTick() {
            if (!token || autoRefreshInFlight) return;
            autoRefreshInFlight = true;
            try {
                await fetchStatus({ forceChartRedraw: currentTab === 'dashboard' });
            } finally {
                autoRefreshInFlight = false;
            }
        }

        function setAutoRefresh() {
            let val = parseInt(document.getElementById("auto-refresh-select").value);
            if (autoRefreshTimer) clearInterval(autoRefreshTimer);
            autoRefreshTimer = null;
            if (val > 0) {
                runLiveRefreshTick();
                autoRefreshTimer = setInterval(runLiveRefreshTick, val * 1000);
            }
        }
    </script>
</body>
</html>
"""
