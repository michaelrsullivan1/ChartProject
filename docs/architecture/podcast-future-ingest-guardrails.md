# Podcast Future Ingest Guardrails

Date: 2026-04-22

## Purpose

This note captures the operational and structural guardrails that should be kept in mind when importing more Belief Engines podcast data in the future.

The goal is to make future ingestion safe, predictable, and compatible with the work already done.

## 1. Keep raw data and normalized data separate

This is the most important rule.

Raw source assets:

- live on disk
- should remain reprocessable
- are not the same thing as the query layer

Normalized relational data:

- lives in Postgres
- should be shaped for joins, filters, grouping, and UI payloads
- should not try to mirror every raw file one-to-one as blobs

Current boundary:

- raw snapshot files live under `data/raw/beliefengines/`
- normalized podcast entities live in Postgres tables such as `podcast_shows`, `podcast_episodes`, `podcast_persons`, `podcast_appearances`, and `podcast_beliefs`

Guardrail:

- do not collapse those two layers together later for convenience

## 2. Treat source ids as durable

The system should continue preserving upstream identifiers exactly.

Examples:

- `source_person_id`
- `source_episode_id`
- `source_belief_id`
- `podcast_slug`
- `episode_slug`

Guardrail:

- never replace source ids with only local surrogate meaning
- keep source ids available even if local remapping or derived tables are added later

Why:

- future snapshots may need reconciliation
- source ids are the safest anchor for debugging and reprocessing

## 3. Assume source drift

The Belief Engines dataset already shows that different source layers do not always agree.

Observed examples:

- person profiles may claim more beliefs than person belief files actually contain
- global belief artifacts may be richer than person-scoped belief files
- parquet exports may expose fields that are not consistently present in raw person belief files

Guardrail:

- future import code should assume fields may appear, disappear, or be partially populated
- optional fields should stay nullable
- importer logic should prefer explicit fallbacks rather than assuming one source layer is always complete

## 4. Prefer richer source layers when there is disagreement

Current lesson learned:

- person-scoped `beliefs.jsonl` is not sufficient as the only belief source
- manifest-referenced global belief artifacts are more complete and richer

Guardrail:

- if future snapshots expose multiple representations of the same entity, use the richer and more reliable layer as the primary import source
- keep the weaker layer only as supplement or fallback

## 5. Imports must remain idempotent

Future imports should be safe to rerun.

That means:

- same source show should not create duplicate show rows
- same source episode should not create duplicate episode rows
- same source person should not create duplicate person rows
- same source belief should not create duplicate belief rows

Current implementation already had to handle duplicate belief references across manifests.

Guardrail:

- maintain unique constraints on source ids
- keep importer logic defensive about duplicates within a single run
- prefer update-or-skip behavior to append-only duplication

## 6. Do not assume profile ordering is chronological

Observed issue:

- person profile `appearances` arrays are not guaranteed to be in time order

Guardrail:

- always derive chronology from joined episode publish dates
- never trust source array order for time-series analysis

## 7. Do not over-trust speaker identity quality

Current policy:

- upstream `person_id` is trusted as canonical for v1

That is fine, but future work should still remember:

- speaker identity may contain duplicates
- alternate spellings may exist
- diarization artifacts may create fragmented or placeholder speakers

Guardrail:

- do not build yourself into a corner where a local identity correction layer becomes impossible
- keep the current schema source-aware enough that remapping can be added later if needed

## 8. Keep transcript ingestion secondary until identity reconciliation is clearer

Current transcript files use local labels like:

- `SPEAKER_00`
- `SPEAKER_01`

Guardrail:

- do not treat raw transcript utterances as the primary source of person identity
- transcript-level phrase drift work is valuable, but should remain downstream of reliable person and episode normalization

## 9. Expect database growth

As more podcast data is imported:

- database size will grow
- backup files will grow
- person/topic aggregation queries may get slower

Guardrail:

- keep indexes on source ids and key foreign keys
- watch for expensive live aggregation queries
- add caches or precomputed aggregates only when there is a demonstrated need

Do not prematurely optimize, but do not ignore growth either.

## 10. Remember what database backups do not cover

Database dumps include:

- normalized podcast tables
- all imported relational rows

Database dumps do **not** include:

- raw archive files
- extracted raw snapshot directories

Guardrail:

- if the raw Belief Engines snapshot matters for reprocessing, it must be preserved separately from Postgres backups

## 11. Avoid overcommitting to optional semantic layers

Fields like:

- `topic`
- `worldview`
- `core_axiom`
- polarity-related fields

are useful, but not always guaranteed to be complete or stable across all source layers.

Guardrail:

- treat these as valuable enrichments, not absolute foundations
- keep the product able to function on:
  - person
  - episode date
  - quote
  - atomic belief

even when higher-order fields are spotty

## 12. When importing future snapshots, validate before trusting

Before treating a new snapshot as production-worthy, run a quick validation pass:

1. total shows
2. total episodes
3. total persons
4. total appearances
5. total beliefs
6. first/last episode dates
7. top recurring persons
8. sample person belief counts versus source profile totals
9. null rates for fields like `topic`, `domain`, `worldview`, `core_axiom`

Guardrail:

- do not assume a new snapshot behaves like the current one until these checks are done

## Practical restart checklist

If revisiting this later, the safest order is:

1. confirm the raw snapshot location on disk
2. confirm the importer still matches the source layout
3. inspect a few manifests, person profiles, and belief artifacts
4. run a dry-run import slice
5. validate counts and field coverage
6. only then run a full import or extend the UI

## Bottom line

The system will age well if future work keeps honoring four rules:

- preserve raw source assets separately
- preserve upstream identifiers exactly
- keep imports idempotent
- expect source inconsistency instead of pretending the source is perfectly uniform
