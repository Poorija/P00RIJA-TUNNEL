FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y iputils-ping curl openssl procps openssh-client sshpass ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY P00RIJA.py /app/P00RIJA.py
COPY download_engines.py /app/download_engines.py
COPY fonts /app/fonts
COPY engines/ /usr/local/bin/
CMD ["python3", "/app/P00RIJA.py"]
