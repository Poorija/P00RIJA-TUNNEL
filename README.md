<div align="center">

<img src="assets/p00rija-logo.svg" width="130" alt="P00RIJA TUNNEL logo">

# P00RIJA TUNNEL

**Multi-node reverse-tunneling control panel — Docker-first, bilingual, battle-ready.**

پنل مدیریت تانل معکوس چندنودی — Docker-first، دوزبانه و آماده عملیات واقعی

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/Poorija/P00RIJA-TUNNEL)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-red.svg)](https://github.com/Poorija/P00RIJA-TUNNEL/blob/main/LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20docker-2496ED.svg)](https://github.com/Poorija/P00RIJA-TUNNEL)
[![Author](https://img.shields.io/badge/author-p00rija-8B5CF6.svg)](https://github.com/Poorija)

**[English](#-english) · [فارسی](#-فارسی)**

</div>

---

## 🇬🇧 English

P00RIJA TUNNEL is a Docker-first, multi-node **reverse tunneling** control panel. It manages internal and external nodes, creates and monitors tunnel links, ships 20+ bundled tunneling engines, and exposes live operational controls from one bilingual (FA/EN) web panel.

### ✨ Highlights (v2.0.0)

- 🛰️ **Multi-node fleet** — internal, external and panel-as-node management with live status, SSH terminal, remote updates and signed node requests
- 🧰 **20+ engines bundled** — Xray, sing-box, Hysteria2, TUIC, NaiveProxy, Cloak, ShadowTLS, Mieru, Brook, AmneziaWG, GOST, FRP, Rathole, Chisel, Backhaul, MASQUE, Phormal, Hedioum and more, with one-click **update-all-cores** and GitHub rate-limit-aware update checks
- 🛡️ **Anti-DPI transport profiles** — REALITY, XHTTP, HTTPUpgrade, WebSocket/TLS, HTTP/2, HTTP/3/QUIC, Cloak camouflage, AnyTLS, MASQUE CONNECT-UDP, AmneziaWG paths, plus adaptive Mux/Bonding hybrid modes
- 🔐 **Hardened security** — verified TLS on all panel/node channels, fail-closed signature checks, PBKDF2 credentials, TOTP 2FA, encrypted SSH vault, atomic encrypted backups with rollback
- 🔄 **Panel self-update** — check GitHub for new releases straight from the panel and update through the root host agent
- 📈 **Live monitoring** — traffic, CPU/RAM pressure, sessions, smart tunnel guardian with actionable recommendations
- 💾 **Backup & migration** — encrypted full-state backups, atomic restore, host-to-host migration
- 🇮🇷 **Iran-ready** — IranServer/Shatel APT mirrors, Docker registry mirrors with probe-based ranking, offline engine bundles

### 🚀 Install

Interactive installer (recommended):

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh
```

Panel only / node only:

```bash
sudo bash install.sh --panel   # control panel host
sudo bash install.sh --node    # tunnel node host
```

Pin to an exact tag or commit for reproducible installs:

```bash
sudo P00RIJA_SOURCE_REF=v2.0.0 bash install.sh
```

Day-2 management: `sudo p00rija {start|stop|restart|logs|update|status|uninstall}`.

> Fresh databases start with an emergency `admin`/`admin` login — the installer forces a new password, and you should still rotate credentials immediately on any real server.

### 🔒 Security notes

- Node→panel traffic uses **verified TLS** (pin your CA via `panel_ca_path`); insecure mode requires an explicit opt-in flag.
- Report vulnerabilities to **p00rija@tutamail.com** — see [SECURITY.md](SECURITY.md).

### 📄 License

GNU **AGPL-3.0** — network-server copyleft. See [LICENSE](LICENSE) or the [canonical text](https://opensource.org/licenses/AGPL-3.0).

### 💜 Support the project

TON (Telegram) wallet: `UQCEgGxRZ5A101w6RBNLwHhnva5EdK3kyDsFQcxni35DlCJf` — also available as a QR code inside **Panel → About**.

**Contact:** [p00rija@tutamail.com](mailto:p00rija@tutamail.com) · [GitHub](https://github.com/Poorija)

---

## 🇮🇷 فارسی

P00RIJA TUNNEL یک پنل مدیریت **تانل معکوس** چندنودی و Docker-first است؛ نودهای داخلی و خارجی را مدیریت می‌کند، لینک‌های تانل را می‌سازد و پایش می‌کند، بیش از ۲۰ هسته تانلینگ را همراه خود دارد و همه کنترل‌های عملیاتی را از یک پنل وب دوزبانه در اختیارتان می‌گذارد.

### ✨ امکانات کلیدی (نسخه 2.0.0)

- 🛰️ **مدیریت ناوگان چندنودی** — نود داخلی، خارجی و پنل‌به‌عنوان‌نود با وضعیت زنده، ترمینال SSH، آپدیت از راه دور و درخواست‌های امضاشده
- 🧰 **بیش از ۲۰ هسته همراه پنل** — Xray، sing-box، Hysteria2، TUIC، NaiveProxy، Cloak، ShadowTLS، Mieru، Brook، AmneziaWG، GOST، FRP، Rathole، Chisel، Backhaul، MASQUE، Phormal، Hedioum و… با دکمه **آپدیت همه هسته‌ها** و بررسی آپدیت مقاوم به محدودیت گیت‌هاب
- 🛡️ **پروفایل‌های ضد DPI** — REALITY، XHTTP، HTTPUpgrade، WebSocket/TLS، HTTP/2، HTTP/3/QUIC، camouflage کلوک، AnyTLS، MASQUE CONNECT-UDP، مسیرهای AmneziaWG و حالت‌های ترکیبی Mux/Bonding
- 🔐 **امنیت سخت‌گیرانه** — TLS تأییدشده در تمام کانال‌های پنل/نود، امضای fail-closed، رمز PBKDF2، ورود دومرحله‌ای TOTP، والط رمزشده SSH، بکاپ رمزشده اتمیک با rollback
- 🔄 **آپدیت خود پنل** — بررسی ریلیزهای جدید گیت‌هاب از داخل پنل و آپدیت از طریق ایجنت روت سرور
- 📈 **مانیتورینگ زنده** — ترافیک، فشار CPU/RAM، سشن‌ها و نگهبان هوشمند تانل‌ها با پیشنهاد عملیاتی
- 💾 **بکاپ و مهاجرت** — بکاپ کامل رمزشده، بازیابی اتمیک و مهاجرت میزبان‌به‌میزبان
- 🇮🇷 **آماده ایران** — میرورهای IranServer/Shatel، میرورهای رجیستری Docker با رتبه‌بندی پروب‌محور و بسته آفلاین هسته‌ها

### 🚀 نصب

نصب‌کننده تعاملی (پیشنهادی):

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh
```

فقط پنل / فقط نود:

```bash
sudo bash install.sh --panel   # سرور پنل مدیریتی
sudo bash install.sh --node    # سرور نود تانل
```

برای نصب قابل تکرار روی نسخه دقیق پین کنید:

```bash
sudo P00RIJA_SOURCE_REF=v2.0.0 bash install.sh
```

مدیریت روزمره: `sudo p00rija {start|stop|restart|logs|update|status|uninstall}`

> دیتابیس تازه با ورود اضطراری `admin`/`admin` شروع می‌شود — نصب‌کننده رمز جدید اجباری می‌گیرد، اما در سرور واقعی بلافاصله اطلاعات ورود را عوض کنید.

### 🔒 نکات امنیتی

- ترافیک نود→پنل با **TLS تأییدشده** است (می‌توانید CA خود را با `panel_ca_path` پین کنید)؛ حالت ناامن فقط با فلگ صریح فعال می‌شود.
- گزارش آسیب‌پذیری به **p00rija@tutamail.com** — [SECURITY.md](SECURITY.md)

### 📄 لایسنس

**AGPL-3.0** — کپی‌لفت مخصوص نرم‌افزار سرورِ تحت شبکه. متن کامل: [LICENSE](LICENSE)

### 💜 حمایت از پروژه

کیف پول TON (تلگرام): `UQCEgGxRZ5A101w6RBNLwHhnva5EdK3kyDsFQcxni35DlCJf` — QR آن هم داخل **پنل ← درباره من** موجود است.

**تماس:** [p00rija@tutamail.com](mailto:p00rija@tutamail.com) · [گیت‌هاب](https://github.com/Poorija)

---

<div align="center">
<sub>Built with ❤️ by <a href="https://github.com/Poorija">p00rija</a> · AGPL-3.0</sub>
</div>
