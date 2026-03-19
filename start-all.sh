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
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

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

start_backend() {
  if [[ -f "$BACKEND_PID_FILE" ]]; then
    local pid
    pid="$(cat "$BACKEND_PID_FILE")"
    if [[ -n "$pid" ]] && is_alive "$pid"; then
      echo "[start-all] Backend already running (pid=$pid)"
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

  if [[ ! -d "$BACKEND_DIR/venv" ]]; then
    echo "[start-all] ERROR: backend/venv not found"
    exit 1
  fi

  echo "[start-all] Starting backend on :$BACKEND_PORT ..."
  (
    cd "$BACKEND_DIR"
    nohup ./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" >"$BACKEND_LOG" 2>&1 &
    echo $! >"$BACKEND_PID_FILE"
  )

  sleep 1
  local pid
  pid="$(cat "$BACKEND_PID_FILE")"
  if is_alive "$pid"; then
    echo "[start-all] Backend started (pid=$pid)"
  else
    if rg -q "address already in use" "$BACKEND_LOG"; then
      port_pid="$(get_port_listener_pid "$BACKEND_PORT")"
      if [[ -n "$port_pid" ]]; then
        echo "[start-all] Backend already running on :$BACKEND_PORT (pid=$port_pid)"
        echo "$port_pid" >"$BACKEND_PID_FILE"
        return
      fi
    fi
    echo "[start-all] ERROR: backend failed to start, check $BACKEND_LOG"
    exit 1
  fi
}

start_frontend() {
  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    local pid
    pid="$(cat "$FRONTEND_PID_FILE")"
    if [[ -n "$pid" ]] && is_alive "$pid"; then
      echo "[start-all] Frontend already running (pid=$pid)"
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

  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    echo "[start-all] ERROR: frontend/node_modules not found"
    exit 1
  fi

  echo "[start-all] Starting frontend on :$FRONTEND_PORT ..."
  (
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" >"$FRONTEND_LOG" 2>&1 &
    echo $! >"$FRONTEND_PID_FILE"
  )

  sleep 1
  local pid
  pid="$(cat "$FRONTEND_PID_FILE")"
  if is_alive "$pid"; then
    echo "[start-all] Frontend started (pid=$pid)"
  else
    if rg -q "address already in use" "$FRONTEND_LOG"; then
      port_pid="$(get_port_listener_pid "$FRONTEND_PORT")"
      if [[ -n "$port_pid" ]]; then
        echo "[start-all] Frontend already running on :$FRONTEND_PORT (pid=$port_pid)"
        echo "$port_pid" >"$FRONTEND_PID_FILE"
        return
      fi
    fi
    echo "[start-all] ERROR: frontend failed to start, check $FRONTEND_LOG"
    exit 1
  fi
}

start_backend
start_frontend

echo "[start-all] Done"
echo "[start-all] Backend log : $BACKEND_LOG"
echo "[start-all] Frontend log: $FRONTEND_LOG"
