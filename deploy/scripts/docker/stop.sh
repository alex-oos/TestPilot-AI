#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[docker] Stopping containers..."

cd "$SCRIPT_DIR"

docker compose down

echo "[docker] Containers stopped."
