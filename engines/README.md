# Engines

This directory is used by the offline installer and Docker image build.

For a clean GitHub repository, keep only this file and `manifest.json` here. Downloaded engine binaries and archives are generated artifacts and should be prepared locally with:

```bash
python3 download_engines.py --bundle p00rija-offline-bundle.tar.gz
```

When the offline bundle is present, panel and node installers can build the runtime image without downloading tunneling engines from GitHub.
