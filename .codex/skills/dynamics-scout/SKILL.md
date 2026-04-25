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

## Style

- Lead with the most interesting observations, not methodology
- Prefer concise narrative statements over metric dumps
- Use metrics only as support when they sharpen the story
- Do not spend time on chart paths or UI click instructions unless the user asks
- Hypotheses are encouraged, but label them clearly as hypotheses

## Recommended Structure

Use this structure when summarizing scout output:

1. `Top storylines`
2. `Cross-patterns`
3. `Hypotheses`

Keep each section short. If the user wants more depth, expand from the JSON findings.

## Heuristics

When choosing what matters most:

- favor observations supported by multiple finding types
- favor recent shifts when they reinforce a longer-running pattern
- treat strong contradictions as interesting, not as noise
- avoid over-weighting a single extreme score if the rest of the scout run does not support it

Examples of good synthesis:

- a cohort is broadly rising in optimism while one member is sharply diverging downward
- multiple cohorts are decoupling from BTC at the same time in different moods
- a user appears in outlier, divergence, and regime-shift findings simultaneously

Examples of weak synthesis:

- listing 20 leaderboard rows with no interpretation
- repeating raw z-scores without explaining why they matter
- focusing on a finding solely because it is numerically largest
