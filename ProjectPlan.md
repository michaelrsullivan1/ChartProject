# X/Twitter Research Visualization App
## Project Plan and Architecture Guide

## Purpose

This project is a **local-first research and visualization application** for collecting, storing, enriching, and presenting X/Twitter post data, with an initial emphasis on Bitcoin-related analysis.

The application is not being designed as a public SaaS product at the start. It is being designed as a **personal research tool and demoable web experience** with the following priorities:

- preserve raw data as a long-term asset
- support manual and incremental ingestion of X/Twitter data
- allow future enrichment with sentiment, confidence, keywords, and other labels
- expose precomputed view data through a Python API
- render polished, highly custom visualizations in a JavaScript frontend
- optimize for local-first use, manual refreshes, and strong presentation quality

This is best understood as a system with four major layers:

1. **Raw acquisition layer**
2. **Normalization and database layer**
3. **Enrichment and view-building layer**
4. **Presentation layer**

The application should remain simple in day-to-day usage, but it should be designed with enough structure that it can grow without requiring a full rewrite.

---

## Product Vision

The long-term vision is a tool that allows the user to:

- ingest tweet data for specific users or specific slices of Twitter/X activity
- retain that data permanently as a proprietary archive
- derive structured signals from the data
- build visually rich, narratively strong charts and dashboards
- demo those charts in videos, threads, or other content
- incrementally expand the system over time as new analyses emerge

The frontend is not intended to be a generic app platform with accounts, permissions, and dynamic multi-user workflows. It is closer to a **private analytical publishing environment**.

That means the architecture should favor:

- data durability over app complexity
- precomputed views over real-time computation
- manual orchestration over automation-heavy infrastructure
- local control over deployment complexity
- chart quality and UX polish over generalized admin tooling

---

## Core Design Principles

### 1. Data is the core asset
The most valuable part of this project is the stored data archive and the ability to enrich it over time.

### 2. Raw data should be preserved
The system should preserve the original API responses or raw payloads as a safety net so the ingestion logic can evolve without data loss.

### 3. Structured storage still matters
The database should not be blob-first. It should remain a traditional structured relational schema for the fields that are important to query, filter, join, sort, or aggregate.

### 4. Derived analytics should be layered on top
Sentiment scores, labels, confidence scores, and future analytical outputs should be stored separately from raw tweet records.

### 5. The frontend should stay relatively dumb
The backend should perform heavy shaping and precomputation so that frontend pages can focus on rendering and interaction.

### 6. The frontend should look excellent
The visual and interaction quality of the charts is a key differentiator. The application should feel polished enough for screen-recorded demos and public-facing explanation, even if the app itself remains private.

### 7. The system should be incremental
The project should be buildable in stages. It should not require every future question to be answered before development begins.

---

## High-Level Architecture

## Layer 1: Raw Acquisition

This layer is responsible for fetching X/Twitter data from the chosen provider.

Current planned provider:

- `twitterapi.io`

This layer should:
- perform manual or script-triggered API requests
- fetch user and tweet data in chunks
- support initial backfills and later refresh windows
- preserve the exact response payload somewhere as an archive
- track what was fetched, when, and for whom

This is the start of the ingestion pipeline.

## Layer 2: Normalized Storage

This layer is the canonical relational representation of the imported data.

It should:
- store users and tweets in traditional tables
- represent important relationships cleanly
- support future joins and analysis
- keep inserted and updated timestamps
- be designed to grow as more analytical needs emerge

## Layer 3: Enrichment and View Generation

This layer is responsible for:
- sentiment scoring
- keyword extraction
- confidence scoring
- topic tagging
- other derived metadata
- page-specific payload generation
- caching or persisting precomputed frontend-ready data

This layer sits between the raw data archive and the frontend.

## Layer 4: Presentation

This layer is the user-facing React frontend.

It should:
- provide basic navigation
- request already-prepared view data from FastAPI endpoints
- render polished, custom charts
- support manual demo workflows
- prioritize aesthetics, clarity, and strong interaction design

---

## Recommended Tech Stack

## Backend
- **Python**
- **FastAPI**
- **PostgreSQL**
- **SQLAlchemy**
- **Alembic**

## Frontend
- **React**
- **TypeScript**
- **Vite**
- **D3** used selectively for custom charts and interactions
- Standard React component architecture for layout, routing, page composition, and supporting UI

## Development Environment
- local-first development
- manual scripts or CLI-based ingestion
- manual regeneration of analysis and view data
- optional Docker later, but not required to start

---

## Why This Stack

## Python backend
Python is the correct home for:
- API ingestion
- data transformation
- enrichment pipelines
- scoring logic
- caching and view construction

## React frontend
React is the correct home for:
- page composition
- UI controls
- reusable layout patterns
- chart containers
- demo-friendly navigation and structure

## D3
D3 should not necessarily be the entire charting system, but it is the right tool for:
- high-control visuals
- custom scales and shapes
- bespoke animation or annotation behavior
- polished demo-worthy data storytelling

Use D3 where its control matters. Do not force raw D3 into every chart if a simpler approach is sufficient.

## PostgreSQL
Postgres is preferred over SQLite because:
- the data archive matters
- future relationships and joins matter
- schema growth is expected
- view generation and analytical querying will likely become more complex
- long-term data reliability is important

---

## Scope

## In scope for v1
- local-only workflow
- manual ingestion
- user and tweet storage
- preservation of raw API payloads
- basic relational schema
- a few derived scoring tables
- page-specific FastAPI endpoints
- polished React views for a handful of charts
- simple inspection and validation flow for ingested data

## Out of scope for v1
- authentication
- permissions
- public hosting
- self-service ingestion from the UI
- user-generated charts
- multi-tenant architecture
- real-time data updates
- frequent or automatic syncing
- advanced admin tools

---

## Core Workflow

The project should support the following end-to-end workflow.

### Step 1: choose a target
Select a user or dataset slice to ingest.

Examples:
- a specific X/Twitter user
- a specific Bitcoin-adjacent account
- a curated set of accounts later
- a time-bound subset of content

### Step 2: fetch raw API data
Call the API manually or via script.

### Step 3: archive raw response
Store the untouched API response somewhere safe.

Possible locations:
- filesystem artifact archive
- a raw ingestion artifact table in Postgres
- both

### Step 4: parse and normalize
Convert the raw response into relational objects:
- users
- tweets
- references
- metadata
- entities if needed

### Step 5: validate
Verify that the ingest worked correctly.

Examples:
- number of tweets parsed
- duplicates encountered
- min/max dates
- missing required fields
- linked user records created or updated

### Step 6: upsert into normalized tables
Insert or update canonical database rows.

### Step 7: run enrichment
Generate derived metadata such as:
- sentiment score
- confidence score
- keyword tags
- account-level or tweet-level labels

### Step 8: build frontend view payloads
Generate precomputed, page-specific payloads to serve through FastAPI.

### Step 9: render in frontend
Open the local web app and navigate to the page or chart.

### Step 10: demo or export findings
Use the page for videos, explanation, threads, screenshots, or internal analysis.

---

## Data Model Philosophy

The core database should be structured around three forms of truth.

## 1. Raw truth
This is the original payload returned by the API.

Purpose:
- backup and auditability
- re-parsing later
- debugging
- preserving fields not yet modeled relationally

## 2. Normalized truth
This is the canonical relational model for the data that will be queried often.

Purpose:
- joins
- filtering
- aggregations
- analytics
- serving downstream views

## 3. Derived truth
This is the set of analytical outputs generated from normalized data.

Purpose:
- scoring
- labeling
- ranking
- trend analysis
- explanatory drilldowns
- prepared UI views

This separation is essential. It prevents confusion between:
- what the API actually said
- what the database stores canonically
- what the system inferred later

---

## Database Strategy

The database should prioritize:
- durability
- clarity
- future extensibility
- straightforward joins
- low ambiguity around what each table represents

The schema should **not** become a dumping ground of endless speculative nullable columns.

Instead, the schema should follow this rule:

> Promote fields to explicit columns when they are likely to be queried, filtered, joined, sorted, or aggregated repeatedly.

Everything else can remain:
- in raw archived payloads
- in JSON sidecars when appropriate
- deferred until a real need emerges

---

## Recommended Initial Tables

These are the tables recommended for the initial project foundation.

## 1. `users`
Canonical information about X/Twitter users.

Likely responsibilities:
- store user identity and profile fields
- link tweets to authors
- support future account-level analysis
- hold the most recent known user profile data

Example fields:
- internal id
- platform user id
- username
- display name
- profile url
- description
- location
- follower count
- following count
- favourites count
- media count
- statuses count
- created at on platform
- verified flags
- profile image URLs
- inserted at
- updated at

Optional:
- raw payload JSON
- archive linkage to raw ingestion artifacts

## 2. `tweets`
Canonical information about individual tweets/posts.

Likely responsibilities:
- store one row per tweet
- link each tweet to an author
- hold the main textual and time-based fields
- hold the current known metrics if snapshots are not used initially

Example fields:
- internal id
- platform tweet id
- author user id
- url
- text
- source
- created at on platform
- language
- conversation id
- reply metadata
- quote metadata
- current engagement counts
- inserted at
- updated at

Optional:
- raw payload JSON
- direct linkage to ingestion artifacts

## 3. `tweet_references`
Relationships between tweets.

Purpose:
- represent replies
- represent quotes
- represent retweets/reposts
- support more flexible relationship modeling than hard-coding everything into the tweet table

Example fields:
- internal id
- tweet id
- referenced tweet platform id
- reference type
- referenced user platform id if available
- inserted at

## 4. `ingestion_runs`
A record of each manual ingest attempt or import operation.

Purpose:
- track data provenance
- support debugging
- provide visibility into what was fetched and when
- distinguish backfills from refreshes

Example fields:
- internal id
- source name
- endpoint name
- target user platform id
- import type
- requested since
- requested until
- started at
- completed at
- status
- notes
- inserted at

## 5. `raw_ingestion_artifacts`
Storage for untouched raw payloads or references to stored raw payload files.

Purpose:
- preserve raw API responses
- enable reparsing
- support debugging and recovery
- retain fields not yet modeled

Example fields:
- internal id
- ingestion run id
- artifact type
- payload JSON or file path
- record count estimate
- created at

## 6. `tweet_sentiment_scores`
Derived sentiment outputs for individual tweets.

Purpose:
- hold analytical interpretations separately from canonical tweet data
- support future model changes without polluting the tweet table

Example fields:
- internal id
- tweet id
- model name
- model version
- score value
- score label
- confidence
- analysis run id
- created at

## 7. `tweet_keywords`
Extracted keywords or keyword-level associations for tweets.

Purpose:
- support term analysis
- drive filters and rollups
- link tweet content to derived tags

Example fields:
- internal id
- tweet id
- keyword
- keyword type
- score or weight
- model name
- model version
- analysis run id
- created at

## 8. `tweet_labels`
Generalized labels for future extensibility.

Purpose:
- support custom or model-generated labels
- avoid repeatedly altering the tweet table
- support multiple label namespaces later

Example fields:
- internal id
- tweet id
- label namespace
- label name
- label value
- confidence
- analysis run id
- created at

## 9. `view_cache`
Precomputed payloads for frontend pages.

Purpose:
- serve prepared page data quickly
- keep frontend logic simple
- make charts deterministic and stable until manually regenerated

Example fields:
- internal id
- view key
- subject type
- subject id
- params hash
- schema version
- payload JSON
- generated at
- source analysis run id

---

## Open Modeling Choices

The following choices are intentionally left somewhat flexible at the start.

## Engagement metrics
Two acceptable options:

### Option A: store latest metrics on `tweets`
Simpler for v1. Good if historical metric state is not important.

### Option B: store historical metric snapshots
Better if you want to know how engagement changed over time.

At the moment, the initial direction can safely start with **Option A** and move to snapshots later if needed.

## Raw payload storage
Two acceptable options:

### Option A: raw JSON stored directly on core tables
Simpler, faster to implement, good safety net.

### Option B: raw payloads stored in `raw_ingestion_artifacts`
Cleaner separation between archive storage and canonical relational tables.

Current recommendation:
- prefer `raw_ingestion_artifacts`
- allow selective `raw_payload_json` columns on core tables if useful during early development

## Entities like hashtags, URLs, mentions, media
These can be deferred or introduced incrementally depending on how useful the API data is and how soon those fields matter for analysis.

---

## Ingestion System Design

The project should include an explicit ingestion flow even if it remains fully manual.

This should not be thought of as a side concern. It is a core part of the architecture.

## Goals of the ingestion system
- preserve source data
- keep imports inspectable
- allow replay or reparsing later
- support confidence in the data
- support incremental refreshes

## Recommended ingestion stages

### Stage 1: fetch
Make the API request and collect the raw response.

### Stage 2: archive
Write the raw response to:
- disk
- database
- or both

### Stage 3: register run
Create an `ingestion_runs` record with metadata about the import.

### Stage 4: parse
Transform raw payloads into structured objects.

### Stage 5: validate
Check counts, duplicates, date ranges, and expected relationships.

### Stage 6: commit
Upsert rows into `users`, `tweets`, and other normalized tables.

### Stage 7: summarize
Output a summary for inspection.

Example summary:
- tweets inserted
- tweets updated
- users inserted
- users updated
- min/max tweet date
- duplicates
- errors encountered

---

## Ingestion UX and Tooling

The ingestion experience does not need a full UI in v1. A script or CLI is sufficient.

Possible commands:
- fetch raw data
- normalize and commit data
- inspect last run
- rebuild derived analysis
- rebuild frontend views

Future optional enhancement:
- a local-only inspection page in the frontend for ingestion status

That is not required to start.

---

## Refresh Strategy

The project should support two major ingest modes.

## Initial backfill
Fetch a meaningful chunk of data for a target user and store it permanently.

## Incremental refresh
Later fetch only the recent slice needed to update the dataset, such as:
- the last month
- the last two months
- everything since the newest stored tweet
- a small overlap window to ensure completeness

The system should be written so refreshes do not require re-ingesting everything from scratch.

Helpful fields on `users` or run metadata:
- last ingested at
- last tweet seen at
- most recent tweet timestamp stored

---

## API Layer Design

The FastAPI layer should expose view-oriented endpoints, not generic entity CRUD.

This project is not a generic data admin app. It is a read-focused analytical presentation tool.

Recommended endpoint style:
- `/api/views/{view_key}`
- `/api/views/{view_key}/{subject_id}`
- `/api/views/{view_key}?params=...`

Examples:
- `/api/views/author-vs-btc/12345`
- `/api/views/author-sentiment-timeline/12345`
- `/api/views/keyword-breakdown/12345`

Each endpoint should return:
- exactly the data shape the page needs
- a stable schema version if helpful
- little to no extraneous backend structure

This keeps the frontend simple and fast to iterate on.

---

## Frontend Architecture

The frontend should be intentionally light as an application shell and strong as a presentation layer.

## Responsibilities
- basic routing
- page composition
- loading view payloads from FastAPI
- chart rendering
- UI polish
- inspection panels or chart legends as needed

## Non-responsibilities
- complex business logic
- heavy data transformations
- ad hoc querying against raw datasets
- data refresh orchestration
- ingestion control

## Recommended frontend structure
- `src/app` for app shell and routing
- `src/pages` for page-level views
- `src/components` for reusable layout and UI
- `src/charts` for chart components and D3 logic
- `src/api` for view fetchers
- `src/types` for response shapes
- `src/utils` for small frontend-only helpers

---

## Charting Strategy

Charting is a key differentiator for this project.

The visuals should feel:
- deliberate
- custom
- polished
- screen-recording friendly
- clear in narrative flow

## Recommended approach
Use React for structure and D3 where customization matters.

Possible division:
- React handles layout, component lifecycle, and state
- D3 handles scales, axes, shapes, annotations, brushing, and custom interactions

## Avoid these traps
- do not over-engineer every chart into a generic system too early
- do not force all transformations into the browser
- do not design around public multi-user dashboards yet

## Good chart candidates
- author sentiment vs Bitcoin price
- posting frequency over time
- engagement over time
- confidence-weighted sentiment trend
- keyword usage over time
- comparison between multiple authors
- drilldown from spikes to underlying tweets

---

## UX Principles

This app is private, but the UX still matters a great deal because it will be demoed and visually judged.

The UX should optimize for:
- clarity
- smoothness
- visual confidence
- low friction navigation
- easy storytelling in a screen recording

## UX implications
- page transitions should feel clean
- loading states should be minimal and elegant
- chart legends and labels should be readable
- controls should be sparse and intentional
- the app should feel more like a crafted analytical instrument than a cluttered dashboard

## The target experience
The user opens a page and immediately feels:
- this is focused
- this is high quality
- this has a point of view
- this analysis is intentional

---

## Data Validation and Trust

Because the data is valuable, trust in ingestion matters.

The project should include easy ways to answer:
- what was imported
- when it was imported
- what source it came from
- whether rows were inserted or updated
- how much data is stored for a given user
- what date range is covered

Basic validation utilities should exist early.

Examples:
- count tweets per user
- min/max tweet dates per user
- detect missing users for tweets
- detect duplicate tweet ids
- inspect the latest ingestion run
- inspect a raw artifact manually

---

## Backup Strategy

The data archive is a primary project asset.

Backups should be treated as part of the system design, even if implemented simply at first.

## Principles
- normalized DB data should be backed up
- raw payload archives should be backed up
- generated views are reproducible and lower priority
- at least one backup should exist off the primary machine

## Practical early approach
- regular Postgres dump
- archived raw JSON files stored in a separate data directory
- periodic manual copy to another drive or cloud storage
- simple written backup procedure in the repo

---

## Project Structure Recommendation

A possible monorepo structure:

```text
project-root/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      views/
    scripts/
      ingest/
      enrich/
      validate/
      build_views/
    migrations/
    tests/
    pyproject.toml

  frontend/
    src/
      app/
      api/
      pages/
      components/
      charts/
      hooks/
      types/
      utils/
    package.json
    vite.config.ts

  data/
    raw/
      twitterapi/
    exports/
    backups/

  docs/
    architecture/
    decisions/

  README.md
```

This structure can evolve, but it provides a clean separation.

---

## Backend Modules Recommendation

Possible backend module responsibilities:

## `api`
FastAPI routes and endpoint definitions.

## `models`
SQLAlchemy models.

## `schemas`
Pydantic request and response shapes.

## `services`
Business logic for:
- fetching prepared views
- rebuilding caches
- reading data summaries

## `scripts/ingest`
Manual data ingestion commands.

## `scripts/enrich`
Sentiment and keyword generation logic.

## `scripts/validate`
Validation and consistency checks.

## `scripts/build_views`
Generate precomputed payloads for frontend pages.

## `db`
Session management, engine setup, and migrations integration.

---

## Frontend Modules Recommendation

## `pages`
Page-level containers that correspond closely to routes.

## `charts`
Custom chart components and D3 integration.

## `api`
Typed fetch functions that call backend view endpoints.

## `components`
Reusable non-chart UI pieces:
- page shell
- side panel
- control groups
- legends
- cards
- navigation

## `types`
TypeScript representations of backend payloads.

---

## Suggested Development Phases

## Completed: foundation
- initialize backend
- initialize frontend
- wire up FastAPI and React locally
- set up Postgres
- add Alembic migrations
- create initial tables
- implement basic health endpoint
- implement basic page shell in frontend

## Completed: first-pass ingestion
- add manual ingestion script
- fetch raw data from `twitterapi.io`
- archive raw artifacts
- parse users and tweets
- upsert normalized rows
- add validation summary output

## Completed: first-pass inspection
- build basic data inspection scripts
- confirm counts and date ranges
- manually inspect raw vs normalized output
- refine schema if needed

## Phase 4: enrichment
- add sentiment scoring pipeline
- add keyword extraction pipeline
- add derived tables
- version scoring runs where appropriate

## Phase 5: views
- extend beyond the first dedicated chart page
- add additional view payload builders
- expand explanatory drilldowns
- decide whether and when to add `view_cache`

## Phase 6: frontend presentation
- refine the current Michael Saylor vs BTC page
- decide the default chart granularity and BTC presentation strategy
- improve page shell and navigation as more pages land
- refine typography, spacing, loading states, and animation
- prepare for video demos

## Phase 7: iteration
- add additional chart types
- add more authors
- improve comparative analyses
- refine ingestion refresh flows
- improve backup and validation procedures
- verify restores regularly and keep off-machine backups

---

## Suggested v1 Screens

These are candidate screens, not mandatory commitments.

## 1. Author vs Bitcoin price
Compare a target author's sentiment or posting activity against Bitcoin price action.

## 2. Author sentiment timeline
Show directional sentiment over time, confidence, and spikes.

## 3. Posting frequency timeline
Show volume and cadence over time.

## 4. Keyword trend page
Show how selected terms rise and fall in usage.

## 5. Tweet drilldown view
Show the underlying tweets that explain a spike or interesting moment.

## 6. Multi-author comparison
Compare several authors against the same timeline or metric.

---

## Suggested Decision Log Topics

The project should maintain lightweight architecture decision records over time.

Useful early decisions to log:
- why Postgres over SQLite
- why FastAPI
- why React + D3
- whether raw payloads live in DB, files, or both
- whether metrics are stored directly on tweets or in snapshots
- when to introduce entities like hashtags and mentions
- how view caches are versioned
- whether to move from local-only toward hosted usage later

---

## Risks and Failure Modes

## 1. Schema drift from premature flexibility
Avoid endless nullable columns without clear purpose.

## 2. Overbuilding the frontend as an app platform
Keep it a read-focused analytical presentation tool.

## 3. Losing raw source fidelity
Preserve raw artifacts so future schema changes do not destroy optionality.

## 4. Mixing raw, derived, and presentation data together
Keep those concerns separate.

## 5. Underinvesting in backup discipline
The data is valuable enough to justify backup procedures early.

## 6. Letting frontend transform too much data
Push transformation and shaping to the backend.

---

## Non-Goals

The following are explicitly not required to start:
- public cloud deployment
- production auth
- third-party login
- self-service chart authoring
- generalized query builder UI
- real-time push updates
- event-driven infrastructure
- microservices
- Kubernetes
- complex observability stack

This is a focused local analytical system first.

---

## Initial Concrete Recommendations

If starting implementation immediately, use:

### Backend
- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

### Frontend
- React
- TypeScript
- Vite
- D3 selectively

### Core current tables
- `users`
- `tweets`
- `tweet_references`
- `ingestion_runs`
- `raw_ingestion_artifacts`
- `market_price_points`

### Likely next tables
- `tweet_sentiment_scores`
- `view_cache`

### Completed early workflow
- manually ingest one target user
- validate imported data
- build one derived comparison view
- expose one view endpoint
- render one polished chart page
- add a first drilldown path

### Current workflow
- iterate on the first chart with real data
- decide week versus day as the default tweet view
- decide whether BTC should stay daily in presentation
- choose between a second chart page and deeper drilldown work
- add derived enrichment only when it clearly supports the next screen

---

## Current Near-Term Steps

1. Decide whether the default tweet series for the first chart should stay weekly or switch to daily.
2. Decide whether BTC should remain daily in presentation or be resampled for comparison views.
3. Expand the current drilldown if it materially improves explanation of spikes or interesting weeks.
4. Build the second chart page or second author comparison, whichever best validates reuse.
5. Keep backup discipline operational with regular restores and off-machine copies.

---

## Final Positioning Statement

This project should be treated as a **local-first X/Twitter research archive and visualization system** with a strong emphasis on:

- preserving data as a proprietary asset
- separating raw, normalized, and derived data cleanly
- using Python for ingestion and shaping
- using React and D3 for presentation quality
- manually controlling refresh and regeneration
- building demo-worthy analytical pages incrementally

That combination should give the project:
- strong long-term optionality
- high confidence in the data layer
- low unnecessary app complexity
- a frontend that can genuinely stand out visually
