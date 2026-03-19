#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"

is_alive() {
  local pid="$1"
  kill -0 "$pid" >/dev/null 2>&1
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

  if is_alive "$pid"; then
    echo "[stop-all] Stopping $name (pid=$pid) ..."
    kill "$pid" >/dev/null 2>&1 || true
    sleep 1
    if is_alive "$pid"; then
      echo "[stop-all] Force kill $name (pid=$pid)"
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  else
    echo "[stop-all] $name already stopped (pid=$pid)"
  fi

  rm -f "$pid_file"
}

stop_by_pid_file "backend" "$BACKEND_PID_FILE"
stop_by_pid_file "frontend" "$FRONTEND_PID_FILE"

echo "[stop-all] Done"
