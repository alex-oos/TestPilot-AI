#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3008}"

is_alive() {
  local pid="$1"
  kill -0 "$pid" >/dev/null 2>&1
}

get_port_listener_pid() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -n 1 || true
}

stop_pid() {
  local name="$1"
  local pid="$2"
  if [[ -z "$pid" ]]; then
    return
  fi
  if is_alive "$pid"; then
    echo "[stop-all] Stopping $name (pid=$pid) ..."
    kill "$pid" >/dev/null 2>&1 || true
    sleep 1
    if is_alive "$pid"; then
      echo "[stop-all] Force kill $name (pid=$pid)"
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  fi
}

stop_by_pid_file() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "[stop-all] $name pid file not found, skip"
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if [[ -z "$pid" ]]; then
    echo "[stop-all] $name pid is empty, skip"
    rm -f "$pid_file"
    return
  fi

  stop_pid "$name" "$pid"
  rm -f "$pid_file"
}

stop_by_port() {
  local name="$1"
  local port="$2"
  local pid
  pid="$(get_port_listener_pid "$port")"
  if [[ -n "$pid" ]]; then
    stop_pid "$name" "$pid"
  fi
}

stop_by_pid_file "backend" "$BACKEND_PID_FILE"
stop_by_pid_file "frontend" "$FRONTEND_PID_FILE"

# Fallback: ensure listeners are gone even if pid files are stale.
stop_by_port "backend" "$BACKEND_PORT"
stop_by_port "frontend" "$FRONTEND_PORT"

echo "[stop-all] Done"
