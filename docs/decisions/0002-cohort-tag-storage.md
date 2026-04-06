# ADR 0002: Cohort tags use normalized tables and eligibility-scoped filtering

## Status

Accepted

## Context

Aggregate mood analysis now needs cohort-based filtering across multiple users.

The project also needs a user settings page where those cohorts can be managed without introducing duplicate labels, drifting spelling, or ambiguous filtering behavior.

There are two obvious implementation paths:

- store freeform tag text directly on `users`
- store managed cohort tags in dedicated relational tables and assign them through a join table

The aggregate mood page also cannot treat every row in `users` as eligible because many canonical user rows may exist only as referenced authors from other tweet data, without full scored mood history.

## Decision

The project stores cohort tags in normalized tables:

- `cohort_tags`
- `user_cohort_tags`

Each cohort tag has:

- a readable `name`
- a normalized lowercase `slug`

User assignment is many-to-many through `user_cohort_tags`.

Aggregate mood filtering is scoped only to users with scored mood data for the active/default mood model.

The user settings page shows all managed tags.

The aggregate mood page shows only cohort tags that currently have at least one eligible assigned user.

Aggregate mood filtering is currently single-select:

- no `cohort_tag` means `All tracked users`
- a single `cohort_tag=<slug>` applies one cohort filter

## Consequences

- We avoid duplicate or near-duplicate cohort labels such as `bitcoin`, `Bitcoin`, and `btc`.
- The API can use stable slugs while the UI keeps readable names.
- The aggregate mood page does not expose empty or non-actionable cohort filters.
- Referenced users without scored mood data do not leak into aggregate cohort counts.
- Renaming or deleting tags later can be implemented cleanly because tag identity is not embedded as raw text on user rows.
- The schema and API are slightly more complex than a freeform text field, but the behavior is more consistent and easier to reason about over time.
