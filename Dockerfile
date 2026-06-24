FROM python:3.11-slim
ARG P00RIJA_REGION=global
ENV PYTHONUNBUFFERED=1
RUN if [ "$P00RIJA_REGION" = "ir" ]; then \
      sed -i 's|http://deb.debian.org/debian-security|https://mirror.iranserver.com/debian-security|g; s|http://deb.debian.org/debian|https://mirror.iranserver.com/debian|g' /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true; \
    fi && \
    apt-get -o Acquire::Check-Valid-Until=false update && apt-get install -y --no-install-recommends iputils-ping iperf3 curl openssl procps openssh-client sshpass ca-certificates iproute2 wireguard-tools stunnel4 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY P00RIJA.py /app/P00RIJA.py
COPY download_engines.py /app/download_engines.py
COPY p00rija_core/ /app/p00rija_core/
COPY fonts /app/fonts
COPY install.sh install-panel.sh install-node.sh installer-ui.sh Pooriya-tunnel.sh p00rija-control.sh restore-panel-backup.sh p00rija-host-agent.py README.md README_FA.md LICENSE Dockerfile /app/
COPY engines/ /usr/local/bin/
CMD ["python3", "/app/P00RIJA.py"]
