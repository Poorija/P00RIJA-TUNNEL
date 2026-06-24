#!/bin/bash
set -ex

# Create a docker network for testing
docker network create p00rija-test-net || true

# Build the base image
docker build -t p00rija-tunnel:1.9.95 -f Dockerfile .

echo "Starting Panel (Internal Node 1)..."
docker run -d --name panel-node --network p00rija-test-net \
    -e P00RIJA_TEST=1 -p 8080:8080 -p 8001:8000 \
    p00rija-tunnel:1.9.95 python3 /app/P00RIJA.py --panel

echo "Starting Internal Node 2..."
docker run -d --name internal-node-2 --network p00rija-test-net \
    -e P00RIJA_TEST=1 \
    p00rija-tunnel:1.9.95 python3 /app/P00RIJA.py --internal

echo "Starting External Node 1..."
docker run -d --name external-node-1 --network p00rija-test-net \
    -e P00RIJA_TEST=1 \
    p00rija-tunnel:1.9.95 python3 /app/P00RIJA.py --external

echo "Starting External Node 2..."
docker run -d --name external-node-2 --network p00rija-test-net \
    -e P00RIJA_TEST=1 \
    p00rija-tunnel:1.9.95 python3 /app/P00RIJA.py --external

echo "Starting External Node 3..."
docker run -d --name external-node-3 --network p00rija-test-net \
    -e P00RIJA_TEST=1 \
    p00rija-tunnel:1.9.95 python3 /app/P00RIJA.py --external

docker ps | grep p00rija-tunnel
