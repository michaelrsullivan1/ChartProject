# Podcast Architecture Adjustment

Date: 2026-04-24

## Purpose

This note captures the architectural conclusion reached after reviewing:

- the current Michael Saylor podcast pilot
- the Belief Engines repos and site
- the local raw snapshot structure
- Ryan's feedback that the dataset is flexible but must be tuned to a specific use case

The goal is to preserve what should change, what should stay, and what should **not**
be overreacted to when podcast work resumes later.

## Bottom Line

The current podcast integration is **not wrong** and does **not** need a major rollback.

The current normalized foundation remains valid:

- raw snapshot preserved on disk
- normalized podcast schema in Postgres
- separate podcast area in the app
- person-first pilot around Michael Saylor
- source-id-first import strategy

What needs to change is the **product and derived-layer emphasis**, not the core ingest.

The strongest lesson from the recent review is:

- the dataset is more naturally a **belief + evidence + structure** system
- it is less naturally just a topic-count dashboard

## What To Keep

The following should be treated as the current architectural base and kept unless the
data forces a change:

- `podcast_shows`
- `podcast_episodes`
- `podcast_persons`
- `podcast_appearances`
- `podcast_beliefs`
- raw snapshot files preserved separately from Postgres
- person-first exploratory routing
- podcast subsystem kept separate from tweet/X logic

This relational layer is still the right base for:

- person-level views
- episode joins
- show joins
- timeline analysis
- belief browsing

## What The Current Build Underuses

The current pilot mostly uses:

- person
- appearance order
- topic labels
- belief counts and shares

The dataset appears to offer more than that.

Most underused layers:

### 1. Transcript evidence

The raw transcript files already include:

- speaker-attributed utterances
- per-utterance timestamps
- speaker slug linkage

This means the system can support:

- evidence-backed belief views
- quote drilldowns tied to specific appearances
- rhetorical or phrase-level analysis later

### 2. Matrix semantics

The raw snapshot includes:

- belief-level `matrices/*.json`
- person-level `persons/<id>/matrix.json`

These are not just summary metadata.

They encode:

- domain relevance
- question-level boolean profiles
- higher-order ideological structure

This likely supports product views that are more distinctive than another topic chart.

### 3. Embedding and similarity layers

The snapshot also includes person embeddings and repo references to clustering and viz
build steps.

This suggests future support for:

- nearest-neighbor speaker views
- cluster exploration
- graph-style interfaces

### 4. Question-first exploration

The screenshots and repo framing suggest the intended product direction is closer to:

- "What does Saylor believe about X?"
- "How has that belief evolved?"
- "What evidence supports that?"

than:

- "How many times did Saylor mention topic Y?"

## What Ryan's Feedback Seems To Mean

The most important interpretation of the feedback is:

- do **not** throw away the current ingest
- do **not** assume the first chart-heavy pilot is the final product shape
- do start treating the current implementation as only the first analytical slice

Put differently:

- the relational core was necessary
- it is probably not sufficient for the best product experiences

## Recommended Architecture Going Forward

The podcast subsystem should be thought of in three layers.

### Layer 1: Core relational layer

Keep the current normalized tables as the canonical analytical base.

Purpose:

- stable entity joins
- clean filters
- timeline queries
- durable imported corpus

### Layer 2: Evidence and enrichment layer

Add one or both of the following next:

- transcript access layer
- matrix semantics layer

This can be implemented either by:

- ingesting more artifacts into Postgres
- or reading raw artifacts on demand first

This layer should expose:

- supporting utterances and transcript evidence
- belief-level matrix/domain data
- person-level matrix profiles
- links back to raw source artifacts where useful

### Layer 3: Product view layer

Build views that combine:

- narrative evolution
- evidence
- ideological structure
- later, graph exploration

This is where the product should move beyond basic tables and charts.

## What Not To Do

The following are not recommended right now:

- do not rewrite the importer from scratch
- do not discard the normalized schema
- do not pivot immediately to a graph-only system
- do not add identity repair logic unless the corpus clearly requires it
- do not overfit the product to topic-count charts just because that was the first usable view

## Concrete Next Additions

The most reasonable architectural additions after the current work are:

### 1. Transcript / evidence support

Potential forms:

- `podcast_utterances` table
- transcript service that reads raw files on demand

Primary reason:

- support quote-level evidence and appearance-specific context

### 2. Matrix support

Potential forms:

- imported matrix fields per belief
- matrix service layer with raw artifact lookup
- person matrix profile endpoint

Primary reason:

- expose the richer domain and ideological structure already present in the dataset

## Product Reframing

The strongest product framing now looks like:

- a belief explorer
- an evidence-backed narrative system
- a matrix/structure-aware speaker profile

not just:

- a podcast dashboard

The current `User Narrative Mix` page is still useful, but it should be understood as
one panel or one page inside a broader system, not the whole destination.

## Resume Checklist

When this work resumes, the next architectural check should be:

1. keep the current normalized schema as the base
2. decide whether transcript evidence should be on-demand or imported
3. formalize the semantics of the matrix artifacts before building more chart pages
4. decide whether the next product surface is:
   - evidence-first
   - matrix-first
   - or still chart-first with stronger evidence drilldown

## Summary

The current integration should be treated as a valid first foundation.

The adjustment is:

- keep the base
- extend the evidence and matrix layers
- shift the product thinking from chart-only exploration toward belief, evidence, and structure
