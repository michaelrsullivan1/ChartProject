#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$ROOT_DIR/.venv"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required but was not found."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

echo "Syncing backend dependencies..."
"$VENV_DIR/bin/pip" install -e "$BACKEND_DIR"

if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  (
    cd "$FRONTEND_DIR"
    npm install
  )
fi

if command -v docker >/dev/null 2>&1 && [ -f "$ROOT_DIR/compose.yaml" ]; then
  if docker info >/dev/null 2>&1; then
    echo "Starting Postgres via Docker Compose"
    docker compose -f "$ROOT_DIR/compose.yaml" up -d postgres >/dev/null
  else
    echo "Docker is installed but not running. Continuing without auto-starting Postgres."
  fi
fi

cleanup() {
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi

  if [ -n "${FRONTEND_PID:-}" ]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting backend on http://127.0.0.1:${BACKEND_PORT}"
(
  cd "$BACKEND_DIR"
  "$VENV_DIR/bin/uvicorn" app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" --reload
) &
BACKEND_PID=$!

echo "Starting frontend on http://127.0.0.1:${FRONTEND_PORT}"
(
  cd "$FRONTEND_DIR"
  npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

echo "Open http://127.0.0.1:${FRONTEND_PORT}"
echo "The homepage will confirm the backend health check."

wait "$BACKEND_PID"
wait "$FRONTEND_PID"
