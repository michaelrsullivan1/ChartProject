# Aggregate Narratives Runbook

This runbook describes how the managed `Aggregate Narratives` feature works in ChartProject.

It is separate from the older author-level Narratives/Heatmap flow.

Use this document when you need to:

- understand what Aggregate Narratives is measuring
- add or edit managed narratives in Global Settings
- rebuild narrative matches after data or phrase changes
- troubleshoot why a phrase is not appearing or has low counts

## What Aggregate Narratives Is

Aggregate Narratives is a curated phrase-tracking feature for the aggregate dashboard.

It is designed to answer:

- how often a specific managed phrase appears in tracked-user tweets
- how that weekly volume changes over time
- how that volume differs across user cohorts

It does **not** try to discover new narratives automatically.

It uses only the phrases explicitly created in Global Settings.

## What Aggregate Narratives Is Not

Aggregate Narratives is **not** the same thing as the older author heatmap narrative feature.

The older narrative heatmap:

- uses extracted keyword phrases
- is discovery-oriented
- is per-author
- currently works on monthly buckets

Aggregate Narratives:

- uses explicitly managed phrases
- is tracking-oriented
- is aggregate and cohort-aware
- uses weekly buckets

The two systems intentionally coexist.

## Current Product Rules

These are the current implementation rules.

### Phrase source of truth

Managed narratives are stored in the database and edited from Global Settings.

### One narrative = one phrase

Each managed narrative is currently one explicit phrase.

No alias support is enabled yet.

### Matching behavior

Matching is:

- case-insensitive
- whitespace-normalized
- token-based phrase matching

Practical effects:

- `MSTR` matches `mstr`
- `Bitcoin Treasury` matches `bitcoin treasury`
- repeated use of the same phrase in one tweet still counts only once

### Counting rule

The metric is:

- number of tweets containing the phrase

It is **not**:

- number of times the phrase appears inside tweets

### Granularity

Aggregate Narratives currently uses weekly buckets only.

### Aggregate population

Aggregate Narratives currently uses:

- published tracked authors
- with canonical tweets

It does **not** depend on mood-score eligibility.

## Data Flow

The feature has four main layers.

### 1. Managed narrative catalog

Stored in:

- `managed_narratives`

This is the curated list of tracked phrases.

### 2. Tweet-to-narrative match rows

Stored in:

- `tweet_narrative_matches`

This records whether a tweet matched a managed narrative.

There is at most one row per:

- `tweet_id`
- `managed_narrative_id`

### 3. Aggregate weekly snapshots

Stored in:

- `aggregate_view_snapshots`

View types used by this feature:

- `aggregate-narrative-cohorts`
- `aggregate-narrative-series`

### 4. Frontend aggregate page

The page reads snapshot-backed data and lets the user:

- select one managed narrative
- select one cohort
- pin a comparison cohort

## Main UI Entry Points

### Global Settings

Use Global Settings to:

- create managed narratives
- edit managed narratives

### Aggregate Narratives page

Use the top navigation `Aggregate Narratives` page to:

- view the managed narrative list in a dropdown
- select a cohort
- pin a cohort comparison
- inspect weekly volume history

## Normal Workflow

### Add a new managed narrative

1. Open Global Settings
2. Add the phrase
3. Wait for the create request to complete

Current behavior:

- the phrase is saved
- narrative matches for that phrase are rebuilt
- aggregate narrative snapshots are rebuilt

That means the new phrase should become available on the Aggregate Narratives page after the request finishes and the frontend is refreshed if needed.

### Edit an existing managed narrative

1. Open Global Settings
2. Edit the phrase
3. Save

Current behavior:

- the phrase row is updated
- old match rows for that narrative are rebuilt
- aggregate narrative snapshots are rebuilt

## Manual Rebuild Commands

Use these when:

- new tweets were added outside the normal flow
- you want to backfill after schema changes
- you suspect snapshot staleness
- you want to verify matching behavior against the full dataset

Run from the repo root:

```bash
cd /Users/michaelsullivan/Code/ChartProject
```

### Rebuild narrative match rows

```bash
python3 backend/scripts/enrich/sync_managed_narrative_matches.py --overwrite-existing
```

What it does:

- scans tweets in scope
- matches them against managed phrases
- rewrites `tweet_narrative_matches`

### Rebuild aggregate narrative snapshots

```bash
python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py
```

What it does:

- rebuilds cohort metadata snapshot
- rebuilds aggregate narrative weekly snapshots for `all` and all cohorts

### Rebuild only one cohort

```bash
python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py --cohort <cohort-slug>
```

### Dry-run the match sync

```bash
python3 backend/scripts/enrich/sync_managed_narrative_matches.py --dry-run
```

### Dry-run the snapshot rebuild

```bash
python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py --dry-run
```

## Post-Ingest Behavior

The single-user post-ingest flow now also includes managed narrative syncing.

Relevant paths:

- `scripts/run-user-post-ingest-batch.sh`
- `backend/scripts/ingest/post_process_tracked_author_refresh.py`

Current behavior:

- new tweets are normalized and scored
- keyword extraction still runs for the older heatmap feature
- managed narrative matches are synced for the updated user
- aggregate narrative snapshots are rebuilt in the tracked-author refresh flow

## Troubleshooting

### I created a narrative and nothing showed up

Check these in order:

1. backend request completed successfully
2. aggregate snapshots rebuilt successfully
3. the Aggregate Narratives page is refreshed
4. the phrase actually matches tracked-user tweet text under current rules

If needed, rerun:

```bash
python3 backend/scripts/enrich/sync_managed_narrative_matches.py --overwrite-existing
python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py
```

### The phrase exists in tweets but still shows zero

Most likely causes:

- the phrase is not an exact normalized token sequence match
- the phrase appears only in users outside the tracked published author set
- the phrase is conceptually present but written differently than expected

Examples:

- `microstrategy` will not match `mstr`
- `btc treasury` will not match `bitcoin treasury`

### A save in Global Settings fails

Common causes:

- duplicate phrase after normalization
- duplicate slug or derived name
- snapshot rebuild failure after the row is written

Check the backend traceback first.

### Aggregate page looks stale

Run:

```bash
python3 backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py
```

Then refresh the frontend.

## Matching Notes

The current matcher intentionally keeps behavior narrow and predictable.

It normalizes tweet text by:

- lowercasing
- removing URLs
- removing `@mentions`
- normalizing hashtags to plain tokens
- stripping leading `$` and `#` from tokens
- converting `₿` to `bitcoin`

This helps common crypto-style formatting but still keeps matching explicit.

## Review Points For Future Work

These are the main areas to revisit if the feature evolves.

### Aliases

If users want one narrative to track multiple spellings, add alias support rather than loosening the current matching rules globally.

### Phrase labels vs stored phrase

Right now the UI mostly treats the phrase as the display label.

If editorial labels need to diverge from raw match phrases, make the UI expose `name` more explicitly.

### Aggregate page payload size

The current snapshot includes all managed narratives for a cohort.

That is fine while the managed narrative list is small to moderate.

If the list grows a lot, split the page into:

- bootstrap metadata
- selected narrative series endpoint

### Richer metrics

The current primary metric is tweet volume.

Future extensions could add:

- distinct-user count
- share of cohort tweets
- example tweets or top matching tweets

## Key Files

Backend:

- `backend/app/services/managed_narratives.py`
- `backend/app/services/aggregate_narrative_view.py`
- `backend/app/api/routes/global_settings.py`
- `backend/app/api/routes/views.py`
- `backend/scripts/enrich/sync_managed_narrative_matches.py`
- `backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py`

Frontend:

- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/AggregateNarrativesPage.tsx`
- `frontend/src/api/globalSettings.ts`
- `frontend/src/api/aggregateNarratives.ts`

Planning reference:

- `docs/architecture/aggregate-narratives-plan.md`
