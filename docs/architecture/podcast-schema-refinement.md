# Podcast Schema Refinement

Date: 2026-04-22

This note refines the earlier conceptual implementation plan using the real snapshot layout observed under `data/raw/beliefengines/extracted/podcast-etl-data/`.

## Summary

The source audit supports a straightforward first-pass normalized schema:

- `podcast_shows`
- `podcast_episodes`
- `podcast_persons`
- `podcast_appearances`
- `podcast_beliefs`

Optional later tables:

- `podcast_utterances`
- `podcast_person_trust_scores`
- `podcast_person_embeddings`

The main source files that justify this are:

- `runs/manifests/<show>/<episode>.json`
- `persons/<person>/profile.json`
- `persons/<person>/beliefs.jsonl`
- `raw/podcasts/<show>/episodes/<episode>/transcript.json`

## Why this schema is sufficient for v1

These tables are enough to answer the first product question:

- for one person across the corpus, how do their beliefs and topics change over time

The model does not need:

- local identity correction
- semantic search infrastructure
- belief-family clustering
- graph edges

to support that first analytical experience.

## Recommended table roles

### `podcast_shows`

Purpose:

- one row per show
- stable grouping key for full-history show analysis

Recommended fields:

- `id`
- `source_slug`
- `display_name`
- `created_at`
- `updated_at`

Source:

- primarily derived from the manifest directory structure and manifest `podcast_slug`

Notes:

- there may not be a richer top-level show metadata record in the first-pass source set
- `display_name` may need to start from slug normalization if no better field exists

### `podcast_episodes`

Purpose:

- one row per episode
- canonical date anchor for all longitudinal analysis

Recommended fields:

- `id`
- `source_episode_id`
- `episode_slug`
- `podcast_show_id`
- `title`
- `description`
- `published_at`
- `duration_seconds`
- `audio_url`
- `manifest_status`
- `manifest_created_at`
- `manifest_updated_at`
- `created_at`
- `updated_at`

Primary source:

- manifest JSON

Fallback/enrichment source:

- transcript JSON `episode` block

Notes:

- manifests and transcript files overlap on some fields
- published date should be normalized carefully, since some fields differ between sample sources

### `podcast_persons`

Purpose:

- one row per upstream `person_id`
- canonical person entity for v1

Recommended fields:

- `id`
- `source_person_id`
- `slug`
- `name`
- `bio_summary`
- `has_wiki`
- `wiki_url`
- `total_beliefs_source`
- `created_at_source`
- `updated_at_source`
- `created_at`
- `updated_at`

Primary source:

- `persons/<person>/profile.json`

Notes:

- `appearance_count` can be derived from the appearance table rather than stored redundantly
- this keeps the normalized model closer to actual source relationships

### `podcast_appearances`

Purpose:

- one row per person appearing in one episode
- bridge table that makes person history and show/person analysis clean

Recommended fields:

- `id`
- `podcast_person_id`
- `podcast_episode_id`
- `source_person_id`
- `source_episode_id`
- `created_at`
- `updated_at`

Primary source:

- `persons/<person>/profile.json` `appearances` array

Constraints:

- unique on `(podcast_person_id, podcast_episode_id)`

Notes:

- this table is essential and should not be skipped
- it lets the system answer appearance-based questions without abusing beliefs as a proxy for presence

### `podcast_beliefs`

Purpose:

- one row per extracted belief attributed to one person in one episode

Recommended fields:

- `id`
- `source_belief_id`
- `podcast_person_id`
- `podcast_episode_id`
- `podcast_show_id`
- `quote`
- `atomic_belief`
- `topic`
- `domain`
- `worldview`
- `core_axiom`
- `weights_json`
- `timestamp_start_seconds`
- `timestamp_end_seconds`
- `created_at_source`
- `created_at`
- `updated_at`

Primary source:

- `persons/<person>/beliefs.jsonl`

Potential enrichment source later:

- global `beliefs/` artifacts referenced from manifests

Notes:

- `podcast_show_id` can be derived via episode join, but storing it directly may simplify analytical queries
- `topic` must be treated as optional until confirmed in the raw person belief records or belief artifact files
- the sample person-scoped beliefs inspected so far include `domain`, `worldview`, and `core_axiom`

## Recommended first-pass ingest strategy

Use a three-layer ingest order.

### Layer 1: shows and episodes

Load from manifests first.

Why:

- every downstream entity depends on a reliable episode table
- episode date is the anchor for every longitudinal chart

### Layer 2: persons and appearances

Load person profiles next.

Why:

- this establishes canonical person rows
- this also yields the person-to-episode appearance bridge

### Layer 3: beliefs

Load person belief files last.

Why:

- belief rows need person and episode foreign keys in place
- this creates a clean chain from belief to person to dated episode

## Fields to preserve exactly

The following source values should be preserved as close to verbatim as possible:

- `source_person_id`
- `source_episode_id`
- `source_belief_id`
- `podcast_slug`
- `episode_slug`
- `quote`
- `atomic_belief`
- `domain`
- `worldview`
- `core_axiom`
- `timestamp_start`
- `timestamp_end`

These are the values most likely to matter for future reprocessing, debugging, and UI drilldown.

## Fields that should be nullable

The schema should assume partial completion of upstream stages and allow nulls for:

- `description`
- `duration_seconds`
- `bio_summary`
- `wiki_url`
- `topic`
- `domain`
- `worldview`
- `core_axiom`
- `weights_json`
- `timestamp_start_seconds`
- `timestamp_end_seconds`

This keeps the import resilient to source drift.

## Indexing recommendations

At minimum:

- `podcast_episodes.source_episode_id`
- `podcast_episodes.published_at`
- `podcast_persons.source_person_id`
- `podcast_appearances.podcast_person_id`
- `podcast_appearances.podcast_episode_id`
- `podcast_beliefs.podcast_person_id`
- `podcast_beliefs.podcast_episode_id`
- `podcast_beliefs.podcast_show_id`
- `podcast_beliefs.domain`
- `podcast_beliefs.topic`

These will support the first person-history and later show-history queries.

## First person-history queries the schema must support

The normalized design should make these easy:

1. total appearances for one person
2. total beliefs for one person
3. appearance count by month for one person
4. belief count by month for one person
5. top domains for one person across time
6. topic counts by month for one person, when topic exists
7. top shows a person appears on

## Important source caveats exposed by the audit

### 1. Person appearance arrays are unsorted

Do not treat profile `appearances` order as meaningful chronology.

Use:

- joined episode `published_at`

### 2. Transcript speaker labels are local placeholders

Raw transcript utterances use labels like `SPEAKER_00`, not canonical person ids.

Implication:

- utterance import should be secondary to person import
- transcript-level phrase drift may require a later reconciliation step

### 3. Topic may not be uniformly present in person belief files

The sampled `beliefs.jsonl` rows did not include `topic`, even though the parquet export did.

Implication:

- topic should remain in the schema, but treated as optional until confirmed across the real raw artifacts
- the first analytical layer may need to rely initially on `domain` and raw belief text if topic is absent in the canonical source files

### 4. Global belief artifacts may be richer than person belief files

Manifest `artifacts.beliefs` points to `beliefs/<prefix>/<belief>.json` files.

Implication:

- v1 can ingest from person-scoped `beliefs.jsonl`
- later passes may enrich belief rows from the global belief artifact tree if it contains extra fields such as `topic`

## Immediate implementation recommendation

The first concrete code pass should target:

1. `podcast_shows`
2. `podcast_episodes`
3. `podcast_persons`
4. `podcast_appearances`
5. `podcast_beliefs`

And the first ingest script should read:

1. manifests
2. person profiles
3. person beliefs

before attempting transcript utterances or embedding layers.
