# Tracked Author Registry And Refresh Plan

## Status

In Progress

## Purpose

This document defines the implementation plan for two related changes:

1. move the current tracked-author source of truth fully into the backend and database
2. add a manual tracked-author refresh workflow with separate `plan`, `fetch`, and `post-process` commands

The goal is to remove hardcoded author lists from the frontend, keep the tracked-author set explicit in the backend, and support repeatable refreshes that only query gaps since the last successful advanced-search window.

## Current State Summary

The tracked-author set currently exists in multiple places:

- frontend static config files for overviews, moods, heatmaps, and bitcoin mentions
- legacy hardcoded per-author backend view routes
- partially populated `managed_author_views`

The current tracked-author set is effectively the same 42 authors across:

- `frontend/src/config/overviews.ts`
- `frontend/src/config/moods.ts`
- `frontend/src/config/heatmaps.ts`
- `frontend/src/config/bitcoinMentions.ts`

The current ingestion stack already supports the core primitives needed for refresh:

- raw user info archive
- raw advanced-search archive by time window
- normalization
- validation
- sentiment scoring
- mood scoring
- keyword extraction
- managed author sync

The missing pieces are:

- a backend-owned tracked-author registry for all primary authors
- frontend cutover away from hardcoded author definitions
- a batch refresh workflow for tracked authors only
- cleanup of the old hardcoded frontend and backend author wiring

## Decisions Locked In

### Tracked-author source of truth

The backend database becomes the single source of truth for tracked authors.

The implementation should extend the existing `managed_author_views` model instead of introducing a second tracked-user registry.

### Initial tracked-author set

The first backend seed should use the exact current 42-author implementation from the frontend configs so the backend matches the app before any frontend hardcoding is removed.

### Publication state

All seeded tracked authors should be published immediately because all of them are already shown in the app.

### Refresh scope

Refresh should only target tracked authors from the backend registry, not all rows in `users`.

### Refresh anchor

Refresh planning should not use `users.last_tweet_seen_at`.

Instead:

- `since` should be the latest successful advanced-search `requested_until` for the author
- `until` should be the exact UTC timestamp when the `plan` command starts

This avoids re-querying long empty periods for dormant users while still checking every tracked author each time the workflow is run.

### Missing ingest history behavior

If a tracked author has no prior successful advanced-search ingest run, the refresh planner should not fetch them automatically. The planner should report that the author requires a manual full-history ingest first.

### Refresh command split

The refresh workflow should be split into three commands:

1. `plan`
2. `fetch`
3. `post-process`

### Post-process eligibility

`post-process` should only run for authors with:

- successful refresh fetches
- nonzero new raw tweets

### Validation

Validation remains mandatory in post-process.

### Artifact storage

Refresh plan and results artifacts should be stored under:

- `data/exports/refresh-plans/`

JSON should be the primary machine-readable format.

## Phase 1: Backend Registry Migration

### Goal

Move the tracked-author set into the backend so the app can stop depending on hardcoded frontend author lists.

### Scope

- seed `managed_author_views` for the current 42 tracked authors
- ensure backend registry entries are complete enough to drive all current author dropdowns
- keep existing frontend and legacy backend behavior working during migration

### Implementation Tasks

1. Inventory current tracked-author data

- extract the current 42 `slug` and `username` pairs from the frontend configs
- confirm all 42 usernames already exist in canonical `users`
- confirm slug uniqueness and current route compatibility

2. Define backend registry completeness rules

For each tracked author, ensure:

- `managed_author_views.user_id` exists
- `slug` matches the currently exposed slug
- `published = true`
- `enable_overview = true`
- `enable_moods = true`
- `enable_heatmap = true`
- `enable_bitcoin_mentions = true`
- missing analysis-start values are backfilled from the first canonical tweet date

3. Add a one-time seed or sync path

Recommended implementation:

- add a script that seeds or reconciles the tracked-author list into `managed_author_views`
- make it idempotent
- fail loudly if a configured username is not present in canonical `users`
- print a summary of created, updated, and unchanged rows

4. Add an audit path

Before frontend hardcoding is removed, add a way to verify that:

- the backend registry contains exactly the expected tracked authors
- each tracked author exposes the expected slug
- the enabled view flags match the current app behavior

### Deliverables

- backend seed or sync script for tracked authors
- backend audit command or script
- `managed_author_views` populated for the current 42 tracked authors

### Acceptance Criteria

- backend registry contains exactly 42 tracked authors
- all 42 are published
- all 42 have stable slugs matching current routes
- all 42 appear in the registry payload with expected enabled views
- no frontend behavior changes yet

### Risks

- slug drift between current frontend routes and seeded registry entries
- canonical username mismatches
- hidden assumptions in legacy hardcoded routes

## Phase 2: Frontend And API Cutover

### Goal

Make the frontend consume backend-owned author definitions instead of hardcoded frontend config lists.

### Scope

- overviews dropdown
- moods dropdown
- heatmaps dropdown
- bitcoin mentions dropdown
- routing paths for author pages

### Implementation Strategy

Use the backend registry and dynamic author routes as the new primary path while leaving legacy backend routes available temporarily for compatibility.

### Implementation Tasks

1. Expand registry usage

Ensure `/api/author-registry` is sufficient to drive:

- slug
- username
- per-view API base paths
- view enablement

2. Switch frontend definition loading

Update frontend state loading so the dropdowns are driven by registry data only.

During migration:

- keep fallback behavior only as long as needed for safe cutover
- remove hardcoded tracked-author definitions after registry-driven behavior is verified

3. Prefer dynamic author endpoints

Frontend should prefer:

- `/api/views/authors/{slug}/overview`
- `/api/views/authors/{slug}/moods`
- `/api/views/authors/{slug}/heatmap`

The bitcoin mentions surface should also be driven by backend registry membership instead of static config.

4. Validate route parity

For each tracked author:

- overview route resolves
- moods route resolves
- heatmap route resolves
- bitcoin mentions route resolves

### Deliverables

- frontend no longer depends on hardcoded tracked-author config files
- public author registry served from a precomputed snapshot instead of a live first-load build
- frontend dropdowns and page routing use backend registry data
- dynamic author endpoints are the main path

### Acceptance Criteria

- all current tracked authors still appear in all expected dropdowns
- order and labels remain acceptable
- author pages still load correctly
- no tracked author exists only in frontend config

### Risks

- registry load timing affecting initial route resolution
- stale assumptions in frontend route parsing
- bitcoin mentions path still depending on a separate static definition shape

## Phase 3: Tracked-Author Refresh Workflow

### Goal

Add a manual CLI workflow to refresh raw tweet history for tracked authors only, then post-process only the authors that actually received new raw tweets.

### Command Set

1. `plan`
2. `fetch`
3. `post-process`

### 3.1 Plan Command

#### Responsibilities

- load tracked authors from the backend registry
- compute the latest successful advanced-search `requested_until` per tracked author
- classify authors into:
  - ready to refresh
  - missing prior successful ingest and needing manual full-history ingest
- write a manifest JSON file
- print a readable summary in the terminal

#### Planner Rules

For each tracked author:

- if no successful `tweet_advanced_search_raw_archive` run exists, classify as `manual_full_history_required`
- otherwise:
  - `since = latest successful requested_until`
  - `until = planner_started_at_utc`
  - include author in refresh manifest

#### Manifest Path

Recommended path pattern:

- `data/exports/refresh-plans/tracked-author-refresh-plan-<timestamp>.json`

#### Manifest Shape

Recommended top-level fields:

```json
{
  "workflow": "tracked-author-refresh-plan",
  "planned_at": "2026-04-14T18:30:00Z",
  "author_source": "managed_author_views",
  "authors_total": 42,
  "authors_planned": 39,
  "authors_manual_full_history_required": 3,
  "planned_authors": [
    {
      "slug": "michael-saylor",
      "username": "saylor",
      "user_id": 123,
      "platform_user_id": "123456",
      "since": "2026-04-01T00:00:00Z",
      "until": "2026-04-14T18:30:00Z",
      "window_months": 1,
      "page_delay_seconds": 0.025
    }
  ],
  "manual_full_history_required_authors": [
    {
      "slug": "example-author",
      "username": "ExampleUser",
      "reason": "No successful advanced-search ingest run was found."
    }
  ]
}
```

#### Deliverables

- planner script
- JSON manifest format
- human-readable terminal summary

### 3.2 Fetch Command

#### Responsibilities

- consume a plan manifest
- run the same advanced-search history flow already used for manual user fetches
- continue on per-author failures
- record detailed results
- print progress in the terminal

#### Fetch Behavior

For each planned author:

- run the existing advanced-search history ingest logic
- use:
  - `import_type = refresh`
  - `window_months = 1`
  - `page_delay_seconds = 0.025` unless overridden later
- skip user-info refresh by default for v1
- fetch-results summarization must still work when user-info refresh is skipped
  - first prefer matching completed runs by `target_user_platform_id`
  - fall back to matching advanced-search runs by username/query notes when `target_user_platform_id` is null

The fetch command should not automatically run normalization or enrichment.

#### Results Path

Recommended path pattern:

- `data/exports/refresh-plans/tracked-author-refresh-results-<timestamp>.json`

#### Results Shape

Recommended per-author fields:

```json
{
  "workflow": "tracked-author-refresh-fetch-results",
  "started_at": "2026-04-14T18:35:00Z",
  "completed_at": "2026-04-14T19:10:00Z",
  "source_plan_path": "data/exports/refresh-plans/tracked-author-refresh-plan-2026-04-14T18-30-00Z.json",
  "authors_attempted": 39,
  "authors_succeeded": 37,
  "authors_failed": 2,
  "results": [
    {
      "username": "saylor",
      "slug": "michael-saylor",
      "status": "completed",
      "run_ids": [6001],
      "requested_since": "2026-04-01T00:00:00Z",
      "requested_until": "2026-04-14T18:30:00Z",
      "pages_fetched": 12,
      "tweets_archived": 47,
      "new_raw_tweets": 47,
      "notes": "..."
    },
    {
      "username": "ExampleUser",
      "slug": "example-author",
      "status": "failed",
      "run_ids": [6002],
      "requested_since": "2026-04-01T00:00:00Z",
      "requested_until": "2026-04-14T18:30:00Z",
      "pages_fetched": 3,
      "tweets_archived": 0,
      "new_raw_tweets": 0,
      "notes": "Provider error ..."
    }
  ]
}
```

`new_raw_tweets` should reflect whether the run produced new unique raw tweets for that author within the refresh window. The `post-process` step will use this field to decide eligibility.

#### Deliverables

- fetch runner script
- results JSON format
- terminal progress reporting
- end-of-run failure summary

### 3.3 Post-Process Command

#### Responsibilities

- consume fetch results
- identify authors eligible for post-processing
- run normalization, validation, sentiment, moods, keywords, and managed author sync
- continue on per-author failures and report them clearly

#### Eligibility Rule

Only include authors where:

- fetch status is `completed`
- `new_raw_tweets > 0`

#### Post-Process Steps Per Author

1. normalize archived raw payloads
2. validate canonical rows against raw artifacts
3. score sentiment
4. score moods
5. extract keywords
6. sync managed author registry row

This is intentionally similar to the existing post-ingest batch flow, but scoped to authors that actually changed.

It should reuse `./scripts/run-user-post-ingest-batch.sh --username <handle>` and should not rerun raw fetches or snapshot rebuilds.

#### Results Path

Recommended path pattern:

- `data/exports/refresh-plans/tracked-author-refresh-post-process-<timestamp>.json`

#### Deliverables

- post-process runner script
- results JSON format
- terminal summary of completed, skipped, and failed authors

### Validation And Performance Notes

Validation remains mandatory, but the current normalization and validation implementations scan the full raw artifact corpus and filter in Python.

That is acceptable for the current manual single-user workflow, but it is a risk for the tracked-author refresh workflow.

Recommended handling:

- keep validation mandatory
- be prepared to tighten normalization and validation query scoping as part of this phase or immediately after initial rollout

### Acceptance Criteria

- planner targets backend tracked authors only
- planner excludes authors without prior successful advanced-search runs and reports them
- fetch continues after per-author failures
- fetch-results correctly summarize created runs whether or not user-info refresh was skipped
- post-process runs only for successful fetches with nonzero new raw tweets
- validation runs for every processed author

## Phase 4: Cleanup And Removal

### Goal

Remove the old hardcoded tracked-author definitions and legacy route surfaces after the new backend-owned path is verified.

### Cleanup Tasks

1. Remove frontend hardcoded tracked-author config lists

- `frontend/src/config/overviews.ts`
- `frontend/src/config/moods.ts`
- `frontend/src/config/heatmaps.ts`
- `frontend/src/config/bitcoinMentions.ts`

2. Remove legacy hardcoded backend author routes

Once frontend and any manual workflows are using backend registry plus dynamic slug-based routes, remove the hardcoded per-author routes from `backend/app/api/routes/views.py`.

3. Update runbooks and docs

- add a tracked-author refresh runbook
- update any onboarding steps that currently assume frontend hardcoded author definitions

### Acceptance Criteria

- tracked-author definitions exist only in backend data
- frontend author dropdowns and author page routes are fully registry-driven
- refresh workflow operates only from backend registry data
- no old hardcoded author surface remains required

## Suggested Execution Order

### Chunk 1

- implement backend tracked-author seed and audit
- populate all 42 tracked authors in `managed_author_views`

### Chunk 2

- cut frontend dropdowns and author page loading to backend registry and dynamic author routes
- verify parity while keeping legacy routes temporarily

### Chunk 3

- implement refresh `plan` command and manifest format
- verify planner output on current data

### Chunk 4

- implement refresh `fetch` command and results format
- verify success, failure handling, and progress reporting

### Chunk 5

- implement `post-process` command
- verify changed-author-only processing and mandatory validation

### Chunk 6

- remove hardcoded frontend configs
- remove legacy backend author routes
- finalize docs and runbooks

## Verification Checklist

### Registry Migration

- all 42 tracked authors exist in `managed_author_views`
- slugs match current expected slugs
- registry payload includes all expected view definitions

### Frontend Cutover

- overviews dropdown matches expected authors
- moods dropdown matches expected authors
- heatmaps dropdown matches expected authors
- bitcoin mentions dropdown matches expected authors
- author pages load from dynamic backend-owned definitions

### Refresh Workflow

- `plan` writes manifest and reports manual-full-history exceptions
- `fetch` produces expected results artifact and continues on failures
- `post-process` skips zero-new-tweet authors and processes changed authors only
- validation failures are surfaced clearly

### Cleanup

- no frontend tracked-author list remains hardcoded
- no legacy hardcoded author route remains required by the frontend

## Open Engineering Notes

- The existing `author-registry` pattern is the right base for centralizing tracked-author metadata.
- The refresh workflow should reuse existing ingest service logic rather than reimplementing advanced-search behavior.
- The manifest and results files are intended to make the workflow inspectable, rerunnable, and resumable in chunks.
- The tracked-author registry should become the authoritative list for any future author-specific app surfaces.
