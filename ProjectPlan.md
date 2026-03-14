# Codex Build Prompt: Michael Saylor × Bitcoin Timeline Visualization

## Project Overview

I want to build a polished data visualization project that explores the relationship between **Bitcoin price over time** and **Michael Saylor’s Bitcoin-related posting activity over time**.

This is **not** meant to start as a normal dashboard or broad website product. The first goal is to build a **clean, extensible data pipeline and a compelling animated prototype** that can later evolve into either:

1. a cinematic rendered video,
2. a browser-based interactive visualization,
3. or both.

The core visual concept is:

* a **Bitcoin price line chart** drawn progressively over time,
* a synchronized **bar chart showing Michael Saylor’s Bitcoin-related post count** over time,
* and selected **tweet/post cards** that appear at important moments on the timeline.

This first build should prioritize:

* correctness of data,
* clean architecture,
* reproducible data collection,
* maintainable code,
* and a polished MVP visualization pipeline.

I want a project foundation that is robust enough to support future experimentation, including alternate renderers, alternate time windows, richer annotations, and more nuanced derived metrics.

---

# Primary Goal

Build the foundational version of a project that:

1. Collects **all accessible Michael Saylor posts** needed for this analysis.
2. Identifies which posts are **Bitcoin-related**.
3. Stores the raw post archive in a structured, queryable format.
4. Builds **weekly and monthly aggregated post counts**.
5. Loads a historical **Bitcoin price series**.
6. Aligns both datasets onto consistent time buckets.
7. Produces a first-pass animated visualization showing:

    * Bitcoin price over time
    * Michael Saylor Bitcoin-related post frequency over time
    * placeholders or basic support for selected iconic post cards
8. Makes it easy to later add:

    * hand-picked iconic moments
    * richer classification logic
    * more metrics
    * alternate rendering approaches
    * export-ready assets

---

# High-Level Product Vision

The intended final experience is something like this:

## Top Panel

A line chart of Bitcoin’s price over time.

Requirements:

* line animates left to right
* long time horizon
* clean visual style
* readable on dark background
* monthly view likely best for the first polished version
* weekly support should still exist in the underlying data model

## Bottom Panel

A bar chart of Michael Saylor’s Bitcoin-related posting frequency.

Requirements:

* bars animate in sync with the price timeline
* support both weekly and monthly bucketed data
* likely start with monthly bars in the first cinematic version
* allow later support for alternate definitions, such as:

    * strict Bitcoin-related posts
    * Bitcoin-adjacent posts
    * all posts

## Event Overlays

At selected key moments:

* briefly slow or pause animation
* surface a designed post card
* highlight the relevant time bucket
* optionally show contextual metadata

The post cards should **not** require raw screenshots in the first version. Instead, they should be represented as clean, custom-rendered cards built from structured post data.

---

# Important Constraints and Preferences

## Project Philosophy

* Prioritize **data integrity first**.
* Do **not** over-index on flashy visuals before the underlying archive is correct.
* Build the project in **layers** so it is easy to validate each stage independently.
* Make every transformation reproducible.
* Keep raw data separate from derived data.
* Keep derived data separate from rendered assets.

## Scope Discipline

The first build should **not** try to answer a huge causal claim like:

* “Did Michael Saylor cause Bitcoin to go up?”

Instead, frame this as:

* tracking the evolution of Michael Saylor’s Bitcoin communication intensity,
* and visualizing it alongside Bitcoin’s price over time.

## Aesthetic Intent

The project should aim toward:

* dark theme
* clean typography
* elegant motion
* minimal clutter
* a premium feel
* a narrative / cinematic tone rather than an overloaded dashboard feel

## Technical Preference

The project should start in **Python**.

Recommended initial stack:

* Python
* pandas
* DuckDB or SQLite
* Plotly for the first prototype
* optional notebooks for exploration

Potential later stack:

* Manim for more choreographed animation
* React + D3 for a browser-based interactive version

The first implementation does **not** need to commit to those later stages, but it should be architected so that migration is feasible.

---

# Deliverables I Want from This Build

I want this project scaffolded and implemented in a way that gives me the following deliverables.

## Deliverable 1: Raw Post Archive

A structured table of Michael Saylor posts with metadata.

At minimum, each record should support:

* unique post ID
* created timestamp
* full text
* URL if available
* engagement metrics if available
* repost / quote indicators if available
* media indicators if available
* derived classification fields

## Deliverable 2: Bitcoin Price Dataset

A clean historical Bitcoin price dataset suitable for weekly and monthly aggregation.

At minimum, include:

* timestamp/date
* close price
* ideally OHLC if easy to obtain

## Deliverable 3: Derived Aggregations

Generated datasets that support visualization.

At minimum:

* weekly Bitcoin-related post counts
* monthly Bitcoin-related post counts
* weekly Bitcoin price series
* monthly Bitcoin price series
* aligned time series suitable for animation

## Deliverable 4: Candidate Iconic Post Table

A workflow and table for manually marking or reviewing important posts.

At minimum:

* post ID
* date
* short label
* why it matters
* optional priority / emphasis score
* flag for whether it should appear in the visualization

## Deliverable 5: Static Visualization Preview

A first static chart showing:

* BTC line chart
* Saylor post-count bar chart
* basic visual styling
* at least one sample post card

## Deliverable 6: Animated Prototype

A working animated proof of concept that:

* progressively draws the BTC line
* progressively reveals post count bars
* supports event markers and basic post card overlays
* exports to a usable format, ideally HTML and optionally MP4 or GIF later

---

# What I Want Codex To Do

I want you to act as a senior engineer and project scaffolder.

Your job is to:

* design the project structure,
* create the codebase foundation,
* implement the core data and visualization pipeline,
* and leave the project in a state where I can iteratively refine classification and aesthetics.

Be thoughtful, pragmatic, and modular.
Do not try to over-abstract prematurely.
Favor clear code and good separation of responsibilities.

---

# Requested Development Approach

Please build this in clear phases.

Each phase should be independently runnable and testable.

I want the project organized so I can inspect outputs after each stage.

---

# Phase 1: Scaffold the Repository

Create a clean Python project structure.

## Requirements

Set up a repo with folders along these lines:

```text
btc-saylor-viz/
  README.md
  pyproject.toml
  requirements.txt or uv/pdm/poetry equivalent
  .env.example
  .gitignore
  data/
    raw/
    interim/
    processed/
    manual/
  notebooks/
  src/
    config.py
    utils/
    data_sources/
    ingestion/
    classification/
    transforms/
    visualization/
    rendering/
  scripts/
  tests/
  output/
    charts/
    animations/
    cards/
```

You may adjust folder names if you think there is a significantly better structure, but preserve the same spirit:

* raw data is separate
* processed data is separate
* manual annotations are separate
* visualization code is separated from ingestion code

## Additional setup requirements

* Include a `README.md` explaining the architecture and how to run each phase.
* Include a `.env.example` for any API keys.
* Include a central configuration file or config module.
* Include basic logging.
* Include a `Makefile` or equivalent simple command interface if helpful.
* Include sensible ignore rules for data artifacts, caches, secrets, and virtual env files.

---

# Phase 2: Define the Data Model

Design the core schemas/tables/files used in the project.

## Required datasets

### A. Raw Michael Saylor posts

Create a schema for a raw posts table.

Suggested fields:

* `post_id`
* `created_at`
* `created_date`
* `text`
* `url`
* `author_username`
* `author_display_name`
* `like_count`
* `repost_count`
* `reply_count`
* `quote_count`
* `view_count`
* `is_repost`
* `is_quote`
* `has_media`
* `media_count`
* `language`
* `source`
* `conversation_id`
* `raw_json_path` or a way to preserve original payloads
* ingestion timestamp

If some fields are unavailable depending on API/source, make the schema resilient.

### B. Classified posts

Create a derived classified posts table.

Suggested fields:

* all identifying fields from raw posts as needed
* `bitcoin_related`
* `bitcoin_adjacent`
* `bitcoin_relevance_score`
* `classification_reason`
* `manual_override`
* `iconic_candidate`
* `theme_tags`

### C. Aggregate counts

Create schemas for:

* weekly post counts
* monthly post counts

Suggested fields:

* `bucket_start`
* `bucket_end`
* `bucket_label`
* `bucket_granularity`
* `bitcoin_related_post_count`
* `bitcoin_adjacent_post_count`
* `all_post_count`
* `iconic_post_count`
* optional engagement sums / averages

### D. Bitcoin price history

Create schema for BTC price data.

Suggested fields:

* `timestamp`
* `date`
* `open`
* `high`
* `low`
* `close`
* `volume`
* `source`

### E. Manual iconic events table

Create a manually editable CSV or YAML/JSON file for iconic post selection.

Suggested fields:

* `post_id`
* `date`
* `title`
* `summary`
* `importance_score`
* `include_in_animation`
* `notes`

---

# Phase 3: Build the Michael Saylor Post Ingestion Pipeline

This is one of the most important pieces.

I want a reliable way to build a comprehensive archive of Michael Saylor posts relevant to this project.

## Requirements

* Build an ingestion module that can fetch Michael Saylor’s posts from a source/API.
* Make the ingestion process resumable and paginated.
* Preserve raw responses where useful.
* Normalize output into the raw posts table format.
* Avoid duplicate posts.
* Log progress and counts.

## Important design goals

* Make it easy to rerun ingestion without corrupting data.
* Make it easy to expand with additional fields later.
* If API access is constrained, architect the code so alternative sources can be swapped in later.

## What I need implemented

* a data source abstraction/interface
* one concrete ingestion implementation
* normalization functions
* persistence to CSV and/or Parquet and/or DuckDB
* a script or CLI command like `python scripts/ingest_saylor_posts.py`

## Nice-to-have

* checkpointing or cursor persistence
* detection of already-ingested IDs
* raw payload archiving
* rate-limit-aware behavior

## Important note

The code should not hardcode assumptions that only work once. Make it reusable.

---

# Phase 4: Build the Bitcoin Price Ingestion Pipeline

I want a clean historical BTC price series suitable for long-range analysis.

## Requirements

* ingest historical BTC price data
* normalize it into a standard table
* support weekly and monthly aggregation
* support a long time range

## Implementation goals

* simple, reproducible ingestion
* clear source attribution
* consistent date handling
* no silent timezone weirdness

## What I need

* ingestion script
* normalized output
* aggregation helpers

## Notes

If daily data is the easiest starting point, that is fine.
We can derive weekly/monthly from daily.
The first polished visualization likely uses **monthly close**, but I want the infrastructure to support both monthly and weekly.

---

# Phase 5: Implement Bitcoin-Related Post Classification

I need a reliable first-pass classification layer for determining which Michael Saylor posts are Bitcoin-related.

## Key requirement

I care a lot about being able to get a complete count of posts so I can later inspect important ones manually.

So the classification system should be:

* transparent
* editable
* reproducible
* easy to override

## First-pass classification strategy

Implement a rule-based system first.

Start with keyword and phrase matching for things like:

* bitcoin
* btc
* ₿
* satoshi
* sats
* digital gold
* store of value
* cyber economy
* energy network
* references that are plausibly Bitcoin-related
* MicroStrategy / Strategy posts that clearly relate to Bitcoin treasury accumulation

## Output requirements

For each post, provide:

* classification boolean
* score if possible
* explanation or matched terms
* room for manual override

## Nice-to-have

* distinction between:

    * strict Bitcoin-related
    * Bitcoin-adjacent
    * unrelated
* tags for themes like:

    * treasury
    * acquisition
    * meme
    * macro
    * philosophy
    * product/company

## Important implementation detail

I do not want a black-box classifier first.
Start simple and inspectable.
If you want to make the code easy to later plug in a more advanced model-based classifier, that is good, but the initial version should stay understandable.

---

# Phase 6: Manual Review Workflow

I want a practical workflow for manually reviewing classified posts and selecting iconic ones.

## What I need

Please create:

* a reviewable export of all classified Bitcoin-related posts
* sorted views for highest engagement, earliest posts, most recent posts, etc.
* a file or workflow where I can mark iconic posts manually

## Helpful outputs

Generate some exports such as:

* all Bitcoin-related posts sorted by date
* top engagement Bitcoin-related posts
* candidate iconic posts by engagement percentile
* first N Bitcoin-related posts chronologically

## Goal

This should make it easy for me to inspect posts later and hand-curate which ones deserve a moment in the animation.

---

# Phase 7: Aggregation and Alignment Logic

Now build the time-series transformations.

## Requirements

Generate both weekly and monthly aggregations.

### For Saylor posts

* count Bitcoin-related posts per week
* count Bitcoin-related posts per month
* optionally count adjacent posts too
* optionally count all posts too

### For Bitcoin price

* derive weekly series
* derive monthly series
* preserve a clear definition, such as:

    * week ending close
    * month-end close

### Alignment output

Create merged time-series datasets suitable for charting.

Suggested fields:

* time bucket
* BTC close
* Saylor Bitcoin-related post count
* optional additional metrics
* flag for whether the bucket contains iconic posts

## Key principle

This transformation layer should make it very easy to switch the visualization between weekly and monthly mode.

---

# Phase 8: Static Visualization Prototype

Before building the animation, create a high-quality static chart.

## Requirements

Create a static prototype that includes:

* top BTC line chart
* bottom Saylor Bitcoin-related post count bar chart
* dark theme
* good spacing and hierarchy
* at least one mock or real structured post card

## Design goals

* clean and premium feel
* readable typography
* restrained color palette
* no unnecessary chart junk
* visual structure that could evolve into an animation later

## Output

* save the static preview to the `output/` directory
* ideally generate both an HTML preview and a static image if feasible

## Important

Do not rush to animation until the static composition looks good.

---

# Phase 9: Animated Prototype

Once the static prototype exists, build the first animation.

## Core animation behavior

* Bitcoin line draws progressively over time
* post count bars appear progressively over time
* support a moving current-time indicator if useful
* support event markers
* support brief overlays for selected iconic posts

## Initial animation scope

Keep the first animation relatively simple and robust.

It does not need to be a final cinematic masterpiece.
It just needs to prove the motion concept.

## Implementation goals

* produce a reusable animation pipeline
* keep frame generation / renderer logic organized
* make it possible to swap between weekly and monthly mode
* make it possible to include or exclude iconic overlays

## Suggested output modes

* interactive HTML prototype
* optionally a rendered file path reserved for later export

## Notes

The first implementation can use Plotly if that is the most practical way to get something working quickly.
If you strongly prefer another Python-based approach for maintainability, explain your reasoning in the README.

---

# Phase 10: Post Card Rendering System

I do not want to depend on raw tweet screenshots in the first build.

Instead, build a clean post card renderer using structured post data.

## Requirements

A post card should support:

* display name
* username
* date
* text
* optional engagement row
* optional label/tag
* layout that looks clean in dark mode

## Implementation options

Use whichever approach makes the most sense for the current stack, but keep it maintainable.
For example:

* HTML/CSS templates
* Plotly annotation layer
* image rendering from template
* or other clean structured UI output

## Goal

The post card system should be reusable for event overlays in the animation.

---

# Phase 11: CLI / Scripts / Reproducibility

I want the repo to be easy to rerun from scratch.

## Please provide easy entry points such as:

* ingest posts
* ingest BTC price data
* classify posts
* aggregate series
* generate review exports
* build static preview
* build animated preview

These can be scripts, Makefile targets, or a small CLI.

## Ideal commands

Something like:

```bash
make ingest-posts
make ingest-btc
make classify
make aggregate
make review-exports
make preview-static
make preview-animate
```

Adjust as needed for the actual implementation.

---

# Phase 12: Documentation

The README should be excellent.

## It should include

* project purpose
* architecture overview
* data flow
* how to configure API access
* how to run each phase
* where outputs go
* how manual review works
* how to change weekly vs monthly mode
* how to add iconic events
* what is implemented vs what is future work

## Additional docs

If useful, add:

* a data dictionary
* a developer notes file
* a manual review instructions doc

---

# Engineering Quality Expectations

Please write this as production-style prototype code, not throwaway spaghetti.

## I care about

* clean naming
* clear modularity
* readable functions
* basic tests where sensible
* type hints where useful
* sensible error handling
* comments where they help, not noise everywhere
* logging for long-running steps

## I do not want

* giant monolithic scripts with everything mixed together
* hidden magic
* fragile hardcoded assumptions
* code that only works for one dataset shape

---

# Notes on Data Decisions

## Timeline Start

The visualization likely starts at **Michael Saylor’s first Bitcoin-related post**, not Bitcoin’s genesis.

Please support this naturally in the transformations by:

* collecting a broader archive if practical,
* then determining the first classified Bitcoin-related post date,
* and using that as the default start point for the aligned visualization.

## Time Bucketing

Please support both:

* weekly
* monthly

But assume the first polished long-range version will probably use **monthly**.

## Classification Philosophy

Favor recall + reviewability over pretending to be perfectly precise on the first pass.
It is more important that I can inspect the corpus and manually refine it later.

---

# Future Extensions I Want the Architecture To Support

Please design with these future possibilities in mind, even if you do not implement all of them now.

## Potential future features

* stronger NLP classification
* sentiment tagging
* engagement-weighted post intensity
* separate views for Bitcoin vs MSTR treasury posts
* alternate accounts or additional influencers
* richer annotations and regime labels
* rendered video export pipeline
* interactive React/D3 front-end
* zoomed-in era breakdowns
* auto-generated event summaries
* soundtrack synchronization later

The current implementation does **not** need to build these, but it should avoid boxing me out.

---

# Concrete Implementation Priorities

If you need to prioritize, do the following first:

1. project scaffold
2. post ingestion pipeline
3. BTC price ingestion pipeline
4. classification layer
5. aggregation layer
6. manual review exports
7. static visualization
8. animated prototype
9. post card overlay support
10. polish/documentation

---

# What I Want in the Final Output From You

Please do the following:

1. Scaffold the repository.
2. Implement the data model.
3. Build the ingestion pipelines.
4. Build the classification workflow.
5. Build the aggregation/alignment workflow.
6. Build the static visualization.
7. Build the first animated prototype.
8. Add documentation and instructions.
9. Clearly note any assumptions or areas requiring API keys/manual setup.
10. Leave the repo in a state where I can run the pipeline end-to-end.

---

# Additional Guidance for Decision-Making

When faced with tradeoffs:

* prefer simplicity over cleverness
* prefer inspectability over black-box automation
* prefer reusable structure over quick hacks
* prefer outputs I can manually inspect over hidden intermediate state

If any part of the plan is blocked by unavailable credentials or rate limits:

* still scaffold the full path,
* stub where necessary,
* and document exactly what needs to be filled in.

---

# Suggested First Milestone

A good first milestone would be:

* repo scaffold complete
* BTC ingestion working
* Saylor ingestion pipeline working or stubbed with documented setup
* raw/archive tables created
* rule-based classification implemented
* monthly and weekly aggregates generated
* one static preview chart generated

A good second milestone would be:

* iconic post manual review workflow in place
* sample post cards rendered
* first animation prototype working

---

# Final Instruction

Please start by scaffolding the repo and implementing the data model and ingestion pipeline in the most practical way.
Then proceed phase-by-phase.

Where helpful, explain your architecture choices briefly in code comments or the README, but prioritize building working foundations over excessive prose.

I want a project that is thoughtfully structured, easy to iterate on, and clearly aimed at a polished Michael Saylor × Bitcoin historical visualization.
