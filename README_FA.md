# P00RIJA TUNNEL

![لوگوی P00RIJA TUNNEL](assets/p00rija-logo.svg)

**نسخه:** 1.3.0  
**لایسنس:** GPL v3  
**توسعه‌دهنده:** [Poorija](https://github.com/Poorija)  
**ایمیل:** mohammadmahdi.farhadianfard@gmail.com

[English](README.md)

P00RIJA TUNNEL یک پنل Docker-first برای مدیریت تانل معکوس چندنودی است. پنل، نودهای داخلی و خارجی را ثبت و کنترل می‌کند، تانل‌ها را با پروفایل‌های آماده یا شخصی می‌سازد، موتورهای تانلینگ را به صورت آفلاین در اختیار نودها می‌گذارد، و وضعیت منابع، ترافیک، سشن‌ها و لاگ‌ها را زنده نمایش می‌دهد.

در دیتابیس تازه، ورود اضطراری پیش‌فرض `admin` / `admin` است. اسکریپت نصب پنل رمز جدید را از کاربر می‌پرسد؛ روی سرور واقعی حتماً رمز پیش‌فرض را فوراً تغییر دهید.

## نصب آسان

نصب انتخابی پنل یا نود:

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh
```

اسکریپت اصلی می‌تواند پنل را نصب/آپدیت کند، نود را نصب/آپدیت کند، یا ابتدا پنل و سپس نود را اجرا کند. نصب جداگانه پنل و نود با اسکریپت‌های مستقل هم همچنان وجود دارد.

نصب‌کننده پنل و نود با زبان انگلیسی و محیط `whiptail/dialog` اجرا می‌شود. در ابتدای نصب، IP سرور را تشخیص می‌دهد، محلی/private یا عمومی بودن آن را نشان می‌دهد، IP خروجی اینترنت و کشور آن را پیدا می‌کند، و بر اساس آن mirror ایران یا repository رسمی global را پیشنهاد می‌دهد. اگر `whiptail` یا `dialog` نصب نباشد، بعد از انتخاب لوکیشن و تنظیم mirror مناسب نصب می‌شود.

اگر این دستورها مستقیماً از GitHub اجرا شوند و کنار اسکریپت، پکیج کامل پروژه وجود نداشته باشد، نصب‌کننده به صورت خودکار آرشیو کامل پروژه را در `/opt/p00rija-install` دانلود می‌کند و از همان‌جا ادامه می‌دهد. بنابراین فونت‌ها، engineهای آفلاین، فایل Docker و اسکریپت‌های کمکی در زمان نصب در دسترس هستند.

نصب مستقیم پنل:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install-panel.sh)"
```

نصب مستقیم نود:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install-node.sh)"
```

نصب از سورس:

```bash
git clone https://github.com/Poorija/P00RIJA-TUNNEL.git
cd P00RIJA-TUNNEL
sudo bash install.sh
```

اگر فایل `/opt/p00rija/panel/p00rija_db.json` از قبل وجود داشته باشد، `install-panel.sh` حالت Update را پیشنهاد می‌دهد. در این حالت دیتابیس، certificateها، نودها، تانل‌ها، اکانت ادمین و تنظیمات فعلی حفظ می‌شود و فقط کد جدید، فونت‌ها، engineها، image و کانتینر پنل به‌روزرسانی می‌شوند.

بعد از نصب، دستور محلی سرور می‌تواند برنامه را از GitHub یا از فایل محلی `.zip` / `.tar.gz` آپدیت کند:

```bash
sudo p00rija update
sudo p00rija panel update
sudo p00rija node update
```

اگر پنل یا نود از قبل نصب باشد، updater هشدار می‌دهد که اطلاعات فعلی پاک نمی‌شود و فقط کدها، engine/fontهای همراه، image داکر و کانتینر در حال اجرا آپدیت می‌شوند؛ مگر این که کاربر صراحتاً نصب تازه را انتخاب کند.

نصب از بسته آفلاین:

```bash
tar -xzf p00rija-offline-bundle.tar.gz
cd P00RIJA-TUNNEL
sudo bash install-panel.sh
# یا:
sudo bash install-node.sh
```

## قابلیت‌ها

- پنل امن HTTPS با ساخت certificate محلی/IP، دریافت Let's Encrypt برای دامنه، یا استفاده از certificate آماده.
- اجرای پنل با Docker bridge و اجرای پیشنهادی نودهای واقعی با host network؛ در این حالت Docker درگیر publish تک‌تک پورت‌های تانل نمی‌شود و listenerها مستقیماً توسط کرنل لینوکس روی شبکه سرور مدیریت می‌شوند. حالت Docker bridge هم به‌عنوان fallback ایزوله با رنج کوچک/سفارشی باقی مانده است.
- تشخیص موقعیت سرور ایران/خارج و تنظیم mirrorهای Docker برای ایران یا mirror رسمی برای خارج.
- اگر لوکیشن ایران انتخاب شود، قبل از نصب وابستگی‌ها mirrorهای package manager و Docker برای ایران تنظیم می‌شوند.
- نصب خودکار Docker، فعال‌سازی BBR و کنترل غیرفعال‌سازی IPv6 از پنل.
- اجرای کانتینر نود با محدودیت CPU، RAM، PID، file descriptor و سقف worker برای جلوگیری از لود runaway روی سرورهای کوچک.
- مدیریت نودهای داخلی و خارجی با API token، امضای درخواست، تگ‌های رنگی، ping زنده با واحد ms و نشانگر واضح قطع/توقف.
- داشبورد زنده که فقط همان کارت‌ها و نمودارهای لازم را طبق Refresh Time به‌روزرسانی می‌کند.
- رفرش زنده منابع سرور، ترافیک، تردها، کانکشن‌ها و مانیتورینگ بدون رفرش کل صفحه.
- مدیریت تانل‌ها با Easy Mode، حالت پیشرفته، دسته‌بندی تانل‌ها، تگ‌گذاری رنگی، توقف، ادامه، ویرایش و مشاهده کانفیگ موتور.
- تست هوشمند بین دو نود انتخابی و پیشنهاد پروفایل مناسب.
- دکمه سریع «بزن بریم فضا !» برای ساخت تانل ساده، سبک و سریع بین دو نود انتخابی.
- پروفایل‌ها و موتورهای Builtin، GOST، Backhaul، Rathole، Chisel، FRP، Xray، Hysteria2، sing-box، TUIC، NaiveProxy، ShadowTLS، Brook، Mieru و پروفایل‌های ترکیبی Mux/Quantum.
- پشتیبانی از بسته موتورهای آفلاین با `download_engines.py` و پوشه `engines/` تا نصب پنل و نود بدون دسترسی به GitHub هم ممکن باشد.
- اتصال SSH به نود انتخابی، اجرای دستور، و ذخیره رمزنگاری‌شده مشخصات اتصال در پنل.
- مانیتورینگ runtime برای سشن‌های فعال تانل، پروسس‌ها، تردها، مصرف RSS، منابع نودها و وضعیت Docker.
- پاک‌سازی سشن‌های idle، پاک‌سازی RAM/GC و بهینه‌سازی کامل‌تر منابع از داخل مانیتورینگ.
- زبان فارسی/انگلیسی، فونت پیش‌فرض Vazirmatn، تم‌های مختلف و پشتیبانی PWA.
- امنیت ورود با TOTP دو مرحله‌ای و Quick Unlock بایومتریک مرورگر.

## موتورهای تانلینگ و بسته آفلاین

برای ساخت بسته آفلاین:

```bash
python3 download_engines.py --bundle p00rija-offline-bundle.tar.gz
```

این بسته شامل فایل‌های برنامه، اسکریپت‌های نصب، `engines/manifest.json`، باینری موتورهای دانلودشده و آرشیوهای لازم است. هنگام ساخت Docker image، موتورهای موجود در `engines/` داخل `/usr/local/bin` قرار می‌گیرند و در زمان اجرا نیازی به دریافت موتور از GitHub نیست.

پوشه `fonts/` هم بخشی از بسته آفلاین است و فونت‌های پنل، از جمله Vazirmatn، بدون نیاز به CDN یا اینترنت داخل Docker image کپی می‌شوند.

## روند راه‌اندازی

1. پنل را نصب کنید و URL امن HTTPS نمایش‌داده‌شده توسط installer را باز کنید.
2. نودهای داخلی و خارجی را از بخش مدیریت سرورها ثبت کنید.
3. توکن و private key تولیدشده برای هر نود را در نصب نود وارد کنید.
4. در مدیریت تانل‌ها، از Easy Mode، پروفایل آماده، پیشنهاد تست هوشمند یا پروفایل شخصی استفاده کنید.
5. Port Forwarding را اضافه کنید و سپس ترافیک، سشن‌ها، منابع، لاگ‌ها و وضعیت اتصال را زنده بررسی کنید.
6. در صورت نیاز تانل را متوقف، ادامه، ویرایش یا کانفیگ موتور آن را بررسی کنید.

## دستور مدیریت

```bash
sudo Pooriya-tunnel
```

برای start، stop، restart، مشاهده لاگ، بهینه‌سازی شبکه لینوکس و uninstall.

## دستورهای سطح سرور

بعد از نصب پنل یا نود، دستور زیر هم روی سرور نصب می‌شود و مستقل از ورود به کانتینر کار می‌کند:

```bash
sudo p00rija status
sudo p00rija panel restart
sudo p00rija panel logs
sudo p00rija panel reset-admin
sudo p00rija node restart
sudo p00rija node logs
sudo p00rija uninstall
sudo p00rija purge
```

`uninstall` کانتینرها، سرویس‌ها و imageهای برنامه را حذف می‌کند ولی تنظیمات داخل `/opt/p00rija` را نگه می‌دارد.  
`purge` کل برنامه، کانتینرها، imageها، تنظیمات، certificateها، موتورهای آفلاین و دستورهای CLI را حذف می‌کند.

## بررسی قبل از انتشار

```bash
python3 -m py_compile P00RIJA.py download_engines.py
bash -n install.sh install-panel.sh install-node.sh Pooriya-tunnel.sh
docker build --platform linux/amd64 -t p00rija-tunnel:1.3.0 .
```

## لایسنس

GPL v3. فایل [LICENSE](LICENSE) را ببینید.
