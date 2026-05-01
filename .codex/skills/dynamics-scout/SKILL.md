---
name: dynamics-scout
description: Use this skill when the user wants to interpret the latest Dynamics Scout run, summarize interesting cross-user or cross-cohort mood dynamics, surface BTC-linked mood relationships, or generate high-level hypotheses from the scout outputs. Read the latest scout files from data/exports/dynamics-scout/latest.md and latest.json, then synthesize the most interesting observations without focusing on chart links or low-level UI navigation.
---

# Dynamics Scout

Use this skill only after a Dynamics Scout run exists. The scout run is generated manually from the repo root with:

```bash
./scripts/scout-dynamics.sh
```

## Inputs

Read these files first:

- `data/exports/dynamics-scout/latest.md`
- `data/exports/dynamics-scout/latest.json`

If they do not exist, tell the user to run `./scripts/scout-dynamics.sh` first.

If the user asks about an older run, inspect the timestamped folders under:

- `data/exports/dynamics-scout/`

## Persistence Requirement

Do not leave the interpretation only in the Codex chat output.

Every time you use this skill, write the interpretation to:

- `data/exports/dynamics-scout/latest-interpretation.md`

and also write the same interpretation into the newest timestamped scout run folder as:

- `data/exports/dynamics-scout/<latest-run>/interpretation.md`

Use the newest timestamped directory under `data/exports/dynamics-scout/` as `<latest-run>`.

The markdown should include:

- scout run timestamp
- interpretation timestamp
- top storylines
- cross-patterns
- hypotheses

After writing the markdown files, return the interpretation in chat as usual.

## What To Produce

Your job is not to restate the raw leaderboard. Your job is to surface the most interesting stories hiding inside it.

Prioritize:

- the strongest 5-15 observations worth deeper investigation
- cross-cutting patterns that recur across multiple finding types
- tension between user-level and cohort-level signals
- BTC-linked mood relationships that look unusual, unstable, or newly emerging
- regime shifts that may signal changing behavior rather than random noise

Read the full `latest.json`, not just the markdown summary. The markdown file is a convenience layer; the JSON is the actual source of truth for synthesis depth.

Before writing the interpretation:

- scan well beyond the top 10 findings
- look for repeated entities that appear across multiple finding types
- look for repeated moods that recur across users, cohorts, and BTC-linked findings
- compare what is dominant in the leaderboard with what is broadly recurring lower in the ranked list
- separate likely real patterns from likely statistical artifacts or tiny-variance comparator effects

## Style

- Lead with the most interesting observations, not methodology
- Prefer concise narrative statements over metric dumps
- Use metrics only as support when they sharpen the story
- Do not spend time on chart paths or UI click instructions unless the user asks
- Hypotheses are encouraged, but label them clearly as hypotheses
- Be materially more detailed than the scout markdown summary
- Aim for a substantial interpretation, not a short note
- Default target length is roughly 900-1600 words unless the user asks for brevity
- Surface at least 5 concrete observations and usually closer to 8-12 when the scout run is rich enough

## Recommended Structure

Use this structure when summarizing scout output:

1. `Top storylines`
2. `Cross-patterns`
3. `Hypotheses`
4. `Caveats and weak signals`

Within those sections:

- `Top storylines` should contain multiple distinct observations, not one blended paragraph
- `Cross-patterns` should focus on repeated entities, repeated moods, repeated cohorts, and repeated BTC-linkage behavior
- `Hypotheses` should explain what might be happening and why it may matter
- `Caveats and weak signals` should call out findings that may be numerically extreme but conceptually fragile

Do not keep each section short by default. Depth is preferred here as long as it remains organized and non-repetitive.

## Heuristics

When choosing what matters most:

- favor observations supported by multiple finding types
- favor recent shifts when they reinforce a longer-running pattern
- treat strong contradictions as interesting, not as noise
- avoid over-weighting a single extreme score if the rest of the scout run does not support it
- favor entities that recur across multiple finding types over single isolated appearances
- favor clusters of related moods over one-off mood spikes
- call out when the run is dominated by one signal family, but still identify the best non-dominant stories
- explicitly note when a comparator cohort appears to have tiny variance and is inflating sigma-based divergence

Examples of good synthesis:

- a cohort is broadly rising in optimism while one member is sharply diverging downward
- multiple cohorts are decoupling from BTC at the same time in different moods
- a user appears in outlier, divergence, and regime-shift findings simultaneously
- a reflective-mood cluster like gratitude/remorse/relief appears across multiple entities, suggesting a broader narrative regime

Examples of weak synthesis:

- listing 20 leaderboard rows with no interpretation
- repeating raw z-scores without explaining why they matter
- focusing on a finding solely because it is numerically largest
- giving only 3-4 high-level bullets when the JSON contains enough material for a richer interpretation
