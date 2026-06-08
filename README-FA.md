# P00RIJA TUNNEL

این فایل نسخه فارسی کوتاه README است. نسخه کامل فارسی در [README_FA.md](README_FA.md) و نسخه انگلیسی در [README.md](README.md) قرار دارد.

## معرفی

P00RIJA TUNNEL یک پنل Docker-first برای مدیریت تانل معکوس چندنودی است. پنل از نودهای داخلی و خارجی، پروفایل‌های آماده و شخصی، موتورهای تانلینگ آفلاین، مانیتورینگ زنده، TLS/SSL، تگ‌گذاری، کنترل SSH و بهینه‌سازی منابع پشتیبانی می‌کند.

## نصب آسان

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh
```

نصب مستقیم پنل:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install-panel.sh)"
```

نصب مستقیم نود:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install-node.sh)"
```

در اجرای مستقیم از GitHub، اگر پکیج کامل پروژه کنار اسکریپت نباشد، نصب‌کننده خودش آرشیو کامل پروژه را در `/opt/p00rija-install` دانلود می‌کند تا فونت‌ها، engineهای آفلاین و فایل‌های Docker هم موجود باشند. نصب پنل روی پنل موجود، حالت Update دارد و اطلاعات فعلی را نگه می‌دارد.

اسکریپت اصلی `install.sh` هم پنل و هم نود را مدیریت می‌کند و نصب جداگانه با `install-panel.sh` و `install-node.sh` هم باقی است. نصب‌کننده IP، محلی/private بودن شبکه، IP خروجی اینترنت و کشور سرور را نشان می‌دهد و بر اساس آن mirror ایران یا repository رسمی را پیشنهاد می‌کند.

بعد از نصب:

```bash
sudo p00rija update
sudo p00rija panel update
sudo p00rija node update
```

این دستور از GitHub یا فایل محلی `.zip` / `.tar.gz` آپدیت می‌کند و در حالت Update اطلاعات فعلی پنل/نود را نگه می‌دارد.

## قابلیت‌های اصلی

- پنل HTTPS با certificate محلی، certificate آماده یا Let's Encrypt.
- Docker bridge برای پنل و host network پیشنهادی برای نودهای واقعی؛ Docker دیگر درگیر publish تک‌تک پورت‌های تانل نمی‌شود و حالت bridge با رنج کوچک/سفارشی فقط fallback است.
- تشخیص ایران/خارج و انتخاب mirror مناسب Docker.
- مدیریت نودها با توکن، امضای درخواست، ping زنده، وضعیت منابع، ترافیک و تردها.
- محدودیت CPU، RAM، PID، file descriptor و worker برای جلوگیری از لود runaway کانتینر نود.
- مدیریت تانل با Easy Mode، پروفایل‌های آماده، تست هوشمند، دکمه «بزن بریم فضا !»، توقف/ادامه/ویرایش و دسته‌بندی تانل‌ها.
- موتورهای Builtin، GOST، Backhaul، Rathole، Chisel، FRP، Xray، Hysteria2، sing-box، TUIC، NaiveProxy، ShadowTLS، Brook، Mieru و پروفایل‌های Mux/Quantum.
- بسته آفلاین موتورهای تانلینگ با `download_engines.py`.
- فونت‌های آفلاین داخل `fonts/`، از جمله Vazirmatn، بدون نیاز به CDN.
- مانیتورینگ سشن‌ها، پروسس‌ها، منابع نودها، Docker و ابزارهای پاک‌سازی و بهینه‌سازی منابع.
- زبان فارسی/انگلیسی، فونت Vazirmatn، چند تم، TOTP و بایومتریک مرورگر.

## دستورهای سرور

```bash
sudo p00rija status
sudo p00rija panel reset-admin
sudo p00rija panel restart
sudo p00rija node logs
sudo p00rija uninstall
sudo p00rija purge
```

`uninstall` تنظیمات را نگه می‌دارد، اما `purge` همه فایل‌ها و تنظیمات برنامه را حذف می‌کند.

## بررسی سریع

```bash
python3 -m py_compile P00RIJA.py download_engines.py
bash -n install.sh install-panel.sh install-node.sh Pooriya-tunnel.sh
```
