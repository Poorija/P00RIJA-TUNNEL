#!/bin/bash
set -ex
docker network create panel-net || true
docker network create iran-net || true
docker network create eu-net || true

docker build -t p00rija-tunnel:1.9.95 -f Dockerfile .

docker run -d --name p00rija-panel --network panel-net -e P00RIJA_TEST=1 -p 8080:8080 -p 8000:8000 p00rija-tunnel:1.9.95 python3 /app/P00RIJA.py

sleep 2
