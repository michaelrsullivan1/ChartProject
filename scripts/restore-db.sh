#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/compose.yaml"
BACKUP_DIR="$ROOT_DIR/data/backups"
INPUT_PATH="${1:-}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to restore the local Postgres database."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but the daemon is not running."
  exit 1
fi

if [ -z "$INPUT_PATH" ]; then
  INPUT_PATH="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'chartproject_*.dump' | sort | tail -n 1)"
fi

if [ -z "$INPUT_PATH" ]; then
  echo "No backup dump was provided and no dump files were found in $BACKUP_DIR."
  exit 1
fi

if [ ! -f "$INPUT_PATH" ]; then
  echo "Backup dump not found: $INPUT_PATH"
  exit 1
fi

echo "Restoring database from:"
echo "  $INPUT_PATH"
echo "This will replace the current local chartproject database."

echo "Starting Postgres container..."
docker compose -f "$COMPOSE_FILE" up -d postgres >/dev/null

echo "Waiting for Postgres to accept connections..."
for attempt in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_isready -U chartproject -d chartproject >/dev/null 2>&1; then
    break
  fi

  if [ "$attempt" -eq 30 ]; then
    echo "Postgres did not become ready in time."
    exit 1
  fi

  sleep 2
done

echo "Terminating active connections to chartproject..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U chartproject -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'chartproject' AND pid <> pg_backend_pid();" \
  >/dev/null

echo "Recreating chartproject database..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  dropdb --if-exists --username=chartproject chartproject
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  createdb --username=chartproject chartproject

echo "Restoring dump..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_restore \
    --username=chartproject \
    --dbname=chartproject \
    --no-owner \
    --no-privileges \
    --exit-on-error \
  < "$INPUT_PATH"

echo "Restore complete."
