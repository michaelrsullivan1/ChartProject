# Podcast Implementation Status

Date: 2026-04-22

## Purpose

This note captures the implementation state reached for the podcast belief work so far.

It is intended to preserve:

- what was decided
- what was built
- how the current import path works
- what the first frontend pilot does
- what still remains open

## Current position

The project now has a separate podcast data path living alongside the existing Twitter/X system.

Important boundary:

- this work does **not** replace or modify the existing tweet analysis flows
- this work adds a new podcast-specific schema, import path, API surface, and pilot frontend route
- the two systems currently share project structure, database, backend, frontend shell, and styles, but not analysis logic

## Key decisions locked in

### Source of truth

Canonical source:

- full Belief Engines snapshot archive
- `be-podcast-dataset-2026-04-21.tar.zst`

Local raw paths:

- archive: `data/raw/beliefengines/be-podcast-dataset-2026-04-21.tar.zst`
- extracted snapshot: `data/raw/beliefengines/extracted/podcast-etl-data/`

### Identity handling

For v1:

- trust upstream `person_id` / `speaker_slug` as canonical
- do not add a local identity repair layer yet

### Product emphasis

Primary focus:

- person-first longitudinal analysis

Not the focus right now:

- episode-centric browsing
- coupling to tweet sentiment/mood pages
- embedding-driven UX

### First pilot subject

The first pilot person is:

- `michael-saylor`

## What was learned from the snapshot

The extracted snapshot contains real raw structure beyond the parquet sample layer.

Most important directories:

- `runs/manifests/`
- `raw/podcasts/`
- `persons/`
- `beliefs/`

Most important source files for the current implementation:

- `runs/manifests/<show>/<episode>.json`
- `persons/<person>/profile.json`
- `persons/<person>/beliefs.jsonl`
- `beliefs/<prefix>/<belief>.json`

Important lesson:

- person-scoped `beliefs.jsonl` files are not always complete enough for real belief coverage
- global belief artifacts referenced from episode manifests are richer and more reliable

That is why the importer now treats:

- manifest/global belief artifacts as the primary belief source
- person belief files as fallback / supplemental source

## Schema now implemented

The following tables were added:

- `podcast_shows`
- `podcast_episodes`
- `podcast_persons`
- `podcast_appearances`
- `podcast_beliefs`

Migration:

- [0012_add_podcast_core_schema.py](/Users/michaelsullivan/Code/ChartProject/backend/migrations/versions/0012_add_podcast_core_schema.py)

Model files:

- [podcast_show.py](/Users/michaelsullivan/Code/ChartProject/backend/app/models/podcast_show.py)
- [podcast_episode.py](/Users/michaelsullivan/Code/ChartProject/backend/app/models/podcast_episode.py)
- [podcast_person.py](/Users/michaelsullivan/Code/ChartProject/backend/app/models/podcast_person.py)
- [podcast_appearance.py](/Users/michaelsullivan/Code/ChartProject/backend/app/models/podcast_appearance.py)
- [podcast_belief.py](/Users/michaelsullivan/Code/ChartProject/backend/app/models/podcast_belief.py)

## Import path now implemented

Importer:

- [import_podcast_snapshot.py](/Users/michaelsullivan/Code/ChartProject/backend/scripts/ingest/import_podcast_snapshot.py)

Current import behavior:

1. load shows and episodes from manifests
2. load persons from person profiles
3. load appearance links from person profile `appearances`
4. load beliefs from person belief files when available
5. enrich/backfill beliefs from manifest-referenced global belief artifacts
6. dedupe belief ids in-memory during import to avoid duplicate insert failures

Current import result from the full snapshot:

- 18 shows touched
- 1,551 manifest-backed episodes processed
- 781 person profiles processed
- 2,086 appearance links processed
- 31,935 belief rows processed

## Why the belief importer changed

During the first import pass, Michael Saylor exposed a source mismatch:

- profile suggested 26 appearances and 292 beliefs
- person-scoped `beliefs.jsonl` only contained 2 rows

Inspection of the corresponding episode manifest showed many more belief artifact references.

Conclusion:

- the manifest/global artifact layer is the more trustworthy belief source for full coverage

This changed the importer design.

## Current backend API

Service:

- [podcast_person_view.py](/Users/michaelsullivan/Code/ChartProject/backend/app/services/podcast_person_view.py)

Route:

- `GET /api/views/podcasts/persons/{person_slug}`

Current response shape includes:

- subject
- summary
- top shows
- top topics
- monthly topic counts
- appearances
- recent beliefs

Current route registration lives in:

- [views.py](/Users/michaelsullivan/Code/ChartProject/backend/app/api/routes/views.py)

## Current frontend pilot

Frontend API file:

- [podcastPerson.ts](/Users/michaelsullivan/Code/ChartProject/frontend/src/api/podcastPerson.ts)

Frontend page:

- [PodcastPersonPage.tsx](/Users/michaelsullivan/Code/ChartProject/frontend/src/pages/PodcastPersonPage.tsx)

Current hash route:

- `#/podcasts/michael-saylor`

Current shell entry:

- `Podcast Pilot` button in the shared app shell

Important UI scope:

- basic rendering only
- summary cards
- plain tables
- no advanced charting yet

Files updated for route/shell integration:

- [App.tsx](/Users/michaelsullivan/Code/ChartProject/frontend/src/App.tsx)
- [AppShell.tsx](/Users/michaelsullivan/Code/ChartProject/frontend/src/components/AppShell.tsx)

## Current Michael Saylor pilot data

The current Michael Saylor pilot returns:

- 26 appearances
- 294 imported beliefs
- range start `2025-07-25T19:13:33Z`
- range end `2026-01-24T19:00:51Z`

Sample top topics:

- `Bitcoin / Price Prediction`
- `Bitcoin / Market Sentiment`
- `Bitcoin / Value Prediction`

Sample top show:

- `Simply Bitcoin`

## How to run the current flow

### Apply migrations

```bash
cd /Users/michaelsullivan/Code/ChartProject/backend
../.venv/bin/alembic upgrade head
```

### Run the full podcast import

```bash
cd /Users/michaelsullivan/Code/ChartProject/backend
../.venv/bin/python scripts/ingest/import_podcast_snapshot.py
```

### Run a smaller dry-run slice

```bash
cd /Users/michaelsullivan/Code/ChartProject/backend
../.venv/bin/python scripts/ingest/import_podcast_snapshot.py --limit-shows 2 --limit-persons 5 --dry-run
```

### Open the pilot page

Start the normal app stack, then visit:

- `#/podcasts/michael-saylor`

## What is verified

Verified so far:

- migration applies successfully
- full import completes successfully
- backend person-view service returns real Michael Saylor data
- frontend build passes with the new podcast route and page
- live backend route responds for `michael-saylor`

## What remains open

Still intentionally unresolved:

- final UI design
- richer visual charting
- additional people routes
- show-level pages
- transcript utterance ingestion
- local identity override layer
- embedding-driven features

## Recommended next steps

The most sensible near-term next steps are:

1. add one or two more people to the pilot routing
2. add a small person selector instead of hardcoding a single route
3. add a simple monthly summary section or filter controls before doing fancy charts
4. decide whether transcript utterances should be normalized next for phrase drift work

## Related notes

- [Podcast Person-First Implementation Plan](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-person-first-implementation-plan.md)
- [Podcast Snapshot Layout Audit](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-snapshot-layout-audit.md)
- [Podcast Schema Refinement](/Users/michaelsullivan/Code/ChartProject/docs/architecture/podcast-schema-refinement.md)
