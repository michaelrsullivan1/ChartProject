# ChartProject

ChartProject is a local-first X/Twitter research archive and visualization system.

The architecture source of truth is [ProjectPlan.md](/Users/michaelsullivan/Code/ChartProject/ProjectPlan.md).

Related architecture notes:

- [Podcast Transcripts Investigation](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-transcripts-investigation.md)
- [Podcast Exploration Map](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-exploration-map.md)
- [Podcast Visual Directions](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-visual-directions.md)
- [Podcast Person-First Implementation Plan](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-person-first-implementation-plan.md)
- [Podcast Snapshot Layout Audit](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-snapshot-layout-audit.md)
- [Podcast Schema Refinement](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-schema-refinement.md)
- [Podcast Implementation Status](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-implementation-status-2026-04-22.md)
- [Podcast Future Ingest Guardrails](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-future-ingest-guardrails.md)

## Current state

One full local flow is working end-to-end:

- containerized Postgres on Docker Compose
- Alembic migrations through `0009_managed_author_views`
- FastAPI backend with health, user settings, overview, mood, aggregate mood, Bitcoin mentions, and heatmap view routes
- React frontend with a Foundation page, shared overview pages, shared mood pages, shared heatmap pages, and a user settings page for cohort management
- raw-first X/Twitter ingest archived into Postgres via `raw_ingestion_artifacts`
- canonical normalization and validation for archived `saylor` tweet history
- raw BTC/USD FRED ingest plus canonical normalization and validation
- raw MSTR/USD Twelve Data ingest plus canonical normalization and validation
- versioned RoBERTa tweet sentiment scoring stored in Postgres
- versioned RoBERTa multilabel tweet mood scoring stored in Postgres
- versioned exact phrase extraction stored in Postgres via `tweet_keywords`
- managed cohort tags stored in Postgres via `cohort_tags` and `user_cohort_tags`
- managed author page registry stored in Postgres via `managed_author_views`
- precomputed aggregate mood snapshots stored in Postgres via `aggregate_view_snapshots`
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
- [http://127.0.0.1:5173/#/moods/michael-sullivan](http://127.0.0.1:5173/#/moods/michael-sullivan) shows the Michael Sullivan moods page
- [http://127.0.0.1:5173/#/bitcoin-mentions](http://127.0.0.1:5173/#/bitcoin-mentions) shows the Bitcoin mentions timing analysis page
- [http://127.0.0.1:5173/#/price-mentions](http://127.0.0.1:5173/#/price-mentions) shows the price mentions heatmap (BTC price level density over time, cohort-filtered)
- [http://127.0.0.1:5173/#/price-mentions/distribution](http://127.0.0.1:5173/#/price-mentions/distribution) shows price mentions by price level distribution (cohort vs. baseline step-chart overlay)
- [http://127.0.0.1:5173/#/price-mentions/zscore](http://127.0.0.1:5173/#/price-mentions/zscore) shows price mentions Poisson Z-score deviation by price level for a selected cohort
- [http://127.0.0.1:5173/#/heatmaps/michael-saylor](http://127.0.0.1:5173/#/heatmaps/michael-saylor) shows the Michael Saylor phrase heatmap
- [http://127.0.0.1:5173/#/heatmaps/michael-sullivan](http://127.0.0.1:5173/#/heatmaps/michael-sullivan) shows the Michael Sullivan phrase heatmap
- [http://127.0.0.1:5173/#/settings/user-settings](http://127.0.0.1:5173/#/settings/user-settings) shows the user settings page for cohort tag management

The Foundation page still runs the backend health check and renders the full JSON response.

The overview pages currently:

- request an overview endpoint such as `/api/views/authors/michael-saylor/overview?granularity=week`
- renders BTC, MSTR, activity, and sentiment panes with a shared time axis
- keeps BTC daily and tweet counts weekly in the current UI
- shows hover state for the active date
- loads the top liked tweet for the clicked week from a companion backend endpoint

The heatmap pages currently:

- request a heatmap endpoint such as `/api/views/authors/michael-saylor/heatmap?mode=common&word_count=all&granularity=month&limit=48`
- render a monthly phrase heatmap in the top pane
- support `Common` and `Rising` ranking modes
- support `All`, `1 word`, `2 words`, and `3 words` filters
- load the selected phrase trend on demand in the bottom pane
- load the top liked matching tweets for a clicked month from a companion backend endpoint

The mood pages currently:

- request a mood overview endpoint such as `/api/views/authors/michael-saylor/moods?granularity=week`
- request a companion mood series endpoint such as `/api/views/authors/michael-saylor/moods/mood-series?granularity=week`
- render BTC in the top pane and the selected mood deviation in the bottom pane
- default to relative-to-baseline mood deviation with the same weighted smoothing modes as the sentiment page
- expose the full GoEmotions label set currently stored in the database, including `admiration`, `amusement`, `anger`, `annoyance`, `approval`, `caring`, `confusion`, `curiosity`, `desire`, `disappointment`, `disapproval`, `disgust`, `embarrassment`, `excitement`, `fear`, `gratitude`, `grief`, `joy`, `love`, `nervousness`, `neutral`, `optimism`, `pride`, `realization`, `relief`, `remorse`, `sadness`, and `surprise`
- store absolute per-tweet mood scores in Postgres and compute relative deviation at request time

The aggregate mood pages currently:

- request `/api/views/aggregate-moods?granularity=week` for the cached aggregate activity payload
- request `/api/views/aggregate-moods/mood-series?granularity=week` for the cached aggregate mood-series payload
- request `/api/views/aggregate-moods/outliers?granularity=week` for cached per-mood outlier rankings
- request `/api/views/aggregate-moods/market-series?range_start=<iso>&range_end=<iso>` for BTC and MSTR history
- request `/api/views/aggregate-moods/cohorts` to populate the available cohort filters
- support a single cohort filter at a time via `cohort_tag=<slug>`
- default to `All tracked users`, which means every eligible user with scored mood data
- only show cohort tags on the aggregate page when at least one eligible user is assigned to that tag
- keep overview metrics and mood-series calculations aligned by applying the same filtered user scope to both cached endpoints
- store one current snapshot per aggregate view/cohort/model combination instead of rebuilding aggregate payloads on every page load

The user settings page currently:

- lists only users with scored mood data for the active/default mood model
- lets you create centrally managed cohort tags
- lets you assign or remove those managed tags per eligible user
- does not support freeform user labels
- does not yet support tag rename or tag deletion flows

## Cohort tags

Cohort tags are the mechanism used to filter Aggregate Moods by subsets of users.

Current rules:

- cohort tags are stored as managed records in `cohort_tags`
- user-to-tag assignments are stored in `user_cohort_tags`
- tag `name` is the readable UI label such as `Bitcoin Treasury Leadership`
- tag `slug` is the normalized lowercase identifier used by APIs such as `bitcoin-treasury-leadership`
- eligibility is based on scored mood data for the active/default mood model
- `All tracked users` includes every eligible user, whether they have tags or not
- aggregate mood pages only show tags that currently have at least one eligible assigned user
- aggregate mood filtering is single-select; there is no multi-tag filtering yet
- the user settings page shows all managed tags, even if none are currently assigned to eligible users

The Bitcoin mentions page currently:

- requests `/api/views/bitcoin-mentions?username=<handle>&phrase=bitcoin&buy_amount_usd=10`
- pairs exact tweet timestamps with the stored BTC daily UTC close for that date
- models the result of buying a fixed dollar amount of BTC on every matching mention
- ranks configured authors by average BTC entry price across their matched mentions
- lists the cheapest and full-history Bitcoin mentions for the selected author

Managed author registry:

- `/api/author-registry` returns published, ready author definitions for frontend page controls
- frontend route definitions are now dynamically merged from this registry at app startup
- new users no longer require manual per-user route/config edits when registry sync is run

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

Rebuild aggregate mood snapshots after mood scoring, new-user onboarding, or cohort changes:

```bash
cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --delete-stale
```

Force-clear and rebuild aggregate snapshots when you want an immediate full refresh after cohort/tag changes:

```bash
cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --clear-first --delete-stale
```

Apply the latest database migrations, including the podcast schema:

```bash
cd backend
../.venv/bin/alembic upgrade head
```

Run the first-pass podcast snapshot import after the Belief Engines archive has been extracted:

```bash
cd backend
../.venv/bin/python scripts/ingest/import_podcast_snapshot.py
```

Dry-run a smaller import slice when iterating on the loader:

```bash
cd backend
../.venv/bin/python scripts/ingest/import_podcast_snapshot.py --limit-shows 2 --limit-persons 5 --dry-run
```

Check the Postgres container:

```bash
docker compose ps
```

Stop the local Postgres container:

```bash
docker compose down
```

Resume the existing local stack after a normal reboot or shutdown:

```bash
./scripts/dev.sh
```

If the container runtime is already healthy, this should reuse the existing Postgres container state and named volume rather than creating a fresh database.

## Local setup details

The local database is intentionally containerized and defined in [compose.yaml](/Users/michaelsullivan/Code/ChartProject/compose.yaml).

The Postgres service stores its data in the named Docker volume `chartproject_postgres_data`.

Normal restarts such as laptop shutdowns, restarts, or `docker compose up -d postgres` should reuse that existing volume and preserve data.

Treat the following as destructive to the local database contents:

- `./scripts/restore-db.sh`
- `docker compose down -v`
- deleting the `chartproject_postgres_data` volume from the container runtime UI or CLI

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

Important exported analysis outputs now include:

- `data/exports/refresh-plans/`
- `data/exports/dynamics-scout/`

## Current implementation details

### Core tables currently in use

- `users`
- `cohort_tags`
- `user_cohort_tags`
- `tweets`
- `tweet_keywords`
- `tweet_price_mentions`
- `tweet_references`
- `market_price_points`
- `aggregate_view_snapshots`
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
7. Enrich canonical tweets with Bitcoin price mention rows in `tweet_price_mentions` (regex + context scoring, retweet-excluded).
8. Rebuild aggregate mood snapshots when aggregate mood inputs change.
9. Build request-time backend view payloads from canonical tables for the remaining live endpoints.
10. Render the current frontend chart pages from those backend view payloads.

## Dynamics Scout

Dynamics Scout is the manual analysis workflow for finding interesting cross-user, cross-cohort, and BTC-linked dynamics without having to visually inspect the dashboards first.

It is intentionally split into two layers:

1. a deterministic scout script that computes objective findings and writes structured outputs
2. a Codex skill that reads the latest scout outputs and turns them into higher-level storylines and hypotheses

### When to use it

Run Dynamics Scout when you want a fresh ranked list of potentially interesting things to investigate, such as:

- user mood outliers versus personal baseline
- cohort mood outliers
- cohort-versus-cohort mood divergence
- user-versus-cohort divergence
- BTC-linked mood correlation or anti-correlation
- recent BTC decoupling
- possible lead-lag relationships with BTC
- regime shifts in mood behavior

This is a manual workflow. It does not run on a schedule unless you explicitly wire that up later.

### Scout command

From the repo root:

```bash
./scripts/scout-dynamics.sh
```

That wrapper runs:

```bash
python3 backend/scripts/analysis/find_interesting_dynamics.py
```

If the repo virtualenv exists, the wrapper prefers `.venv/bin/python3`. Otherwise it falls back to `python3`.

### Useful variants

Full scout:

```bash
./scripts/scout-dynamics.sh
```

Smaller scout for one mood:

```bash
./scripts/scout-dynamics.sh --mood-label optimism
```

Recent-only scout:

```bash
./scripts/scout-dynamics.sh --analysis-start 2025-01-01T00:00:00Z
```

Smaller output set:

```bash
./scripts/scout-dynamics.sh --limit 100 --top-markdown-findings 20
```

### What the script writes

Each run creates a timestamped folder under:

- `data/exports/dynamics-scout/<timestamp>/`

Inside each run:

- `summary.json`
- `summary.md`

The script also refreshes stable pointers:

- `data/exports/dynamics-scout/latest.json`
- `data/exports/dynamics-scout/latest.md`
- `data/exports/dynamics-scout/latest-interpretation.md`

`summary.json` is the machine-readable output. `summary.md` is the quick human-readable leaderboard/report.

### What the script currently scores

The scout currently mixes findings into one combined leaderboard and retains the strongest results by `interestingness_score`.

Current finding families include:

- `user_mood_outlier`
- `cohort_mood_outlier`
- `cohort_vs_cohort_divergence`
- `user_vs_cohort_divergence`
- `btc_level_correlation`
- `btc_return_correlation`
- `btc_decoupling`
- `btc_lead_lag_signal`
- `regime_shift`

The current implementation uses weekly data, an `8w` weighted moving average, and a trailing `52w` baseline window by default.

### Dynamics Scout skill

A repository-local Codex skill now lives at:

- `.codex/skills/dynamics-scout/`

The skill is meant to be used after a scout run exists. It reads:

- `data/exports/dynamics-scout/latest.md`
- `data/exports/dynamics-scout/latest.json`

and then produces:

- the strongest storylines
- recurring cross-patterns
- higher-level hypotheses worth investigating

The skill is intentionally not focused on chart navigation or UI click paths. Its job is to synthesize what looks interesting now.

The skill should also persist its interpretation output, not just print it in Codex. The expected markdown outputs are:

- `data/exports/dynamics-scout/latest-interpretation.md`
- `data/exports/dynamics-scout/<latest-run>/interpretation.md`

where `<latest-run>` is the newest timestamped scout run directory.

### Recommended workflow

1. Run `./scripts/scout-dynamics.sh`
2. Inspect `data/exports/dynamics-scout/latest.md` if you want the raw scout output
3. Ask Codex to use the `dynamics-scout` skill to interpret the latest run and surface the strongest themes
4. The interpretation should be written to `data/exports/dynamics-scout/latest-interpretation.md` and to the latest timestamped scout run folder

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

The current chart flow is registry-first for managed authors. Core endpoints:

```text
/api/author-registry
/api/author-registry/admin
/api/views/authors/{slug}/overview?granularity=week
/api/views/authors/{slug}/overview/top-liked-tweet?week_start=2024-01-01T00:00:00Z
/api/views/authors/{slug}/overview/sentiment
/api/views/authors/{slug}/overview/btc-spot
/api/views/authors/{slug}/moods?granularity=week
/api/views/authors/{slug}/moods/mood-series?granularity=week
/api/views/authors/{slug}/moods/btc-spot
/api/views/authors/{slug}/heatmap?mode=common&word_count=all&granularity=month&limit=48
/api/views/authors/{slug}/heatmap/phrase-trend?phrase=bitcoin&granularity=month
/api/views/authors/{slug}/heatmap/top-liked-tweets?phrase=bitcoin&month_start=2026-03-01T00:00:00Z&limit=3
/api/views/aggregate-moods?granularity=week
/api/views/aggregate-moods?granularity=week&cohort_tag=bitcoin
/api/views/aggregate-moods/mood-series?granularity=week
/api/views/aggregate-moods/mood-series?granularity=week&cohort_tag=bitcoin
/api/views/aggregate-moods/outliers?granularity=week
/api/views/aggregate-moods/outliers?granularity=week&cohort_tag=bitcoin
/api/views/aggregate-moods/market-series?range_start=2016-01-04T00:00:00Z&range_end=2026-04-06T00:00:00Z
/api/views/aggregate-moods/cohorts
/api/views/price-mentions?granularity=month&cohort_tag=<slug>&min_confidence=0.5&mention_type=prediction
/api/views/bitcoin-mentions?username={handle}&phrase=bitcoin&buy_amount_usd=10
/api/user-settings/cohort-tags
/api/user-settings/users
/api/user-settings/users/{user_id}/cohort-tags
```

Current behavior:

- registry-backed slug routes support newly ingested users without manual route wiring
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
- aggregate mood pages compute mood deviation against each included user's own historical baseline, then average those deviations in a user-balanced way
- aggregate mood overview and aggregate mood-series payloads are precomputed into `aggregate_view_snapshots`
- aggregate mood overview and aggregate mood-series endpoints share the same eligible-user cohort filter so tracked users, scored posts, baselines, and plotted mood series stay consistent
- aggregate mood cohort filtering currently accepts a single `cohort_tag` slug or no tag for the all-users view
- aggregate market history is fetched separately so BTC and MSTR updates do not require rebuilding aggregate mood snapshots
- the current mood UI is curated to six labels, but the scorer stores every label emitted by the configured model
- heatmap rows are phrase-level exact `1-3` word matches extracted from canonical tweet text
- heatmap ranking supports `mode=common` and `mode=rising`
- heatmap rows are zero-filled for a continuous UTC month timeline
- phrase trends currently use raw monthly matching-tweet counts
- the heatmap drilldown ranks matching tweets within the selected month by `like_count`
- user settings cohort tags are intentionally normalized into dedicated tables rather than stored as freeform text on `users`

Current local BTC coverage begins on `2014-12-01T00:00:00Z` because that is where the FRED `CBBTCUSD` series starts.

## Ingest scripts

The raw ingest scripts live under [backend/scripts/ingest](/Users/michaelsullivan/Code/ChartProject/backend/scripts/ingest).

For the current one-command-at-a-time operator workflow for ingesting a single user, see [TweetIngestionRunbook.md](/Users/michaelsullivan/Code/ChartProject/TweetIngestionRunbook.md).
For tracked-author batch refreshes, see [TrackedAuthorRefreshRunbook.md](/Users/michaelsullivan/Code/ChartProject/TrackedAuthorRefreshRunbook.md).

### Tracked-author refresh workflow

Use this sequence for tracked-author refreshes:

1. plan
2. fetch
3. post-process

Commands:

```bash
python3 backend/scripts/views/audit_tracked_author_views.py
python3 backend/scripts/ingest/plan_tracked_author_refresh.py
python3 backend/scripts/ingest/fetch_tracked_author_refresh.py --plan data/exports/refresh-plans/<plan-name>.json
python3 backend/scripts/ingest/post_process_tracked_author_refresh.py --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.json
```

Current post-process behavior:

- normalization and validation are scoped to the target user's archived raw artifacts rather than the full raw archive
- sentiment and mood scoring stay batched across all preprocess-ready users
- author mood lines are refreshed during that batched mood-scoring step
- keyword extraction uses the refresh manifest `since` window when available and passes `--only-missing-tweets`
- managed narrative sync uses the same refresh window via `--created-since`

If raw tweets are current but author mood lines are still behind, rerun the same post-process manifest before fetching again:

```bash
python3 backend/scripts/ingest/post_process_tracked_author_refresh.py \
  --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.json
```

Then inspect:

- `data/exports/refresh-plans/<plan-name>.fetch-results.post-process-results.json`

Users that fail `normalize_archived_user`, `validate_normalized_user`, `score_tweet_sentiment`, or `score_tweet_moods` will keep stale author mood lines even when the fetch step succeeded.

If the audit or planner reports `excluded_mood_scored_user_count > 0`, repair coverage first:

```bash
python3 backend/scripts/views/reconcile_mood_scored_author_views.py
python3 backend/scripts/views/audit_tracked_author_views.py
```

If an older fetch-results manifest reports all users with `run_ids = []` and `new_raw_tweets = 0`, repair it before post-process:

```bash
python3 backend/scripts/ingest/repair_tracked_author_refresh_fetch_results.py \
  --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.json
python3 backend/scripts/ingest/post_process_tracked_author_refresh.py \
  --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.repaired.json
```

Cache responsibilities after refresh:

- post-process refreshes the author-registry snapshot
- post-process also refreshes per-author mood rows; it does not wait for aggregate mood snapshots
- aggregate mood snapshots still require:

```bash
cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --delete-stale
```

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

This updates the individual author mood line directly from stored `tweet_mood_scores`. Aggregate mood pages still require the separate snapshot rebuild step below.

8. Extract phrase keywords on the normalized tweets:

```bash
python3 backend/scripts/enrich/extract_tweet_keywords.py \
  --username someuser \
  --analysis-start 2020-08-01T00:00:00Z
```

For an incremental rerun on an already-processed user, prefer:

```bash
python3 backend/scripts/enrich/extract_tweet_keywords.py \
  --username someuser \
  --analysis-start 2020-08-01T00:00:00Z \
  --only-missing-tweets
```

9. Extract Bitcoin price mentions on the normalized tweets:

```bash
python3 backend/scripts/enrich/extract_tweet_price_mentions.py \
  --username someuser \
  --analysis-start 2020-08-01T00:00:00Z \
  --only-missing-tweets
```

This populates `tweet_price_mentions` and makes the user's data available in the Price Mentions heatmap, distribution, and Z-score pages. The `--only-missing-tweets` flag makes reruns safe and fast.

10. Sync the managed author registry row so the frontend auto-lists the new user:

```bash
python3 backend/scripts/views/sync_managed_author_view.py --username someuser --published
```

11. Sync managed narrative matches:

```bash
python3 backend/scripts/enrich/sync_managed_narrative_matches.py --username someuser
```

For an incremental rerun on only the recent refresh window, prefer:

```bash
python3 backend/scripts/enrich/sync_managed_narrative_matches.py \
  --username someuser \
  --created-since 2026-03-27T00:00:00Z
```

12. Rebuild aggregate mood snapshots so Aggregate Moods includes the latest scored/cohort data:

```bash
python3 backend/scripts/cache/rebuild_aggregate_snapshots.py --clear-first --delete-stale
```

13. Rebuild aggregate narrative snapshots:

```bash
python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py
```

14. Confirm the registry-backed overview endpoints, mood endpoints, aggregate mood endpoints, heatmap endpoints, price mentions pages, and frontend pages render correctly.

Batch alternative after ingest:

```bash
./scripts/run-user-post-ingest-batch.sh --username someuser --analysis-start 2020-08-01T00:00:00Z
```

By default, this runs normalize through both aggregate snapshot rebuilds (steps 4–14 above), including price mention extraction. Price mention extraction runs with `--only-missing-tweets` so it is fast on incremental re-runs.

If you are ingesting many users in one session, skip per-user snapshot rebuilds and rebuild once at the end:

```bash
./scripts/run-user-post-ingest-batch.sh \
  --username someuser \
  --analysis-start 2020-08-01T00:00:00Z \
  --no-rebuild-snapshots
```

After all users are processed, run one shared rebuild pass:

```bash
python3 backend/scripts/cache/rebuild_aggregate_snapshots.py --delete-stale
python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py
```

## Aggregate snapshot workflow

Aggregate Moods now uses precomputed snapshot payloads stored in `aggregate_view_snapshots`.

Snapshot rows exist for:

- `aggregate-cohorts`
- `aggregate-overview`
- `aggregate-mood-series`
- `aggregate-mood-outliers`
- `aggregate-cohort-mood-outliers`

Each row is keyed by:

- view type
- cohort slug
- granularity
- mood model key
- cache version

The expensive aggregate mood payloads are meant to be rebuilt intentionally, while BTC and MSTR market history is fetched separately.

### When to rebuild aggregate snapshots

Run the rebuild after any change that affects aggregate mood outputs:

- after scoring moods for a newly onboarded or updated user
- after rescoring moods for an existing user
- after changing user cohort assignments
- after creating, deleting, or renaming cohort tags in a way that changes aggregate cohort membership or available cohort filters
- after adding or removing a tracked user from the aggregate set
- after changing aggregate mood response logic
- after changing the active mood model used for aggregate views

Practical operator rule:

- if you changed anything that affects `tweet_mood_scores`, aggregate-user eligibility, `cohort_tags`, or `user_cohort_tags`, rerun the snapshot rebuild
- snapshot rebuilds are manual; user settings cohort edits do not auto-refresh aggregate snapshot rows

Common examples that should trigger a rebuild:

- you ingested one additional user and then scored moods for that user
- you changed cohort assignments from the user settings page
- you rescored mood rows with `--overwrite-existing`
- you changed which cohort tags exist or which users belong to them

You do not need to rebuild aggregate snapshots just because BTC or MSTR market data changed.

You also do not need to rebuild them for:

- frontend-only changes
- sentiment-only changes
- keyword-only changes
- heatmap-only changes
- overview page changes that do not alter aggregate mood payload logic

### Rebuild command

From the repo root:

```bash
cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --delete-stale
```

Force-refresh variant (clear existing snapshot rows first, then rebuild):

```bash
cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --clear-first --delete-stale
```

What this does:

- rebuilds the `aggregate-cohorts` snapshot
- rebuilds `aggregate-overview` for `all` and every eligible cohort
- rebuilds `aggregate-mood-series` for `all` and every eligible cohort
- rebuilds `aggregate-mood-outliers` for `all` and every eligible cohort
- rebuilds `aggregate-cohort-mood-outliers`
- upserts the latest snapshot rows into Postgres
- removes stale snapshot rows for the same model/granularity when `--delete-stale` is used
- optionally clears existing rows first when `--clear-first` is used (full rebuild only)

Useful variants:

```bash
cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --dry-run
python3 scripts/cache/rebuild_aggregate_snapshots.py --clear-first --dry-run
python3 scripts/cache/rebuild_aggregate_snapshots.py --cohort mstr
python3 scripts/cache/rebuild_aggregate_snapshots.py --view aggregate-mood-series
python3 scripts/cache/rebuild_aggregate_snapshots.py --view aggregate-mood-outliers
```

Scoped rebuild note:

- `--delete-stale` and `--clear-first` are full-rebuild-only flags and cannot be combined with `--view` or `--cohort`
- for a scoped outlier-only rebuild, run `python3 scripts/cache/rebuild_aggregate_snapshots.py --view aggregate-mood-outliers`

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

It currently powers the `#/moods/*` pages and stores all labels emitted by the model. The UI now exposes the full GoEmotions label set by default.

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
- `--only-missing-tweets`
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
- `--only-missing-tweets` limits work to tweets that do not yet have keyword rows for that extractor
- the current Michael Saylor heatmap is intended for the August 2020 onward analysis window

### Extract Bitcoin price mentions for one or more normalized users

```bash
cd /Users/mike/ChartProject
source .venv/bin/activate
cd backend
python scripts/enrich/extract_tweet_price_mentions.py \
  --username saylor \
  --analysis-start 2020-08-01T00:00:00Z
```

Useful options:

- `--username saylor otheruser`
- `--analysis-start 2020-08-01T00:00:00Z`
- `--only-missing-tweets`
- `--dry-run`
- `--overwrite-existing`
- `--extractor-version v2`

Current extractor behavior:

- two-stage regex + context scoring — no LLM calls, no external network, ~1ms per tweet
- extracts explicit numeric Bitcoin price mentions in the $10k–$10M range
- handles `$100k`, `$1.5M`, plain numbers, written-out amounts, approximate modifiers, and explicit/shared-suffix ranges
- context-scores each candidate against BTC keywords (positive) and non-BTC tickers/contexts (negative)
- classifies each mention as `prediction`, `conditional`, `current`, `historical`, or `unclassified`
- excludes retweets (joined on `tweet_references`); includes quote tweets and replies
- stores one row per `(tweet_id, price_usd, extractor_key, extractor_version)` — unique constraint prevents duplicates
- `--only-missing-tweets` skips tweets that already have rows for the current extractor+version (safe for incremental runs)

For a full incremental pass over all tracked/published users:

```bash
./scripts/run-price-mentions-extraction.sh
```

Full reprocess after extractor tuning or version bump:

```bash
./scripts/run-price-mentions-extraction.sh --full
```

Single user, full reprocess:

```bash
./scripts/run-price-mentions-extraction.sh --username saylor --full
```

## Publish or tune a page subject

For newly ingested users, do not add new frontend config entries or new dedicated backend routes. Use the managed author registry instead.

### Default publish flow

1. Complete ingest + normalization + validation + sentiment + moods + keyword extraction.
2. Run:

```bash
python3 backend/scripts/views/sync_managed_author_view.py --username someuser --published
```

3. Verify the user appears in `/api/author-registry` under the relevant lists (`overviews`, `moods`, `heatmaps`, `bitcoin_mentions`).
4. Verify `#/overviews/<slug>`.
5. Verify `#/moods/<slug>`.
6. Verify `#/heatmaps/<slug>`.
7. Verify `#/bitcoin-mentions/<slug>`.

### Optional admin tuning via API

You can tune slug, publish state, sort order, enabled views, and per-view analysis starts:

```bash
curl -X PUT "http://127.0.0.1:8000/api/author-registry/<user_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "some-slug",
    "published": true,
    "sort_order": 100,
    "enable_overview": true,
    "enable_moods": true,
    "enable_heatmap": true,
    "enable_bitcoin_mentions": true
  }'
```

And inspect the full managed state:

```bash
curl "http://127.0.0.1:8000/api/author-registry/admin"
```

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
python3 backend/scripts/views/sync_managed_author_view.py --username someuser --published
```

### Recommended repeatable workflow for a new moods author

Use this when you want to add moods for another author in the future.

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
python3 backend/scripts/normalize/normalize_archived_user.py --username someuser
python3 backend/scripts/validate/validate_normalized_user.py --username someuser
python3 backend/scripts/enrich/score_tweet_moods.py --username someuser
python3 backend/scripts/views/sync_managed_author_view.py --username someuser --published
```

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

- The frontend health card shows `status=degraded` and `database.status=unavailable`
  The backend is up, but Postgres is not reachable. If the database was already working before a reboot or shutdown, start by bringing the container runtime back and then rerun:

```bash
cd /Users/michaelsullivan/Code/ChartProject
./scripts/dev.sh
curl http://127.0.0.1:8000/api/health
```

- The frontend shows `Unexpected token '<', "<!doctype "... is not valid JSON` for backend requests
  The frontend is receiving HTML (usually Vite index) instead of proxied API JSON. Confirm [frontend/vite.config.ts](/Users/michaelsullivan/Code/ChartProject/frontend/vite.config.ts) proxy target points to the running backend host and port (for local default: `http://127.0.0.1:8000`), then restart Vite.

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

- Rancher Desktop on macOS reports `vz driver is running but host agent is not`
  This can happen after an unclean VM shutdown. Confirm the container daemon is actually healthy first:

```bash
docker info
```

If `docker info` fails and Rancher Desktop shows that exact `vz driver is running but host agent is not` message, a common cause is a stale runtime file in the Rancher Desktop Lima instance. The safe first response is:

```bash
osascript -e 'quit app "Rancher Desktop"' || true
sleep 2

cd "$HOME/Library/Application Support/rancher-desktop/lima/0"
mkdir -p "$HOME/Desktop/rancher-lima-backup"
cp -p vz.pid ha.stderr.log ha.stdout.log lima.yaml ssh.config "$HOME/Desktop/rancher-lima-backup/" 2>/dev/null || true

rm -f vz.pid ha.sock default_ep.sock default_fd.sock
rm -f "$HOME/.rd/docker.sock"

open -a "Rancher Desktop"
docker info
```

That cleanup removes stale runtime markers only. It does not remove the VM disk or the Docker volumes.

- Rancher Desktop stopped working after a QEMU upgrade or Rancher Desktop upgrade
  Verify the local QEMU binary is new enough for the current Rancher Desktop build:

```bash
/opt/homebrew/bin/qemu-system-aarch64 --version
```

If Rancher Desktop complains that QEMU is too old, update it with Homebrew before troubleshooting the project itself:

```bash
sudo xcodebuild -license accept
brew upgrade qemu || brew reinstall qemu
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
