#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3008}"
BACKEND_LOG="$PROJECT_ROOT/backend-dev.log"
FRONTEND_LOG="$PROJECT_ROOT/frontend-dev.log"

echo "[linux] Starting AI Test Platform..."
echo "[linux] Backend port: $BACKEND_PORT"
echo "[linux] Frontend port: $FRONTEND_PORT"

get_listen_pids_by_port() {
    local port="$1"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true
}

wait_for_port() {
    local port="$1"
    local retries="${2:-15}"
    local delay="${3:-1}"
    local i
    local pid=""
    for ((i=1; i<=retries; i++)); do
        pid="$(get_listen_pids_by_port "$port" | head -n 1)"
        if [[ -n "$pid" ]]; then
            echo "$pid"
            return 0
        fi
        sleep "$delay"
    done
    return 1
}

kill_service_by_port() {
    local name="$1"
    local port="$2"
    local pids
    pids="$(get_listen_pids_by_port "$port")"
    if [[ -z "$pids" ]]; then
        echo "[linux] No existing $name service on port $port, starting directly"
        return 0
    fi

    echo "[linux] Existing $name service found on port $port (pid(s): $(echo "$pids" | tr '\n' ' ')), restarting..."
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        kill "$pid" 2>/dev/null || true
    done <<< "$pids"

    sleep 1
    local remain
    remain="$(get_listen_pids_by_port "$port")"
    if [[ -n "$remain" ]]; then
        while IFS= read -r pid; do
            [[ -z "$pid" ]] && continue
            kill -9 "$pid" 2>/dev/null || true
        done <<< "$remain"
        sleep 1
    fi

    local final_check
    final_check="$(get_listen_pids_by_port "$port")"
    if [[ -n "$final_check" ]]; then
        echo "[linux] ERROR: failed to stop existing $name on port $port (pid(s): $(echo "$final_check" | tr '\n' ' '))"
        return 1
    fi
}

start_backend() {
    kill_service_by_port "backend" "$BACKEND_PORT"

    echo "[linux] Starting backend..."
    cd "$PROJECT_ROOT/backend"
    
    if [[ ! -d ".venv" ]]; then
        echo "[linux] Creating Python virtual environment..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
    fi
    
    : > "$BACKEND_LOG"
    nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" > "$BACKEND_LOG" 2>&1 &

    local backend_pid
    backend_pid="$(wait_for_port "$BACKEND_PORT" 20 1 || true)"
    if [[ -z "$backend_pid" ]]; then
        echo "[linux] ERROR: backend failed to start on port $BACKEND_PORT"
        echo "[linux] Check log: $BACKEND_LOG"
        return 1
    fi

    echo "[linux] Backend started (pid=$backend_pid)"
}

start_frontend() {
    kill_service_by_port "frontend" "$FRONTEND_PORT"

    echo "[linux] Starting frontend..."
    cd "$PROJECT_ROOT/frontend"
    
    if [[ ! -d "node_modules" ]]; then
        echo "[linux] Installing frontend dependencies..."
        npm install
    fi
    
    : > "$FRONTEND_LOG"
    nohup npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort > "$FRONTEND_LOG" 2>&1 &

    local frontend_pid
    frontend_pid="$(wait_for_port "$FRONTEND_PORT" 20 1 || true)"
    if [[ -z "$frontend_pid" ]]; then
        echo "[linux] ERROR: frontend failed to start on port $FRONTEND_PORT"
        echo "[linux] Check log: $FRONTEND_LOG"
        return 1
    fi

    echo "[linux] Frontend started (pid=$frontend_pid)"
}

start_backend
start_frontend

echo ""
echo "[linux] =========================================="
echo "[linux] Application started successfully!"
echo "[linux] Backend:  http://localhost:$BACKEND_PORT"
echo "[linux] Frontend: http://localhost:$FRONTEND_PORT"
echo "[linux] =========================================="
