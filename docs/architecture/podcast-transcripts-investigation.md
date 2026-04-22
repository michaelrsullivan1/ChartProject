# Podcast Transcripts Investigation

Date: 2026-04-22

Dataset under review:

- Hugging Face dataset: https://huggingface.co/datasets/BeliefEngines/podcast-transcripts
- Upstream ETL pipeline: https://github.com/beliefengines/be-podcast-etl

## Why this matters

This project already follows a useful pattern for new research sources:

- archive raw source payloads
- normalize queryable entities into Postgres
- store derived analytical outputs in separate tables
- build frontend-ready aggregate views on top

That pattern is a good fit for podcast transcripts and belief graphs, but they should be introduced as a parallel content family, not squeezed into the existing tweet tables.

## What the dataset claims

The dataset card currently describes a snapshot dated `2026-04-21` with:

- 1,551 episodes
- 18 podcasts
- 876 speakers
- 3,915 persons
- 66,453 belief shards
- 65,007 embeddings
- 62,882 matrices

It advertises five parquet exports:

- `data/transcripts.parquet`
- `data/transcript_chunks.parquet`
- `data/beliefs.parquet`
- `data/persons.parquet`
- `data/episode_metadata.parquet`

It also exposes a full ETL archive:

- `be-podcast-dataset-2026-04-21.tar.zst`

## What I actually observed locally

I downloaded the published parquet files directly from Hugging Face on 2026-04-22 and inspected them locally.

Observed parquet sizes:

- `beliefs.parquet`: about 2.2 MB
- `persons.parquet`: about 1.2 MB
- `transcript_chunks.parquet`: about 720 KB
- `transcripts.parquet`: about 475 KB
- `episode_metadata.parquet`: about 10 KB

Observed row counts:

- `beliefs.parquet`: 308 rows, 13 columns
- `persons.parquet`: 84 rows, 14 columns
- `transcript_chunks.parquet`: 156 rows, 12 columns
- `transcripts.parquet`: 4 rows, 8 columns
- `episode_metadata.parquet`: 4 rows, 12 columns

Important mismatch:

- the dataset card presents full-scale corpus counts
- the downloadable parquet exports currently look like a narrow sample or partial export, not the full corpus

Additional cross-checks:

- `beliefs.parquet` spans 18 podcasts and 110 distinct `episode_id` values
- `beliefs.parquet` references 69 distinct `person_id` values
- all `person_id` values in `beliefs.parquet` were present in `persons.parquet`
- only 4 `episode_id` values were present in `episode_metadata.parquet`
- only 4 full transcript rows were present in `transcripts.parquet`

Working assumption:

- the parquet layer is useful for schema exploration and proof-of-concept work
- the full `tar.zst` snapshot is likely the real source to use for corpus-scale ingestion

## Schema notes

### `beliefs.parquet`

Columns observed:

- `belief_id`
- `person_id`
- `episode_id`
- `podcast_id`
- `quote`
- `atomic_belief`
- `topic`
- `domain`
- `worldview`
- `core_axiom`
- `weights`
- `timestamp_start`
- `embedding`

This is the most interesting table for integration with sentiment work because it already contains:

- a human-readable quote span
- a normalized atomic belief statement
- topical framing
- abstract worldview and axiom layers
- a 10-dimensional weight vector
- a 1536-dimensional embedding
- a timestamp anchor back into the episode

### `transcripts.parquet`

Columns observed:

- `episode_id`
- `podcast_slug`
- `episode_slug`
- `episode_title`
- `published_at`
- `duration_seconds`
- `transcript_text`
- `segments`

The `segments` field appears to contain diarized transcript segments with:

- `speaker_name`
- `speaker_slug`
- `text`
- `timestamp_start`
- `timestamp_end`
- `word_count`

### `transcript_chunks.parquet`

Columns observed:

- `chunk_id`
- `episode_id`
- `podcast_slug`
- `episode_slug`
- `text`
- `timestamp_start`
- `timestamp_end`
- `speakers`
- `primary_speaker`
- `chunk_index`
- `overlap_tokens`
- `embedding`

This is likely the cleanest source for retrieval, semantic search, and future cross-source nearest-neighbor work.

### `persons.parquet`

Columns observed:

- `person_id`
- `name`
- `bio`
- `wiki_url`
- `thumbnail_url`
- `belief_count`
- `appearance_count`
- `weights_array`
- `primary_domain`
- `cluster_id`
- `cluster_name`
- `similar_persons`
- `opposite_persons`
- `embedding`

This table is useful if you want speaker-level or worldview-cluster views rather than only episode-level analysis.

## Caveats from the dataset card

The dataset card itself calls out three things that matter for ingestion design:

- diarization skew on 187 episodes
- schema drift across belief records, with some abstract fields missing
- `unknown-*` placeholder speakers for a small share of the corpus

Implication:

- transcript and speaker fields should not be treated as perfectly canonical
- belief-layer fields like `worldview` and `core_axiom` must be nullable in any normalized schema

## Best fit for this repo

The cleanest approach is to treat podcasts as a second content source alongside X/Twitter.

Recommended conceptual model:

- `podcast_episodes`
- `podcast_segments`
- `podcast_transcript_chunks`
- `podcast_persons`
- `podcast_beliefs`
- `podcast_belief_relationships` later, if the raw ETL snapshot exposes graph edges in a usable form

Do not reuse:

- `tweets`
- `tweet_sentiment_scores`
- `tweet_mood_scores`
- `tweet_narrative_matches`

Instead, mirror the same architecture pattern with podcast-specific tables plus shared downstream views where comparison is useful.

## High-value integration opportunities

### 1. Cross-source narrative alignment

Use the podcast belief layer to compare against:

- managed tweet narratives
- extracted tweet keywords
- aggregate sentiment windows

This would let you answer questions like:

- which beliefs show up in podcasts before they spread through tracked accounts on X
- which speakers most strongly reinforce or contradict narratives already visible in the tweet archive
- whether spikes in a belief topic coincide with changes in tweet sentiment or mood

### 2. Speaker-to-author comparison

Create a bridge layer between:

- podcast `person_id`
- X `users`

This does not need to be automatic at first. A small manual mapping table would be enough.

Example use:

- compare Michael Sullivan's podcast belief profile against Michael Sullivan's tweet sentiment or keyword profile
- compare Breedlove, Saylor, Schiff, or others across speech and posting behavior

### 3. Longitudinal show and speaker analysis

The strongest immediate fit for this dataset may be longitudinal analysis, not episode browsing.

Potential uses:

- topic-rate trends across the full history of a show
- speaker topic trajectories across all appearances
- speaker phrase drift over time
- belief-family trend charts for a show or person

Why this matters:

- it matches the structure of the dataset well
- it keeps the focus on change over time
- it aligns with the most compelling recurring entities in the corpus: shows and people

### 4. Retrieval and quote drilldown

The chunk and belief timestamps make it possible to build a much richer drilldown flow than tweets alone.

Potential UI pattern:

- click a sentiment or narrative spike
- show matching tweets
- show related podcast beliefs and transcript excerpts from the same time period

### 5. Cluster-level worldview analysis

The person embeddings, clusters, and similarity fields open up a new type of aggregate chart:

- worldview clusters over time
- belief-topic intensity by speaker cohort
- nearest-neighbor ideology maps for podcast guests and hosts

## Recommended ingestion strategy

Start in two stages.

### Stage 1: exploration and proof of fit

Use the parquet exports to:

- validate schemas
- build a small local prototype
- test joins and UI concepts
- confirm how much useful overlap exists with your current tracked authors

This stage is cheap and low risk.

### Stage 2: real corpus ingestion

If the source proves useful, ingest from the full `be-podcast-dataset-2026-04-21.tar.zst` snapshot rather than relying on the currently published parquet exports alone.

Why:

- the parquet row counts do not currently match the advertised corpus scale
- the tar snapshot likely contains the full sharded ETL outputs
- the raw snapshot aligns better with this repo's raw-first design principle

## Concrete next steps

Best next move:

1. download the full `tar.zst` snapshot into a local raw data area
2. inspect its directory structure and identify the episode, belief, embedding, and person manifests worth normalizing
3. design podcast-specific SQLAlchemy models and an Alembic migration
4. build a first ingest script that archives the snapshot metadata and normalizes episodes plus beliefs
5. add one comparison endpoint that overlays podcast beliefs with existing tweet narratives or sentiment windows

## Bottom line

This source is promising and materially different from the current tweet archive.

The main caution is that the Hugging Face parquet exports currently appear to be partial, while the dataset card describes a much larger corpus. For serious integration work, the full ETL snapshot is the safer foundation.
