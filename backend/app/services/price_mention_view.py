from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.cohort_tag import CohortTag
from app.models.market_price_point import MarketPricePoint
from app.models.tweet import Tweet
from app.models.tweet_price_mention import TweetPriceMention
from app.models.tweet_reference import TweetReference
from app.models.user import User
from app.models.user_cohort_tag import UserCohortTag
from app.services.price_mentions import (
    DEFAULT_PRICE_MENTION_ANALYSIS_START,
    DEFAULT_PRICE_MENTION_EXTRACTOR_KEY,
    DEFAULT_PRICE_MENTION_EXTRACTOR_VERSION,
    _parse_utc_datetime,
)
from app.services.market_data import floor_to_day, floor_to_week


@dataclass(slots=True)
class PriceMentionViewRequest:
    granularity: str = "month"
    cohort_tag: str | None = None
    min_confidence: float = 0.5
    mention_type: str | None = None
    min_price: float = 10_000.0
    max_price: float = 10_000_000.0
    bin_size: float = 1_000.0
    extractor_key: str = DEFAULT_PRICE_MENTION_EXTRACTOR_KEY
    extractor_version: str = DEFAULT_PRICE_MENTION_EXTRACTOR_VERSION
    analysis_start: str = DEFAULT_PRICE_MENTION_ANALYSIS_START
    view_name: str = "price-mentions"


def build_price_mention_view(
    request: PriceMentionViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    granularity = request.granularity.strip().lower()
    if granularity not in {"month", "week"}:
        raise RuntimeError("price-mentions view only supports granularity=month or granularity=week.")

    analysis_start = _parse_utc_datetime(request.analysis_start)

    session = session_factory()
    try:
        cohort_user_ids, cohort_selection = _resolve_cohort_scope(session, request)

        if not cohort_user_ids:
            return {
                "granularity": granularity,
                "cohort": cohort_selection,
                "bin_size": request.bin_size,
                "extractor_key": request.extractor_key,
                "extractor_version": request.extractor_version,
                "periods": [],
                "generated_at": datetime.now(UTC).isoformat(),
            }

        bucket_fn = _floor_to_month if granularity == "month" else floor_to_week

        # Retweet exclusion subquery
        retweet_ids_sq = (
            select(TweetReference.tweet_id)
            .where(TweetReference.reference_type == "retweeted")
            .subquery()
        )

        # Eligible tweet subquery for the denominator (retweet-excluded, same user scope)
        eligible_tweet_sq = (
            select(Tweet.id, Tweet.author_user_id, Tweet.created_at_platform)
            .where(
                Tweet.author_user_id.in_(cohort_user_ids),
                Tweet.created_at_platform >= analysis_start,
                Tweet.id.not_in(select(retweet_ids_sq.c.tweet_id)),
            )
            .subquery()
        )

        # Per-bucket tweet count and user count (denominator)
        bucket_tweet_counts: dict[datetime, int] = {}
        bucket_user_counts: dict[datetime, int] = {}
        tweet_count_rows = session.execute(
            select(
                eligible_tweet_sq.c.created_at_platform,
                eligible_tweet_sq.c.author_user_id,
            )
        ).all()
        for created_at, user_id in tweet_count_rows:
            bucket = bucket_fn(created_at.astimezone(UTC))
            bucket_tweet_counts[bucket] = bucket_tweet_counts.get(bucket, 0) + 1
            if bucket not in bucket_user_counts:
                bucket_user_counts[bucket] = set()  # type: ignore[assignment]
            bucket_user_counts[bucket].add(user_id)  # type: ignore[attr-defined]
        # Convert user sets to counts
        bucket_user_counts = {k: len(v) for k, v in bucket_user_counts.items()}  # type: ignore[assignment]

        # Price mention rows
        mention_filter = [
            TweetPriceMention.user_id.in_(cohort_user_ids),
            TweetPriceMention.extractor_key == request.extractor_key,
            TweetPriceMention.extractor_version == request.extractor_version,
            TweetPriceMention.confidence >= Decimal(str(request.min_confidence)),
            TweetPriceMention.price_usd >= Decimal(str(request.min_price)),
            TweetPriceMention.price_usd <= Decimal(str(request.max_price)),
        ]
        if request.mention_type:
            mention_filter.append(TweetPriceMention.mention_type == request.mention_type)

        mention_rows = session.execute(
            select(
                TweetPriceMention.price_usd,
                TweetPriceMention.mention_type,
                Tweet.created_at_platform,
            )
            .join(Tweet, Tweet.id == TweetPriceMention.tweet_id)
            .where(
                Tweet.id.not_in(select(retweet_ids_sq.c.tweet_id)),
                *mention_filter,
            )
            .order_by(Tweet.created_at_platform.asc())
        ).all()

        # Bucket and bin mentions
        # Structure: {bucket_start: {(bin_price, mention_type): count}}
        buckets: dict[datetime, dict[tuple[int, str], int]] = {}
        for price_usd, mention_type, created_at in mention_rows:
            bucket = bucket_fn(created_at.astimezone(UTC))
            bin_price = _bin_price(float(price_usd), request.bin_size)
            key = (bin_price, mention_type)
            if bucket not in buckets:
                buckets[bucket] = {}
            buckets[bucket][key] = buckets[bucket].get(key, 0) + 1

        # All buckets that have either tweets or mentions
        all_buckets = sorted(set(bucket_tweet_counts) | set(buckets))

        # Load BTC daily close prices for the period
        if all_buckets:
            range_start = all_buckets[0]
            range_end = all_buckets[-1] + (
                timedelta(days=31) if granularity == "month" else timedelta(weeks=1)
            )
            btc_prices = _load_btc_closes(session, range_start, range_end)
        else:
            btc_prices = {}

        periods = []
        for bucket in all_buckets:
            bucket_mentions = buckets.get(bucket, {})
            mention_count = sum(bucket_mentions.values())
            tweet_count = bucket_tweet_counts.get(bucket, 0)
            user_count = bucket_user_counts.get(bucket, 0)

            mentions_list = [
                {"price_usd": price, "mention_type": mtype, "count": count}
                for (price, mtype), count in sorted(bucket_mentions.items())
            ]

            btc_close = _find_btc_close(btc_prices, bucket, granularity)

            periods.append(
                {
                    "period_start": bucket.isoformat(),
                    "tweet_count": tweet_count,
                    "user_count": user_count,
                    "mention_count": mention_count,
                    "mentions": mentions_list,
                    "btc_close": btc_close,
                }
            )

        return {
            "granularity": granularity,
            "cohort": cohort_selection,
            "bin_size": request.bin_size,
            "extractor_key": request.extractor_key,
            "extractor_version": request.extractor_version,
            "periods": periods,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    finally:
        session.close()


def _resolve_cohort_scope(
    session: Session,
    request: PriceMentionViewRequest,
) -> tuple[set[int], dict[str, object]]:
    eligible_rows = session.execute(
        select(User.id)
        .join(TweetPriceMention, TweetPriceMention.user_id == User.id)
        .where(
            TweetPriceMention.extractor_key == request.extractor_key,
            TweetPriceMention.extractor_version == request.extractor_version,
        )
        .group_by(User.id)
    ).scalars().all()
    eligible_user_ids = set(eligible_rows)

    cohort_tag_slug = (request.cohort_tag or "").strip().lower() or None
    if cohort_tag_slug is None:
        return (
            eligible_user_ids,
            {"type": "all", "tag_slug": None, "tag_name": "All tracked users"},
        )

    cohort_tag = session.scalar(select(CohortTag).where(CohortTag.slug == cohort_tag_slug))
    if cohort_tag is None:
        raise RuntimeError(f"Unknown cohort tag slug={cohort_tag_slug!r}.")

    tagged_user_ids = set(
        session.execute(
            select(UserCohortTag.user_id).where(
                UserCohortTag.cohort_tag_id == cohort_tag.id,
                UserCohortTag.user_id.in_(eligible_user_ids),
            )
        ).scalars().all()
    )
    if not tagged_user_ids:
        raise RuntimeError(
            f"No eligible users are assigned to cohort tag slug={cohort_tag_slug!r}."
        )

    return (
        tagged_user_ids,
        {"type": "tag", "tag_slug": cohort_tag.slug, "tag_name": cohort_tag.name},
    )


def _load_btc_closes(
    session: Session,
    range_start: datetime,
    range_end: datetime,
) -> dict[datetime, float]:
    rows = session.execute(
        select(MarketPricePoint.observed_at, MarketPricePoint.price)
        .where(
            MarketPricePoint.asset_symbol == "BTC",
            MarketPricePoint.quote_currency == "USD",
            MarketPricePoint.interval == "day",
            MarketPricePoint.observed_at >= range_start,
            MarketPricePoint.observed_at <= range_end,
        )
        .order_by(MarketPricePoint.observed_at.asc())
    ).all()
    return {floor_to_day(observed_at): price for observed_at, price in rows}


def _find_btc_close(
    btc_prices: dict[datetime, float],
    bucket: datetime,
    granularity: str,
) -> float | None:
    if not btc_prices:
        return None
    if granularity == "month":
        # Latest available price within the month (handles incomplete months)
        next_month = (bucket.replace(day=1) + timedelta(days=32)).replace(day=1)
        period_end = floor_to_day(next_month - timedelta(days=1))
        best = None
        for day, price in btc_prices.items():
            if bucket <= day <= period_end:
                if best is None or day > best[0]:
                    best = (day, price)
        return best[1] if best else None
    else:
        # Latest available price within the week (Mon–Sun)
        week_end = bucket + timedelta(days=6)
        best = None
        for day, price in btc_prices.items():
            if bucket <= day <= week_end:
                if best is None or day > best[0]:
                    best = (day, price)
        return best[1] if best else None


def _bin_price(price: float, bin_size: float) -> int:
    return int((price // bin_size) * bin_size)


def _floor_to_month(value: datetime) -> datetime:
    normalized = value.astimezone(UTC)
    return normalized.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
