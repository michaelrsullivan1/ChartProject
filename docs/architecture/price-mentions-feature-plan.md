# Bitcoin Price Mention Extraction Feature Plan

## Problem Statement

Tracked authors and cohorts mention specific Bitcoin price levels constantly — as predictions, historical anchors, conditional triggers, and current observations. The goal is to extract every explicit numeric price mention from the tweet corpus, store it with type and confidence metadata, and visualize where price-level "magnets" exist: which price points cluster in narrative frequency, when they dominated discourse, and how that varies across cohorts.

A secondary but compelling output of this data is what might be called **narrative-implied volatility**: the spread of price levels being discussed at any given time mirrors how wide open the prediction space is. During a bull run, mentions cluster tightly above current price. During uncertainty, they scatter. This spread over time is a genuinely novel signal worth capturing and may invite comparison to options-implied volatility over the same periods.

---

## Scope

### In scope

- Explicit numeric Bitcoin price mentions ($10,000 and above) extracted from original tweet text
- Per-cohort aggregate view as the primary UI surface, on a new standalone page
- Mention type classification (prediction, historical, current observation, conditional)
- Confidence scoring as a filter rather than a gate — store everything, let the UI decide what to show
- Full historical Y-axis range on a log scale so the spread and shift of price mentions over time is visible
- BTC actual price line overlay on all time-series views
- Retweet exclusion — original authored content only

### Out of scope for now

- Qualitative references ("six figures", "seven figures")
- Satoshi-denominated amounts
- Market cap mentions that could be back-calculated to price
- Non-USD denominations
- Per-author drilldown pages — cohort-level density is the primary value
- LLM-per-tweet extraction — definitively ruled out at 500k–1M+ tweet scale

---

## Retweet Handling

**Key finding from the codebase:** Retweets are stored in the database. The normalization service processes them and writes a `tweet_references` row with `reference_type="retweeted"` for each one. No existing enrichment script (sentiment, moods, keywords) currently filters them out.

For price mention extraction, retweets must be explicitly excluded. A retweet's text is "RT @originaluser: [truncated original]..." — it contains the original author's words, not the retweeting author's. Counting those as mentions for the retweeter's user/cohort would introduce amplification noise: 20 authors retweeting the same Saylor "$100k target" tweet would show up as 20 mentions for 20 different users, distorting both the density signal and the cohort data.

**Implementation:** In the extraction script, join on `tweet_references` and exclude any tweet that has a `reference_type = 'retweeted'` row. The table is already indexed on `reference_type`. This is a clean, cheap filter with no schema changes required.

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
| Approximate modifiers | `~$100k`, `>$100k`, `sub-$100k`, `around $100k`, `over $100k` |
| Range formats | `$60k-$100k`, `$60k to $100k`, `between $60k and $100k` — each endpoint extracted as a separate row |

Normalization rules applied to every match:
- Strip commas: `100,000` → `100000`
- Expand k/K suffix: `100k` → `100000`
- Expand M suffix: `1.5M` → `1500000`
- Skip numbers followed immediately by `%` (percentage context)
- Apply floor of `$10,000` and ceiling of `$10,000,000` as a sanity range filter

The $10,000 floor handles most cross-contamination naturally. MSTR stock, ETH, and most other prices that appear in BTC-focused author tweets live below this floor.

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

"BTC between $60k and $80k" extracts two separate rows: one at $60,000 and one at $80,000. This is intentional. Each endpoint is a real price level being named. The repetition and clustering of individual price level mentions is the core signal this feature is built to surface. No deduplication beyond tweet-level uniqueness per price value.

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
CREATE UNIQUE INDEX idx_price_mentions_dedup
    ON tweet_price_mentions(tweet_id, price_usd, extractor_key, extractor_version);
```

Design notes:

- `user_id` is denormalized intentionally. Cohort queries filter by user set, and joining through `tweets` on every cohort query would be expensive at this scale.
- `raw_fragment` stores the matched substring (e.g., `"$100k"`, `"100,000 dollars"`). Useful for debugging the extractor and for any future UI that wants to show source context.
- `extractor_key` + `extractor_version` follow the same versioning pattern as `tweet_keywords` and `tweet_mood_scores`. A v2 extractor can coexist with v1 rows.
- The unique index prevents duplicate rows for the same tweet + price + extractor, so the script is safely re-runnable.
- Multiple rows per tweet are expected and correct.

---

## Extraction Script

Following the existing enrichment script conventions:

**Path:** `backend/scripts/enrich/extract_tweet_price_mentions.py`

**Retweet exclusion:** The script's tweet query excludes any tweet that has a matching row in `tweet_references` with `reference_type = 'retweeted'`. Quote tweets and replies are included.

**Supported options:**

```bash
# Run for one author
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor

# Incremental: only tweets with no existing rows for this extractor+version
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor --only-missing-tweets

# Dry run: print what would be extracted without writing
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor --dry-run

# Overwrite existing rows for this extractor+version
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor --overwrite-existing

# Multiple users
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor schiff

# Custom extractor version (for testing algorithm changes against existing data)
python3 backend/scripts/enrich/extract_tweet_price_mentions.py --username saylor --extractor-version v2
```

**Expected output summary:**

```
Processed 12,450 tweets for saylor (retweets excluded: 841)
  Candidates found: 3,841
  After floor/ceiling filter: 3,612
  High confidence: 2,104
  Medium confidence: 981
  Low confidence: 527
  Rows written: 3,612
  By type — prediction: 1,240  historical: 890  current: 710  conditional: 445  unclassified: 327
```

The extractor service module itself (`backend/app/services/price_mention_extractor.py`) will be approximately 400–500 lines: pattern definitions, normalization functions, written-number handling, context scoring, and mention type classification. Every rule is explicit and auditable.

---

## Backend API Design

### Primary endpoint: aggregate / cohort

```
GET /api/views/price-levels
    ?granularity=month          # month | week; default: month
    &cohort_tag=bitcoin-treasury-leadership   # optional; default: all tracked users
    &min_confidence=0.5         # default: 0.5 (High + Medium)
    &mention_type=prediction    # optional; default: all types
    &min_price=10000            # optional; default: 10000
    &max_price=10000000         # optional
    &normalize=per_tweet        # per_tweet | per_user | none; default: per_tweet
```

**Response shape:**

```json
{
  "granularity": "month",
  "cohort_tag": null,
  "normalize": "per_tweet",
  "periods": [
    {
      "period_start": "2024-01-01T00:00:00Z",
      "tweet_count": 4820,
      "user_count": 18,
      "mention_count": 312,
      "mentions": [
        { "price_usd": 100000, "mention_type": "prediction", "count": 48 },
        { "price_usd": 150000, "mention_type": "prediction", "count": 21 },
        { "price_usd": 60000,  "mention_type": "conditional", "count": 14 }
      ],
      "btc_close": 42800.00
    }
  ]
}
```

`btc_close` per period is included directly in the response — sourced from `market_price_points` using the period-end daily close. This lets the frontend draw the BTC price line from the same payload without a second request.

`tweet_count` and `user_count` per period enable normalization (mentions per 100 tweets, or per user) so cohorts of different sizes and activity levels are comparable.

**Normalization modes:**

| Value | Behavior |
|---|---|
| `per_tweet` | Mentions per 100 tweets — removes activity-level bias; best for comparing periods |
| `per_user` | Mentions per user per period — removes cohort-size bias; best for comparing cohorts |
| `none` | Raw counts |

### Cohorts list endpoint

Reuses the existing `/api/views/aggregate-moods/cohorts` endpoint — no new endpoint needed, same cohort infrastructure.

---

## Frontend: Price Levels Page

### Page identity

A new standalone page, not attached to per-author pages. Suggested route: `#/price-levels`

This page is entirely aggregate and cohort-focused. The primary controls are:
- Cohort selector (same pattern as Aggregate Moods: "All tracked users" default + managed cohort tags)
- Mention type filter (All / Prediction / Historical / Current / Conditional)
- Granularity toggle (Month / Week)
- Confidence filter toggle (High + Medium default, option to include Low)
- View mode toggle (Heatmap / Scatter / Cohort Comparison) — see visualization section

### Managed author registry

No new `enable_price_mentions` flag required on `managed_author_views` for the initial build since this is a cohort/aggregate page, not a per-author page. Users contribute to the cohort views as long as they have price mention rows.

---

## Visualization Options

Three views built on the same underlying API data. The toggle between them is a UI rendering decision — the backend payload shape is the same for all three.

### View A: Price-Time Density Heatmap (primary)

- **X axis:** Time in monthly (or weekly) buckets
- **Y axis:** Price level on a **log scale** — this is essential. Bitcoin prices span orders of magnitude across the corpus history and a linear scale makes older mentions unreadable. Fixed bins at psychologically meaningful round numbers: 10k, 20k, 25k, 30k, 40k, 50k, 60k, 70k, 75k, 80k, 90k, 100k, 110k, 120k, 150k, 200k, 250k, 300k, 500k, 1M
- **Color:** Normalized mention density
- **Overlay:** Actual BTC price as a line running across the heatmap at the Y position of the real price for each time period — sourced from `btc_close` in the API response

**Why this view is the most important:** It captures the core insight at a glance. In a given month, the dark cells show which price levels dominate narrative. The BTC price line shows where the real market was. You can see:
- Price levels that act as persistent magnets regardless of where BTC actually is
- How the cluster of active discussion shifts as BTC price moves
- The spread of discussion narrowing or widening over time (narrative-implied volatility)

The full historical range on the Y axis (log scale, $10k to $10M) is intentional — it lets you see the shift in what counts as a "reasonable" price target as BTC itself moves. A $100k mention in 2021 looks very different from a $100k mention in 2024.

### View B: Scatter Plot

- **X axis:** Tweet date
- **Y axis:** Price mentioned (log scale)
- **Dot:** Each individual mention, optionally colored by mention type
- **Overlay:** BTC price line

More granular than the heatmap. Better for spotting individual outlier predictions. Can become noisy at scale but useful for shorter time windows.

### View C: Price Level Frequency Chart (cohort comparison)

- **X axis:** Price level (same fixed bins as heatmap Y axis)
- **Y axis:** Normalized mention frequency
- **Series:** One per cohort (or one per mention type within a cohort)

Best for cross-cohort comparison: "Does the Bitcoin Treasury Leadership cohort over-index on $1M mentions compared to all tracked users?" Can be expressed as raw normalized counts or as Z-scores relative to the all-users baseline to show divergence more clearly.

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

`post_process_tracked_author_refresh.py` should include price mention extraction as an optional step initially, promoted to default once the extractor is validated against a real corpus sample.

### Addition to `run-user-post-ingest-batch.sh`

```bash
python3 backend/scripts/enrich/extract_tweet_price_mentions.py \
  --username "$USERNAME" \
  --only-missing-tweets
```

### No aggregate snapshot rebuild required (initially)

Price mention queries filter directly on indexed columns (`user_id`, `price_usd`, via tweets join for date). At 500k tweets with proper indexing, cohort queries should run well under a second. If query performance degrades at scale, a snapshot layer can be added later following the `aggregate_view_snapshots` pattern — the API shape already accommodates this transparently.

---

## Confidence Calibration Plan

The initial heuristic confidence scores are educated guesses. Before treating medium-confidence mentions as reliable, do a calibration pass:

1. Run the extractor on one well-understood author (Saylor is ideal — heavily BTC-focused, ground truth is easy to eyeball).
2. Export a random sample of ~200 medium-confidence rows with their `raw_fragment` and tweet text.
3. Manually label each as valid BTC price mention / not.
4. Adjust scoring weights based on false positive and false negative rates.
5. Document the calibrated thresholds in the extractor module.

This is a one-time cost after the first extraction pass and should take under an hour.

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
