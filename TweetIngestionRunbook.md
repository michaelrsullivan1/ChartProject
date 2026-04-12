# Tweet Ingestion Runbook

This is the current operator flow for ingesting a single X/Twitter user into ChartProject.

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

For page onboarding, this flow now uses managed author registry sync and no longer requires manual route/config edits for new users.

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

### 7. Sync managed author registry

What it does:

- creates or updates a `managed_author_views` row for the user
- derives a stable slug if one does not already exist
- fills missing per-view `analysis_start` values from the first normalized tweet date
- marks the user published for `/api/author-registry` by default

Command:

```bash
python3 backend/scripts/views/sync_managed_author_view.py --username <USERNAME> --published
```

### Optional: Batch Steps 2-7

If step 1 has already completed successfully, you can run steps 2, 3, 4, 5, 6, and 7 in one command.

Script:

```bash
./scripts/run-user-post-ingest-batch.sh --username <USERNAME> --analysis-start <KEYWORD_ANALYSIS_START_UTC>
```

If you omit `--analysis-start`, the script auto-resolves the user's first normalized tweet timestamp from canonical `tweets` and uses that for step 6:

```bash
./scripts/run-user-post-ingest-batch.sh --username <USERNAME>
```

Behavior:

- runs only steps 2-7
- does not run step 1 ingest
- does not run aggregate snapshot rebuild
- defaults step 6 `--analysis-start` to the user's first normalized tweet timestamp
- runs step 7 managed author registry sync for the username
- stops on the first failure
- prints which step failed, the command, and exit code
- leaves all underlying commands unchanged so each can still be rerun manually

### 8. Rebuild aggregate snapshots

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
- this step is intentionally independent and not included in the step 2-7 batch script

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
python3 backend/scripts/views/sync_managed_author_view.py --username <USERNAME> --published
cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py --delete-stale
cd ..
```

## Copy/Paste Example (Batched Steps 2-7)

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
- a `managed_author_views` row exists for the user
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

## Managed Author Registry (Current Flow)

For newly ingested users, local page registration is now handled by the managed author registry.

`./scripts/run-user-post-ingest-batch.sh` now runs a step `7` sync that calls:

```bash
python3 backend/scripts/views/sync_managed_author_view.py --username <USERNAME> --published
```

That sync step automatically:

- creates or updates a row in `managed_author_views`
- derives a stable slug from display name or username
- fills missing `analysis_start` defaults from the user's first normalized tweet date
- publishes the user for `/api/author-registry` so the frontend can auto-list them

### Repeatable checklist

Use this sequence every time:

1. Run step 1 ingest independently.
2. Run steps 2-7 with `./scripts/run-user-post-ingest-batch.sh`.
3. Run snapshot rebuild independently.
4. Start or refresh the local app if needed.
5. Verify the user appears in page controls and managed pages.

## Legacy Manual Route/Config Workflow

The old per-author route/config wiring flow is no longer the default and should not be used for new users.

For new users:

- do not add dedicated route handlers in [backend/app/api/routes/views.py](/Users/michaelsullivan/Code/ChartProject/backend/app/api/routes/views.py)
- do not add manual entries in frontend config files
- run managed author sync and verify `/api/author-registry`
- verify `#/overviews/<slug>`
- verify `#/moods/<slug>`
- verify `#/heatmaps/<slug>`
- verify `#/bitcoin-mentions/<slug>`
