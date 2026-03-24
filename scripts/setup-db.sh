#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$ROOT_DIR/.venv"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to start the local Postgres service."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but the daemon is not running."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found."
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

echo "Starting Postgres container..."
docker compose -f "$ROOT_DIR/compose.yaml" up -d postgres

echo "Waiting for Postgres to accept connections..."
for attempt in $(seq 1 30); do
  if docker compose -f "$ROOT_DIR/compose.yaml" exec -T postgres \
    pg_isready -U chartproject -d chartproject >/dev/null 2>&1; then
    break
  fi

  if [ "$attempt" -eq 30 ]; then
    echo "Postgres did not become ready in time."
    exit 1
  fi

  sleep 2
done

echo "Applying migrations..."
(
  cd "$BACKEND_DIR"
  "$VENV_DIR/bin/alembic" upgrade head
)

echo "Postgres is ready and migrations are applied."
