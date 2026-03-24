#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "[docker] Project root: $PROJECT_ROOT"

check_and_copy_env() {
    local src_dir="$1"
    local env_file=".env"
    
    if [[ -f "$src_dir/$env_file" ]]; then
        echo "[docker] Found $env_file in $src_dir"
    else
        if [[ -f "$src_dir/$env_file.example" ]]; then
            echo "[docker] Copying $env_file.example to $env_file in $src_dir"
            cp "$src_dir/$env_file.example" "$src_dir/$env_file"
        else
            echo "[docker] Warning: No $env_file or $env_file.example found in $src_dir"
        fi
    fi
}

echo "[docker] Checking .env files..."
check_and_copy_env "$FRONTEND_DIR"
check_and_copy_env "$BACKEND_DIR"

echo "[docker] Building and starting containers..."

cd "$SCRIPT_DIR"

docker compose down 2>/dev/null || true
docker compose build --no-cache
docker compose up -d

echo ""
echo "[docker] =========================================="
echo "[docker] Containers started!"
echo "[docker] Frontend: http://localhost:3008"
echo "[docker] Backend:  http://localhost:8001"
echo "[docker] Run 'docker compose logs -f' to view logs"
echo "[docker] =========================================="
