# ChartProject

ChartProject is a local-first X/Twitter research archive and visualization system.

The architecture source of truth is [ProjectPlan.md](/Users/michaelsullivan/Code/ChartProject/ProjectPlan.md).

## Current state

The local foundation is working end-to-end:

- containerized Postgres
- Alembic migrations
- FastAPI backend health check
- React frontend that confirms backend and database connectivity on page load
- raw-first X/Twitter ingest archived in Postgres
- canonical tweet normalization and validation for `saylor`
- local BTC/USD daily archive, normalization, and validation
- first dedicated backend view for `author-vs-btc`

If the stack is healthy, the frontend should show:

- `Health check succeeded.`
- backend `status: ok`
- database `status: ok`
- the full JSON health payload rendered on the page

## Quick start

From the repo root:

```bash
./scripts/setup-db.sh
./scripts/dev.sh
```

Then open [http://127.0.0.1:5173](http://127.0.0.1:5173).

## Daily commands

Set up or re-apply the local database:

```bash
./scripts/setup-db.sh
```

Start backend and frontend for local development:

```bash
./scripts/dev.sh
```

Check backend health directly:

```bash
curl http://127.0.0.1:8000/api/health
```

Check the Postgres container:

```bash
docker compose ps
```

Stop the local Postgres container:

```bash
docker compose down
```

## Postgres setup

The local database is intentionally containerized and defined in [compose.yaml](/Users/michaelsullivan/Code/ChartProject/compose.yaml). This is the portable development setup for the repo because it makes the database runtime reproducible across machines.

### Why this setup exists

- same Postgres version on different machines
- less machine-specific configuration drift
- easier to recreate the environment from the repo itself
- easier to move the project to another machine later

### Current local connection details

The backend expects:

```env
CHART_DATABASE_URL=postgresql+psycopg://chartproject:chartproject@localhost:5433/chartproject
```

The host port is `5433`, not `5432`.

This project uses `5433` deliberately so it does not collide with other local Postgres instances that may already be using the default `5432`.

### What `./scripts/setup-db.sh` does

- creates `.venv/` if needed
- installs backend dependencies if needed
- creates `backend/.env` from [backend/.env.example](/Users/michaelsullivan/Code/ChartProject/backend/.env.example) if missing
- starts the `postgres:16` container from [compose.yaml](/Users/michaelsullivan/Code/ChartProject/compose.yaml)
- waits for Postgres to become ready
- runs `alembic upgrade head`

This applies the current Alembic chain through [0003_add_market_price_points.py](/Users/michaelsullivan/Code/ChartProject/backend/migrations/versions/0003_add_market_price_points.py).

## Verification

After `./scripts/setup-db.sh` and `./scripts/dev.sh`, the expected backend health response is:

```json
{
  "status": "ok",
  "app_name": "ChartProject API",
  "environment": "development",
  "database": {
    "connected": true,
    "status": "ok",
    "detail": "Connection succeeded."
  }
}
```

If the frontend is working, that same state should appear visibly in the UI.

## Move to another machine

To recreate the same local environment elsewhere:

1. Clone the repo.
2. Install a Docker-compatible runtime.
3. Run `./scripts/setup-db.sh`.
4. Run `./scripts/dev.sh`.

That is the intended portable workflow for local development.

## Manual backend/frontend commands

If you need to run pieces separately instead of using the scripts:

### Backend

```bash
cd /Users/michaelsullivan/Code/ChartProject
python3 -m venv .venv
source .venv/bin/activate
pip install -e backend

cd backend
cp .env.example .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd /Users/michaelsullivan/Code/ChartProject/frontend
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

## Project layout

```text
backend/
frontend/
data/
docs/
scripts/
ProjectPlan.md
compose.yaml
```

## Current foundation choices

- Raw API payloads are archived in Postgres first via `raw_ingestion_artifacts`
- Historical tweet backfills currently use `twitterapi.io` `advanced_search`
- Historical backfills are sliced into UTC time windows and paginated with `cursor` plus `max_id`
- BTC/USD daily history is archived locally from the FRED `CBBTCUSD` series
- Canonical relational tables now include `users`, `tweets`, `tweet_references`, and `market_price_points`
- Validation scripts exist for normalized tweet data and normalized BTC price data
- The first view endpoint is intentionally specific and request-time only: `/api/views/michael-saylor-vs-btc`
- Frontend work remains intentionally minimal until the data and first view layers are in place

## Next implementation steps

1. Wire the frontend to the first backend view endpoint and evaluate the chart visually.
2. Decide whether tweet granularity should remain weekly or switch to daily for this first chart.
3. Decide whether BTC should remain daily in the payload or also be aggregated for presentation.
4. Add backup and restore scripts for moving the database between machines.

## Raw ingest safety

The current raw ingest path is designed for cautious full-history backfills before normalization:

- resolves a username through the user info endpoint
- archives raw user info responses into `raw_ingestion_artifacts`
- fetches tweets with `twitterapi.io` `advanced_search`
- builds bounded queries in the shape `from:<username> since:<UTC> until:<UTC>`
- archives every raw search response page into `raw_ingestion_artifacts`
- retries transient request failures
- deduplicates tweets by tweet ID within each window
- uses `cursor` pagination first, then falls back to `max_id:<oldest_seen_tweet_id>` when pages stop advancing
- waits briefly between page requests
- stores run progress on `ingestion_runs`
- supports resume from a failed single-window run with `--resume-run-id`

## Canonical data and local market data

The current normalized/local tables are:

- `users`
- `tweets`
- `tweet_references`
- `market_price_points`
- `ingestion_runs`
- `raw_ingestion_artifacts`

The working local data flow is now:

1. Archive raw tweet and BTC source payloads into `raw_ingestion_artifacts`.
2. Normalize those archived payloads into canonical relational tables.
3. Run local validation against raw vs normalized data.
4. Build dedicated backend view payloads from canonical tables only.

No live provider calls are required for normalization, validation, or the `author-vs-btc` view.

## Ingest scripts

The current raw-ingest scripts live under [backend/scripts/ingest](/Users/michaelsullivan/Code/ChartProject/backend/scripts/ingest).

### 1. Fetch raw user info

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/ingest/fetch_user_info.py --username someuser --debug
```

### 2. Fetch one UTC tweet window

Use ISO 8601 UTC timestamps with a trailing `Z`:
- `2024-01-01T00:00:00Z`
- `2024-02-01T00:00:00Z`

Example:

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/ingest/fetch_user_tweets.py \
  --username someuser \
  --since 2024-01-01T00:00:00Z \
  --until 2024-02-01T00:00:00Z \
  --page-delay-seconds 0.5 \
  --debug
```

### 3. Fetch a larger history range in monthly windows

This wrapper runs raw user info once, then iterates month-by-month across a larger UTC range.

Example:

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/ingest/fetch_user_tweets_history.py \
  --username someuser \
  --since 2024-01-01T00:00:00Z \
  --until 2025-01-01T00:00:00Z \
  --window-months 1 \
  --page-delay-seconds 0.5 \
  --debug
```

### Why monthly windows

In practice, the provider's pagination is much more stable when historical backfills are broken into smaller UTC windows. The current recommended default is:

- larger overall history ranges
- `--window-months 1`
- `queryType=Latest`
- `cursor` plus `max_id` continuation inside each month

### Useful options

- `--page-delay-seconds 0.5`
- `--max-retries 3`
- `--retry-backoff-seconds 1.0`
- `--resume-run-id <id>`
- `--query-fragment "<extra advanced search terms>"`
- `--window-months 1`

### 4. Fetch raw BTC/USD daily history

BTC/USD daily data is currently archived from the FRED `CBBTCUSD` series.

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/ingest/fetch_btc_fred_daily.py
```

## Normalization scripts

### Normalize archived tweets for one user

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/normalize/normalize_archived_user.py --username saylor
```

### Normalize archived BTC price points

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/normalize/normalize_market_price_points.py --asset-symbol BTC --quote-currency USD --interval day
```

## Validation scripts

### Validate normalized tweets for one user

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/validate/validate_normalized_user.py --username saylor
```

### Validate normalized BTC price points

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/validate/validate_market_price_points.py --asset-symbol BTC --quote-currency USD --interval day
```

## First backend view

The first dedicated backend view endpoint is:

```text
/api/views/michael-saylor-vs-btc?granularity=week
```

Current behavior:

- the subject is fixed to Michael Saylor for this page
- `granularity` supports `day` or `week` and currently defaults to `week`
- tweet counts include all authored tweets, including replies and quote tweets
- tweet series are zero-filled for a continuous UTC timeline
- BTC series come from local `market_price_points`
- the endpoint returns one payload containing both tweet activity and BTC price data

Current local BTC coverage begins on `2014-12-01T00:00:00Z` because that is where the FRED `CBBTCUSD` series starts.
