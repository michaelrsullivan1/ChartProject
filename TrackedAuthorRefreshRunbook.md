# Tracked Author Refresh Runbook

This runbook refreshes tweets for the backend-owned tracked-author set.

It is intentionally split into three separate commands:

1. `plan`
2. `fetch`
3. `post-process`

The tracked-author source of truth now lives in `managed_author_views` and the refresh scope is limited to published tracked authors only.

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
- computes the newest unchecked gap for each author
- writes a JSON manifest for the fetch step
- reports any authors that need a manual full-history ingest first

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
- the fetch-results manifest records which authors succeeded and how many new raw tweets were archived

## Step 3: Post-Process

Run:

```bash
python3 backend/scripts/ingest/post_process_tracked_author_refresh.py \
  --fetch-results data/exports/refresh-plans/<plan-name>.fetch-results.json
```

What it does:

- reads the fetch-results manifest
- selects only authors with successful fetches and nonzero new raw tweets
- runs `./scripts/run-user-post-ingest-batch.sh --username <handle>` for each eligible author
- continues if one author fails
- writes a post-process results manifest next to the fetch-results file

Default output:

- `data/exports/refresh-plans/<plan-name>.fetch-results.post-process-results.json`

Important behavior:

- validation remains mandatory because it is part of `run-user-post-ingest-batch.sh`
- authors with zero new raw tweets are skipped automatically

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
- Legacy hardcoded backend author routes still exist for compatibility, but the frontend author definitions no longer depend on the removed static config files.
