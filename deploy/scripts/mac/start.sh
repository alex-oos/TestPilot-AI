#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3008}"

echo "[mac] Starting AI Test Platform..."
echo "[mac] Backend port: $BACKEND_PORT"
echo "[mac] Frontend port: $FRONTEND_PORT"

mkdir -p "$PROJECT_ROOT/.run"

start_backend() {
    echo "[mac] Starting backend..."
    cd "$PROJECT_ROOT/backend"
    
    if [[ ! -d ".venv" ]]; then
        echo "[mac] Creating Python virtual environment..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
    fi
    
    source .venv/bin/activate
    nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" > "$PROJECT_ROOT/backend-dev.log" 2>&1 &
    echo $! > "$PROJECT_ROOT/.run/backend.pid"
    echo "[mac] Backend started (pid=$(cat $PROJECT_ROOT/.run/backend.pid))"
}

start_frontend() {
    echo "[mac] Starting frontend..."
    cd "$PROJECT_ROOT/frontend"
    
    if [[ ! -d "node_modules" ]]; then
        echo "[mac] Installing frontend dependencies..."
        npm install
    fi
    
    nohup npm run dev > "$PROJECT_ROOT/frontend-dev.log" 2>&1 &
    echo $! > "$PROJECT_ROOT/.run/frontend.pid"
    echo "[mac] Frontend started (pid=$(cat $PROJECT_ROOT/.run/frontend.pid))"
}

start_backend
start_frontend

echo ""
echo "[mac] =========================================="
echo "[mac] Application started successfully!"
echo "[mac] Backend:  http://localhost:$BACKEND_PORT"
echo "[mac] Frontend: http://localhost:$FRONTEND_PORT"
echo "[mac] =========================================="
