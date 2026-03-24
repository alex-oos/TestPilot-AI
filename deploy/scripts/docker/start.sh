#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"

echo "[docker] Building and starting containers..."

cd "$DEPLOY_DIR"

docker compose down 2>/dev/null || true
docker compose build --no-cache
docker compose up -d

echo ""
echo "[docker] =========================================="
echo "[docker] Containers started!"
echo "[docker] Backend:  http://localhost:8001"
echo "[docker] Frontend: http://localhost:3008"
echo "[docker] Run 'docker compose logs -f' to view logs"
echo "[docker] =========================================="
