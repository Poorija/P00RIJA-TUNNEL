# P00RIJA TUNNEL

![لوگوی P00RIJA TUNNEL](assets/p00rija-logo.svg)

**نسخه:** 1.9.95  
**لایسنس:** GPL v3  
**توسعه‌دهنده:** [Poorija](https://github.com/Poorija)  
**ایمیل:** mohammadmahdi.farhadianfard@gmail.com

[English](README.md)

P00RIJA TUNNEL یک پنل Docker-first برای مدیریت تانل معکوس چندنودی است. پنل، نودهای داخلی و خارجی را ثبت و کنترل می‌کند، تانل‌ها را با پروفایل‌های آماده یا شخصی می‌سازد، موتورهای تانلینگ را همراه خود ارائه می‌دهد، و وضعیت منابع، ترافیک، سشن‌ها و لاگ‌ها را زنده نمایش می‌دهد.

در دیتابیس تازه، ورود اضطراری پیش‌فرض `admin` / `admin` است. اسکریپت نصب پنل رمز جدید را از کاربر می‌پرسد؛ روی سرور واقعی حتماً رمز پیش‌فرض را فوراً تغییر دهید.

پنل برای استفاده عملیاتی واقعی طراحی شده است: مدیریت certificate، ثبت نود، کنترل SSH، ساخت تانل، تست سرعت، مدیریت هسته‌ها، بکاپ و restore، مهاجرت هاست، مانیتورینگ، تنظیم معماری انتقال دیتا و مدیریت موبایل‌پسند همگی از داخل رابط وب انجام می‌شوند.

ابزارهای انتقال و پروفایل شامل Reverse TCP کلاسیک، WebSocket/TLS، HTTP/2، HTTP/3/QUIC، REALITY، XHTTP، ShadowTLS، AnyTLS، MASQUE CONNECT-UDP، مسیرهای AmneziaWG/WireGuard، Multiplexing اشتراکی، Bonding تطبیقی و حالت Hybrid Mux/Bonding هستند. فعال بودن هر قابلیت به باینری‌های نصب‌شده و توانایی نودهای انتخابی وابسته است.

## نصب آسان

نصب انتخابی پنل یا نود:

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh
```

این روش پیشنهاد اصلی است. اگر فقط `install.sh` موجود باشد، اسکریپت پیش از ادامه کل آرشیو branch `main` را از `https://github.com/Poorija/P00RIJA-TUNNEL` در `/opt/p00rija-install` دریافت می‌کند تا رابط گرافیکی ترمینال، فایل‌های Docker، فونت‌ها، باینری‌های آماده‌ی هسته‌ها و نصب‌کننده‌های پنل/نود در دسترس باشند. آدرس Raw و آرشیو مخزن در تاریخ ۲۴ ژوئن ۲۰۲۶ بررسی شدند.

نصب مستقیم پنل:

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh --panel
```

نصب مستقیم نود:

```bash
curl -fsSL https://raw.githubusercontent.com/Poorija/P00RIJA-TUNNEL/main/install.sh -o install.sh
sudo bash install.sh --node
```

نصب از سورس:

```bash
git clone https://github.com/Poorija/P00RIJA-TUNNEL.git
cd P00RIJA-TUNNEL
sudo bash install.sh
```

نصب از بسته آفلاین:

```bash
tar -xzf p00rija-offline-bundle.tar.gz
cd P00RIJA-TUNNEL
sudo bash install-panel.sh
# یا:
sudo bash install-node.sh
```

## قابلیت‌های پنل

### نصب، کنترل هاست و استقرار

- اینستالر یکپارچه و گرافیکی ترمینال برای نصب پنل، نود یا نصب ترکیبی، با منوی whiptail، حالت متنی جایگزین، انتخاب mirror ایران/خارج، نصب Docker، تنظیم BBR و دریافت خودکار بسته کامل از GitHub.
- استقرار Docker-first برای پنل و نودها، همراه با فونت‌ها، assets، ماژول‌های core و باینری‌های آماده‌ی engine داخل image اجرا.
- Host Agent میزبان برای تغییر امن پورت وب/API پنل، عملیات certificate و ساخت سرور پنل به‌عنوان یک نود داخلی واقعی بدون قرار دادن Docker socket داخل کانتینر وب.
- مدیریت موقعیت ایران/خارج؛ در حالت ایران، mirrorهای APT و Docker مناسب برای سرورهای ایران استفاده می‌شود.
- ابزار مدیریتی `sudo Pooriya-tunnel` برای start، stop، restart، logs، update، بهینه‌سازی شبکه و uninstall.

### امنیت، دسترسی و Certificate

- پنل HTTPS با certificate محلی/IP، certificate آماده، Let's Encrypt HTTP-01 و جریان‌های سازگار با DNS-01 برای دامنه و wildcard.
- مسیر مدیریت رندوم اختیاری با Cookie امضاشده و HttpOnly؛ مسیرهای عادی پنل/Login می‌توانند 404 بدهند، در حالی که API نودها پایدار می‌ماند.
- ورود امن مدیر با TOTP دو مرحله‌ای و Quick Unlock بایومتریک مرورگر.
- درخواست‌های امضاشده نود، enrollment token، private key اختیاری برای نود و vault رمزگذاری‌شده برای اطلاعات SSH.
- امکان نگهداری certificate، key، token، SSH vault و هویت نودها داخل بکاپ رمزگذاری‌شده و restore روی هاست دیگر.

### مدیریت نودها

- مدیریت نودهای داخلی، خارجی و خود سرور پنل به‌عنوان نود از یک بخش واحد.
- وضعیت زنده نود، ping، ترافیک، فشار CPU/RAM، وضعیت Docker/runtime، snapshot منابع، tag، role و نشانگرهای اتصال.
- اتصال SSH به نود انتخابی، ذخیره امن credentials، اجرای دستور و کنترل عملیاتی از داخل پنل.
- بررسی سازگاری و نسخه نودها در وضعیت‌های به‌روز، قدیمی، اختلاف build، جلوتر از پنل و ناسازگار.
- ترتیب نمایش زنده نودها، tagهای رنگی و ذخیره پایدار ترتیب بدون نیاز به Refresh.

### مدیریت تانل و Port Forward

- ساخت تانل با Easy Mode و Advanced Mode.
- دو جهت تانل: External to Internal و Internal to External.
- انتخاب خودکار و بک‌اندی جفت Bridge/Sync آزاد، همراه با امکان override دستی پورت و رد کردن تداخل روی هر دو نود انتخاب‌شده.
- دسته‌بندی تانل‌ها، ترتیب دسته‌ها، ترتیب تانل‌ها، tagهای سرعت/امنیت/پایداری، pause/resume/edit/delete، وضعیت زنده و preview کانفیگ engine.
- مدیریت Port Forward برای هر تانل شامل پورت listener، پورت مقصد، وضعیت، install-package action و مشاهده ترافیک.
- ساخت سریع تانل سبک بین دو نود انتخابی.

### پروفایل‌های انتقال و پوشش Engineها

- engine داخلی reverse tunnel به‌همراه پروفایل‌ها و engineهای Reverse TCP، AmneziaWG v2، مسیرهای WireGuard-style، GOST، Backhaul، Rathole، Chisel، FRP، Xray، Hysteria2، sing-box، TUIC، NaiveProxy، ShadowTLS، Brook، Mieru، MASQUE و پروفایل‌های Mux/Quantum.
- catalog پروفایل با امتیاز سرعت، امنیت و پایداری.
- پشتیبانی از خانواده‌های REALITY gRPC/HTTP2، XHTTP + REALITY، AnyTLS، ShadowTLS، HTTP/2 TLS، HTTP/3/QUIC، MASQUE CONNECT-UDP، MASQUE QUIC-aware proxy، TUIC UDP-over-stream، TURN-like TLS relay و پیکربندی‌های سازگار با ECH در صورت پشتیبانی DNS/کلاینت/ارائه‌دهنده.
- Engine Manager برای کشف باینری، تست سلامت، اصلاح permission اجرا، بررسی نسخه، نصب دستی آرشیو، توقف/شروع مجدد process و بررسی update موتور.
- پوشه `engines/` و ابزار `download_engines.py` برای به‌روزرسانی یا بازسازی assetهای engine.

### تست هوشمند و تست سرعت

- Smart Benchmark بین دو نود انتخابی با ترکیب liveness، ping/loss، probe اتصال TCP، فشار CPU/RAM/thread، سازگاری engine نصب‌شده، metadata پروفایل و معیارهای balanced/speed/stability/security.
- مرکز گرافیکی تست سرعت iperf3 برای تست جفت نود، mesh نودهای انتخابی و تست اینترنت هر نود با سرور iperf3 معرفی‌شده توسط مدیر.
- بررسی/نصب iperf3 روی نودهای درگیر، خروجی JSON، سرعت upload/download، jitter، loss، retransmit، مصرف CPU، خطاها و پاک‌سازی سرور موقت تست.
- خروجی پیشنهاد پروفایل برای بهترین حالت متعادل، سریع‌ترین، پایدارترین و امن‌ترین انتخاب.

### معماری انتقال دیتا و کنترل کارایی

- انتخاب معماری انتقال برای هر تانل: Per-user Classic، Adaptive Bonding، Shared Mux Pool یا Smart Hybrid Mux + Bonding.
- Adaptive Bonding برای لینک‌های سازگار Built-in با ۲ تا ۱۶ lane، frame مرتب، CRC32، queue مستقل هر lane و بودجه lane هوشمند هنگام افزایش کاربران همزمان.
- Shared Mux Pool با carrierهای پایدار، تقسیم stream، keepalive، recovery و فشار کمتر روی تعداد connection برای سناریوهای چندکاربره.
- Smart Hybrid برای ترکیب carrierهای mux اشتراکی کاربران عادی با bonding تطبیقی برای جریان‌های سنگین یا idle.
- تشخیص و استفاده opt-in از TCP Brutal برای سناریوهای مناسب packet loss در صورت وجود capability لازم روی هاست/کرنل.

### بکاپ، Restore و مهاجرت

- بکاپ رمزگذاری‌شده AES-256 شامل state پنل، تنظیمات، نودها، تانل‌ها، tokenها، certificateها، SSH vault، فایل‌های برنامه و engineهای آفلاین اختیاری.
- دانلود بکاپ از داخل پنل.
- Restore داخل پنل از دو مسیر: upload مستقیم فایل از سیستم مدیر یا انتخاب backup رمزگذاری‌شده موجود روی سرور.
- اعتبارسنجی restore، ساخت rollback snapshot، بازگردانی state/application و restart کنترل‌شده پنل.
- مهاجرت مستقیم به هاست جدید از طریق SSH، restore مرحله‌ای، بررسی endpoint پنل جدید، ارسال endpoint جدید به نودها و نگه‌داشت fallback پنل قبلی.

### مانیتورینگ، لاگ و بهینه‌سازی

- داشبورد زنده برای نمودارها، کارت‌ها، منابع نودها، ترافیک، threadها، sessionهای فعال، وضعیت Docker و ویجت‌های مانیتورینگ.
- مانیتورینگ runtime برای سشن‌های فعال تانل، process/session/resource و وضعیت runtime نودها.
- لاگ‌های سیستم، نگهداری bounded لاگ، خروجی CSV و تاریخچه رویدادهای عملیاتی.
- Link Guardian برای تنظیم workerهای آماده، حذف socketهای رزرو مرده یا اضافه، حفظ session فعال، rate-limit تست سلامت و حذف فرمان‌های تکراری.
- optimizerهای منابع برای پاک‌سازی session idle، پاک‌سازی RAM/GC، مدیریت فشار thread و تنظیم محافظه‌کارانه idle retention بر اساس فشار واقعی.

### رابط کاربری، زبان و موبایل

- رابط فارسی و انگلیسی، فونت پیش‌فرض Vazirmatn، چند تم، PWA و ممیزی ترجمه در مرورگر.
- چیدمان واکنش‌گرا برای موبایل و تبلت؛ جدول نود و پورت به کارت خوانا تبدیل می‌شود، جدول‌های عریض اسکرول لمسی دارند، نمودارها با container هماهنگ می‌شوند و modalها به bottom sheet سازگار با safe area تبدیل می‌شوند.
- کنترل‌های جهت‌مند برای جابه‌جایی نود، دسته تانل و تانل با آیکون‌های بالا/پایین مجزا و ذخیره زنده ترتیب جدید.

## موتورهای تانلینگ و بسته آفلاین

برای ساخت بسته آفلاین:

```bash
python3 download_engines.py --bundle p00rija-offline-bundle.tar.gz
```

این بسته شامل فایل‌های برنامه، ماژول core، اسکریپت‌های نصب، فایل‌های README، فونت‌های آفلاین، assets، `engines/manifest.json`، باینری موتورهای دانلودشده و آرشیوهای لازم است. هنگام ساخت Docker image، موتورهای موجود در `engines/` داخل `/usr/local/bin` و فونت‌ها داخل `/app/fonts` قرار می‌گیرند و در زمان اجرا نیازی به دریافت موتور از GitHub نیست.

Reverse TCP از worker pool داخلی P00RIJA برای Port Forwarding معکوس مستقیم استفاده می‌کند. AmneziaWG v2 همراه با `amneziawg-go`، `awg` و `awg-quick` داخل بسته قرار دارد؛ کانتینرهای پنل و نود هم با دسترسی NET_ADMIN/TUN آماده می‌شوند تا کانفیگ AmneziaWG روی هاست لینوکسی اجرا شود.

تست سلامت در مدیریت هسته‌ها تمام باینری‌های مورد انتظار هر انجین را بررسی می‌کند، permission اجرا را در صورت نیاز اصلاح می‌کند، روی لینوکس probe سبک نسخه می‌گیرد و در محیط توسعه اگر معماری باینری با سیستم یکی نباشد پیام واضح می‌دهد. توقف/ریست هم پروسس‌های runtime همان هسته را متوقف می‌کند و کانفیگ تانل‌ها را آماده relaunch نگه می‌دارد.

## روند راه‌اندازی

1. پنل را نصب کنید و URL امن HTTPS نمایش‌داده‌شده توسط installer را باز کنید.
2. نودهای داخلی و خارجی را از بخش مدیریت سرورها ثبت کنید.
3. توکن و private key تولیدشده برای هر نود را در نصب نود وارد کنید.
4. در مدیریت تانل‌ها، از Easy Mode، پروفایل آماده، پیشنهاد تست هوشمند یا پروفایل شخصی استفاده کنید.
5. Port Forwarding را اضافه کنید و سپس ترافیک، سشن‌ها، منابع، لاگ‌ها و وضعیت اتصال را زنده بررسی کنید.
6. در صورت نیاز تانل را متوقف، ادامه، ویرایش یا کانفیگ موتور آن را بررسی کنید.

### جهت‌های تانل

حالت پیش‌فرض `External -> Internal` است؛ نود داخلی روی Bridge/Sync گوش می‌دهد و نود خارجی اتصال‌های رزرو را به سمت داخلی ایجاد می‌کند. وقتی نود داخلی پورت قابل دسترس دارد یا بین دو سمت route مستقیم باز است، این مسیر ساده‌تر است.

```text
External Node (client/dialer)  ====>  Internal Node (server/listener)
```

در حالت `Internal -> External` جهت آغاز اتصال برعکس می‌شود؛ نود خارجی listener است و نود داخلی اتصال خروجی را به سمت خارجی می‌زند. وقتی نود داخلی پشت NAT یا فایروال است اما خروجی اینترنت دارد، این حالت عملی‌تر است.

```text
Internal Node (client/dialer)  ====>  External Node (server/listener)
```

در catalog پروفایل‌ها، رنگ سبز یعنی خوب، زرد یعنی عادی، و قرمز یعنی ضعیف برای سرعت، امنیت و پایداری.

خانواده‌های preset شامل MASQUE/CONNECT-UDP روی HTTP/3، MASQUE QUIC-aware proxy، sing-box XHTTP REALITY، TUIC UDP-over-stream و TURN-like TLS relay هستند. اجرای عملی آن‌ها به core/binary متناظر روی نود نیاز دارد، و پنل می‌تواند آن‌ها را اعتبارسنجی، امتیازدهی، export و روی تانل اعمال کند.

برای استقرار واقعی، Hysteria2 را روی مسیر UDP سالم، AnyTLS یا XHTTP/REALITY را در مسیرهایی که ظاهر TLS/HTTP پایدارتر است، و Adaptive Bonding را در شرایط محدودسازی per-flow تست کنید. Bonding پهنای باند فیزیکی تازه تولید نمی‌کند؛ چند اتصال TCP را تجمیع می‌کند و زمانی بیشترین اثر را دارد که محدودیت روی هر اتصال جداگانه اعمال شده باشد.

## دستور مدیریت

```bash
sudo Pooriya-tunnel
```

برای start، stop، restart، مشاهده لاگ، بهینه‌سازی شبکه لینوکس و uninstall.

## بررسی قبل از انتشار

```bash
python3 -m py_compile P00RIJA.py download_engines.py p00rija_core/*.py
bash -n install.sh install-panel.sh install-node.sh Pooriya-tunnel.sh
docker build --platform linux/amd64 -t p00rija-tunnel:1.9.95 .
```

برای انتشار کامل در GitHub از آرشیو ساخته‌شده با نام `P00RIJA-TUNNEL-GitHub-v1.9.95-*.tar.gz` استفاده کنید. این بسته cache، ابزارهای debug، آرشیوهای قدیمی و state زمان اجرا را حذف می‌کند، اما باینری‌های آماده‌ی `engines/` را نگه می‌دارد تا کاربری که repository/package را دانلود می‌کند یک درخت نصب کامل داشته باشد. در صورت نیاز، هسته‌ها بعداً با `python3 download_engines.py` قابل به‌روزرسانی هستند.

## لایسنس

GPL v3. فایل [LICENSE](LICENSE) را ببینید.
