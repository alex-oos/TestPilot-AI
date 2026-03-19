#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUN_DIR="$ROOT_DIR/.run"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$ROOT_DIR/backend-dev.log"
FRONTEND_LOG="$ROOT_DIR/frontend-dev.log"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3008}"

mkdir -p "$RUN_DIR"

echo "[start-all] Root: $ROOT_DIR"

is_alive() {
  local pid="$1"
  kill -0 "$pid" >/dev/null 2>&1
}

get_port_listener_pid() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -n 1 || true
}

wait_for_port() {
  local port="$1"
  local timeout_seconds="${2:-15}"
  local i=0
  while [[ "$i" -lt "$timeout_seconds" ]]; do
    if [[ -n "$(get_port_listener_pid "$port")" ]]; then
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

start_backend() {
  if [[ -f "$BACKEND_PID_FILE" ]]; then
    local old_pid
    old_pid="$(cat "$BACKEND_PID_FILE")"
    if [[ -n "$old_pid" ]] && is_alive "$old_pid"; then
      echo "[start-all] Backend already running (pid=$old_pid)"
      return
    fi
  fi

  local port_pid
  port_pid="$(get_port_listener_pid "$BACKEND_PORT")"
  if [[ -n "$port_pid" ]]; then
    echo "[start-all] Backend port :$BACKEND_PORT already in use (pid=$port_pid), treating as running"
    echo "$port_pid" >"$BACKEND_PID_FILE"
    return
  fi

  if [[ ! -x "$BACKEND_DIR/venv/bin/python" ]]; then
    echo "[start-all] ERROR: backend Python env not found at $BACKEND_DIR/venv/bin/python"
    exit 1
  fi

  echo "[start-all] Starting backend on :$BACKEND_PORT ..."
  (
    cd "$BACKEND_DIR"
    nohup ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload >"$BACKEND_LOG" 2>&1 < /dev/null &
    local launched_pid=$!
    disown "$launched_pid" 2>/dev/null || true
  )

  if wait_for_port "$BACKEND_PORT" 20; then
    port_pid="$(get_port_listener_pid "$BACKEND_PORT")"
    echo "$port_pid" >"$BACKEND_PID_FILE"
    echo "[start-all] Backend started (pid=$port_pid)"
  else
    echo "[start-all] ERROR: backend failed to listen on :$BACKEND_PORT"
    tail -n 80 "$BACKEND_LOG" || true
    exit 1
  fi
}

start_frontend() {
  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    local old_pid
    old_pid="$(cat "$FRONTEND_PID_FILE")"
    if [[ -n "$old_pid" ]] && is_alive "$old_pid"; then
      echo "[start-all] Frontend already running (pid=$old_pid)"
      return
    fi
  fi

  local port_pid
  port_pid="$(get_port_listener_pid "$FRONTEND_PORT")"
  if [[ -n "$port_pid" ]]; then
    echo "[start-all] Frontend port :$FRONTEND_PORT already in use (pid=$port_pid), treating as running"
    echo "$port_pid" >"$FRONTEND_PID_FILE"
    return
  fi

  if [[ ! -f "$FRONTEND_DIR/node_modules/vite/bin/vite.js" ]]; then
    echo "[start-all] ERROR: vite runtime not found, run npm install in frontend first"
    exit 1
  fi

  echo "[start-all] Starting frontend on :$FRONTEND_PORT ..."
  (
    cd "$FRONTEND_DIR"
    nohup node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort >"$FRONTEND_LOG" 2>&1 < /dev/null &
    local launched_pid=$!
    disown "$launched_pid" 2>/dev/null || true
  )

  if wait_for_port "$FRONTEND_PORT" 20; then
    port_pid="$(get_port_listener_pid "$FRONTEND_PORT")"
    echo "$port_pid" >"$FRONTEND_PID_FILE"
    echo "[start-all] Frontend started (pid=$port_pid)"
  else
    echo "[start-all] ERROR: frontend failed to listen on :$FRONTEND_PORT"
    tail -n 80 "$FRONTEND_LOG" || true
    exit 1
  fi
}

start_backend
start_frontend

echo "[start-all] Done"
echo "[start-all] Backend URL : http://127.0.0.1:$BACKEND_PORT"
echo "[start-all] Frontend URL: http://127.0.0.1:$FRONTEND_PORT"
echo "[start-all] Backend log : $BACKEND_LOG"
echo "[start-all] Frontend log: $FRONTEND_LOG"
