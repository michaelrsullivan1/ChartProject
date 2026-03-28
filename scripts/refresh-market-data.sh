#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$ROOT_DIR/.venv"
IMPORT_TYPE="${IMPORT_TYPE:-refresh}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

echo "Syncing backend dependencies..."
"$VENV_DIR/bin/pip" install -e "$BACKEND_DIR" >/dev/null

if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

run_backend_script() {
  (
    cd "$BACKEND_DIR"
    "$VENV_DIR/bin/python" "$@"
  )
}

echo "Archiving raw BTC/USD daily history from FRED..."
run_backend_script scripts/ingest/fetch_btc_fred_daily.py --import-type "$IMPORT_TYPE"

echo "Normalizing BTC/USD daily history..."
run_backend_script scripts/normalize/normalize_market_price_points.py --asset-symbol BTC --quote-currency USD --interval day

echo "Validating BTC/USD daily history..."
run_backend_script scripts/validate/validate_market_price_points.py --asset-symbol BTC --quote-currency USD --interval day

echo "Archiving raw MSTR/USD daily history from Twelve Data..."
run_backend_script scripts/ingest/fetch_equity_twelvedata_daily.py --symbol MSTR --asset-symbol MSTR --import-type "$IMPORT_TYPE"

echo "Normalizing MSTR/USD daily history..."
run_backend_script scripts/normalize/normalize_market_price_points.py --asset-symbol MSTR --quote-currency USD --interval day

echo "Validating MSTR/USD daily history..."
run_backend_script scripts/validate/validate_market_price_points.py --asset-symbol MSTR --quote-currency USD --interval day

echo "Market data refresh complete."
