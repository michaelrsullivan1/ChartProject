# Podcast Snapshot Layout Audit

Date: 2026-04-22

Source archive audited:

- `data/raw/beliefengines/be-podcast-dataset-2026-04-21.tar.zst`

Extracted under:

- `data/raw/beliefengines/extracted/podcast-etl-data/`

## Purpose

This note records the observed internal layout of the full Belief Engines snapshot so the ingest design can be based on the actual source files rather than the Hugging Face dataset card alone.

## Top-level directories observed

The extracted snapshot expands into these top-level directories:

- `beliefs/`
- `embeddings/`
- `matrices/`
- `persons/`
- `raw/`
- `runs/`
- `search/`
- `speakers/`
- `tmp/`

This matches the dataset card at a high level and confirms that the snapshot is richer than the published parquet sample exports.

## High-confidence source areas for first-pass ingestion

Based on direct file inspection, the most important directories for the first normalized import are:

- `runs/manifests/`
- `raw/podcasts/`
- `persons/`

These three areas are already enough to support the first person-first longitudinal product.

## `runs/manifests/`

Observed structure:

- `runs/manifests/<podcast-slug>/<episode-slug>.json`

Examples:

- `runs/manifests/what-is-money-show/2025-12-12-are-we-better-than-nature-w-michael-sullivan.json`
- `runs/manifests/simply-bitcoin/...`

The manifest tree currently exposes 18 podcast directories:

- `bitcoin-audible`
- `bitcoin-magazine-podcast`
- `btc-sessions`
- `coin-stories`
- `lex-fridman`
- `rugpull-radio`
- `simply-bitcoin`
- `stephan-livera-podcast`
- `swan-signal-live`
- `test-podcast`
- `tftc`
- `the-bitcoin-matrix`
- `the-bitcoin-podcast`
- `the-bitcoin-standard-podcast`
- `the-peter-mccormack-show`
- `we-study-billionaires`
- `what-bitcoin-did`
- `what-is-money-show`

Sample manifest counts observed from the extracted tree:

- `simply-bitcoin`: 375
- `the-bitcoin-matrix`: 264
- `bitcoin-audible`: 114
- `what-is-money-show`: 106
- `we-study-billionaires`: 92
- `btc-sessions`: 87
- `tftc`: 83

Sample manifest fields observed:

- `episode_id`
- `episode_slug`
- `podcast_slug`
- `title`
- `audio_url`
- `published_date`
- `duration_seconds`
- `status`
- `stages`
- `artifacts`
- `created_at`
- `updated_at`

Important observations:

- manifests appear to be the best episode-level control records
- `artifacts.beliefs` points to individual belief artifact paths such as `beliefs/d4fa/b_d4fa3b3e7d01a0af.json`
- `stages` enumerates pipeline stages such as `extract`, `speakers`, `weights`, `embed`, and `matrix`

Recommendation:

- use manifest files as the canonical source for episode identity and pipeline artifact references

## `raw/podcasts/`

Observed structure:

- `raw/podcasts/<podcast-slug>/episodes/<episode-slug>/transcript.json`

Example:

- `raw/podcasts/what-is-money-show/episodes/2025-12-12-are-we-better-than-nature-w-michael-sullivan/transcript.json`

Sample `transcript.json` structure observed:

- top-level keys:
  - `episode`
  - `original_speakers`
  - `source`
  - `utterances`

Sample nested `episode` fields observed:

- `title`
- `description`
- `published_at`
- `duration_seconds`
- `audio_url`

Sample `utterances` fields observed:

- `speaker`
- `text`
- `start`
- `end`
- `confidence`

Important observations:

- transcript files contain a complete per-episode utterance stream
- utterances use local speaker labels such as `SPEAKER_00` and `SPEAKER_01`
- this is enough to support transcript-level phrase analysis later
- speaker identity resolution is not directly human-readable here, so transcript files should not be the only source used for person-level normalization

Recommendation:

- treat raw transcript files as the source of utterances and episode-level published metadata
- do not rely on raw transcripts alone for canonical person identity

## `persons/`

Observed structure:

- `persons/<person-id>/profile.json`
- `persons/<person-id>/beliefs.jsonl`
- `persons/<person-id>/trust.json`
- `persons/<person-id>/embedding.json`
- `persons/<person-id>/matrix.json`

Examples:

- `persons/michael-sullivan/profile.json`
- `persons/peter-mccormack/profile.json`

### `profile.json`

Sample fields observed:

- `id`
- `name`
- `slug`
- `bio`
- `has_wiki`
- `wiki`
- `appearances`
- `stats`
- `created_at`
- `updated_at`

Important observations:

- `appearances` is an array of episode slugs
- `stats.total_beliefs` is directly available
- this file appears to be the cleanest first-pass source for person identity and appearance linkage

### `beliefs.jsonl`

Sample fields observed per line:

- `id`
- `episode_id`
- `podcast_id`
- `quote`
- `atomic_belief`
- `worldview`
- `core_axiom`
- `domain`
- `weights`
- `timestamp_start`
- `timestamp_end`
- `created_at`

Important observations:

- the file is scoped to a person directory, so the enclosing folder supplies the person identity
- this is enough to build person-level belief history without depending on the global `beliefs/` tree
- `topic` was not present in the sampled `beliefs.jsonl` rows even though it appeared in the parquet export

Recommendation:

- use `persons/<id>/beliefs.jsonl` as a highly practical first-pass belief source
- verify later whether the global `beliefs/` tree contains a richer superset of fields

### `trust.json`

Sample fields observed:

- `slug`
- `badge`
- `score`
- `factors`
- `weights`
- `breakdown`
- `calculated_at`

Recommendation:

- do not make v1 analytics depend on trust scores
- preserve them if easy, since they may become useful metadata later

## Person-density observations

A quick profile over extracted person folders currently shows:

- 781 `profile.json` files loaded successfully
- 33 people with 10 or more appearances

Top recurring people observed so far:

- `peter-mccormack`: 103 appearances, 3522 beliefs
- `cedric-youngleman`: 92 appearances, 1149 beliefs
- `cedric`: 76 appearances, 773 beliefs
- `nico`: 64 appearances, 1797 beliefs
- `ben`: 43 appearances, 1223 beliefs
- `stephan-livera`: 39 appearances, 466 beliefs
- `michael-saylor`: 26 appearances, 292 beliefs

Important caveat:

- `appearances` arrays are not necessarily date-sorted in the profile files
- longitudinal views should be ordered by joined episode publish date, not by profile array order

## Ingest implications

The audit suggests the first-pass import should be built primarily from:

1. manifests for episode and show structure
2. person profiles for person identity and appearance lists
3. person-scoped `beliefs.jsonl` for person belief history
4. raw transcript files for optional utterance import later

That combination supports a clean initial model for:

- shows
- episodes
- persons
- appearances
- beliefs

without needing to solve every downstream embedding or matrix concern immediately.
