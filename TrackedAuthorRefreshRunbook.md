# Tracked Author Refresh Runbook

This runbook refreshes tweets for the backend-owned tracked-author set.

It is intentionally split into three separate commands:

1. `plan`
2. `fetch`
3. `post-process`

The tracked-author source of truth now lives in `managed_author_views` and the refresh scope is limited to published tracked authors only.

## Common Bash Recipe: Refresh All Tracked Users

This is the repeatable operator flow when you want to refresh the full tracked-author set and then do the shared aggregate rebuilds manually at the end.

Commands:

```bash
python3 backend/scripts/views/audit_tracked_author_views.py

python3 backend/scripts/ingest/plan_tracked_author_refresh.py

python3 backend/scripts/ingest/fetch_tracked_author_refresh.py \
  --plan /Users/michaelsullivan/Code/ChartProject/data/exports/refresh-plans/tracked-author-refresh-plan-<timestamp>.json

python3 backend/scripts/ingest/post_process_tracked_author_refresh.py \
  --fetch-results /Users/michaelsullivan/Code/ChartProject/data/exports/refresh-plans/tracked-author-refresh-plan-<timestamp>.fetch-results.json

python3 backend/scripts/cache/rebuild_aggregate_snapshots.py --delete-stale
python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py
```

What changed under the hood:

- the command sequence above is still valid
- run the audit first so mood-scored users cannot silently fall outside the tracked refresh scope
- post-process now keeps normalization and validation scoped to the target author's archived raw artifacts
- post-process is still the step that updates each author's sentiment and mood rows after fetch
- post-process now uses the refresh window for keyword extraction and managed narrative sync
- post-process now passes `--only-missing-tweets` to keyword extraction, so reruns avoid rescanning already-tagged tweets in that refresh window

If the audit fails because mood-scored users are not tracked or published, repair them with:

```bash
python3 backend/scripts/views/reconcile_mood_scored_author_views.py
python3 backend/scripts/views/audit_tracked_author_views.py
```

Notes:

- the audit script can still emit `warn` entries for extra tracked users not present in the old 42-name seed list
- the failure you care about for refresh coverage is `excluded_mood_scored_user_count > 0`

## What The Planner Uses

The planner does **not** use `users.last_tweet_seen_at`.

Instead, for each tracked author it uses:

- `since = latest successful tweet_advanced_search_raw_archive requested_until`
- `until = exact UTC time when the plan command starts`

If an author has no prior successful advanced-search history, the planner lists that author as requiring a manual full-history ingest first and does not include them in the fetch manifest.

## Step 1: Plan

Run:

```bash
python3 backend/scripts/ingest/plan_tracked_author_refresh.py
```

Default output:

- `data/exports/refresh-plans/tracked-author-refresh-plan-<timestamp>.json`

Optional flags:

```bash
python3 backend/scripts/ingest/plan_tracked_author_refresh.py \
  --output data/exports/refresh-plans/my-refresh-plan.json \
  --window-months 1 \
  --page-delay-seconds 0.025 \
  --refresh-user-info
```

What it does:

- loads the published tracked-author set from the backend registry
- reports how many mood-scored users exist and how many are excluded from tracked refresh scope
- computes the newest unchecked gap for each author
- writes a JSON manifest for the fetch step
- reports any authors that need a manual full-history ingest first

If the printed summary shows `excluded_mood_scored_user_count > 0`, stop and run:

```bash
python3 backend/scripts/views/reconcile_mood_scored_author_views.py
python3 backend/scripts/views/audit_tracked_author_views.py
python3 backend/scripts/ingest/plan_tracked_author_refresh.py
```

## Step 2: Fetch

Run:

```bash
python3 backend/scripts/ingest/fetch_tracked_author_refresh.py \
  --plan data/exports/refresh-plans/tracked-author-refresh-plan-<timestamp>.json
```

Optional debug mode:

```bash
python3 backend/scripts/ingest/fetch_tracked_author_refresh.py \
  --plan data/exports/refresh-plans/tracked-author-refresh-plan-<timestamp>.json \
  --debug
```

What it does:

- reads the plan manifest
- runs the existing `fetch_user_tweets_history.py` command for each planned author
- continues if one author fails
- writes a fetch-results manifest next to the plan file

Default output:

- `data/exports/refresh-plans/<plan-name>.fetch-results.json`

Important behavior:

- this step only fetches raw data
- user info refresh is skipped by default unless the plan was created with `--refresh-user-info`
- fetch-results summarization supports both cases:
  - runs linked by `target_user_platform_id`
  - runs created with `--skip-user-info`, matched back by username/query notes
- the fetch-results manifest records which authors succeeded and how many new raw tweets were archived

## Step 3: Post-Process

Run:

```bash
python3 backend/scripts/ingest/post_process_tracked_author_refresh.py \
  --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.json
```

Faster refresh mode (defer non-critical sync work):

```bash
python3 backend/scripts/ingest/post_process_tracked_author_refresh.py \
  --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.json \
  --skip-managed-author-sync \
  --skip-managed-narrative-sync
```

What it does:

- reads the fetch-results manifest
- selects only authors with successful fetches and nonzero new raw tweets
- runs normalize and validation per eligible author using only that author's archived raw artifacts
- runs sentiment scoring in one batch across preprocess-ready authors
- runs mood scoring in one batch across preprocess-ready authors
- runs incremental keyword extraction per successful author
- runs managed-author sync and managed narrative sync per successful author
- rebuilds the author-registry snapshot once after successful syncs
- continues if one author fails
- writes a post-process results manifest next to the fetch-results file
- prints top elapsed stages in the summary so bottlenecks are visible per run

Default output:

- `data/exports/refresh-plans/<plan-name>.fetch-results.post-process-results.json`

Important behavior:

- validation remains mandatory because it is part of `run-user-post-ingest-batch.sh`
- authors with zero new raw tweets are skipped automatically
- the tracked refresh post-process batches sentiment scoring across all preprocess-ready users in one command
- the tracked refresh post-process batches mood scoring across all preprocess-ready users in one command
- author mood lines are refreshed by that batched `score_tweet_moods.py` step; they do not wait for aggregate mood snapshot rebuilds
- if a user fails normalize or validate, that user never reaches the batched mood step, so raw tweets can be current while the author's mood line stays stale
- keyword extraction uses each author's refresh-window `since` value from the fetch manifest when available
- keyword extraction passes `--only-missing-tweets`, so already-tagged tweets in that window are skipped
- managed narrative sync uses the same refresh-window `since` value via `--created-since`
- managed author rows are synced per user, but the public author-registry snapshot is rebuilt once at the end
- if you skip per-user syncs, run the deferred sync commands listed below after post-process

What `post-process` runs:

- `python3 backend/scripts/normalize/normalize_archived_user.py --username <handle>`
- `python3 backend/scripts/validate/validate_normalized_user.py --username <handle>`
- `python3 backend/scripts/enrich/score_tweet_sentiment.py --username <all preprocess-ready handles...>`
- `python3 backend/scripts/enrich/score_tweet_moods.py --username <all preprocess-ready handles...>`
- `python3 backend/scripts/enrich/extract_tweet_keywords.py --username <handle> --analysis-start <refresh-since-or-first-normalized-tweet> --only-missing-tweets`
- `python3 backend/scripts/views/sync_managed_author_view.py --username <handle> --published --no-rebuild-snapshot`
- `python3 backend/scripts/enrich/sync_managed_narrative_matches.py --username <handle> --created-since <refresh-since-or-first-normalized-tweet>`
- `python3 backend/scripts/cache/rebuild_author_registry_snapshot.py`
- `python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py`

It does **not** fetch new raw tweets.
It does **not** rebuild aggregate mood snapshots.
It **does** rebuild the author-registry snapshot and aggregate narrative snapshots unless you skip those steps.

### Optional Post-Process Flags

- `--skip-keywords`: skip per-user keyword extraction
- `--skip-managed-author-sync`: skip per-user managed author sync and skip author-registry snapshot rebuild
- `--skip-managed-narrative-sync`: skip per-user managed narrative sync and skip aggregate narrative snapshot rebuild
- `--skip-author-registry-snapshot`: run per-user managed author sync but skip the final author-registry snapshot rebuild
- `--skip-aggregate-narrative-snapshot`: run per-user managed narrative sync but skip the final aggregate narrative snapshot rebuild

### Manual Incremental Rerun Commands

Use these when you need to rerun only the slower post-fetch stages for one author outside the full tracked refresh command.

If raw tweets are current but one or more author mood lines are still behind after a tracked refresh, rerun the same post-process manifest before fetching again:

```bash
python3 backend/scripts/ingest/post_process_tracked_author_refresh.py \
  --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.json
```

Then inspect:

- `data/exports/refresh-plans/<plan-name>.fetch-results.post-process-results.json`

Look for users with:

- `failed_step = "normalize_archived_user"`
- `failed_step = "validate_normalized_user"`
- `failed_step = "score_tweet_sentiment"`
- `failed_step = "score_tweet_moods"`

Those are the failure modes that leave author mood lines stale even when the fetch step succeeded.

Incremental keyword extraction:

```bash
python3 backend/scripts/enrich/extract_tweet_keywords.py \
  --username <USERNAME> \
  --analysis-start <REFRESH_SINCE_UTC> \
  --only-missing-tweets
```

Incremental managed narrative sync:

```bash
python3 backend/scripts/enrich/sync_managed_narrative_matches.py \
  --username <USERNAME> \
  --created-since <REFRESH_SINCE_UTC>
```

Add `--overwrite-existing` only when you intentionally want to rebuild rows already in scope.

### Deferred Sync Commands (When Using Skip Flags)

If you run `post-process` with `--skip-managed-author-sync` and/or `--skip-managed-narrative-sync`, run these once at the end:

```bash
python3 backend/scripts/views/seed_tracked_author_views.py
python3 backend/scripts/cache/rebuild_author_registry_snapshot.py
python3 backend/scripts/enrich/sync_managed_narrative_matches.py
python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py
```

## Manual Full-History Catch-Up

If the plan manifest reports a tracked author as requiring manual full-history ingest first, run the normal history command manually for that author:

```bash
python3 backend/scripts/ingest/fetch_user_tweets_history.py \
  --username EXAMPLE_USER_HERE \
  --since 2020-01-01T00:00:00Z \
  --until 2026-04-12T00:00:00Z \
  --window-months 1 \
  --page-delay-seconds 0.025 \
  --debug
```

Then rerun the tracked-author refresh planner.

## Notes

- `fetch` and `post-process` are safe to rerun from their manifest files.
- The refresh manifests are stored in-repo under `data/exports/refresh-plans/`.
- Author-registry snapshot refresh is included in post-process.
- Aggregate mood snapshots still require a separate rebuild command.

## Troubleshooting Older Fetch-Results Manifests

If you created a fetch-results manifest before the fetch summarizer fix, you might see:

- `success_count` looks correct
- but every result has `completed_window_run_count = 0`
- `run_ids = []`
- `new_raw_tweets = 0`

That means the underlying fetch subprocesses likely succeeded, but the manifest failed to correlate the created ingestion runs back to the planned authors.

Repair the manifest without calling the provider again:

```bash
python3 backend/scripts/ingest/repair_tracked_author_refresh_fetch_results.py \
  --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.json
```

Then use the repaired manifest for post-process:

```bash
python3 backend/scripts/ingest/post_process_tracked_author_refresh.py \
  --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.repaired.json
```

## First Refresh Run Checklist

For a first refresh run in a new environment or after script changes:

- run `plan`
- run `fetch`
- inspect fetch-results summary and verify `run_ids` and `new_raw_tweets` look reasonable
- if all users show `run_ids = []` and `new_raw_tweets = 0`, run the repair script above
- run `post-process` using the repaired manifest when needed
- rebuild aggregate snapshots after post-process

## Author Registry Cache

The public `/api/author-registry` response is now served from a cached snapshot so the frontend does not have to wait for the full live registry build on first load.

Warm just the author registry cache:

```bash
python3 backend/scripts/cache/rebuild_author_registry_snapshot.py
```

Or rebuild it alongside the existing aggregate snapshot flow:

```bash
cd backend
python3 scripts/cache/rebuild_aggregate_snapshots.py
```

`rebuild_aggregate_snapshots.py` now includes the author-registry snapshot by default unless you explicitly disable it with `--no-author-registry`.
