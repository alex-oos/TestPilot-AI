#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3008}"

stop_service() {
    local name="$1"
    local port="$2"

    local pids
    pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
    if [[ -z "$pids" ]]; then
        echo "[linux] No $name service found on port $port"
        return 0
    fi

    echo "[linux] Stopping $name on port $port (pid(s): $(echo "$pids" | tr '\n' ' '))..."
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        kill "$pid" 2>/dev/null || true
    done <<< "$pids"
    sleep 1

    local remain
    remain="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
    if [[ -n "$remain" ]]; then
        while IFS= read -r pid; do
            [[ -z "$pid" ]] && continue
            kill -9 "$pid" 2>/dev/null || true
        done <<< "$remain"
        sleep 1
    fi
}

echo "[linux] Stopping AI Test Platform..."

stop_service "backend" "$BACKEND_PORT"
stop_service "frontend" "$FRONTEND_PORT"

echo "[linux] All services stopped."
