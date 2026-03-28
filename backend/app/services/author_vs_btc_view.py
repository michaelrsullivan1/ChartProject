from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.market_price_point import MarketPricePoint
from app.models.tweet import Tweet
from app.models.user import User
from app.services.market_data import floor_to_day, floor_to_week


@dataclass(slots=True)
class AuthorVsBtcViewRequest:
    username: str
    granularity: str = "week"
    view_name: str = "author-vs-btc"


@dataclass(slots=True)
class AuthorTopTweetForWeekRequest:
    username: str
    week_start: str
    view_name: str = "author-top-tweet-for-week"


def build_author_vs_btc_view(
    request: AuthorVsBtcViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    granularity = request.granularity.strip().lower()
    if granularity not in {"day", "week"}:
        raise RuntimeError("author-vs-btc view only supports granularity=day or granularity=week.")

    session = session_factory()
    try:
        user = session.scalar(
            select(User).where(User.username == request.username)
        )
        if user is None:
            raise RuntimeError(f"No canonical user found for username={request.username!r}.")

        tweet_rows = session.execute(
            select(Tweet.created_at_platform)
            .where(Tweet.author_user_id == user.id)
            .order_by(Tweet.created_at_platform)
        ).all()
        if not tweet_rows:
            raise RuntimeError(f"No normalized tweets found for username={request.username!r}.")

        tweet_times = [row[0].astimezone(UTC) for row in tweet_rows]
        bucket_fn = floor_to_week if granularity == "week" else floor_to_day
        tweet_series = _build_tweet_series(tweet_times, bucket_fn=bucket_fn, granularity=granularity)

        range_start = tweet_series[0]["period_start"]
        range_end = tweet_series[-1]["period_start"]
        btc_rows = session.execute(
            select(MarketPricePoint.observed_at, MarketPricePoint.price)
            .where(
                MarketPricePoint.asset_symbol == "BTC",
                MarketPricePoint.quote_currency == "USD",
                MarketPricePoint.interval == "day",
                MarketPricePoint.observed_at >= datetime.fromisoformat(range_start.replace("Z", "+00:00")),
                MarketPricePoint.observed_at <= datetime.fromisoformat(range_end.replace("Z", "+00:00")) + timedelta(days=7),
            )
            .order_by(MarketPricePoint.observed_at)
        ).all()

        btc_series = [
            {
                "timestamp": observed_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "price_usd": price,
            }
            for observed_at, price in btc_rows
        ]

        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
            },
            "tweet_granularity": granularity,
            "btc_granularity": "day",
            "range": {
                "start": tweet_series[0]["period_start"],
                "end": tweet_series[-1]["period_start"],
            },
            "tweet_series": tweet_series,
            "btc_series": btc_series,
        }
    finally:
        session.close()


def build_author_top_tweet_for_week(
    request: AuthorTopTweetForWeekRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    requested_at = _parse_utc_datetime(request.week_start)
    week_start = floor_to_week(requested_at)
    week_end = week_start + timedelta(days=7)

    session = session_factory()
    try:
        user = session.scalar(select(User).where(User.username == request.username))
        if user is None:
            raise RuntimeError(f"No canonical user found for username={request.username!r}.")

        top_tweet = session.scalar(
            select(Tweet)
            .where(
                Tweet.author_user_id == user.id,
                Tweet.created_at_platform >= week_start,
                Tweet.created_at_platform < week_end,
            )
            .order_by(Tweet.like_count.desc().nullslast(), Tweet.created_at_platform.asc())
            .limit(1)
        )

        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "profile_image_url": user.profile_image_url,
            },
            "week": {
                "start": week_start.isoformat().replace("+00:00", "Z"),
                "end": week_end.isoformat().replace("+00:00", "Z"),
            },
            "top_tweet": None
            if top_tweet is None
            else {
                "platform_tweet_id": top_tweet.platform_tweet_id,
                "url": top_tweet.url,
                "text": top_tweet.text,
                "created_at_platform": top_tweet.created_at_platform.astimezone(UTC)
                .isoformat()
                .replace("+00:00", "Z"),
                "reply_count": top_tweet.reply_count,
                "repost_count": top_tweet.repost_count,
                "like_count": top_tweet.like_count,
                "bookmark_count": top_tweet.bookmark_count,
            },
        }
    finally:
        session.close()


def _build_tweet_series(
    tweet_times: list[datetime],
    *,
    bucket_fn,
    granularity: str,
) -> list[dict[str, object]]:
    counts: dict[datetime, int] = {}
    for tweet_time in tweet_times:
        bucket_start = bucket_fn(tweet_time)
        counts[bucket_start] = counts.get(bucket_start, 0) + 1

    sorted_buckets = sorted(counts.keys())
    current = sorted_buckets[0]
    end = sorted_buckets[-1]
    step = timedelta(days=7 if granularity == "week" else 1)
    series: list[dict[str, object]] = []
    while current <= end:
        series.append(
            {
                "period_start": current.isoformat().replace("+00:00", "Z"),
                "tweet_count": counts.get(current, 0),
            }
        )
        current += step
    return series


def _parse_utc_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"Invalid week_start datetime {value!r}.") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)
