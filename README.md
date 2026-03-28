# ChartProject

ChartProject is a local-first X/Twitter research archive and visualization system.

The architecture source of truth is [ProjectPlan.md](/Users/michaelsullivan/Code/ChartProject/ProjectPlan.md).

## Current state

One full local flow is working end-to-end:

- containerized Postgres on Docker Compose
- Alembic migrations through `0003_add_market_price_points`
- FastAPI backend with health and view routes
- React frontend with a Foundation page and a dedicated Michael Saylor vs BTC chart page
- raw-first X/Twitter ingest archived into Postgres via `raw_ingestion_artifacts`
- canonical normalization and validation for archived `saylor` tweet history
- raw BTC/USD FRED ingest plus canonical normalization and validation
- versioned RoBERTa tweet sentiment scoring stored in Postgres
- a working chart flow from canonical data to backend payloads to frontend rendering
- click-through drilldown for the top liked tweet in a selected week

## Current UI

After the stack is running:

- [http://127.0.0.1:5173](http://127.0.0.1:5173) shows the Foundation page
- [http://127.0.0.1:5173/#/michael-saylor-vs-btc](http://127.0.0.1:5173/#/michael-saylor-vs-btc) shows the working chart page

The Foundation page still runs the backend health check and renders the full JSON response.

The Michael Saylor page currently:

- requests `/api/views/michael-saylor-vs-btc?granularity=week`
- renders BTC and tweet-count panes with a shared time axis
- keeps BTC daily and tweet counts weekly in the current UI
- shows hover state for the active date
- loads the top liked tweet for the clicked week from a companion backend endpoint

## Quick start

From the repo root:

```bash
./scripts/setup-db.sh
./scripts/dev.sh
```

Then open [http://127.0.0.1:5173](http://127.0.0.1:5173).

## Common commands

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

Create a database backup:

```bash
./scripts/backup-db.sh
```

Restore the database from the most recent backup:

```bash
./scripts/restore-db.sh
```

Check the Postgres container:

```bash
docker compose ps
```

Stop the local Postgres container:

```bash
docker compose down
```

## Local setup details

The local database is intentionally containerized and defined in [compose.yaml](/Users/michaelsullivan/Code/ChartProject/compose.yaml).

### Current backend env file

The backend reads [backend/.env.example](/Users/michaelsullivan/Code/ChartProject/backend/.env.example) and expects values in `backend/.env`.

The default local connection is:

```env
CHART_DATABASE_URL=postgresql+psycopg://chartproject:chartproject@localhost:5433/chartproject
```

The host port is `5433`, not `5432`.

For X/Twitter ingest, also set:

```env
CHART_TWITTERAPI_API_KEY=
```

### What `./scripts/setup-db.sh` does

- creates `.venv/` if needed
- installs backend dependencies with `pip install -e backend`
- creates `backend/.env` from [backend/.env.example](/Users/michaelsullivan/Code/ChartProject/backend/.env.example) if missing
- starts the `postgres:16` container from [compose.yaml](/Users/michaelsullivan/Code/ChartProject/compose.yaml)
- waits for Postgres to become ready
- runs `alembic upgrade head`

### What `./scripts/dev.sh` does

- syncs backend dependencies
- installs frontend dependencies if `frontend/node_modules` is missing
- starts Postgres automatically when Docker is available and running
- starts Uvicorn on `127.0.0.1:8000`
- starts Vite on `127.0.0.1:5173`

## Verification

With the stack healthy, `GET /api/health` returns:

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

That same payload is rendered on the Foundation page.

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

The main runtime data directories currently kept in the repo are:

- `data/raw/twitterapi/`
- `data/exports/`
- `data/backups/`

## Current implementation details

### Core tables currently in use

- `users`
- `tweets`
- `tweet_references`
- `market_price_points`
- `tweet_sentiment_scores`
- `ingestion_runs`
- `raw_ingestion_artifacts`

### Current data flow

1. Archive raw user info, tweet search pages, and BTC market data into `raw_ingestion_artifacts`.
2. Normalize archived payloads into canonical relational tables.
3. Run validation against raw versus normalized data.
4. Enrich canonical tweets with versioned sentiment scores.
5. Build request-time backend view payloads from canonical tables.
6. Render the current frontend chart from those backend view payloads.

No live provider calls are required for normalization, validation, the Michael Saylor vs BTC page, or the top-liked-tweet drilldown.

## Raw ingest behavior

The current X/Twitter ingest path is designed for cautious historical backfills:

- resolves a username through `twitterapi.io`
- archives raw user info responses into `raw_ingestion_artifacts`
- fetches tweets with `advanced_search`
- builds bounded queries in the shape `from:<username> since:<UTC> until:<UTC>`
- archives every raw search response page into `raw_ingestion_artifacts`
- retries transient request failures
- deduplicates tweets by tweet ID within each window
- uses `cursor` pagination first, then falls back to `max_id:<oldest_seen_tweet_id>` when pages stop advancing
- stores run progress on `ingestion_runs`
- supports resume from a failed single-window run with `--resume-run-id`

## Backend view endpoints

The current chart flow uses two dedicated endpoints:

```text
/api/views/michael-saylor-vs-btc?granularity=week
/api/views/michael-saylor-vs-btc/top-liked-tweet?week_start=2024-01-01T00:00:00Z
```

Current behavior:

- the subject is fixed to Michael Saylor for this first chart page
- the chart endpoint supports `granularity=day` or `granularity=week`
- the current frontend page requests `granularity=week`
- tweet counts include all authored tweets, including replies and quote tweets
- tweet series are zero-filled for a continuous UTC timeline
- BTC series come from local `market_price_points`
- BTC stays daily in the payload and in the current chart UI
- the click drilldown ranks tweets within the selected week by `like_count`

Current local BTC coverage begins on `2014-12-01T00:00:00Z` because that is where the FRED `CBBTCUSD` series starts.

## Ingest scripts

The raw ingest scripts live under [backend/scripts/ingest](/Users/michaelsullivan/Code/ChartProject/backend/scripts/ingest).

### Fetch raw user info

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/ingest/fetch_user_info.py --username someuser --debug
```

### Fetch one UTC tweet window

Use ISO 8601 UTC timestamps with a trailing `Z`, for example:

- `2024-01-01T00:00:00Z`
- `2024-02-01T00:00:00Z`

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

### Fetch a larger history range in monthly windows

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

Useful options:

- `--page-delay-seconds 0.5`
- `--max-retries 3`
- `--retry-backoff-seconds 1.0`
- `--resume-run-id <id>`
- `--query-fragment "<extra advanced search terms>"`
- `--window-months 1`

### Fetch raw BTC/USD daily history

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

## Enrichment scripts

### Score tweet sentiment for one or more normalized users

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/enrich/score_tweet_sentiment.py --username saylor
```

Useful options:

- `--username saylor otheruser`
- `--dry-run`
- `--overwrite-existing`
- `--model-key some-custom-key`
- `--batch-size 64`

## Backups

The current backup helper is [scripts/backup-db.sh](/Users/michaelsullivan/Code/ChartProject/scripts/backup-db.sh).

It writes a custom-format Postgres dump into `data/backups/` by default:

```bash
./scripts/backup-db.sh
```

You can also provide an explicit output path:

```bash
./scripts/backup-db.sh /absolute/path/to/chartproject.dump
```

The restore companion is [scripts/restore-db.sh](/Users/michaelsullivan/Code/ChartProject/scripts/restore-db.sh).

If you run it with no arguments, it restores the newest `chartproject_*.dump` file from `data/backups/`:

```bash
./scripts/restore-db.sh
```

You can also restore from an explicit dump path:

```bash
./scripts/restore-db.sh /absolute/path/to/chartproject.dump
```

The restore script replaces the local `chartproject` database, so stop the app first if you want to avoid active reconnects during restore.

## Current follow-ups

The original first-chart milestone is effectively complete. The main open product questions now are:

1. Whether the default tweet series should stay weekly or switch to daily.
2. Whether BTC should remain daily in the chart presentation or be resampled for comparison views.
3. Whether the next step after this first chart should be more drilldown depth or a second chart page.
