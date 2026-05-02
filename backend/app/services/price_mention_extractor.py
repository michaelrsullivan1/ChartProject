"""
price_mention_extractor.py — Bitcoin price mention extraction from tweet text.

Two-stage approach:
  Stage 1: regex candidate extraction across multiple pattern families
  Stage 2: context scoring + mention type classification

All patterns operate on preprocessed text (URLs and @mentions stripped).

Calibration notes (Phase 4 — 2026-05-02, four authors, 288 labeled medium-confidence rows):

False positive patterns identified and addressed:

1. 401k retirement accounts — hard-excluded via _401K_FRAGMENT_RE. "401k" appears
   in tweets about retirement accounts (Jeff Walton, Michael Sullivan), not BTC prices.

2. Bare scale words without a numeral prefix — "million" alone (no preceding digit
   or numeral word) was matching via _WRITTEN_NUM_RE in tweets like "21 million
   bitcoin" (supply cap) or "$962.7 million at ~$90k per bitcoin" (acquisition cost).
   Fixed by removing standalone hundred/thousand/million/billion from the leading
   position in _WRITTEN_NUM_RE; they now only appear as multipliers after a numeral.

3. BTC/sats quantity units — numbers immediately followed by "BTC", "bitcoin",
   "sats", or "satoshi" are coin counts, not USD prices (e.g., "18k of BTC into
   Gemini", "850k sats", "500k Bitcoin"). Excluded via _POST_MATCH_QUANTITY_RE
   post-match check on the characters following the matched fragment.

4. Acquisition cost amounts — MicroStrategy announcements ("purchased 850 BTC for
   ~$99.7 million in cash") contain both a total cost and a per-BTC price. The
   total cost is not a price-per-BTC. "in cash" added to _NON_PRICE_DOLLAR_KEYWORDS
   to reduce confidence on these tweets; reduces both the acquisition cost AND the
   per-BTC price in the same tweet, but the per-BTC price ($100k-range) will still
   score above medium once the BTC keyword boost is applied.

5. MSTR/equity context insufficiently penalised — Jeff Walton tweets heavily mix
   BTC price talk with MSTR stock analysis (options, per-share multiples, float).
   Added "multiple", "per share", "float", "option", "puts", "calls", "pps", "nav",
   "loan", "home equity" to _EQUITY_CONTEXT_KEYWORDS. Increased equity penalty
   from -0.3 to -0.4 to push MSTR-context tweets below the medium threshold.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from word2number import w2n as _w2n

    _HAS_W2N = True
except ImportError:
    _HAS_W2N = False


# ─────────────────────────── public constants ────────────────────────────────

DEFAULT_EXTRACTOR_KEY = "price-mention-regex"
DEFAULT_EXTRACTOR_VERSION = "v1"

PRICE_FLOOR = 10_000
PRICE_CEILING = 10_000_000


# ─────────────────────────── output type ─────────────────────────────────────


@dataclass
class PriceMentionCandidate:
    price_usd: float
    mention_type: str
    confidence: float
    raw_fragment: str


# ─────────────────────────── preprocessing ───────────────────────────────────

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MENTION_RE = re.compile(r"(?<!\w)@\w+")


def preprocess_tweet(text: str) -> str:
    """Strip URLs and @mentions; preserve hashtags."""
    text = _URL_RE.sub(" ", text)
    text = _MENTION_RE.sub(" ", text)
    return text


# ─────────────────────────── BTC context detection ───────────────────────────

_BTC_STRONG_KEYWORDS = frozenset(
    {
        "bitcoin",
        "btc",
        "#bitcoin",
        "#btc",
        "satoshi",
        "sats",
        "hodl",
        "halving",
        "halvening",
        "lightning",
        "on-chain",
        "onchain",
        "price target",
        "price prediction",
        "resistance",
        "support level",
        "buy zone",
        "sell zone",
        "digital gold",
        "sound money",
        "store of value",
        "hard money",
    }
)


def has_btc_context(text_lower: str) -> bool:
    return any(kw in text_lower for kw in _BTC_STRONG_KEYWORDS)


# ─────────────────────────── confidence scoring ──────────────────────────────

_PRICE_NARRATIVE_KEYWORDS = frozenset(
    {
        "prediction",
        "forecast",
        "target",
        "floor",
        "ceiling",
        "buy zone",
        "sell zone",
        "price target",
        "price prediction",
    }
)

_NEGATIVE_CRYPTO_KEYWORDS = frozenset(
    {
        "mstr",
        "microstrategy",
        "ethereum",
        "eth",
        "solana",
        "sol",
        "xrp",
        "ripple",
        "bnb",
        "dogecoin",
        "doge",
    }
)

_EQUITY_CONTEXT_KEYWORDS = frozenset(
    {
        "per share",
        "stock price",
        "shares",
        "equity",
        " eps ",
        "multiple",
        "float",
        "option",
        " puts ",
        " calls ",
        "pps",
        "nav",
    }
)

_NON_PRICE_DOLLAR_KEYWORDS = frozenset(
    {
        "salary",
        "income",
        "revenue",
        "profit",
        "rent",
        "mortgage",
        "in cash",
        "home equity",
        "loan",
    }
)


def score_confidence(text_lower: str, has_dollar_sign: bool) -> float:
    score = 0.3

    if any(kw in text_lower for kw in _BTC_STRONG_KEYWORDS):
        score += 0.5
    if any(kw in text_lower for kw in _PRICE_NARRATIVE_KEYWORDS):
        score += 0.1
    if has_dollar_sign:
        score += 0.1

    if any(kw in text_lower for kw in _NEGATIVE_CRYPTO_KEYWORDS):
        score -= 0.3
    if any(kw in text_lower for kw in _EQUITY_CONTEXT_KEYWORDS):
        score -= 0.4
    if any(kw in text_lower for kw in _NON_PRICE_DOLLAR_KEYWORDS):
        score -= 0.2

    return max(0.0, min(1.0, round(score, 3)))


# ─────────────────────────── mention type classification ─────────────────────

# Each list is tried in order; first match wins at that priority level.
# Priority: prediction > conditional > current > historical > unclassified.

_PREDICTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bwill\s+(?:reach|hit|be\s+at|get\s+to|go\s+to|cross|break)\b",
    r"\bgonna\b",
    r"\bgoing\s+to\s+(?:reach|hit|be|get|go|cross)\b",
    r"\bexpect\b",
    r"\bprediction\b",
    r"\bforecast\b",
    r"\beoy\b",
    r"\bend\s+of\s+year\b",
    r"\bcould\s+reach\b",
    r"\bmight\s+hit\b",
    r"\bheading\s+to(?:ward)?\b",
    r"\bnext\s+(?:target|stop|level)\b",
    r"\bprice\s+target\b",
    r"\bprice\s+prediction\b",
    r"\bmooning?\b",
    r"\bwill\b",  # fallback: any "will"
]]

_CONDITIONAL_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bif\s+(?:btc|bitcoin)\b",
    r"\bwhen\s+it\s+(?:hits?|reaches?|touches?)\b",
    r"\bonce\s+it\b",
    r"\bshould\s+it\b",
    r"\b(?:drops?|falls?|dips?)\s+to\b",
    r"\b(?:rises?|climbs?|pumps?)\s+to\b",
    r"\bbreaks?\s+(?:above|below)\b",
    r"\breclaims?\b",
    r"\bif\b",  # fallback: any "if"
]]

_CURRENT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bright\s+now\b",
    r"\btrading\s+at\b",
    r"\bsitting\s+at\b",
    r"\bjust\s+(?:hit|crossed|touched|broke)\b",
    r"\bspot\s+price\b",
    r"\bcurrent\s+price\b",
    r"\bcurrently\b",
    r"\bhovering\b",
    r"\bnow\b",
    r"\btoday\b",
]]

_HISTORICAL_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bback\s+when\b",
    r"\ball[- ]time\s+high\b",
    r"\bath\b",
    r"\bbought\s+at\b",
    r"\bsold\s+at\b",
    r"\bbear\s+market\s+bottom\b",
    r"\bwhen\s+it\s+crashed\b",
    r"\blow\s+of\b",
    r"\bbottom(?:ed)?\b",
    r"\bpeak\b",
    r"\bin\s+20\d{2}\b",  # "in 2021", "in 2022", etc.
    r"\bwas\b",
    r"\bwere\b",
]]


def classify_mention_type(text: str) -> str:
    for pat in _PREDICTION_PATTERNS:
        if pat.search(text):
            return "prediction"
    for pat in _CONDITIONAL_PATTERNS:
        if pat.search(text):
            return "conditional"
    for pat in _CURRENT_PATTERNS:
        if pat.search(text):
            return "current"
    for pat in _HISTORICAL_PATTERNS:
        if pat.search(text):
            return "historical"
    return "unclassified"


# ─────────────────────────── numeric normalization ───────────────────────────


def _normalize_with_suffix(val_str: str, suffix: str) -> float | None:
    try:
        val = float(val_str.replace(",", ""))
    except ValueError:
        return None
    s = suffix.lower()
    if s == "k":
        val *= 1_000
    elif s == "m":
        val *= 1_000_000
    if val < PRICE_FLOOR or val > PRICE_CEILING:
        return None
    return val


def _normalize_with_word(val_str: str, word: str) -> float | None:
    try:
        val = float(val_str.replace(",", ""))
    except ValueError:
        return None
    w = word.lower()
    if "thousand" in w:
        val *= 1_000
    elif "million" in w:
        val *= 1_000_000
    elif "billion" in w:
        val *= 1_000_000_000
    if val < PRICE_FLOOR or val > PRICE_CEILING:
        return None
    return val


def _normalize_plain(val_str: str) -> float | None:
    try:
        val = float(val_str.replace(",", ""))
    except ValueError:
        return None
    if val < PRICE_FLOOR or val > PRICE_CEILING:
        return None
    return val


# ─────────────────────────── pattern definitions ─────────────────────────────

# Number component: "1,234.56" or "1234.56" or "1.5" or "100"
_N = r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
# k/K/m/M suffix
_S = r"([kKmM])"
# Optional approximate prefix (non-capturing)
_AP = r"(?:~|>(?!=)|<(?!=)|sub-\s*|around\s+|over\s+|near\s+|above\s+|below\s+)?"
# Currency words
_CW = r"(thousand|million|billion)s?"
# Dollar words
_DW = r"(?:dollars?|usd|bucks?)"


# Pattern 1: Explicit-suffix range — $60k-$100k, $60k to $100k, between $60k and $100k
# Groups: (val1, suf1, val2, suf2)
_RANGE_EXPLICIT_RE = re.compile(
    r"(?:between\s+)?" + _AP + r"\$" + _N + r"\s*" + _S + r"\s*"
    r"(?:-|to|and)\s*" + _AP + r"\$?" + _N + r"\s*" + _S,
    re.IGNORECASE,
)

# Pattern 2: Shared-suffix range with leading $ — $60-100k, $60 to 100k
# Groups: (val1, val2, suffix)
_RANGE_SHARED_DOLLAR_RE = re.compile(
    r"\$" + _N + r"\s*(?:-|to)\s*" + _N + r"\s*" + _S + r"(?!\w)",
    re.IGNORECASE,
)

# Pattern 3: Shared-suffix range without $ (BTC context required) — 60-100k, 60 to 100k
# Groups: (val1, val2, suffix)
_RANGE_SHARED_BARE_RE = re.compile(
    r"(?<!\$)(?<![.\d])" + _N + r"\s*(?:-|to)\s*" + _N + r"\s*" + _S + r"(?!\w)",
    re.IGNORECASE,
)

# Pattern 4: Dollar + suffix — $100k, $1.5M, ~$100k
# Groups: (val, suffix)
_DOLLAR_SUFFIX_RE = re.compile(
    _AP + r"\$" + _N + r"\s*" + _S + r"(?!\w)",
    re.IGNORECASE,
)

# Pattern 5: Dollar + currency word — $1 million, $250 thousand
# Groups: (val, currency_word)
_DOLLAR_CW_RE = re.compile(
    _AP + r"\$" + _N + r"\s+" + _CW + r"(?!\w)",
    re.IGNORECASE,
)

# Pattern 6: Dollar + plain number with commas or 5+ digits — $100,000 or $10000
# Only blocked by currency suffixes/words to allow "$97500 resistance" but not "$100 million".
# Groups: (val)
_DOLLAR_PLAIN_RE = re.compile(
    _AP + r"\$" + r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{5,}(?:\.\d+)?)"
    r"(?!\s*(?:[kKmM]\b|thousand|million|billion|dollars?|usd|bucks?|%))",
    re.IGNORECASE,
)

# Pattern 7: Number + suffix + dollar word — 100k USD, 100k dollars
# Groups: (val, suffix)
_NUM_SUFFIX_DW_RE = re.compile(
    r"(?<!\$)" + _N + r"\s*" + _S + r"\s+" + _DW + r"(?!\w)",
    re.IGNORECASE,
)

# Pattern 8: Number + currency word — 1.5 million dollars, 250 thousand USD, 1 million
# Groups: (val, currency_word)
_NUM_CW_RE = re.compile(
    r"(?<!\$)" + _N + r"\s+" + _CW + r"(?:\s+" + _DW + r")?(?!\w)",
    re.IGNORECASE,
)

# Pattern 9: Bare suffix (BTC context required) — 100k, 1.5M
# Groups: (val, suffix)
_BARE_SUFFIX_RE = re.compile(
    r"(?<!\$)(?<![.\d])" + _N + r"\s*" + _S + r"(?!\w)",
    re.IGNORECASE,
)

# Written number patterns (BTC context required)
# Matches spans like "one hundred thousand", "a million", "half a million".
# Standalone scale words ("million", "thousand", "billion") are intentionally
# excluded from the leading position — they must follow a numeral word or "a/half a"
# to avoid matching "21 million bitcoin" (supply cap) or acquisition cost fragments.
_WRITTEN_NUM_RE = re.compile(
    r"\b(?:half\s+a\s+(?:million|billion)|"
    r"a\s+(?:hundred|thousand|million|billion)|"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)"
    r"(?:[\s-]+(?:and\s+)?(?:one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
    r"hundred|thousand|million|billion))*)\b",
    re.IGNORECASE,
)

# Year-shape written number exclusion: "twenty twenty-five", "two thousand twenty-four"
_YEAR_WRITTEN_RE = re.compile(
    r"^(?:twenty[\s-]+(?:twenty|twenty-one|twenty-two|twenty-three|twenty-four|"
    r"twenty-five|twenty-six|twenty-seven|twenty-eight|twenty-nine|thirty|"
    r"one|two|three|four|five|six|seven|eight|nine)|"
    r"two\s+thousand(?:\s+(?:and\s+)?(?:twenty|thirty)[\s-]\w+)?)$",
    re.IGNORECASE,
)

# Percent-following exclusion: skip any match immediately followed by %
_PERCENT_AFTER_RE = re.compile(r"^\s*%")

# BTC/sats quantity unit: number followed by these units is a coin count, not a USD price
_POST_MATCH_QUANTITY_RE = re.compile(
    r"^\s*(?:btc|bitcoin|sat(?:oshi)?s?)\b", re.IGNORECASE
)

# 401k retirement account: exact fragment match
_401K_FRAGMENT_RE = re.compile(r"^~?4[o0]1\s*[kK]$", re.IGNORECASE)


# ─────────────────────────── internal span tracking ──────────────────────────


def _overlaps(span: tuple[int, int], consumed: list[tuple[int, int]]) -> bool:
    s, e = span
    return any(s < ce and e > cs for cs, ce in consumed)


# ─────────────────────────── written number helpers ──────────────────────────


def _try_written_number(span_text: str) -> float | None:
    if not _HAS_W2N:
        return None
    if _YEAR_WRITTEN_RE.match(span_text.strip()):
        return None
    try:
        val = float(_w2n.word_to_num(span_text))
    except (ValueError, AttributeError):
        return None
    if val < PRICE_FLOOR or val > PRICE_CEILING:
        return None
    return val


# ─────────────────────────── main extraction ─────────────────────────────────


def extract_mentions_from_text(text: str) -> list[PriceMentionCandidate]:
    """Extract Bitcoin price mention candidates from a single tweet's text.

    Returns a list of candidates, deduplicated by price_usd (same price value
    appears at most once per tweet). The mention type and confidence are
    computed from the full tweet text, not just the matched fragment.
    """
    if not text:
        return []

    cleaned = preprocess_tweet(text)
    text_lower = cleaned.lower()
    btc_context = has_btc_context(text_lower)

    # Collect (price_usd, raw_fragment, has_dollar, span) tuples
    raw: list[tuple[float, str, bool, tuple[int, int]]] = []
    consumed: list[tuple[int, int]] = []

    def _add(price: float, fragment: str, has_dollar: bool, span: tuple[int, int]) -> None:
        if _overlaps(span, consumed):
            return
        after = cleaned[span[1] : span[1] + 15]
        # Skip if followed immediately by % (percentage context)
        if _PERCENT_AFTER_RE.match(after):
            return
        # Skip if followed by a BTC/sats unit — it's a coin quantity, not a USD price.
        # Only apply when the fragment has no explicit dollar indicator ("$", "dollar",
        # "usd", "bucks"); if the fragment is dollar-denominated, "bitcoin" following
        # is a subject/context word, not a unit (e.g. "$100k bitcoin target").
        frag_lower = fragment.lower()
        if "$" not in fragment and not any(w in frag_lower for w in ("dollar", "usd", "buck")):
            if _POST_MATCH_QUANTITY_RE.match(after):
                return
        # Skip 401k retirement account references
        if _401K_FRAGMENT_RE.match(fragment.strip()):
            return
        consumed.append(span)
        raw.append((price, fragment, has_dollar, span))

    def _add_range(
        p1: float | None,
        p2: float | None,
        frag: str,
        has_dollar: bool,
        span: tuple[int, int],
    ) -> None:
        """Consume the range span once and push both endpoint prices."""
        if _overlaps(span, consumed):
            return
        after = cleaned[span[1] : span[1] + 15]
        if _PERCENT_AFTER_RE.match(after):
            return
        frag_lower = frag.lower()
        if "$" not in frag and not any(w in frag_lower for w in ("dollar", "usd", "buck")):
            if _POST_MATCH_QUANTITY_RE.match(after):
                return
        consumed.append(span)
        if p1 is not None:
            raw.append((p1, frag, has_dollar, span))
        if p2 is not None:
            raw.append((p2, frag, has_dollar, span))

    # ── Pattern 1: explicit-suffix range ─────────────────────────────────────
    for m in _RANGE_EXPLICIT_RE.finditer(cleaned):
        val1, suf1, val2, suf2 = m.group(1), m.group(2), m.group(3), m.group(4)
        _add_range(
            _normalize_with_suffix(val1, suf1),
            _normalize_with_suffix(val2, suf2),
            m.group(0),
            True,
            m.span(),
        )

    # ── Pattern 2: shared-suffix range with $ ────────────────────────────────
    for m in _RANGE_SHARED_DOLLAR_RE.finditer(cleaned):
        val1, val2, suf = m.group(1), m.group(2), m.group(3)
        _add_range(
            _normalize_with_suffix(val1, suf),
            _normalize_with_suffix(val2, suf),
            m.group(0),
            True,
            m.span(),
        )

    # ── Pattern 3: shared-suffix range without $ (BTC context required) ──────
    if btc_context:
        for m in _RANGE_SHARED_BARE_RE.finditer(cleaned):
            val1, val2, suf = m.group(1), m.group(2), m.group(3)
            _add_range(
                _normalize_with_suffix(val1, suf),
                _normalize_with_suffix(val2, suf),
                m.group(0),
                False,
                m.span(),
            )

    # ── Pattern 4: dollar + suffix ────────────────────────────────────────────
    for m in _DOLLAR_SUFFIX_RE.finditer(cleaned):
        val, suf = m.group(1), m.group(2)
        p = _normalize_with_suffix(val, suf)
        if p is not None:
            _add(p, m.group(0), True, m.span())

    # ── Pattern 5: dollar + currency word ────────────────────────────────────
    for m in _DOLLAR_CW_RE.finditer(cleaned):
        val, cw = m.group(1), m.group(2)
        p = _normalize_with_word(val, cw)
        if p is not None:
            _add(p, m.group(0), True, m.span())

    # ── Pattern 6: dollar + plain number ─────────────────────────────────────
    for m in _DOLLAR_PLAIN_RE.finditer(cleaned):
        p = _normalize_plain(m.group(1))
        if p is not None:
            _add(p, m.group(0), True, m.span())

    # ── Pattern 7: number + suffix + dollar word ──────────────────────────────
    for m in _NUM_SUFFIX_DW_RE.finditer(cleaned):
        val, suf = m.group(1), m.group(2)
        p = _normalize_with_suffix(val, suf)
        if p is not None:
            _add(p, m.group(0), False, m.span())

    # ── Pattern 8: number + currency word ────────────────────────────────────
    for m in _NUM_CW_RE.finditer(cleaned):
        val, cw = m.group(1), m.group(2)
        p = _normalize_with_word(val, cw)
        if p is not None:
            _add(p, m.group(0), False, m.span())

    # ── Pattern 9: bare suffix (BTC context required) ────────────────────────
    if btc_context:
        for m in _BARE_SUFFIX_RE.finditer(cleaned):
            val, suf = m.group(1), m.group(2)
            p = _normalize_with_suffix(val, suf)
            if p is not None:
                _add(p, m.group(0), False, m.span())

    # ── Written numbers (BTC context required) ───────────────────────────────
    if btc_context and _HAS_W2N:
        for m in _WRITTEN_NUM_RE.finditer(cleaned):
            if _overlaps(m.span(), consumed):
                continue
            p = _try_written_number(m.group(0))
            if p is not None:
                _add(p, m.group(0), False, m.span())

    if not raw:
        return []

    # Deduplicate by price_usd: keep first occurrence of each price
    seen_prices: set[float] = set()
    deduped: list[tuple[float, str, bool]] = []
    for price, frag, has_dollar, _span in raw:
        if price not in seen_prices:
            seen_prices.add(price)
            deduped.append((price, frag, has_dollar))

    # Score confidence and classify type once for this tweet (tweet-level signals)
    mention_type = classify_mention_type(cleaned)

    return [
        PriceMentionCandidate(
            price_usd=price,
            mention_type=mention_type,
            confidence=score_confidence(text_lower, has_dollar),
            raw_fragment=frag,
        )
        for price, frag, has_dollar in deduped
    ]
