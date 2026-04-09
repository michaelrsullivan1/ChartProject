# Tweet Ingestion Runbook

This is the current manual operator flow for ingesting a single X/Twitter user into ChartProject.

The intended usage is:

1. Run one command at a time in bash.
2. Confirm each command succeeds before moving to the next one.
3. Use the exact same order every time.

This runbook covers the full path:

- raw tweet-history ingest
- canonical normalization
- canonical validation
- sentiment scoring
- mood scoring
- keyword extraction

## Preflight

Before starting, make sure:

- Docker is running
- the local Postgres container is available on `localhost:5433`
- [backend/.env](/Users/michaelsullivan/Code/ChartProject/backend/.env) contains `CHART_DATABASE_URL`
- [backend/.env](/Users/michaelsullivan/Code/ChartProject/backend/.env) contains `CHART_TWITTERAPI_API_KEY`

If the project is already running and the virtualenv is already active, you do not need to rerun setup.

Minimum working shell state:

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
```

Run the full setup only when needed:

```bash
cd /Users/michaelsullivan/Code/ChartProject
./scripts/setup-db.sh
source .venv/bin/activate
```

`./scripts/setup-db.sh` will create the virtualenv if needed, install the backend package, start Docker Postgres, and apply migrations.

## Timestamp Rules

Use ISO 8601 UTC timestamps with a trailing `Z`.

Examples:

- `2024-01-01T00:00:00Z`
- `2026-04-10T00:00:00Z`

For a full-history ingest:

- `--since` should be the date of the user's earliest post you want to cover
- `--until` should usually be the next UTC midnight after the most recent day you want included

Example:

- if you want coverage through `2026-04-09`, use `--until 2026-04-10T00:00:00Z`

## Preferred Full-User Flow

Replace these placeholders before running:

- `<USERNAME>`: X handle without `@`
- `<FIRST_POST_UTC>`: earliest UTC timestamp you want to include
- `<UNTIL_UTC>`: UTC end timestamp for the backfill window
- `<KEYWORD_ANALYSIS_START_UTC>`: UTC date where phrase analysis should begin

### 1. Ingest raw tweet history

What it does:

- fetches raw user info first
- fetches advanced-search tweet history in monthly windows
- archives raw payloads into Postgres

Current preferred flags:

- `--window-months 1`
- `--page-delay-seconds 0.25`
- `--debug`

Command:

```bash
python3 backend/scripts/ingest/fetch_user_tweets_history.py \
  --username <USERNAME> \
  --since <FIRST_POST_UTC> \
  --until <UNTIL_UTC> \
  --window-months 1 \
  --page-delay-seconds 0.25 \
  --debug
```

Notes:

- this is the main full-history ingest command
- the script does not support `--resume-run-id`
- some windows can legitimately return `0` tweets
- the raw provider corpus may start later than the first date you requested

### 2. Normalize archived raw payloads

What it does:

- reads archived raw artifacts from Postgres
- upserts canonical users, tweets, and tweet references

Command:

```bash
python3 backend/scripts/normalize/normalize_archived_user.py --username <USERNAME>
```

Expected output includes:

- normalized tweet count
- raw distinct tweet count
- first and last raw tweet timestamps
- first and last normalized tweet timestamps

Important interpretation:

- if normalization reports the first raw tweet later than your requested `--since`, that means the ingest worked but the provider returned no earlier tweets for that user

### 3. Validate canonical rows against raw artifacts

What it does:

- checks that canonical users, tweets, and references match the archived raw corpus
- exits non-zero on validation failure

Command:

```bash
python3 backend/scripts/validate/validate_normalized_user.py --username <USERNAME>
```

Optional:

```bash
python3 backend/scripts/validate/validate_normalized_user.py \
  --username <USERNAME> \
  --sample-limit 20
```

### 4. Score sentiment

What it does:

- runs the canonical tweets through the default sentiment model
- stores versioned sentiment rows in Postgres

Command:

```bash
python3 backend/scripts/enrich/score_tweet_sentiment.py --username <USERNAME>
```

Expected output includes:

- tweets considered
- tweets scored
- tweets skipped
- tweets truncated
- selected inference device such as `mps`, `cuda`, or `cpu`

### 5. Score moods

What it does:

- runs the canonical tweets through the default multilabel mood model
- stores versioned mood rows in Postgres

Command:

```bash
python3 backend/scripts/enrich/score_tweet_moods.py --username <USERNAME>
```

Important downstream effect:

- this step makes the user eligible for the tracked-user mood and cohort flows used by the user settings page and aggregate mood views

### 6. Extract keywords

What it does:

- extracts exact `1` to `3` word phrases from canonical tweets
- stores versioned phrase rows in Postgres

Command:

```bash
python3 backend/scripts/enrich/extract_tweet_keywords.py \
  --username <USERNAME> \
  --analysis-start <KEYWORD_ANALYSIS_START_UTC>
```

Recommendation:

- set `--analysis-start` to the first date you want included in phrase analysis
- using the user's first normalized tweet date is a good default

## Copy/Paste Example

This is the full sequence in the preferred order:

```bash
cd /Users/michaelsullivan/Code/ChartProject
./scripts/setup-db.sh
source .venv/bin/activate

python3 backend/scripts/ingest/fetch_user_tweets_history.py \
  --username <USERNAME> \
  --since <FIRST_POST_UTC> \
  --until <UNTIL_UTC> \
  --window-months 1 \
  --page-delay-seconds 0.25 \
  --debug

python3 backend/scripts/normalize/normalize_archived_user.py --username <USERNAME>
python3 backend/scripts/validate/validate_normalized_user.py --username <USERNAME>
python3 backend/scripts/enrich/score_tweet_sentiment.py --username <USERNAME>
python3 backend/scripts/enrich/score_tweet_moods.py --username <USERNAME>
python3 backend/scripts/enrich/extract_tweet_keywords.py \
  --username <USERNAME> \
  --analysis-start <KEYWORD_ANALYSIS_START_UTC>
```

## What Success Looks Like

After the full sequence succeeds:

- the user exists in canonical `users`
- the user's tweets exist in canonical `tweets`
- sentiment rows exist for the user
- mood rows exist for the user
- keyword rows exist for the user
- the user should appear in [user settings](http://127.0.0.1:5173/#/settings/user-settings) once the app is running

## After Ingestion

Start the app locally:

```bash
cd /Users/michaelsullivan/Code/ChartProject
./scripts/dev.sh
```

Then verify:

- [http://127.0.0.1:5173/#/settings/user-settings](http://127.0.0.1:5173/#/settings/user-settings) shows the user
- the user can be assigned to cohort tags there if needed

## Add The User To Local Pages

For a newly ingested user, data pipeline completion is not enough by itself.

If you want the user to show up in the local UI controls and dedicated pages, add the user in both places:

- [backend/app/api/routes/views.py](/Users/michaelsullivan/Code/ChartProject/backend/app/api/routes/views.py)
- the frontend config lists under [frontend/src/config](/Users/michaelsullivan/Code/ChartProject/frontend/src/config)

This is usually part of the same unit of work as ingesting the user.

### Backend routes to add

Add dedicated entries for:

- overview
- overview top-liked tweet
- overview sentiment
- overview BTC spot
- moods
- mood series
- moods BTC spot
- heatmap
- heatmap phrase trend
- heatmap top-liked tweets

Use the real username and a clean slug. Set `analysis_start` to the beginning of the actual usable analysis window for that user.

### Frontend config entries to add

Add the user to:

- [frontend/src/config/overviews.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/overviews.ts)
- [frontend/src/config/moods.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/moods.ts)
- [frontend/src/config/heatmaps.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/heatmaps.ts)
- [frontend/src/config/bitcoinMentions.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/bitcoinMentions.ts)

That is what makes the user appear in the overview, moods, heatmap, and Bitcoin mentions page controls.

### Current example: Chris Millas

Current local subject wiring for `ChrisMMillas` uses:

- slug: `chris-millas`
- username: `ChrisMMillas`
- analysis start: `2024-09-09T00:00:00Z`

After adding the routes and config entries, verify:

- `#/overviews/chris-millas`
- `#/moods/chris-millas`
- `#/heatmaps/chris-millas`
- `#/bitcoin-mentions/chris-millas`
