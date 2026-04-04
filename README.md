# ChartProject

ChartProject is a local-first X/Twitter research archive and visualization system.

The architecture source of truth is [ProjectPlan.md](/Users/michaelsullivan/Code/ChartProject/ProjectPlan.md).

## Current state

One full local flow is working end-to-end:

- containerized Postgres on Docker Compose
- Alembic migrations through `0006_add_tweet_mood_scores`
- FastAPI backend with health, overview, mood, and heatmap view routes
- React frontend with a Foundation page, shared overview pages, shared mood pages, and shared heatmap pages
- raw-first X/Twitter ingest archived into Postgres via `raw_ingestion_artifacts`
- canonical normalization and validation for archived `saylor` tweet history
- raw BTC/USD FRED ingest plus canonical normalization and validation
- raw MSTR/USD Twelve Data ingest plus canonical normalization and validation
- versioned RoBERTa tweet sentiment scoring stored in Postgres
- versioned RoBERTa multilabel tweet mood scoring stored in Postgres
- versioned exact phrase extraction stored in Postgres via `tweet_keywords`
- a working chart flow from canonical data to backend payloads to frontend rendering
- click-through drilldown for the top liked tweet in a selected week
- click-through drilldown for the top liked phrase-matching tweets in a selected month

## Current UI

After the stack is running:

- [http://127.0.0.1:5173](http://127.0.0.1:5173) shows the Foundation page
- [http://127.0.0.1:5173/#/overviews/michael-saylor](http://127.0.0.1:5173/#/overviews/michael-saylor) shows the Michael Saylor overview
- [http://127.0.0.1:5173/#/overviews/michael-sullivan](http://127.0.0.1:5173/#/overviews/michael-sullivan) shows the Michael Sullivan overview
- [http://127.0.0.1:5173/#/moods/michael-saylor](http://127.0.0.1:5173/#/moods/michael-saylor) shows the Michael Saylor moods page
- [http://127.0.0.1:5173/#/moods/peter-schiff](http://127.0.0.1:5173/#/moods/peter-schiff) shows the Peter Schiff moods page
- [http://127.0.0.1:5173/#/bitcoin-mentions](http://127.0.0.1:5173/#/bitcoin-mentions) shows the Bitcoin mentions timing analysis page
- [http://127.0.0.1:5173/#/heatmaps/michael-saylor](http://127.0.0.1:5173/#/heatmaps/michael-saylor) shows the Michael Saylor phrase heatmap
- [http://127.0.0.1:5173/#/heatmaps/michael-sullivan](http://127.0.0.1:5173/#/heatmaps/michael-sullivan) shows the Michael Sullivan phrase heatmap

The Foundation page still runs the backend health check and renders the full JSON response.

The overview pages currently:

- request a dedicated overview endpoint such as `/api/views/michael-saylor-overview?granularity=week`
- renders BTC, MSTR, activity, and sentiment panes with a shared time axis
- keeps BTC daily and tweet counts weekly in the current UI
- shows hover state for the active date
- loads the top liked tweet for the clicked week from a companion backend endpoint

The heatmap pages currently:

- request a dedicated heatmap endpoint such as `/api/views/michael-saylor-heatmap?mode=common&word_count=all&granularity=month&limit=48`
- render a monthly phrase heatmap in the top pane
- support `Common` and `Rising` ranking modes
- support `All`, `1 word`, `2 words`, and `3 words` filters
- load the selected phrase trend on demand in the bottom pane
- load the top liked matching tweets for a clicked month from a companion backend endpoint

The mood pages currently:

- request a dedicated mood overview endpoint such as `/api/views/michael-saylor-moods?granularity=week`
- request a companion mood series endpoint such as `/api/views/michael-saylor-moods/mood-series?granularity=week`
- render BTC in the top pane and the selected mood deviation in the bottom pane
- default to relative-to-baseline mood deviation with the same weighted smoothing modes as the sentiment page
- expose the current curated mood set from the GoEmotions model: `optimism`, `fear`, `nervousness`, `annoyance`, `excitement`, `confusion`, `anger`, `disapproval`, `curiosity`, `surprise`, `disappointment`, `disgust`, and `embarrassment`
- store absolute per-tweet mood scores in Postgres and compute relative deviation at request time

The Bitcoin mentions page currently:

- requests `/api/views/bitcoin-mentions?username=<handle>&phrase=bitcoin&buy_amount_usd=10`
- pairs exact tweet timestamps with the stored BTC daily UTC close for that date
- models the result of buying a fixed dollar amount of BTC on every matching mention
- ranks configured authors by average BTC entry price across their matched mentions
- lists the cheapest and full-history Bitcoin mentions for the selected author

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

Refresh local chart market data for both BTC and MSTR:

```bash
./scripts/refresh-market-data.sh
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

For Twelve Data equity history, also set:

```env
CHART_TWELVEDATA_API_KEY=
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
- `tweet_keywords`
- `tweet_references`
- `market_price_points`
- `tweet_mood_scores`
- `tweet_sentiment_scores`
- `ingestion_runs`
- `raw_ingestion_artifacts`

### Current data flow

1. Archive raw user info, tweet search pages, and market data payloads into `raw_ingestion_artifacts`.
2. Normalize archived payloads into canonical relational tables.
3. Run validation against raw versus normalized data.
4. Enrich canonical tweets with versioned sentiment scores.
5. Enrich canonical tweets with versioned multilabel mood scores.
6. Enrich canonical tweets with versioned exact phrase rows in `tweet_keywords`.
7. Build request-time backend view payloads from canonical tables.
8. Render the current frontend chart pages from those backend view payloads.

No live provider calls are required for normalization, validation, the overview pages, the heatmap pages, or their tweet drilldowns.

Current local market sources:

- `BTC/USD` daily closes from FRED
- `MSTR/USD` daily closes from Twelve Data

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

The current chart flow uses dedicated overview endpoints:

```text
/api/views/michael-saylor-overview?granularity=week
/api/views/michael-saylor-overview/top-liked-tweet?week_start=2024-01-01T00:00:00Z
/api/views/michael-saylor-overview/btc-spot
/api/views/michael-saylor-moods?granularity=week
/api/views/michael-saylor-moods/mood-series?granularity=week
/api/views/michael-saylor-moods/btc-spot
/api/views/peter-schiff-moods?granularity=week
/api/views/peter-schiff-moods/mood-series?granularity=week
/api/views/peter-schiff-moods/btc-spot
/api/views/michael-sullivan-overview?granularity=week
/api/views/michael-sullivan-overview/top-liked-tweet?week_start=2024-01-01T00:00:00Z
/api/views/michael-sullivan-overview/btc-spot
/api/views/michael-saylor-heatmap?mode=common&word_count=all&granularity=month&limit=48
/api/views/michael-saylor-heatmap/phrase-trend?phrase=digital%20credit&granularity=month
/api/views/michael-saylor-heatmap/top-liked-tweets?phrase=digital%20credit&month_start=2025-08-01T00:00:00Z&limit=3
/api/views/michael-sullivan-heatmap?mode=common&word_count=all&granularity=month&limit=48
/api/views/michael-sullivan-heatmap/phrase-trend?phrase=bitcoin&granularity=month
/api/views/michael-sullivan-heatmap/top-liked-tweets?phrase=bitcoin&month_start=2026-03-01T00:00:00Z&limit=3
```

Current behavior:

- each overview route is dedicated to a single manually configured subject
- the chart endpoint supports `granularity=day` or `granularity=week`
- the current frontend page requests `granularity=week`
- tweet counts include all authored tweets, including replies and quote tweets
- tweet series are zero-filled for a continuous UTC timeline
- BTC series come from local `market_price_points`
- latest BTC spot comes from Coinbase on request via `/btc-spot`
- MSTR series come from local `market_price_points`
- BTC stays daily in the payload and in the current chart UI
- MSTR stays daily in the payload and in the current chart UI
- the click drilldown ranks tweets within the selected week by `like_count`
- mood pages currently reuse the overview BTC payload but replace the lower pane with mood deviation
- mood deviation is computed against the selected author's own historical baseline
- the current mood UI is curated to six labels, but the scorer stores every label emitted by the configured model
- heatmap rows are phrase-level exact `1-3` word matches extracted from canonical tweet text
- heatmap ranking supports `mode=common` and `mode=rising`
- heatmap rows are zero-filled for a continuous UTC month timeline
- phrase trends currently use raw monthly matching-tweet counts
- the heatmap drilldown ranks matching tweets within the selected month by `like_count`

Current local BTC coverage begins on `2014-12-01T00:00:00Z` because that is where the FRED `CBBTCUSD` series starts.

## Ingest scripts

The raw ingest scripts live under [backend/scripts/ingest](/Users/michaelsullivan/Code/ChartProject/backend/scripts/ingest).

Before running any ingest, normalization, validation, or enrichment command:

- run `./scripts/setup-db.sh` at least once for the current machine/session
- ensure Docker/Postgres is running and reachable on `localhost:5433`
- ensure [backend/.env](/Users/michaelsullivan/Code/ChartProject/backend/.env) exists and points at the project database
- activate the project virtualenv with `source .venv/bin/activate`

These data scripts do not start Postgres for you. If you see connection errors on `localhost:5432` or `localhost:5433`, first run:

```bash
cd /Users/michaelsullivan/Code/ChartProject
./scripts/setup-db.sh
source .venv/bin/activate
```

### Onboard a new user

Use this order for a new X username:

1. Start the local database and ensure the Python env is ready:

```bash
cd /Users/michaelsullivan/Code/ChartProject
./scripts/setup-db.sh
source .venv/bin/activate
```

2. Run a small first-window ingest to confirm the provider query works:

```bash
python3 backend/scripts/ingest/fetch_user_tweets_history.py \
  --username someuser \
  --since 2024-01-01T00:00:00Z \
  --until 2024-02-01T00:00:00Z \
  --window-months 1
```

3. Run the larger backfill once the first window succeeds:

```bash
python3 backend/scripts/ingest/fetch_user_tweets_history.py \
  --username someuser \
  --since 2024-01-01T00:00:00Z \
  --until 2025-01-01T00:00:00Z \
  --window-months 1
```

4. Normalize the archived raw payloads:

```bash
python3 backend/scripts/normalize/normalize_archived_user.py --username someuser
```

5. Validate canonical rows against the raw corpus:

```bash
python3 backend/scripts/validate/validate_normalized_user.py --username someuser
```

6. Score sentiment on the normalized tweets:

```bash
python3 backend/scripts/enrich/score_tweet_sentiment.py --username someuser
```

7. Score moods on the normalized tweets:

```bash
python3 backend/scripts/enrich/score_tweet_moods.py --username someuser
```

8. Extract phrase keywords on the normalized tweets:

```bash
python3 backend/scripts/enrich/extract_tweet_keywords.py \
  --username someuser \
  --analysis-start 2020-08-01T00:00:00Z
```

9. Confirm the dedicated overview endpoints, mood endpoints, heatmap endpoints, and frontend pages render correctly.

### Preflight checklist

Before starting a new-user run, verify:

- `./scripts/setup-db.sh` completed successfully at least once
- the project Postgres is reachable on `localhost:5433`
- [backend/.env](/Users/michaelsullivan/Code/ChartProject/backend/.env) contains a valid `CHART_DATABASE_URL`
- [backend/.env](/Users/michaelsullivan/Code/ChartProject/backend/.env) contains `CHART_TWITTERAPI_API_KEY`
- the project virtualenv is active via `source .venv/bin/activate`
- commands are being run from the repo root or with paths rooted from the repo root

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

Expected normal outcomes:

- some monthly windows may legitimately return `0` tweets
- an account join date on X does not guarantee the provider search corpus begins on that same date
- the total ingested tweets can differ from the X profile's public `posts` count
- replies and quote tweets are included in the current overview flow
- reposts/retweets may not align with the way X displays profile-level counts

### Fetch raw BTC/USD daily history

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/ingest/fetch_btc_fred_daily.py
```

### Fetch raw MSTR/USD daily history

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/ingest/fetch_equity_twelvedata_daily.py --symbol MSTR --asset-symbol MSTR
```

Useful options:

- `--import-type full_backfill`
- `--import-type refresh`
- `--dry-run`

Current refresh behavior:

- the chart does not call Twelve Data at request time
- MSTR prices are stored locally after ingest and normalization
- running the fetch script again archives a new raw snapshot and the normalize step upserts canonical rows by day
- the current Twelve Data script still requests the provider's full daily history response on each fetch, even for `refresh`
- because normalization is idempotent, rerunning refresh updates local data safely rather than duplicating rows

### Refresh both chart market sources in one pass

```bash
./scripts/refresh-market-data.sh
```

Notes:

- refreshes `BTC/USD` from FRED and `MSTR/USD` from Twelve Data
- normalizes both assets into `market_price_points`
- validates both assets against archived raw payloads
- uses `IMPORT_TYPE=refresh` by default
- you can force a labeled backfill run with `IMPORT_TYPE=full_backfill ./scripts/refresh-market-data.sh`

## Normalization scripts

These commands also require the local project Postgres to already be running.

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

### Normalize archived MSTR price points

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/normalize/normalize_market_price_points.py --asset-symbol MSTR --quote-currency USD --interval day
```

## Validation scripts

These commands also require the local project Postgres to already be running.

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

### Validate normalized MSTR price points

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/validate/validate_market_price_points.py --asset-symbol MSTR --quote-currency USD --interval day
```

## Enrichment scripts

These commands also require the local project Postgres to already be running.

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

Expected normal outcomes:

- Hugging Face may warn about unauthenticated downloads if `HF_TOKEN` is unset
- the RoBERTa load report may show `UNEXPECTED` keys for this checkpoint; that is acceptable in the current setup
- some tweets may be skipped because they are unsupported for scoring after language or preprocessing checks

### Score tweet moods for one or more normalized users

The current mood scorer uses [`SamLowe/roberta-base-go_emotions`](https://huggingface.co/SamLowe/roberta-base-go_emotions).

It stores one row per `(tweet, model_key, mood_label)` in `tweet_mood_scores`.

It currently powers the `#/moods/michael-saylor` page and stores all labels emitted by the model, even though the UI only exposes a curated subset today.

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/enrich/score_tweet_moods.py --username saylor
```

Useful options:

- `--username saylor otheruser`
- `--dry-run`
- `--overwrite-existing`
- `--model-key some-custom-key`
- `--batch-size 16`

Expected normal outcomes:

- Hugging Face may warn about unauthenticated downloads if `HF_TOKEN` is unset
- the RoBERTa load report may show `UNEXPECTED` keys for this checkpoint; that is acceptable in the current setup
- some tweets may be skipped because they are unsupported for scoring after language or preprocessing checks
- the first run may take longer because the model weights need to be downloaded and cached locally
- very long tweets can trigger a tokenizer max-length warning during the truncation check; that warning is non-fatal in the current setup
- truncated tweets are still scored and counted in the `tweets_truncated` summary field

Current scorer behavior:

- reuses the same URL stripping, mention normalization, language filtering, and empty-after-preprocess skip rules as the sentiment scorer
- stores absolute per-label probabilities only
- leaves baseline-relative calculations to the backend view layer
- is reusable for any normalized user by running the same command with a different `--username`
- writes one row per `(tweet, model_key, mood_label)`, so large accounts can generate very large row counts quickly

### Extract exact phrase keywords for one or more normalized users

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
python scripts/enrich/extract_tweet_keywords.py \
  --username saylor \
  --analysis-start 2020-08-01T00:00:00Z
```

Useful options:

- `--username saylor otheruser`
- `--analysis-start 2020-08-01T00:00:00Z`
- `--dry-run`
- `--overwrite-existing`
- `--extractor-key exact-ngram`
- `--extractor-version v1`

Current extractor behavior:

- strips URLs and `@mentions`
- strips leading `$` from ticker-like tokens
- normalizes phrase matching to lowercase exact phrases
- extracts exact `1`, `2`, and `3` word phrases per tweet
- aggressively filters stopword-heavy or generic English fragments
- stores one row per `(tweet, phrase, extractor version)`
- the current Michael Saylor heatmap is intended for the August 2020 onward analysis window

## Add a new page subject

To add a new author cleanly, treat the backend route wiring and frontend page config as two separate steps.

### Add a new overview subject

1. Ensure the user's tweets are ingested, normalized, validated, and sentiment-scored.
2. Add a dedicated route entry in [backend/app/api/routes/views.py](/Users/michaelsullivan/Code/ChartProject/backend/app/api/routes/views.py).
3. Add a frontend entry in [frontend/src/config/overviews.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/overviews.ts).
4. Verify the route renders under `#/overviews/<slug>`.

### Add a new moods subject

1. Ensure the user's tweets are ingested, normalized, validated, and mood-scored.
2. Add a dedicated route entry in [backend/app/api/routes/views.py](/Users/michaelsullivan/Code/ChartProject/backend/app/api/routes/views.py).
3. Add a frontend entry in [frontend/src/config/moods.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/moods.ts).
4. Verify the route renders under `#/moods/<slug>`.

### Add a new heatmap subject

1. Ensure the user's tweets are ingested, normalized, validated, and keyword-extracted.
2. Add a dedicated route entry in [backend/app/api/routes/views.py](/Users/michaelsullivan/Code/ChartProject/backend/app/api/routes/views.py).
3. Add a frontend entry in [frontend/src/config/heatmaps.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/heatmaps.ts).
4. Verify the route renders under `#/heatmaps/<slug>`.

### Recommended data prep order for a new heatmap author

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
python3 backend/scripts/normalize/normalize_archived_user.py --username someuser
python3 backend/scripts/validate/validate_normalized_user.py --username someuser
python3 backend/scripts/enrich/score_tweet_sentiment.py --username someuser
python3 backend/scripts/enrich/extract_tweet_keywords.py \
  --username someuser \
  --analysis-start 2020-08-01T00:00:00Z
```

### Recommended repeatable workflow for a new moods author

Use this when you want to add moods for another author in the future.

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
python3 backend/scripts/normalize/normalize_archived_user.py --username someuser
python3 backend/scripts/validate/validate_normalized_user.py --username someuser
python3 backend/scripts/enrich/score_tweet_moods.py --username someuser
```

Then wire the new author into:

- [backend/app/api/routes/views.py](/Users/michaelsullivan/Code/ChartProject/backend/app/api/routes/views.py)
- [frontend/src/config/moods.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/moods.ts)

### Add more moods to the current moods page

The current GoEmotions scorer already stores every label emitted by the model for each scored tweet.

That means adding another mood label to the page usually does not require rescoring existing users, as long as:

- you keep using the same `model_key`
- the mood label already exists in the underlying model output

For a new display mood label:

1. Add the label to the curated mood list in [backend/app/services/moods.py](/Users/michaelsullivan/Code/ChartProject/backend/app/services/moods.py).
2. Confirm the view returns it from [backend/app/services/author_mood_view.py](/Users/michaelsullivan/Code/ChartProject/backend/app/services/author_mood_view.py).
3. Confirm it appears in the page controls on [frontend/src/pages/AuthorMoodPage.tsx](/Users/michaelsullivan/Code/ChartProject/frontend/src/pages/AuthorMoodPage.tsx).
4. Verify the chart renders cleanly for that label.

You only need a fresh backfill if:

- you switch to a different mood model
- you change the `model_key`
- you want to recompute rows for tweets that were not previously scored under that model key

## Troubleshooting

Common issues during local data work:

- `ModuleNotFoundError: No module named 'sqlalchemy'`
  Use the project virtualenv and sync backend deps:

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
pip install -e backend
```

- Database connection errors referencing `localhost:5432`
  The project database lives on `localhost:5433`. This usually means Postgres is not running or the backend env file was not loaded as expected. Start with:

```bash
cd /Users/michaelsullivan/Code/ChartProject
./scripts/setup-db.sh
source .venv/bin/activate
```

- A first ingest window succeeds for user info but returns `0` tweets
  This can be normal for that time range. Try a slightly later or larger window before assuming the ingest flow is broken.

- The X profile `posts` count does not match the ingested tweet count
  This can happen when platform-visible counts and provider-searchable corpora are not defined the same way.

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
