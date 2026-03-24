#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"

echo "[docker] Stopping containers..."

cd "$DEPLOY_DIR"

docker compose down

echo "[docker] Containers stopped."
