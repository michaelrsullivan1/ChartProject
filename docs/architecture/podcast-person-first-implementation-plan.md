# Podcast Person-First Implementation Plan

Date: 2026-04-22

## Purpose

This document defines the implementation plan for bringing the Belief Engines podcast snapshot into this project as a new, separate product area.

The guiding idea is:

- ingest the full snapshot cleanly
- preserve the source structure faithfully
- normalize the data into a coherent relational model
- build the first analytical experience around a single person over time
- defer deeper UI decisions until the data is loaded and validated

This is a plan for the whole effort, but it is intentionally phased so the work can proceed incrementally.

## Scope

### In scope

- full local acquisition of the published snapshot
- raw snapshot preservation
- normalized Postgres schema for podcast data
- person-first analytical modeling
- backend support for longitudinal person-level views
- enough frontend structure to host a new podcast area later
- validation and profiling of the imported corpus

### Out of scope for the first implementation pass

- any coupling to existing Twitter/X views
- cross-source comparisons with tweet sentiment, mood, or narratives
- identity repair or custom person remapping
- final UI polish for all podcast pages
- embedding-driven retrieval, clustering, or semantic map features
- advanced worldview graph products

## Decisions already made

These decisions should be treated as fixed unless something material changes in the source data.

### 1. Source of truth

Canonical source:

- the full `be-podcast-dataset-2026-04-21.tar.zst` snapshot

Supporting sources only:

- Hugging Face parquet exports for exploration and quick inspection

Implication:

- the full snapshot should be acquired and preserved locally
- the app should not rely on the current parquet sample layer as the primary ingestion target

### 2. Data acquisition philosophy

Use as much of the published snapshot as is practical and coherent from the beginning.

Implication:

- do not design around a toy subset
- do not shape the schema only for a single first person
- design for the whole corpus even if the first product view is narrow

### 3. Identity handling

Use the upstream `person_id` as canonical in v1.

Implication:

- trust the snapshot's person identities as given
- avoid building a local identity override layer at the start
- keep the schema flexible enough to add remapping later if needed

### 4. Product emphasis

The first analytical emphasis is longitudinal person history.

Implication:

- the first meaningful visual experience should center on one person across all appearances in the corpus
- show-level views matter, but they are not the first focal point
- episode-level data is input and drilldown, not the primary product surface

### 5. Embeddings

Embeddings are not required for the first product pass.

Implication:

- if they are easy to store, preserve them
- do not block ingestion or v1 analytics on embedding-specific work

## Product framing

This dataset should be treated as a separate research area inside the same application.

Recommended framing:

- current app area: Twitter/X research archive
- new app area: podcast belief explorer

Shared infrastructure:

- same repo
- same backend
- same database
- same frontend shell
- same deployment and local dev workflow

Separate product concepts:

- separate routes
- separate models
- separate services
- separate caches or precomputed views where needed
- separate settings and registry concepts unless proven useful later

## Core product question

The first question the system should answer is:

- for one person across the full corpus, how do their beliefs and topics change over time

That question is specific enough to guide schema and endpoint design, while still leaving room for broader exploration later.

## High-level architecture

The new podcast subsystem should follow the same broad architectural pattern already present in the repo:

1. raw acquisition and preservation
2. normalized relational storage
3. derived analytical layers
4. backend view shaping
5. frontend rendering later

The important difference is that the primary entities are not users and tweets. They are:

- shows
- episodes
- persons
- appearances
- beliefs
- transcript units

## Recommended canonical entities

The following conceptual entities should anchor the design.

### `podcast_shows`

Represents one show across its full history.

Minimum purpose:

- stable show identity
- show metadata and labeling
- long-term grouping key for longitudinal show analysis

### `podcast_episodes`

Represents one published episode.

Minimum purpose:

- stable episode identity
- publish date
- source show association
- duration and title metadata

Episode records are important even though episode-centric pages are not the first product surface.

### `podcast_persons`

Represents one upstream person identity from the snapshot.

Minimum purpose:

- stable `person_id`
- display name
- profile metadata
- appearance and belief counts
- optional cluster and embedding metadata

### `podcast_appearances`

Represents a person appearing in an episode.

Minimum purpose:

- join person to episode
- support longitudinal person history
- support show/person analysis without duplicating logic into belief rows

This is one of the most important tables in the design.

### `podcast_beliefs`

Represents one extracted belief.

Minimum purpose:

- stable belief identity
- person association
- episode association
- show association
- quote
- atomic belief
- topic and optional higher-order fields
- time anchor within the source episode

This is the primary analytical content table.

### Optional later entities

These may be included in the first ingestion if straightforward, but they are not required to unlock the first person view.

- `podcast_transcript_segments`
- `podcast_transcript_chunks`
- `podcast_belief_relationships`
- `podcast_search_index` or equivalent derived tables

## Minimum relational schema requirements

The normalized schema must make the following questions easy to answer:

1. Which shows exist in the corpus?
2. Which people exist in the corpus?
3. Which episodes belong to a show, and when were they published?
4. Which people appeared in which episodes?
5. Which beliefs belong to which person?
6. Which beliefs belong to which show?
7. How many beliefs and appearances does a person have over time?
8. What topics dominate for a person or show over time?

At minimum, every belief should be traceable to:

- one person
- one episode
- one show
- one publish date

Without that chain, the longitudinal charts will be incomplete or misleading.

## Suggested target tables

This section is conceptual. Exact field names can be adjusted during implementation.

### `podcast_shows`

Suggested fields:

- `id`
- `source_podcast_id` or `slug`
- `name`
- `description`
- `source_snapshot_key`
- `created_at`
- `updated_at`

### `podcast_episodes`

Suggested fields:

- `id`
- `source_episode_id`
- `podcast_show_id`
- `episode_slug`
- `title`
- `description`
- `published_at`
- `duration_seconds`
- `audio_url`
- `source_url`
- `created_at`
- `updated_at`

### `podcast_persons`

Suggested fields:

- `id`
- `source_person_id`
- `name`
- `bio`
- `wiki_url`
- `thumbnail_url`
- `belief_count_source`
- `appearance_count_source`
- `primary_domain`
- `cluster_id`
- `cluster_name`
- `weights_array`
- `embedding`
- `created_at`
- `updated_at`

### `podcast_appearances`

Suggested fields:

- `id`
- `podcast_episode_id`
- `podcast_person_id`
- `source_person_id`
- `source_episode_id`
- `role_label` if derivable later
- `created_at`
- `updated_at`

Constraints:

- unique on episode/person pair

### `podcast_beliefs`

Suggested fields:

- `id`
- `source_belief_id`
- `podcast_show_id`
- `podcast_episode_id`
- `podcast_person_id`
- `source_belief_id`
- `quote`
- `atomic_belief`
- `topic`
- `domain`
- `worldview`
- `core_axiom`
- `weights`
- `timestamp_start_seconds`
- `embedding`
- `created_at`
- `updated_at`

Constraints:

- unique on `source_belief_id`

### `podcast_raw_artifacts` or reuse of `raw_ingestion_artifacts`

The existing raw ingestion pattern should be reused if practical.

Minimum purpose:

- preserve snapshot acquisition metadata
- preserve manifest-level raw payloads or references
- make future reprocessing possible

## Raw acquisition plan

### Acquisition target

Acquire locally:

- `be-podcast-dataset-2026-04-21.tar.zst`

Preserve:

- original archive filename
- download timestamp
- source URL
- snapshot date or commit when available
- checksum if easily obtainable

### Storage approach

Recommended:

- keep the original archive on disk in a raw data area outside the normalized database
- also record acquisition metadata in the database

Reasoning:

- the archive is part of the durable source asset
- reprocessing should not depend on the Hugging Face site remaining unchanged

### Extraction approach

After acquisition:

- extract the archive into a stable local raw directory
- inspect the resulting directory structure
- identify the exact subdirectories and manifests that back shows, episodes, persons, beliefs, embeddings, and transcript units

Important:

- do not guess the raw file layout in code before inspecting the extracted archive
- the first implementation step after acquisition should be a structure audit

## Ingest phases

The work should proceed in explicit phases.

### Phase 0: acquisition and structure audit

Goals:

- download the full snapshot
- preserve the archive
- extract it locally
- document the raw directory structure
- identify the exact files needed for first-pass normalization

Deliverables:

- archive present locally
- extracted snapshot directory
- raw structure note added to docs
- list of selected source files for ingestion

### Phase 1: normalized schema design

Goals:

- define SQLAlchemy models
- define Alembic migration(s)
- decide constraints and indexes
- decide which source fields are required versus optional

Deliverables:

- migration plan
- model plan
- validation assumptions documented

### Phase 2: base normalization

Goals:

- ingest shows
- ingest episodes
- ingest persons
- ingest appearances
- ingest beliefs

Priority:

- correctness over speed
- clear traceability from normalized rows back to source identifiers

Deliverables:

- repeatable ingest script
- coherent normalized corpus in Postgres

### Phase 3: validation and profiling

Goals:

- confirm row counts
- confirm relationships
- confirm date coverage
- confirm top persons and top shows
- confirm topic distribution
- confirm that at least a few persons have meaningful longitudinal density

Deliverables:

- validation output
- first profiling summary
- shortlist of strong candidate first persons

### Phase 4: first analytical layer

Goals:

- create backend logic for person-level longitudinal metrics
- focus only on one person-oriented analytical flow

Minimum metrics:

- appearances over time
- beliefs over time
- topic counts over time
- topic share over time

Deliverables:

- service layer or query layer for person history
- simple API payload shape for future UI

### Phase 5: first frontend surface

Goals:

- create minimal podcast route scaffolding
- build one person-first exploratory page
- use it to validate whether the longitudinal model is interesting

Important:

- do not overdesign the entire podcast UI upfront
- the first page should be a learning tool, not a finished product family

## Validation requirements

Before any UI work is taken seriously, the ingest must satisfy a validation checklist.

### Required validation checks

- total show count imported
- total episode count imported
- total person count imported
- total appearance count imported
- total belief count imported
- distinct topics count
- min and max publish date
- belief rows with missing person link
- belief rows with missing episode link
- episode rows with missing show link
- duplicate source ids detected

### Person-history validation checks

For the top recurring people:

- number of appearances
- number of beliefs
- first and last appearance dates
- count of months or weeks with activity
- top topics

This is the key validation pass for the first product.

## First analytical outputs

The first derived outputs should be intentionally narrow.

### Person history series

For one person:

- appearances per month
- beliefs per month
- topic counts per month
- topic share per month

### Person summary

For one person:

- total appearances
- total beliefs
- active date range
- top shows by appearance count
- top topics

### Candidate follow-on outputs

After the first person view works:

- show topic-rate series
- phrase drift series for one person
- belief-family trend series
- person comparison views

## UI planning stance

UI decisions should be acknowledged, but not prematurely frozen.

### What should be decided now

- the first user-facing concept is person-first longitudinal exploration
- the new area should live in the same app shell
- the first page should visualize one person over time

### What should remain open for now

- exact chart composition
- route naming details
- navigation hierarchy for multiple podcast pages
- whether topic mix is shown as line chart, stacked area, heatmap, or multiple coordinated panels
- how much drilldown is needed in the first page

### Why this matters

If UI choices are forced too early, they will distort the data model.

The correct sequence is:

1. acquire and normalize correctly
2. validate corpus structure
3. generate person-level analytical payloads
4. choose the best first chart language based on the actual data density

## Recommended first person selection criteria

The first subject should be chosen after profiling, but the criteria should be explicit.

Prefer:

- high `appearance_count`
- high `belief_count`
- broad date coverage
- enough topic variety to make change over time visible
- identity likely to be stable and recognizable

This will likely favor hosts and frequent co-hosts.

## Major risks

### 1. Partial or irregular raw structure

The full snapshot may not be arranged exactly as expected.

Mitigation:

- perform a raw structure audit before writing the real ingest code

### 2. Missing publish date joins

Beliefs alone may not include enough dating information.

Mitigation:

- ensure episode metadata is normalized before belief loading logic is finalized

### 3. Identity noise

Some person labels or diarization assignments may be wrong.

Mitigation:

- trust upstream identity in v1
- keep notes on observed issues
- defer repair logic until the need is real

### 4. Sparse person histories

Many individuals may not have enough repeated appearances to make longitudinal charts meaningful.

Mitigation:

- start with the most recurrent people
- validate density before designing generalized UI

### 5. Overcommitting to higher-order fields

Fields like `worldview` and `core_axiom` may be inconsistent.

Mitigation:

- do not make v1 dependent on them
- treat them as optional enrichments

## Milestone sequence

This is the recommended order of execution.

1. Acquire the full snapshot archive locally.
2. Extract the archive and document its internal structure.
3. Design the normalized podcast schema.
4. Add migrations and models.
5. Build the base ingest pipeline for shows, episodes, persons, appearances, and beliefs.
6. Validate the imported corpus.
7. Profile top recurring persons.
8. Define the first person-history backend payload.
9. Build the first person-first exploratory page.
10. Decide the next layer only after the first person page proves useful.

## Definition of success for the first implementation pass

The first pass is successful if all of the following are true:

- the full snapshot is locally preserved and reprocessable
- the normalized schema faithfully captures the source entities
- one person can be analyzed across the full imported date range
- topic and belief activity can be charted over time for that person
- the system is structurally ready to expand to more persons and later show-level views

## Immediate next actions

The next concrete tasks should be:

1. acquire and extract the full snapshot
2. inspect and document the raw file layout
3. design the exact normalized tables and required fields based on the real extracted structure

Everything else should follow from those three steps.
