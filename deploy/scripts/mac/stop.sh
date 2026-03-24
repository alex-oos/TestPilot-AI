#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

stop_service() {
    local name="$1"
    local pid_file="$2"
    local port="$3"
    
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            echo "[mac] Stopping $name (pid=$pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$pid_file"
    fi
    
    local port_pid
    port_pid=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)
    if [[ -n "$port_pid" ]]; then
        echo "[mac] Stopping $name on port $port (pid=$port_pid)..."
        kill "$port_pid" 2>/dev/null || true
    fi
}

echo "[mac] Stopping AI Test Platform..."

stop_service "backend" "$PROJECT_ROOT/.run/backend.pid" "8001"
stop_service "frontend" "$PROJECT_ROOT/.run/frontend.pid" "3008"

echo "[mac] All services stopped."
