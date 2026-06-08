# Offline Engines

This directory is intentionally part of the offline/develop package. Keep the engine binaries, `manifest.json`, and `archives/` here so panel and node installers can work when GitHub or public internet access is unavailable.

To refresh or rebuild the offline engine set on a machine that has internet access, run:

```bash
python3 download_engines.py --bundle p00rija-offline-bundle.tar.gz
```

The panel and node Docker images copy this directory into `/usr/local/bin`, so bundled engines are available at runtime without downloading them during install.
