# Bitcoin Price Mention Extraction Feature Plan

## Problem Statement

Tracked authors and cohorts mention specific Bitcoin price levels constantly — as predictions, historical anchors, conditional triggers, and current observations. The goal is to extract every explicit numeric price mention from the tweet corpus, store it with type and confidence metadata, and visualize where price-level "magnets" exist: which price points cluster in narrative frequency, when they dominated discourse, and how that varies across cohorts.

A secondary but compelling output of this data is what might be called **narrative-implied volatility**: the spread of price levels being discussed at any given time mirrors how wide open the prediction space is. During a bull run, mentions cluster tightly above current price. During uncertainty, they scatter. This spread over time is a genuinely novel signal worth capturing and may invite future comparison to options-implied volatility over the same periods.

---

## Scope

### In scope

- Explicit numeric Bitcoin price mentions ($10,000 and above) extracted from original tweet text
- Per-cohort aggregate view as the primary UI surface, on a new standalone page
- Mention type classification (prediction, historical, current observation, conditional)
- Confidence scoring as a filter rather than a gate — store everything, let the UI decide what to show
- Full historical Y-axis range on a log scale with $1,000 binning so the spread and shift of price mentions over time is visible
- BTC actual price line overlay on all time-series views
- Retweet exclusion — original authored content only

### Out of scope for now

- Qualitative references ("six figures", "seven figures")
- Satoshi-denominated amounts
- Market cap mentions that could be back-calculated to price
- Non-USD denominations
- Per-author drilldown pages — cohort-level density is the primary value
- LLM-per-tweet extraction — definitively ruled out at 500k–1M+ tweet scale
- Multi-cohort overlay views — single cohort selection at a time, matching Aggregate Moods/Narratives

---

## Retweet Handling

**Key finding from the codebase:** Retweets are stored in the database. The normalization service processes them and writes a `tweet_references` row with `reference_type="retweeted"` for each one. No existing enrichment script (sentiment, moods, keywords) currently filters them out.

For price mention extraction, retweets must be explicitly excluded. A retweet's text is "RT @originaluser: [truncated original]..." — it contains the original author's words, not the retweeting author's. Counting those as mentions for the retweeter's user/cohort would introduce amplification noise: 20 authors retweeting the same Saylor "$100k target" tweet would show up as 20 mentions for 20 different users, distorting both the density signal and the cohort data.

**Implementation:** In the extraction script, join on `tweet_references` and exclude any tweet that has a `reference_type = 'retweeted'` row. The table is already indexed on `reference_type`. This is a clean, cheap filter with no schema changes required.

**Important:** The same retweet exclusion must also apply to the `tweet_count` denominator used for normalization in the API. If we exclude retweets from the numerator (price mentions) but include them in the denominator (total tweets), the "mentions per 100 tweets" ratio will be artificially depressed. Both numerator and denominator come from the same eligible tweet pool.

Note: quote tweets (`reference_type = 'quoted'`) and replies (`reference_type = 'replied_to'`) are **not** excluded — those represent the author's own voice engaging with content and are legitimate original price mentions.

---

## The Core Extraction Problem

The hardest design decision is: **what counts as a valid Bitcoin price mention, and how do we determine that without reading every tweet manually or calling an LLM?**

### Why not LLM per tweet

At 500k+ tweets scaling to millions, LLM-per-tweet is cost and latency prohibitive. A Claude API call per tweet would cost hundreds of dollars for a single full-corpus pass and would take hours to run. More importantly, it conflicts with the local-first, offline design of this project. The extraction must work like `extract_tweet_keywords.py` — a local script, no external calls, milliseconds per tweet, resumable with `--only-missing-tweets`.

### Approach: two-stage regex + context scoring

**Stage 1 — Numeric candidate extraction**

A regex pass finds all numbers in the tweet that fit plausible Bitcoin price formats:

| Pattern family | Examples |
|---|---|
| Dollar sign + numeric suffix | `$100k`, `$1.5k`, `$100K`, `$1.5M`, `$2.5m` |
| Dollar sign + currency word | `$1 million`, `$1.5 million`, `$250 thousand` |
| Dollar sign + plain number | `$100,000`, `$100000`, `$97,500`, `$100,000.00` |
| Number + currency word | `100k USD`, `100K dollars`, `1.5 million USD`, `250 thousand bucks` |
| Bare number with k/M suffix | `100k`, `1.5M` — requires BTC context in tweet |
| Written out | `one hundred thousand`, `a million`, `half a million` — requires BTC context |
| Approximate modifiers | `~$100k`, `>$100k`, `sub-$100k`, `around $100k`, `over $100k` — modifier discarded, base price stored |
| Range formats — explicit suffixes | `$60k-$100k`, `$60k to $100k`, `between $60k and $100k` — each endpoint stored as a separate row |
| Range formats — shared suffix | `$60-100k`, `60 to 100k`, `60-100k` (with BTC context) — suffix applies to both endpoints; both stored as separate rows |

**Tweet text preprocessing** (matching the keyword extractor):
- Strip URLs before matching (URLs sometimes contain digit sequences that would false-positive)
- Strip `@mentions` before matching
- Preserve hashtags — `#100k` is rare but legitimately a price mention with BTC context
- Preserve original text in `raw_fragment` storage for debugging (the matched substring uses original casing/formatting)

**Normalization rules applied to every match:**
- Strip commas: `100,000` → `100000`
- Expand k/K suffix: `100k` → `100000`
- Expand M suffix: `1.5M` → `1500000`
- For shared-suffix ranges, apply the trailing suffix to both endpoints
- Skip numbers followed immediately by `%` (percentage context)
- Apply floor of `$10,000` (inclusive) and ceiling of `$10,000,000` (inclusive) as a sanity range filter

The $10,000 floor handles most cross-contamination naturally. MSTR stock, ETH, and most other prices that appear in BTC-focused author tweets live below this floor.

**Approximate modifiers** (`~`, `>`, `<`, `sub-`, `around`, `over`, `near`, `above`, `below`) are recognized and consumed by the pattern but discarded. "around $100k" stores as a $100,000 mention. The intent for the magnet visualization is that "around $100k" still names $100k as the magnet level.

**Stage 2 — Context scoring**

Each candidate number gets a confidence score (0.0–1.0) based on the full tweet text (tweets are short enough that windowing is unnecessary):

Signals that increase confidence:
- Strong BTC keywords: "bitcoin", "btc", "#bitcoin", "#btc", "satoshi", "sats", "hodl", "halving", "halvening", "lightning", "on-chain", "onchain", "price target", "price prediction", "resistance", "support level", "buy zone", "sell zone", "digital gold", "sound money", "store of value", "hard money"
- Price-narrative context words: "prediction", "forecast", "target", "floor", "ceiling", "buy zone", "sell zone"
- Dollar sign directly attached to the number

Signals that decrease confidence:
- Non-BTC ticker near the number: "mstr", "microstrategy", "ethereum", "eth", "solana", "sol", "xrp", "ripple", "bnb", "dogecoin"
- Equity/stock context: "shares", "stock price", "per share", "equity", "eps"
- Non-price dollar contexts: "salary", "income", "revenue", "profit", "rent", "mortgage"

**Confidence bands:**

| Band | Score | Meaning |
|---|---|---|
| High | ≥ 0.80 | Explicit BTC keyword + plausible price range |
| Medium | 0.50–0.79 | BTC-focused author + price context, no conflicting signals |
| Low | < 0.50 | No BTC keyword, generic context, or weak signal |

All bands are stored. The UI defaults to showing High + Medium. Low-confidence mentions can be toggled on as an overlay. Thresholds are query-time parameters, not extraction-time gates, so they can be adjusted without rerunning the extractor.

**Author-level BTC prior (future refinement)**

For authors who are overwhelmingly Bitcoin-focused (Saylor, Schiff, etc.), the base confidence for any $10k+ number can reasonably start higher. An `author_btc_prior` float on `managed_author_views` could feed the scorer without changing the core algorithm.

---

## Written Number Handling

The `word2number` library (small, well-maintained, ~1k lines of Python) converts English number words to integers cleanly:

```
"one hundred thousand"        → 100000
"a million"                   → 1000000
"two hundred fifty thousand"  → 250000
"half a million"              → 500000
```

**Activation rule:** Written-number spans are only extracted when the tweet already contains at least one BTC keyword. This avoids false positives like "I've made one hundred thousand decisions" or "the company serves a million customers."

**Year-shape exclusion:** Before passing a span to `word2number`, the extractor checks whether it matches a year-reference pattern (two 2-digit chunks like "twenty twenty-five"). Those spans are skipped. Numeric years (2020–2035) are already handled by the $10k floor, but the written-number guard prevents messiness in the library.

**"A million" treatment:** Written-out round numbers with no attached currency symbol or dollar sign are treated as low-confidence by default. A tweet saying "a million" requires a strong BTC keyword nearby to even be stored. This reflects genuine ambiguity in that phrasing.

---

## Range Mention Behavior

"BTC between $60k and $80k" extracts two separate rows: one at $60,000 and one at $80,000. This is intentional. Each endpoint is a real price level being named. The repetition and clustering of individual price level mentions is the core signal this feature is built to surface.

**Shared-suffix ranges** like `$60-100k` are explicitly handled. The pattern recognizes that the trailing `k` applies to both numbers, so both $60,000 and $100,000 are stored. Without this special handling, `$60` alone would fail the $10k floor and the $60k endpoint would be silently lost.

No deduplication beyond tweet-level uniqueness per price value (the unique index handles this).

---

## Mention Type Classification

After a candidate clears the confidence threshold, it gets a mention type assigned by keyword heuristics against the full tweet text. Types are assigned independently per candidate, so a single tweet can produce multiple mentions with different types.

| Type | Heuristic signals |
|---|---|
| `prediction` | "will", "gonna", "going to", "expect", "target", "prediction", "forecast", "eoy", "end of year", "by 2025/2026/...", "could reach", "might hit", "heading to", "moon", "next target", "next stop" |
| `conditional` | "if", "when it hits", "when it reaches", "once it", "should it", "drops to", "falls to", "dips to", "rises to", "breaks above", "breaks below", "reclaims", "if btc", "if bitcoin" |
| `current` | "now", "currently", "today", "right now", "trading at", "sitting at", "hovering", "just hit", "just crossed", "spot price", "current price" |
| `historical` | "was", "were", "back when", "in 2020/2021/...", "ath", "all time high", "all-time high", "peak", "bottom", "low of", "when it crashed", "bought at", "sold at", "bear market bottom" |
| `unclassified` | no clear signal matched |

**Tie-breaking rule:** When a single tweet contains signals for multiple types, classification follows this priority order: **prediction > conditional > current > historical > unclassified**. The first signal in priority order that matches anywhere in the tweet wins for all candidates in that tweet. The reasoning: prediction and conditional are forward-looking and represent the most distinctive narrative signal; historical references are common in passing and shouldn't override stronger signals when both are present.

This rule is intentionally simple. The user has stated that perfect type classification is less important than capturing the price levels themselves, so this is calibrated for low complexity rather than maximum nuance.

---

## Data Schema

New table: `tweet_price_mentions`

```sql
CREATE TABLE tweet_price_mentions (
    id                BIGSERIAL PRIMARY KEY,
    tweet_id          BIGINT NOT NULL REFERENCES tweets(tweet_id),
    user_id           INTEGER NOT NULL REFERENCES users(id),
    price_usd         NUMERIC(16, 2) NOT NULL,
    mention_type      VARCHAR(20) NOT NULL DEFAULT 'unclassified',
    confidence        NUMERIC(4, 3) NOT NULL,
    raw_fragment      TEXT NOT NULL,
    extractor_key     VARCHAR(64) NOT NULL DEFAULT 'price-mention-regex',
    extractor_version VARCHAR(16) NOT NULL DEFAULT 'v1',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_price_mentions_tweet_id ON tweet_price_mentions(tweet_id);
CREATE INDEX idx_price_mentions_user_id ON tweet_price_mentions(user_id);
CREATE INDEX idx_price_mentions_price ON tweet_price_mentions(price_usd);

-- Composite index optimized for the primary cohort query pattern:
-- WHERE user_id IN (...) AND extractor_key = ? AND extractor_version = ? AND confidence >= ?
CREATE INDEX idx_price_mentions_cohort_query
    ON tweet_price_mentions(user_id, extractor_key, extractor_version, confidence);

-- Dedup constraint
CREATE UNIQUE INDEX idx_price_mentions_dedup
    ON tweet_price_mentions(tweet_id, price_usd, extractor_key, extractor_version);
```

Design notes:

- `user_id` is denormalized intentionally. Cohort queries filter by user set, and joining through `tweets` on every cohort query would be expensive at this scale.
- The composite cohort-query index speeds up the most common query pattern (cohort filter + extractor scope + confidence threshold) significantly. The `(user_id)`-only index is kept for queries that don't filter by extractor.
- `raw_fragment` stores the matched substring (e.g., `"$100k"`, `"100,000 dollars"`). Useful for debugging the extractor and for any future UI that wants to show source context.
- `extractor_key` + `extractor_version` follow the same versioning pattern as `tweet_keywords` and `tweet_mood_scores`. A v2 extractor can coexist with v1 rows.
- The unique index prevents duplicate rows for the same tweet + price + extractor, so the script is safely re-runnable. Two mentions of `$100k` in the same tweet collapse to one row — correct for the magnet density signal.
- Multiple rows per tweet are expected and correct.
- No `tweet_created_at` denormalization in v1 — the join through `tweets` for date bucketing is cheap with proper indexing. Can be added later if performance demands.

---

## Extraction Script

Following the existing enrichment script conventions:

**Path:** `backend/scripts/enrich/extract_tweet_price_mentions.py`

**Retweet exclusion:** The script's tweet query excludes any tweet that has a matching row in `tweet_references` with `reference_type = 'retweeted'`. Quote tweets and replies are included.

**Default analysis window:** `--analysis-start 2020-08-01T00:00:00Z` (matching the keyword extractor). This skips ancient tweets where prices were sub-$10k anyway and provides a deterministic floor on processing scope.

**Supported options:**

```bash
# Run for one author with default analysis window
python3 backend/scripts/enrich/extract_tweet_price_mentions.py \
  --username saylor \
  --analysis-start 2020-08-01T00:00:00Z

# Incremental: only tweets with no existing rows for this extractor+version
python3 backend/scripts/enrich/extract_tweet_price_mentions.py \
  --username saylor \
  --analysis-start 2020-08-01T00:00:00Z \
  --only-missing-tweets

# Dry run: print what would be extracted without writing
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor --dry-run

# Overwrite existing rows for this extractor+version
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor --overwrite-existing

# Multiple users
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor sullivan

# Custom extractor version (for testing algorithm changes against existing data)
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor --extractor-version v2
```

**Expected output summary:**

```
Processed 12,450 tweets for saylor (retweets excluded: 841, before analysis-start: 2,100)
  Candidates found: 3,841
  After floor/ceiling filter: 3,612
  High confidence: 2,104
  Medium confidence: 981
  Low confidence: 527
  Rows written: 3,612
  By type — prediction: 1,240  historical: 890  current: 710  conditional: 445  unclassified: 327
```

The extractor service module itself (`backend/app/services/price_mention_extractor.py`) will be approximately 400–500 lines: pattern definitions, normalization functions, written-number handling, context scoring, and mention type classification. Every rule is explicit and auditable.

**Re-processing of empty tweets:** With `--only-missing-tweets`, tweets that produced no price mentions on a previous run will be re-processed every incremental run (because no rows exist to skip them on). At 1ms/tweet for the regex extractor and ~70% of tweets being empty, this adds ~5 minutes per incremental run on a 500k corpus. Accepted as v1 behavior. If it becomes a bottleneck, add a `tweet_price_mention_runs` tracking table that records every processed tweet regardless of outcome.

---

## Backend API Design

### Primary endpoint

```
GET /api/views/price-mentions
    ?granularity=month          # month | week; default: month
    &cohort_tag=bitcoin-treasury-leadership   # optional; default: all tracked users
    &min_confidence=0.5         # default: 0.5 (High + Medium)
    &mention_type=prediction    # optional; default: all types
    &min_price=10000            # optional; default: 10000
    &max_price=10000000         # optional
    &bin_size=1000              # price bucket size in USD; default: 1000
```

**Response shape:**

```json
{
  "granularity": "month",
  "cohort_tag": null,
  "bin_size": 1000,
  "periods": [
    {
      "period_start": "2024-01-01T00:00:00Z",
      "tweet_count": 4820,
      "user_count": 18,
      "mention_count": 312,
      "mentions": [
        { "price_usd": 100000, "mention_type": "prediction", "count": 48 },
        { "price_usd": 100000, "mention_type": "conditional", "count": 6 },
        { "price_usd": 99000,  "mention_type": "prediction", "count": 3 },
        { "price_usd": 150000, "mention_type": "prediction", "count": 21 },
        { "price_usd": 60000,  "mention_type": "conditional", "count": 14 }
      ],
      "btc_close": 42800.00
    }
  ]
}
```

**Count semantics:** All `count` values are **raw integer counts** of mentions in that bucket. The `tweet_count` and `user_count` fields are denominators the frontend can use for normalization (e.g., `count / tweet_count * 100` for "mentions per 100 tweets"). This keeps the backend simpler and lets the frontend toggle normalization modes without re-fetching.

**Bucketing:** The `price_usd` value in each row is the bottom of the $1k bin (or whatever `bin_size` is set to). So all mentions between $99,500 and $100,499 collapse into the bin at `100000` (or stay as their exact value, depending on bin alignment — TBD as implementation detail). The default $1k bin gives enough resolution to see whether $97,500 has density vs. the round numbers, while keeping response sizes manageable.

**Mention type breakdown:** Each `(price_usd, mention_type)` pair is its own row. To render an "all types combined" heatmap, the frontend sums across types for each price bin. To render a single-type view, the frontend filters by type (or sets the `mention_type` query parameter).

**`btc_close`:** Sourced from `market_price_points` using the period-end daily close (Friday close for weekly granularity, last trading day of the month for monthly). Null if no BTC price exists for the period (shouldn't happen for any period after 2014-12-01 given the FRED coverage).

### Cohorts list endpoint

Reuses the existing `/api/views/aggregate-moods/cohorts` endpoint — no new endpoint needed, same cohort infrastructure. Cohort eligibility is "users with at least one price mention row in the active extractor version."

---

## Frontend: Price Mentions Page

### Page identity

A new standalone page, not attached to per-author pages.

- **Route:** `#/price-mentions`
- **Page name:** "Price Mentions"

This page is entirely aggregate and cohort-focused. It mirrors the structure of the Aggregate Moods and Aggregate Narratives pages — single-cohort selection with switching between cohorts to compare.

### Page controls

- **Cohort selector:** Single-select, same pattern as Aggregate Moods. Default: "All tracked users". Available cohorts come from the existing cohorts endpoint.
- **Granularity toggle:** Month / Week (default Month)
- **Mention type filter:** All / Prediction / Historical / Current / Conditional (default All)
- **Confidence filter:** "High + Medium" (default) / "Include Low"
- **View mode toggle:** Heatmap / Comparison / Scatter (default Heatmap)
- **Time range:** Full available history by default; consider a zoom/pan UI if response sizes become unwieldy

### Managed author registry

No new `enable_price_mentions` flag required on `managed_author_views` for the initial build since this is a cohort/aggregate page, not a per-author page. Users contribute to the cohort views as long as they have price mention rows.

---

## Visualization Options

Three views built on the same underlying API data. The toggle between them is a UI rendering decision — the backend payload shape is the same for all three.

### View A: Price-Time Density Heatmap (primary view)

- **X axis:** Time in monthly (or weekly) buckets
- **Y axis:** Price level on a **log scale** with $1,000 binning. The full historical range ($10k to $10M log scale) is shown by default. Round-number magnets ($50k, $100k, $150k, etc.) will visually emerge as denser horizontal bands without needing to be hardcoded as the bin scheme.
- **Color:** Mention density per cell
- **Color scale:** Default to a fixed scale (calibrated across the full dataset) so cross-cohort switching produces honest comparisons. Provide a toggle to switch to per-view auto-scale for individual cohort exploration. This is a "see it in action and iterate" decision.
- **Overlay:** Actual BTC price as a line running across the heatmap at the Y position of the real price for each time period — sourced from `btc_close` in the API response

**Why this view is the most important:** It captures the core insight at a glance. In a given month, the dark cells show which price levels dominate narrative. The BTC price line shows where the real market was. You can see:
- Price levels that act as persistent magnets regardless of where BTC actually is
- How the cluster of active discussion shifts as BTC price moves
- The spread of discussion narrowing or widening over time (narrative-implied volatility)

The full historical range on the Y axis (log scale, $10k to $10M) is intentional — it lets you see the shift in what counts as a "reasonable" price target as BTC itself moves. A $100k mention in 2021 looks very different from a $100k mention in 2024.

### View B: Scatter Plot

- **X axis:** Tweet date
- **Y axis:** Price mentioned (log scale)
- **Dot:** Each individual mention, colored by mention type
- **Overlay:** BTC price line

Granular per-mention detail. At full corpus scale this view will be dense. Use hexbin density rendering when the visible window contains more than ~5,000 mentions; fall back to individual dots when zoomed in. Mention type colors are consistent with the comparison view legend.

This is the lowest priority view — build only after the heatmap and comparison views are working and only if it adds value.

### View C: Cohort vs. Baseline Comparison

- **X axis:** Price level (log scale, same $1k bins as heatmap Y axis)
- **Y axis:** Normalized mention frequency (mentions per 100 tweets)
- **Series:** Two — the selected cohort's distribution overlaid on the "All tracked users" baseline distribution
- **Optional Z-score view:** A toggle to render the selected cohort's deviation from baseline rather than absolute frequency, surfacing which price levels the cohort over- or under-emphasizes relative to the population

Best for answering "what does this cohort talk about that the broader population doesn't?" Switching between cohorts on this view is the equivalent of cross-cohort comparison without needing multi-select UI.

### The "narrative-implied volatility" read

One non-obvious but valuable analysis the heatmap enables: measuring the **spread** of price mentions around the actual BTC price at each point in time. During high-conviction bull runs, discussion clusters tightly above current price ($100k–$150k when BTC is at $90k). During uncertainty, mentions scatter widely ($40k down to $20k up to $200k when BTC is at $60k). This spread over time is a novel signal that may correlate with or lead options-implied volatility. Worth keeping in mind when building the UI — the heatmap should make this spread visually obvious rather than compressing it.

---

## Integration with Existing Pipeline

### Position in the enrichment sequence

Price mention extraction slots in after keyword extraction:

```
normalize → validate → score_sentiment → score_moods → extract_keywords → extract_price_mentions → sync_narratives → rebuild_snapshots
```

### Addition to tracked-author refresh post-process

`post_process_tracked_author_refresh.py` should include price mention extraction as an optional step initially, promoted to default once the extractor is validated against the calibration corpus.

### Addition to `run-user-post-ingest-batch.sh`

```bash
python3 backend/scripts/enrich/extract_tweet_price_mentions.py \
  --username "$USERNAME" \
  --analysis-start 2020-08-01T00:00:00Z \
  --only-missing-tweets
```

### Standalone batch extraction script: `run-price-mentions-extraction.sh`

A shell wrapper script for running price mention extraction across all tracked users in one command. The primary use case is running a full incremental pass after any data change — including importing newer data from another system.

**Path:** `scripts/run-price-mentions-extraction.sh`

**Design:** Queries `managed_author_views` for all tracked, published users and runs `extract_tweet_price_mentions.py` for each in sequence. Modeled on the thin-wrapper pattern of `scout-dynamics.sh` for the passthrough case and the orchestration pattern of `run-user-post-ingest-batch.sh` for multi-user iteration.

**Usage:**

```bash
# Default: incremental pass over all tracked users — safe to run any time, before or after a data import
./scripts/run-price-mentions-extraction.sh

# Single user, incremental
./scripts/run-price-mentions-extraction.sh --username saylor

# Full reprocess all users (drops --only-missing-tweets — use after extractor tuning or version bump)
./scripts/run-price-mentions-extraction.sh --full

# Single user, full reprocess
./scripts/run-price-mentions-extraction.sh --username saylor --full
```

**Why it is safe to run before or after a data import:**

The default mode uses `--only-missing-tweets`, which checks `tweet_price_mentions` before processing each tweet. Any tweet that already has rows for the current extractor+version is skipped. Any tweet added by a subsequent data import will have no rows and will be processed the next time the script runs. This makes the script fully idempotent — running it twice in a row produces the same state as running it once, and running it after pulling in new tweets naturally processes only the new ones without touching existing data.

**`--full` mode use cases:**

- After adjusting confidence scoring weights during calibration (to recompute scores with the new weights)
- After bumping the extractor version from `v1` to `v2` (to generate new rows alongside the old ones)
- After discovering a systematic extraction error that requires re-processing the affected users

### No aggregate snapshot rebuild required (initially)

Price mention queries filter directly on indexed columns (`user_id`, `extractor_key`, `extractor_version`, `confidence`, `price_usd`) with the join through `tweets` for date filtering. At 500k tweets with proper indexing — including the new composite cohort-query index — cohort queries should run well under a second. If query performance degrades at scale, a snapshot layer can be added later following the `aggregate_view_snapshots` pattern. The API shape already accommodates this transparently.

---

## Confidence Calibration Plan

The initial heuristic confidence scores are educated guesses. Before treating medium-confidence mentions as reliable, do a calibration pass on four authors chosen to cover distinct noise profiles:

**Author 1 — Saylor (BTC-pure baseline)**
Profile: Bitcoin maximalist, near-zero non-BTC dollar noise. Establishes that the extractor performs cleanly on the highest-signal corpus in the set.
1. Run the extractor on Saylor's full corpus.
2. Export a random sample of ~150 medium-confidence rows with their `raw_fragment` and tweet text.
3. Manually label each as valid BTC price mention / not.
4. Establish baseline precision/recall in a high-signal environment.

**Author 2 — Michael Sullivan (mixed-topic stress test)**
Profile: Mixed topics — politics, tech, general commentary — with frequent non-BTC dollar amounts. The hardest false-positive environment in the set.
1. Run the extractor on Sullivan's full corpus.
2. Export a random sample of ~150 medium-confidence rows.
3. Manually label, paying particular attention to false positives from non-BTC contexts (politics, tech, general life mentions of dollar amounts).
4. Adjust scoring weights based on the false positive patterns found.

**Author 3 — Willy Woo (on-chain analyst)**
Profile: BTC-focused but heavily technical — support/resistance levels, on-chain metrics, price targets with specific numeric ranges. Tests whether technical analysis vocabulary scores correctly and whether dense price-level tweets produce false duplicates or missed range matches.
1. Run the extractor on Woo's full corpus.
2. Export a random sample of ~150 medium-confidence rows.
3. Manually label, with attention to whether range patterns (`$60k-$100k` style) are being extracted correctly and whether on-chain metric numbers (non-price) are leaking through.

**Author 4 — Jeff Walton (corporate/institutional BTC context)**
Profile: Provides a distinct institutional framing — BTC in a corporate treasury or capital allocation context. Tests whether corporate financial language (balance sheet, allocation percentages, share counts) introduces false positives that Sullivan's personal-finance noise doesn't cover.
1. Run the extractor on Walton's full corpus.
2. Export a random sample of ~150 medium-confidence rows.
3. Manually label, with attention to corporate financial false positives distinct from Sullivan's personal-finance noise.

**Output:**
- Document calibration findings as comments at the top of `price_mention_extractor.py`
- Note any new negative-signal keywords added based on false positives from each author
- Re-run on all four authors after adjustments to confirm improvement
- Promote price mention extraction to a default step in the post-process pipeline once calibration converges

At ~5–10 seconds per row and 150 rows per author, the full four-author pass is roughly 30–60 minutes of labeling total. This is a one-time cost.

---

## Phased Implementation Plan

This plan breaks the work into self-contained phases that can be picked up and completed in order. Each phase ends with a verifiable output.

### Picking up this plan in a new session

**Phases 1–3 are complete.** Start at Phase 4 (calibration).

Full build order: Phase 1 (migration) → Phase 2 (extractor service + tests) → Phase 3 (extraction script) → Phase 4 (calibration) → Phase 5 (full corpus run) → Phase 6 (API endpoint) → Phase 7 (heatmap UI) → Phase 8 (cohort comparison UI) → Phase 9 (pipeline integration + shell script) → Phase 10 (scatter view, optional).

Before starting any phase, confirm the local stack is healthy:

```bash
# From repo root
./scripts/setup-db.sh          # starts Postgres, runs migrations, installs deps
source .venv/bin/activate      # activate virtualenv
pip install -e backend         # sync backend deps
curl http://127.0.0.1:8000/api/health  # confirm backend is reachable (start dev.sh first if needed)
```

The first concrete command to run is in Phase 1, step 4: `alembic upgrade head` after creating the migration file.

### Phase 1 — Database schema and migration

**Goal:** Persist a new table ready to receive price mention rows.

Steps:
1. Create alembic migration `backend/migrations/versions/0010_tweet_price_mentions.py` (verify next available number — README mentions through `0009`).
2. Add `tweet_price_mentions` table per the schema in this doc, including all four indexes (tweet_id, user_id, price, composite cohort-query) and the unique dedup index.
3. Add the SQLAlchemy model at `backend/app/models/tweet_price_mention.py`.
4. Run `alembic upgrade head` against the local DB.
5. Verify rollback with `alembic downgrade -1`, then `alembic upgrade head` again to confirm idempotent.

**Done when:** Migration runs cleanly both directions; table exists with all indexes verified via `\d tweet_price_mentions` in psql.

### Phase 2 — Extractor service module

**Goal:** Pure Python module that takes tweet text and returns structured price mention candidates. No DB access; fully unit-testable.

Steps:
1. Add `word2number` to `backend/pyproject.toml`.
2. Create `backend/app/services/price_mention_extractor.py` with:
   - Pattern definitions (named, with `requires_btc_context` flags as appropriate)
   - Tweet text preprocessing function (URL strip, @mention strip, hashtag preserve)
   - Numeric normalization function (commas, suffixes, floor/ceiling)
   - Shared-suffix range pattern handler
   - Written-number span detector + word2number wrapper with year-shape exclusion
   - Context scoring function (strong/medium/negative keyword sets, scoring math)
   - Mention type classifier with priority-order tie-breaking
   - Top-level `extract_mentions_from_text(text: str) -> list[PriceMentionCandidate]` function
3. Write unit tests at `backend/tests/services/test_price_mention_extractor.py`:
   - Each pattern family has at least one positive and one negative test
   - Floor and ceiling boundary tests
   - Range pattern tests (explicit suffix and shared suffix)
   - Year-shape exclusion test
   - Each confidence band reachable
   - Each mention type assignable
   - Tie-breaking priority order verified

**Done when:** All unit tests pass; manual ad-hoc invocations on sample tweets produce expected output.

### Phase 3 — Extraction script

**Goal:** CLI script that reads tweets from the DB, runs the extractor, and writes mentions.

Steps:
1. Create `backend/scripts/enrich/extract_tweet_price_mentions.py` modeled on `extract_tweet_keywords.py`.
2. Implement CLI argument parsing matching the spec in this doc (username, analysis-start, only-missing-tweets, dry-run, overwrite-existing, extractor-version).
3. Implement the tweet query with retweet exclusion via `tweet_references` left join.
4. Implement batched insert respecting the unique constraint (use `ON CONFLICT DO NOTHING` or `ON CONFLICT DO UPDATE` for `--overwrite-existing`).
5. Implement progress logging matching the style of existing enrichment scripts.
6. Smoke-test on a small slice (`--username saylor --analysis-start 2024-01-01T00:00:00Z`) and inspect output.

**Done when:** Script runs cleanly on a small slice, writes expected rows, supports dry-run, supports incremental re-runs without errors.

### Phase 4 — Calibration

**Goal:** Validate and tune the extractor against real corpus before scaling out.

Steps:
1. Run extractor on full corpora for all four calibration authors: Saylor, Michael Sullivan, Willy Woo, Jeff Walton.
2. For each author, export a random sample of ~150 medium-confidence rows (raw_fragment + tweet text).
3. Manually label each row: valid BTC price mention / not.
4. Identify false positive patterns by author profile:
   - Sullivan: non-BTC personal finance / general dollar amounts
   - Woo: on-chain metric numbers, range extraction accuracy
   - Walton: corporate financial language (balance sheet, allocations, share counts)
5. Adjust scoring weights and negative-signal keyword sets based on patterns found.
6. Re-run on all four authors after adjustments to confirm improvement.
7. Document calibration outcomes in the extractor module's top comment.

**Done when:** False positive rate is acceptable (target < 10% for medium-confidence band); calibration notes recorded; all four authors' data is treated as v1-quality.

### Phase 5 — Run extraction over full corpus

**Goal:** Populate the table for all tracked users.

Steps:
1. Loop the extraction script over every tracked user with `--analysis-start 2020-08-01T00:00:00Z --only-missing-tweets`.
2. Confirm row counts are reasonable per user (spot check a few).
3. Confirm no errors in the script logs.

**Done when:** Every tracked user has been processed; total row count is logged and sanity-checked.

### Phase 6 — Backend view service and API endpoint

**Goal:** Endpoint returning the cohort-bucketed payload.

Steps:
1. Create `backend/app/services/price_mention_view.py`.
2. Implement the cohort query: filter by user set + extractor key/version + confidence + price range + mention type, join `tweets` for date, exclude retweets, aggregate by period bucket and price bin.
3. Implement BTC close lookup per period from `market_price_points`.
4. Implement `tweet_count` and `user_count` denominators (also retweet-excluded for consistency).
5. Add the route handler in `backend/app/api/`.
6. Add Pydantic request/response schemas.
7. Test endpoint with curl across all major filter combinations.

**Done when:** Endpoint returns valid payloads for `cohort_tag=null`, several specific cohorts, all granularity options, all mention types, varying confidence thresholds.

### Phase 7 — Frontend page skeleton + heatmap view

**Goal:** Working `#/price-mentions` page with the primary heatmap visualization.

Steps:
1. Add the route to the frontend router config.
2. Create `PriceMentionsPage.tsx` modeled on `AggregateMoodsPage.tsx`.
3. Implement the cohort selector control (reuse component or pattern from Aggregate Moods).
4. Implement the granularity toggle, mention type filter, confidence filter.
5. Wire up the API call.
6. Build the heatmap visualization with log-scale Y axis and $1k binning.
7. Add the BTC price overlay line.
8. Verify against the design intent: round-number magnets emerge visually; spread over time is observable.

**Done when:** Page loads at `#/price-mentions`, all controls work, heatmap renders for all-users and at least one specific cohort, BTC overlay is visible.

### Phase 8 — Cohort comparison view

**Goal:** Add View C (selected cohort vs. baseline) to the page.

Steps:
1. Add the view mode toggle (Heatmap / Comparison) to the page controls.
2. Implement the comparison rendering: two distributions overlaid on the same X axis (price levels).
3. Implement the optional Z-score toggle.
4. Verify cohort switching produces meaningful divergence visualizations.

**Done when:** Toggle works, comparison view renders correctly, switching cohorts shows visibly different distributions.

### Phase 9 — Pipeline integration

**Goal:** Make extraction part of the standard ingest workflow and create the standalone batch shell script.

Steps:
1. Create `scripts/run-price-mentions-extraction.sh` per the design in the Integration section above. The script queries `managed_author_views` for all tracked published users and iterates over them, calling `extract_tweet_price_mentions.py` with `--only-missing-tweets` by default.
2. Verify the script works in incremental mode (run it once, run it again, confirm no duplicate rows and minimal re-work).
3. Add the extraction step to `scripts/run-user-post-ingest-batch.sh` as a new numbered step after `extract_tweet_keywords`.
4. Add an optional flag/step to `post_process_tracked_author_refresh.py` (initially opt-in, promoted to default once calibration is solid).
5. Update README with:
   - The new `run-price-mentions-extraction.sh` command and its usage modes
   - The new script command
   - The new page URL
   - The new endpoint in the endpoints list
   - Position in the enrichment sequence
4. Verify a fresh user onboarding produces price mention data end-to-end.

**Done when:** A new user added via the standard ingest flow gets price mentions extracted automatically and appears in the cohort views.

### Phase 10 — Scatter view (optional)

Only build this phase if, after Phases 7–8 are working and seeing real data, the scatter view feels genuinely needed for analysis the heatmap can't deliver.

---

## Open Questions and Future Extensions

**Qualitative price references**
"Six figures" and "seven figures" are excluded now because they don't map to a specific price level. They could be captured as a separate mention type with a `null` price_usd and a `qualitative_band` field later without schema changes.

**Narrative-implied volatility metric**
The spread of price mentions around the actual BTC price at each time period could be formalized as a scalar metric (e.g., interquartile range of mentioned prices, weighted by mention count). Storing this as a derived series alongside BTC price and options IV would make the comparison concrete. Not in scope for the initial build but the raw data will be there.

**Satoshi-denominated amounts**
Not in scope. Could be a separate extractor key/version.

**Author-level BTC prior**
As noted in the extraction approach, an author-level weight stored in `managed_author_views` could improve medium-confidence precision for well-known BTC accounts. Designed to slot in without changing the schema.

**Aggregate snapshot for price mentions**
If cohort query performance becomes a problem at scale, add a snapshot table following the `aggregate_view_snapshots` pattern. The API shape already accommodates this transparently.

**Implied volatility comparison**
The user noted that the spread of narrative price levels over time may invite direct comparison to Bitcoin options implied volatility over the same periods. This would require ingesting IV data (Deribit or similar) as a new market data source. Not in scope for the initial build but worth tracking as a follow-up once the price mentions data is established.

**Tracking table for empty-tweet skip optimization**
If the re-processing cost of empty tweets becomes painful, add `tweet_price_mention_runs` (one row per `(tweet_id, extractor_key, extractor_version)` regardless of mention outcome). The `--only-missing-tweets` flag would then check that table instead of `tweet_price_mentions`. Add only when actually needed.

**Multi-cohort overlay**
Out of scope for v1 to keep the page consistent with Aggregate Moods/Narratives. If cross-cohort comparison feels limited by single-select switching, multi-select with overlay is a natural future addition.

**Approximate modifier metadata**
Currently modifiers (`~`, `>`, `<`, `around`, `over`, etc.) are recognized but discarded. If the analysis ever needs to distinguish "exactly $100k" from "around $100k" mentions, store the modifier as a column without changing the price normalization.
