# Aggregate Narratives Plan

## Status

Proposed

## Purpose

This document defines the implementation plan for a new `Aggregate Narratives` feature built around explicitly managed narrative phrases.

The goal is to add a new aggregate narrative workflow that:

1. uses a constrained list of phrases defined in Global Settings
2. tracks weekly narrative volume at the tweet level
3. supports aggregate cohort comparison with the same cohort-selection and pinning model used by Aggregate Moods
4. avoids the compute cost and noise of open-ended keyword extraction

This plan intentionally preserves the existing author-level Narratives/Heatmap feature as a separate system. The new aggregate narrative workflow is a new concept, not a replacement for the current heatmap-driven narrative discovery flow.

## Problem Summary

The current narrative heatmap system is useful for discovery, but it is not a good fit for the new aggregate narrative use case.

Current issues:

- the keyword universe is too large because it is generated from open-ended 1/2/3-gram extraction
- many extracted phrases are noisy, uninteresting, or only weakly related to real narratives
- aggregate computation over the full extracted phrase set would be slow and expensive
- the existing per-author heatmap UI is optimized for phrase discovery, not for explicit phrase tracking across cohorts
- the existing narrative service currently supports monthly buckets only

The new aggregate feature should solve a narrower problem:

- explicitly track a curated list of important narratives
- measure weekly tweet volume for those narratives
- compare those narratives across all tracked users or a single cohort

## Product Scope

### In Scope

- new Global Settings management for curated narratives
- new backend storage for managed narrative definitions
- new backend storage for tweet-to-narrative matches
- weekly aggregate narrative series for all tracked users and cohort subsets
- new `Aggregate Narratives` page
- cohort selection and pinning behavior similar to Aggregate Moods
- precomputed caching and snapshot-style delivery for fast page loads

### Out Of Scope

- replacing the current author Narratives/Heatmap page
- removing or deprecating keyword extraction
- narrative discovery from uncataloged phrases
- aliases, categories, tags, featured ordering, or active/inactive toggles
- multi-phrase narratives
- regex or fuzzy semantic matching

## Decisions Locked In

### Existing narrative heatmap stays in place

The current author heatmap narrative experience remains largely unchanged.

This new work adds a second narrative system for explicit phrase tracking rather than replacing the keyword heatmap flow.

### Managed narratives are single phrases

Each managed narrative is a single explicit phrase entered by the user in Global Settings.

No alias support is required for v1.

### Matching behavior

Matching should be rough but basically exact:

- case-insensitive
- whitespace-normalized
- intended to behave like exact phrase matching after normalization

V1 should not support:

- aliases
- regex patterns
- semantic expansion
- broad substring matching without boundaries

### Counting rule

A tweet counts at most once per narrative.

If a phrase appears multiple times in the same tweet, it still contributes only one match for that tweet.

### Primary metric

Aggregate narrative ranking and comparison should use total tweet volume.

The primary series value is:

- number of tweets in the bucket that contain the managed narrative phrase

### Granularity

The new aggregate narrative system should use weekly buckets.

### Aggregate page interaction model

The new aggregate page should be phrase-driven, not heatmap-driven.

The page should:

- let the user choose a managed narrative from a dropdown or selector
- let the user choose a cohort or all tracked users
- let the user pin a comparison cohort

The page should not include the large phrase-ranking heatmap from the existing narrative page.

### Settings placement

Managed narratives should be created and edited from the existing Global Settings surface.

### Caching strategy

Aggregate narrative views should be precomputed and cached.

They should not be built from raw live aggregation on each page load.

## Current State Summary

The current codebase already has several useful building blocks:

- a simple settings-management pattern for cohort tags in `frontend/src/pages/UserSettingsPage.tsx`
- aggregate cohort selection and pinning behavior in `frontend/src/pages/AggregateMoodPage.tsx`
- aggregate snapshot storage in `aggregate_view_snapshots`
- aggregate snapshot read/write helpers in `backend/app/services/aggregate_snapshot_cache.py`
- snapshot rebuild scripting in `backend/scripts/cache/rebuild_aggregate_snapshots.py`

The current narrative implementation differs substantially from the desired feature:

- keyword extraction is generated from open-ended exact n-grams
- the author heatmap view groups by extracted keyword and currently supports `granularity=month` only
- the existing UI is built around ranking and browsing many extracted phrases rather than tracking a small managed list

## Target User Experience

### Global Settings

Global Settings should expose a new managed narratives section where the user can:

- view the current list of narratives
- add a new narrative phrase
- edit an existing narrative phrase

The UI can follow the same simple pattern currently used for cohort-tag creation:

- one input or edit form
- one list of existing managed rows
- lightweight validation and error handling

### Aggregate Narratives Page

The new page should appear as a separate route and concept, titled `Aggregate Narratives`.

Recommended page behavior:

1. load the managed narrative list
2. load available cohorts
3. show one selected narrative at a time
4. show weekly aggregate volume for the selected cohort
5. optionally overlay a pinned comparison cohort

Recommended controls:

- narrative selector
- selected cohort control
- pinned comparison cohort control

Recommended summary cards:

- tracked narrative
- selected cohort
- total matching tweets
- latest weekly count
- peak weekly count

Recommended chart:

- weekly line or bar series for the selected narrative
- optional comparison series for pinned cohort

This page should not include:

- phrase heatmaps
- keyword ranking modes
- keyword search
- uncataloged phrase discovery

## Architecture Overview

The new feature should use a managed phrase catalog plus a normalized match table.

High-level flow:

1. user creates or edits narrative phrases in Global Settings
2. backend matching job evaluates tweets against managed phrases
3. matches are stored as normalized tweet-to-narrative rows
4. weekly aggregate snapshots are built for all tracked users and each cohort
5. frontend aggregate narrative page reads snapshot-backed series quickly

This architecture intentionally separates:

- narrative definition
- per-tweet match detection
- aggregate weekly series generation
- frontend display

## Data Model

### Table: `managed_narratives`

Purpose:

- source of truth for explicit narrative phrases

Recommended fields:

- `id`
- `slug`
- `name`
- `phrase`
- `created_at`
- `updated_at`

Notes:

- `name` is the display label
- `phrase` is the normalized or user-provided exact phrase to match
- for v1, `name` and `phrase` may often be the same
- keep both fields so labels can diverge later without schema churn

Constraints:

- `slug` unique
- `name` unique enough for UI sanity
- `phrase` unique after normalization

### Table: `tweet_narrative_matches`

Purpose:

- record that a tweet matched a managed narrative

Recommended fields:

- `id`
- `tweet_id`
- `managed_narrative_id`
- `matched_phrase`
- `created_at`
- `updated_at`

Constraints:

- unique on `tweet_id + managed_narrative_id`

Notes:

- one row per tweet and narrative
- repeated phrase mentions inside the same tweet do not create duplicate rows
- `matched_phrase` is optional but useful if future alias support is added

### Optional Future Table

Not required for v1:

- `managed_narrative_aliases`

This should be deferred until alias support is clearly needed.

## Matching Rules

V1 matching should be simple, explicit, and predictable.

Recommended normalization:

- lowercase phrase and tweet text
- collapse repeated whitespace
- trim leading and trailing whitespace

Recommended matching semantics:

- phrase-level exact matching with boundary-aware behavior
- treat a tweet as matched if the normalized phrase appears as a distinct phrase in the normalized text

Recommended implementation approach:

- normalize tweet text once during matching
- normalize phrase once on write and before matching
- avoid loose substring logic that would match inside unrelated tokens

Examples:

- `MSTR` should match `mstr`
- `microstrategy` should not automatically match `mstr`
- `bitcoin treasury` should match that exact normalized phrase
- multiple appearances in one tweet still count as one matching tweet

## Data Processing Strategy

### Why not reuse keyword extraction?

Keyword extraction is still useful for the existing author heatmap discovery workflow, but it is not the right backbone for aggregate narratives.

Reasons:

- it generates too many phrases
- it includes noisy and weakly meaningful phrases
- it forces the aggregate page to rank or filter a huge phrase universe
- it couples aggregate narrative quality to keyword-extractor heuristics

### Recommended pipeline

Use a separate narrative-matching path:

1. load managed narratives
2. load candidate tweets in scope
3. evaluate each tweet against the managed phrase list
4. upsert rows into `tweet_narrative_matches`
5. aggregate to weekly series
6. snapshot aggregate outputs

### Incremental behavior

The matching pipeline should support incremental rebuilds.

Recommended practical rule:

- when new tweets are normalized, only process tweets that do not yet have narrative-match rows evaluated for the current managed narrative set

Because narrative definitions can change, the system also needs a rebuild path:

- full narrative rematch after managed narrative edits
- or targeted rematch for affected narrative rows if implementation time allows

V1 recommendation:

- support a straightforward rebuild command for all narrative matches
- optimize to targeted rebuild later if needed

## Aggregate Snapshot Strategy

The feature should follow the same snapshot philosophy already used by aggregate mood views.

Recommended snapshot scope:

- one snapshot row for `aggregate-narratives-catalog`
- one snapshot row per cohort for weekly narrative overview data if needed
- one snapshot row per `cohort + narrative + week granularity` for fast series delivery, or one richer snapshot per cohort containing all managed narratives

Recommended v1 approach:

- one snapshot per cohort containing weekly series for all managed narratives

Why:

- the number of managed narratives is expected to be relatively small
- cohort selection is already a first-class aggregate concept
- one snapshot read can power both the narrative selector and selected narrative chart

Potential snapshot payload shape:

- `view`
- `generated_at`
- `cohort`
- `granularity`
- `range`
- `narratives`
  - `slug`
  - `name`
  - `phrase`
  - `summary`
    - `total_matching_tweets`
    - `latest_period_count`
    - `peak_period_count`
  - `series`
    - `period_start`
    - `matching_tweet_count`

### Cache invalidation and rebuild triggers

Snapshots should be rebuilt when:

- managed narratives are created or edited
- new tweets are added that could affect narrative counts
- cohort membership changes

V1 can use explicit rebuild hooks rather than a more complex reactive invalidation system.

## API Plan

### Global Settings API

Add a new route family for managed narratives.

Recommended endpoints:

- `GET /api/global-settings/narratives`
- `POST /api/global-settings/narratives`
- `PUT /api/global-settings/narratives/{narrative_id}`

Optional later:

- `DELETE /api/global-settings/narratives/{narrative_id}`

Recommended response shape:

- `view`
- `narratives`
  - `id`
  - `slug`
  - `name`
  - `phrase`

### Aggregate Narratives API

Recommended endpoints:

- `GET /api/views/aggregate-narratives/cohorts`
- `GET /api/views/aggregate-narratives`
- `GET /api/views/aggregate-narratives/series?narrative_slug=...&cohort_tag=...&granularity=week`

Two implementation options are acceptable:

#### Option A: Bootstrap + series endpoints

- one endpoint for catalog and cohort metadata
- one endpoint for selected narrative series

This keeps payloads smaller and easier to reason about.

#### Option B: One snapshot-rich endpoint per cohort

- one endpoint returns all narratives plus all weekly series for a cohort
- frontend selects narrative client-side

This is acceptable if the managed narrative list stays modest.

Recommended v1:

- use a richer cohort snapshot payload because the narrative set is intentionally constrained

## Frontend Plan

### Global Settings

Extend `frontend/src/pages/SettingsPage.tsx` with a new managed narratives section.

Recommended behavior:

- load narratives on page mount
- render creation input
- render editable list of narratives
- refresh list after successful create or edit

This should mirror the simplicity of the existing cohort-tag management pattern rather than introducing a heavier admin UI.

### New Aggregate Narratives Page

Add a new route and page component:

- `frontend/src/pages/AggregateNarrativesPage.tsx`

Recommended interaction model:

- selected narrative in state
- selected cohort in state
- pinned cohort in state
- load cohort options on page mount
- load snapshot-backed narrative payloads for selected and pinned cohort
- render selected narrative series for one or two cohorts

Recommended reuse:

- cohort-selection interaction patterns from `AggregateMoodPage.tsx`
- existing charting primitives where practical
- existing app-shell routing and dropdown patterns

### Navigation

Add `Aggregate Narratives` as a new top-level section in the dashboard navigation.

This should be separate from the current `Narratives` heatmap dropdown because the two features are conceptually different:

- `Narratives` remains author-level heatmap discovery
- `Aggregate Narratives` becomes managed phrase tracking across cohorts

## Backend Implementation Tasks

### Phase 1: Managed Narrative Catalog

#### Goal

Create the source of truth for explicit narrative phrases.

#### Tasks

1. Add `managed_narratives` model and migration
2. Add normalization helpers for phrase and slug handling
3. Add services for list, create, and update
4. Add API routes for Global Settings narrative management
5. Add frontend Global Settings UI section

#### Acceptance Criteria

- user can create a new managed narrative
- user can edit an existing managed narrative
- narratives persist in the database
- duplicate phrases are rejected after normalization

### Phase 2: Tweet Narrative Match Storage

#### Goal

Create the per-tweet narrative match layer used by all aggregate computations.

#### Tasks

1. Add `tweet_narrative_matches` model and migration
2. Implement phrase normalization and boundary-aware matching logic
3. Add narrative match build/rebuild service
4. Add script or command to rebuild narrative matches
5. Ensure one row per `tweet_id + managed_narrative_id`

#### Acceptance Criteria

- a tweet matching a managed phrase creates one match row
- repeated phrase mentions in the same tweet do not create extra rows
- case differences do not prevent matching
- full rebuild produces stable results across reruns

### Phase 3: Aggregate Weekly Narrative Views

#### Goal

Expose aggregate narrative volume by week for all users and cohorts.

#### Tasks

1. Build aggregate cohort resolver reuse from aggregate moods
2. Build weekly aggregation service over `tweet_narrative_matches`
3. Build snapshot-backed payload shape for aggregate narrative series
4. Add aggregate narrative view endpoints
5. Add cohort metadata endpoint if needed

#### Acceptance Criteria

- all tracked users view loads for a selected narrative
- cohort-filtered view loads for a selected narrative
- pinned cohort comparison is supported by the API shape
- data is bucketed weekly

### Phase 4: Frontend Aggregate Narratives Page

#### Goal

Ship the new phrase-driven cohort comparison page.

#### Tasks

1. Add route and page wiring
2. Add cohort selection and pinning UI
3. Add narrative selector UI
4. Add summary cards
5. Add weekly chart rendering
6. Add loading and empty states

#### Acceptance Criteria

- page loads without heatmap UI
- narrative can be selected from explicit managed list
- cohort can be changed
- pinned cohort overlays correctly
- chart renders selected narrative weekly volume

### Phase 5: Snapshot Rebuild Integration

#### Goal

Make the feature operationally cheap and fast.

#### Tasks

1. Add aggregate narrative snapshot types to the snapshot cache helpers
2. extend the aggregate snapshot rebuild flow or add a companion rebuild command
3. trigger narrative snapshot rebuild from relevant post-process or maintenance flows
4. document rebuild behavior and operational expectations

#### Acceptance Criteria

- aggregate narrative page reads cached data for normal loads
- rebuild path is explicit and repeatable
- page load time is decoupled from raw tweet volume

## Operational Considerations

### Rebuild cost

Narrative rematching cost is driven by:

- number of managed narratives
- number of canonical tweets in scope

Because the managed phrase set is intentionally constrained, this should be substantially cheaper than open-ended keyword extraction and ranking for aggregate pages.

### Failure handling

Recommended operational behavior:

- narrative creation and edits should not silently invalidate cached pages forever
- rebuild failures should leave the previous snapshot available until the next successful rebuild

### Diagnostics

Recommended diagnostics in rebuild output:

- narratives scanned
- tweets scanned
- narrative match rows inserted or retained
- cohort snapshots rebuilt
- total runtime

## Risks

### Phrase boundary bugs

Loose matching could create false positives.

Mitigation:

- keep v1 matching conservative
- add tests for punctuation, casing, and token boundaries

### Narrative edits invalidating old matches

Changing a phrase means previous match rows may no longer be correct.

Mitigation:

- treat narrative edits as rebuild-triggering events

### Snapshot shape bloat

If the number of managed narratives grows significantly, one-payload-per-cohort may become large.

Mitigation:

- acceptable for v1 because the set is intentionally constrained
- split into bootstrap and series endpoints later if needed

### UI concept overlap with current Narratives

Users may confuse the old heatmap page with the new aggregate narrative page.

Mitigation:

- keep naming explicit
- present aggregate narratives as a separate page and concept

## Testing Plan

### Backend tests

- phrase normalization
- boundary-aware match semantics
- one row per `tweet_id + narrative_id`
- weekly aggregation correctness
- cohort filtering correctness
- snapshot payload generation

### Frontend tests

- Global Settings narrative create/edit interactions
- narrative dropdown population
- cohort selector and pinning behavior
- selected narrative chart updates
- loading, empty, and error states

### Manual verification

1. create narratives in Global Settings
2. run narrative rebuild
3. run aggregate snapshot rebuild
4. open Aggregate Narratives page
5. switch narratives
6. switch cohorts
7. pin a comparison cohort
8. confirm weekly series changes as expected

## Migration Notes

This feature does not require removal of the existing author heatmap narrative system.

Recommended migration posture:

- leave current author heatmaps untouched
- ship Aggregate Narratives as an additive feature
- use managed narratives only for the new feature

This avoids coupling the new explicit narrative workflow to the existing discovery-oriented keyword system.

## Recommended Build Order

1. add `managed_narratives` schema and Global Settings CRUD
2. add `tweet_narrative_matches` schema and rebuild service
3. add weekly aggregate view builder
4. add snapshot storage and rebuild flow
5. add frontend Aggregate Narratives page
6. integrate rebuild hooks into operational workflows

## Final Recommendation

The correct implementation strategy is to treat Aggregate Narratives as a new managed phrase-tracking feature rather than an extension of the current keyword heatmap system.

That yields:

- tighter editorial control over tracked narratives
- less noisy results
- better aggregate cohort comparisons
- lower compute cost
- simpler explanation of what the page is measuring

The existing author heatmap feature can continue serving narrative discovery, while Aggregate Narratives serves curated narrative monitoring.
