#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/compose.yaml"
BACKUP_DIR="$ROOT_DIR/backups"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
DEFAULT_OUTPUT="$BACKUP_DIR/chartproject_${TIMESTAMP}.dump"
OUTPUT_PATH="${1:-$DEFAULT_OUTPUT}"

mkdir -p "$BACKUP_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to back up the local Postgres database."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but the daemon is not running."
  exit 1
fi

echo "Writing database backup to:"
echo "  $OUTPUT_PATH"

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump \
    --username=chartproject \
    --dbname=chartproject \
    --format=custom \
    --no-owner \
    --no-privileges \
  > "$OUTPUT_PATH"

echo "Backup complete."
