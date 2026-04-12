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

### Optional: Batch Steps 2-6

If step 1 has already completed successfully, you can run steps 2, 3, 4, 5, and 6 in one command.

Script:

```bash
./scripts/run-user-post-ingest-batch.sh --username <USERNAME> --analysis-start <KEYWORD_ANALYSIS_START_UTC>
```

If you omit `--analysis-start`, the script auto-resolves the user's first normalized tweet timestamp from canonical `tweets` and uses that for step 6:

```bash
./scripts/run-user-post-ingest-batch.sh --username <USERNAME>
```

Behavior:

- runs only steps 2-6
- does not run step 1 ingest
- does not run step 7 snapshot rebuild
- defaults step 6 `--analysis-start` to the user's first normalized tweet timestamp
- stops on the first failure
- prints which step failed, the command, and exit code
- leaves all underlying commands unchanged so each can still be rerun manually

### 7. Rebuild aggregate snapshots

What it does:

- rebuilds the precomputed aggregate mood payloads stored in `aggregate_view_snapshots`
- ensures Aggregate Moods reflects the latest scored users and cohort assignments

Command:

```bash
cd /Users/michaelsullivan/Code/ChartProject/backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --delete-stale
```

Important downstream effect:

- this is the command that makes newly scored users and updated cohort assignments show up correctly in Aggregate Moods without waiting for request-time recomputation
- this step is intentionally independent and not included in the step 2-6 batch script

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
cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --delete-stale
cd ..
```

## Copy/Paste Example (Batched Steps 2-6)

Use this when you want ingest isolated, then a single post-ingest batch command:

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate

python3 backend/scripts/ingest/fetch_user_tweets_history.py \
  --username <USERNAME> \
  --since <FIRST_POST_UTC> \
  --until <UNTIL_UTC> \
  --window-months 1 \
  --page-delay-seconds 0.25 \
  --debug

./scripts/run-user-post-ingest-batch.sh \
  --username <USERNAME> \
  --analysis-start <KEYWORD_ANALYSIS_START_UTC>

cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --delete-stale
cd ..
```

## What Success Looks Like

After the full sequence succeeds:

- the user exists in canonical `users`
- the user's tweets exist in canonical `tweets`
- sentiment rows exist for the user
- mood rows exist for the user
- aggregate snapshot rows were rebuilt after the mood changes
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
- if cohort assignments were changed, rerun `python3 scripts/cache/rebuild_aggregate_snapshots.py --delete-stale` from `backend/`

## Add The User To Local Pages

For a newly ingested user, data pipeline completion is not enough by itself.

If you want the user to show up in the local UI controls and dedicated pages, add the user in both places:

- [backend/app/api/routes/views.py](/Users/michaelsullivan/Code/ChartProject/backend/app/api/routes/views.py)
- the frontend config lists under [frontend/src/config](/Users/michaelsullivan/Code/ChartProject/frontend/src/config)

This is usually part of the same unit of work as ingesting the user.

### Repeatable checklist

Use this sequence every time:

1. Run step 1 ingest independently.
2. Run steps 2-6 either manually or with `./scripts/run-user-post-ingest-batch.sh`.
3. Run step 7 snapshot rebuild independently.
4. Choose the final slug for the user.
5. Decide the `analysis_start` timestamp.
6. Add the dedicated backend routes in [backend/app/api/routes/views.py](/Users/michaelsullivan/Code/ChartProject/backend/app/api/routes/views.py).
7. Add the frontend config entries under [frontend/src/config](/Users/michaelsullivan/Code/ChartProject/frontend/src/config).
8. Start or refresh the local app if needed.
9. Verify the user appears in the page controls and the dedicated URLs load.

### Slug and analysis-start rules

Use a clean slug:

- lowercase
- words separated by hyphens
- usually derived from the display name

Examples:

- `ChrisMMillas` -> `chris-millas`
- `RichardByworth` -> `richard-byworth`

Set `analysis_start` deliberately:

- for overviews and moods, use the beginning of the intended analysis window
- for heatmaps, use the same beginning of the intended phrase-analysis window unless there is a specific reason to start later
- this does not have to be the exact first normalized tweet timestamp down to the second
- in practice, using the start-of-day UTC boundary is cleaner

Examples:

- if the first normalized tweet is `2024-09-09T09:16:38Z`, use `2024-09-09T00:00:00Z`
- if you intentionally backfilled from March 2019, use `2019-03-01T00:00:00Z`

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

Use the real username and chosen slug consistently in every route.

### Backend route pattern

For one user, the backend pattern is:

```python
@router.get("/<slug>-overview")
@router.get("/<slug>-overview/top-liked-tweet")
@router.get("/<slug>-overview/sentiment")
@router.get("/<slug>-overview/btc-spot")

@router.get("/<slug>-moods")
@router.get("/<slug>-moods/mood-series")
@router.get("/<slug>-moods/btc-spot")

@router.get("/<slug>-heatmap")
@router.get("/<slug>-heatmap/phrase-trend")
@router.get("/<slug>-heatmap/top-liked-tweets")
```

Map them to the canonical username and view names:

- username: exact stored X handle, such as `RichardByworth`
- view name: slug-based string such as `richard-byworth-overview`
- analysis start: UTC timestamp string such as `2019-03-01T00:00:00Z`

### Frontend config entries to add

Add the user to:

- [frontend/src/config/overviews.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/overviews.ts)
- [frontend/src/config/moods.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/moods.ts)
- [frontend/src/config/heatmaps.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/heatmaps.ts)
- [frontend/src/config/bitcoinMentions.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/config/bitcoinMentions.ts)

That is what makes the user appear in the overview, moods, heatmap, and Bitcoin mentions page controls.

### Frontend config pattern

Add one entry per file:

```ts
{
  slug: "<slug>",
  username: "<USERNAME>",
  apiBasePath: "/api/views/<slug>-overview",
}
```

```ts
{
  slug: "<slug>",
  username: "<USERNAME>",
  apiBasePath: "/api/views/<slug>-moods",
}
```

```ts
{
  slug: "<slug>",
  username: "<USERNAME>",
  apiBasePath: "/api/views/<slug>-heatmap",
}
```

```ts
{
  slug: "<slug>",
  username: "<USERNAME>",
}
```

### Verification URLs

After adding backend routes and frontend config, verify:

- `#/overviews/<slug>`
- `#/moods/<slug>`
- `#/heatmaps/<slug>`
- `#/bitcoin-mentions/<slug>`

Also confirm the user appears in the relevant dropdowns or page controls.

### Worked examples

#### Chris Millas

Current local subject wiring for `ChrisMMillas` uses:

- slug: `chris-millas`
- username: `ChrisMMillas`
- analysis start: `2024-09-09T00:00:00Z`

- `#/overviews/chris-millas`
- `#/moods/chris-millas`
- `#/heatmaps/chris-millas`
- `#/bitcoin-mentions/chris-millas`

#### Richard Byworth

Current local subject wiring for `RichardByworth` uses:

- slug: `richard-byworth`
- username: `RichardByworth`
- analysis start: `2019-03-01T00:00:00Z`

- `#/overviews/richard-byworth`
- `#/moods/richard-byworth`
- `#/heatmaps/richard-byworth`
- `#/bitcoin-mentions/richard-byworth`
