FROM python:3.11-slim
ARG P00RIJA_REGION=global
ENV PYTHONUNBUFFERED=1
# Install ca-certificates first so HTTPS Iranian mirrors can be verified.
RUN apt-get -o Acquire::Check-Valid-Until=false update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*
# Switch to Iranian Debian mirrors for Iran-built images (Arvancloud first, IranServer fallback).
RUN if [ "$P00RIJA_REGION" = "ir" ]; then \
      sed -i 's|http://deb.debian.org/debian-security|https://mirror.arvancloud.ir/debian-security|g; s|http://deb.debian.org/debian|https://mirror.arvancloud.ir/debian|g' /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true; \
    fi
RUN apt-get -o Acquire::Check-Valid-Until=false update && \
    apt-get install -y --no-install-recommends openssl iputils-ping iperf3 curl procps openssh-client sshpass ca-certificates iproute2 wireguard-tools stunnel4 && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY P00RIJA.py /app/P00RIJA.py
COPY download_engines.py /app/download_engines.py
COPY p00rija_core/ /app/p00rija_core/
COPY fonts /app/fonts
COPY static /app/static
COPY install.sh install-panel.sh install-node.sh installer-ui.sh Pooriya-tunnel.sh p00rija-control.sh restore-panel-backup.sh p00rija-host-agent.py README.md LICENSE Dockerfile /app/
COPY engines/ /usr/local/bin/
# The panel's default web port constant is 8080; the container reads its actual
# port from p00rija_config.json. Non-panel (node) containers have nothing to probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python3 -c "import json,socket; c=json.load(open('/opt/p00rija/p00rija_config.json')); p=int(c.get('port',8080)); socket.create_connection(('127.0.0.1',p),5) if c.get('role')=='panel' else None"
CMD ["python3", "/app/P00RIJA.py"]
