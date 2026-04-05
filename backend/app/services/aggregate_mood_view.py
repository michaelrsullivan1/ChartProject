from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.market_price_point import MarketPricePoint
from app.models.tweet import Tweet
from app.models.tweet_mood_score import TweetMoodScore
from app.models.user import User
from app.services.author_sentiment_view import _parse_utc_datetime
from app.services.market_data import floor_to_day, floor_to_week
from app.services.moods import DEFAULT_MOOD_MODEL, DEFAULT_VISIBLE_MOOD_LABELS


@dataclass(slots=True)
class AggregateMoodOverviewRequest:
    granularity: str = "week"
    model_key: str = DEFAULT_MOOD_MODEL
    view_name: str = "aggregate-moods"
    analysis_start: str | None = None


@dataclass(slots=True)
class AggregateMoodViewRequest:
    granularity: str = "week"
    model_key: str = DEFAULT_MOOD_MODEL
    mood_labels: tuple[str, ...] = DEFAULT_VISIBLE_MOOD_LABELS
    view_name: str = "aggregate-mood-series"
    analysis_start: str | None = None


def build_aggregate_mood_overview(
    request: AggregateMoodOverviewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    granularity = request.granularity.strip().lower()
    if granularity not in {"day", "week"}:
        raise RuntimeError("aggregate-moods view only supports granularity=day or granularity=week.")
    analysis_start = (
        _parse_utc_datetime(request.analysis_start) if request.analysis_start is not None else None
    )

    session = session_factory()
    try:
        scored_tweet_ids = (
            select(TweetMoodScore.tweet_id)
            .where(
                TweetMoodScore.model_key == request.model_key,
                TweetMoodScore.status == "scored",
            )
            .group_by(TweetMoodScore.tweet_id)
            .subquery()
        )

        tweet_query = (
            select(
                Tweet.created_at_platform,
                Tweet.like_count,
                Tweet.bookmark_count,
                Tweet.impression_count,
            )
            .where(Tweet.id.in_(select(scored_tweet_ids.c.tweet_id)))
            .order_by(Tweet.created_at_platform.asc(), Tweet.id.asc())
        )
        if analysis_start is not None:
            tweet_query = tweet_query.where(Tweet.created_at_platform >= analysis_start)

        tweet_rows = session.execute(tweet_query).all()
        if not tweet_rows:
            raise RuntimeError(
                f"No scored tweet mood rows found for aggregate view and model_key={request.model_key!r}."
            )

        cohort_rows = session.execute(
            select(User.username, User.display_name)
            .join(Tweet, Tweet.author_user_id == User.id)
            .where(Tweet.id.in_(select(scored_tweet_ids.c.tweet_id)))
            .group_by(User.id, User.username, User.display_name)
            .order_by(User.username.asc())
        ).all()
        cohort_usernames = [username for username, _display_name in cohort_rows]

        bucket_fn = floor_to_week if granularity == "week" else floor_to_day
        series_start = bucket_fn(analysis_start) if analysis_start is not None else None
        tweet_series = _build_tweet_series(
            tweet_rows,
            bucket_fn=bucket_fn,
            granularity=granularity,
            range_start=series_start,
        )

        range_start = tweet_series[0]["period_start"]
        range_end = tweet_series[-1]["period_start"]
        range_start_dt = datetime.fromisoformat(range_start.replace("Z", "+00:00"))
        range_end_dt = datetime.fromisoformat(range_end.replace("Z", "+00:00")) + timedelta(
            days=7 if granularity == "week" else 1
        )

        btc_series = _build_market_series(
            session,
            asset_symbol="BTC",
            quote_currency="USD",
            range_start=range_start_dt,
            range_end=range_end_dt,
        )
        mstr_series = _build_market_series(
            session,
            asset_symbol="MSTR",
            quote_currency="USD",
            range_start=range_start_dt,
            range_end=range_end_dt,
        )

        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": "aggregate",
                "username": "aggregate",
                "display_name": "Aggregate Moods",
            },
            "cohort": {
                "user_count": len(cohort_usernames),
                "usernames": cohort_usernames,
            },
            "tweet_granularity": granularity,
            "btc_granularity": "day",
            "mstr_granularity": "day",
            "range": {
                "start": tweet_series[0]["period_start"],
                "end": tweet_series[-1]["period_start"],
            },
            "tweet_series": tweet_series,
            "btc_series": btc_series,
            "mstr_series": mstr_series,
        }
    finally:
        session.close()


def build_aggregate_mood_view(
    request: AggregateMoodViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    granularity = request.granularity.strip().lower()
    if granularity not in {"day", "week"}:
        raise RuntimeError(
            "aggregate-mood-series view only supports granularity=day or granularity=week."
        )
    analysis_start = (
        _parse_utc_datetime(request.analysis_start) if request.analysis_start is not None else None
    )

    mood_labels = tuple(label.strip().lower() for label in request.mood_labels if label.strip())
    if not mood_labels:
        raise RuntimeError("aggregate-mood-series view requires at least one mood label.")

    session = session_factory()
    try:
        mood_query = (
            select(
                Tweet.author_user_id,
                Tweet.id,
                Tweet.created_at_platform,
                TweetMoodScore.mood_label,
                TweetMoodScore.score,
            )
            .join(TweetMoodScore, TweetMoodScore.tweet_id == Tweet.id)
            .where(
                TweetMoodScore.model_key == request.model_key,
                TweetMoodScore.status == "scored",
                TweetMoodScore.mood_label.in_(mood_labels),
            )
            .order_by(
                Tweet.created_at_platform.asc(),
                Tweet.author_user_id.asc(),
                Tweet.id.asc(),
                TweetMoodScore.mood_label.asc(),
            )
        )
        if analysis_start is not None:
            mood_query = mood_query.where(Tweet.created_at_platform >= analysis_start)

        rows = session.execute(mood_query).all()
        if not rows:
            raise RuntimeError(
                f"No scored tweet mood rows found for aggregate view and model_key={request.model_key!r}."
            )

        cohort_rows = session.execute(
            select(User.id, User.username, User.display_name)
            .where(User.id.in_({int(row.author_user_id) for row in rows}))
            .order_by(User.username.asc())
        ).all()
        cohort_usernames = [username for _user_id, username, _display_name in cohort_rows]

        bucket_fn = floor_to_week if granularity == "week" else floor_to_day
        step = timedelta(days=7 if granularity == "week" else 1)
        user_baselines: dict[int, dict[str, float]] = {}
        user_overall_totals: dict[int, dict[str, dict[str, float | int]]] = {}
        bucket_map: dict[datetime, dict[int, dict[str, object]]] = {}
        overall_tweet_ids: set[int] = set()

        for author_user_id, tweet_id, created_at, mood_label, score in rows:
            user_id = int(author_user_id)
            bucket_start = bucket_fn(created_at.astimezone(UTC))
            user_totals = user_overall_totals.setdefault(
                user_id,
                {
                    label: {"sum_score": 0.0, "score_count": 0}
                    for label in mood_labels
                },
            )
            user_totals[mood_label]["sum_score"] += float(score)
            user_totals[mood_label]["score_count"] += 1

            bucket_users = bucket_map.setdefault(bucket_start, {})
            user_bucket = bucket_users.setdefault(
                user_id,
                {
                    "tweet_ids": set(),
                    "moods": {
                        label: {"sum_score": 0.0, "score_count": 0}
                        for label in mood_labels
                    },
                },
            )
            user_bucket["tweet_ids"].add(int(tweet_id))
            mood_bucket = user_bucket["moods"][mood_label]
            mood_bucket["sum_score"] += float(score)
            mood_bucket["score_count"] += 1

            overall_tweet_ids.add(int(tweet_id))

        baseline_summary = {
            mood_label: {"sum_baseline": 0.0, "user_count": 0}
            for mood_label in mood_labels
        }
        for user_id, label_totals in user_overall_totals.items():
            user_baselines[user_id] = {}
            for mood_label in mood_labels:
                score_count = int(label_totals[mood_label]["score_count"])
                if score_count <= 0:
                    continue
                baseline = float(label_totals[mood_label]["sum_score"]) / score_count
                user_baselines[user_id][mood_label] = baseline
                baseline_summary[mood_label]["sum_baseline"] += baseline
                baseline_summary[mood_label]["user_count"] += 1

        summary_moods = {
            mood_label: {
                "average_score": (
                    baseline_summary[mood_label]["sum_baseline"]
                    / baseline_summary[mood_label]["user_count"]
                    if baseline_summary[mood_label]["user_count"] > 0
                    else 0.0
                ),
                "average_deviation": 0.0,
                "score_count": sum(
                    int(user_overall_totals[user_id][mood_label]["score_count"])
                    for user_id in user_overall_totals
                ),
            }
            for mood_label in mood_labels
        }

        sorted_buckets = sorted(bucket_map.keys())
        current = bucket_fn(analysis_start) if analysis_start is not None else sorted_buckets[0]
        end = sorted_buckets[-1]
        mood_series: list[dict[str, object]] = []
        while current <= end:
            period_users = bucket_map.get(current, {})
            period_tweet_ids: set[int] = set()
            period_moods: dict[str, dict[str, float | int]] = {}

            for mood_label in mood_labels:
                raw_sum = 0.0
                raw_user_count = 0
                deviation_sum = 0.0
                deviation_user_count = 0
                total_score_count = 0

                for user_id, user_bucket in period_users.items():
                    period_tweet_ids.update(user_bucket["tweet_ids"])
                    mood_bucket = user_bucket["moods"][mood_label]
                    score_count = int(mood_bucket["score_count"])
                    if score_count <= 0:
                        continue

                    average_score = float(mood_bucket["sum_score"]) / score_count
                    raw_sum += average_score
                    raw_user_count += 1
                    total_score_count += score_count

                    baseline = user_baselines.get(user_id, {}).get(mood_label)
                    if baseline is not None:
                        deviation_sum += average_score - baseline
                        deviation_user_count += 1

                period_moods[mood_label] = {
                    "average_score": raw_sum / raw_user_count if raw_user_count > 0 else 0.0,
                    "average_deviation": (
                        deviation_sum / deviation_user_count if deviation_user_count > 0 else 0.0
                    ),
                    "score_count": total_score_count,
                }

            mood_series.append(
                {
                    "period_start": current.isoformat().replace("+00:00", "Z"),
                    "active_user_count": len(period_users),
                    "scored_tweet_count": len(period_tweet_ids),
                    "moods": period_moods,
                }
            )
            current += step

        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": "aggregate",
                "username": "aggregate",
                "display_name": "Aggregate Moods",
            },
            "cohort": {
                "user_count": len(cohort_usernames),
                "usernames": cohort_usernames,
            },
            "model": {
                "model_key": request.model_key,
                "granularity": granularity,
                "status_filter": "scored",
                "mood_labels": list(mood_labels),
                "aggregation_mode": "user-balanced",
                "baseline_mode": "per-user",
            },
            "range": {
                "start": mood_series[0]["period_start"],
                "end": mood_series[-1]["period_start"],
            },
            "summary": {
                "scored_tweet_count": len(overall_tweet_ids),
                "cohort_user_count": len(cohort_usernames),
                "moods": summary_moods,
            },
            "mood_series": mood_series,
        }
    finally:
        session.close()


def _build_tweet_series(
    tweet_rows: list[tuple[datetime, int | None, int | None, int | None]],
    *,
    bucket_fn,
    granularity: str,
    range_start: datetime | None = None,
) -> list[dict[str, object]]:
    counts: dict[datetime, dict[str, int]] = {}
    for tweet_time, like_count, bookmark_count, impression_count in tweet_rows:
        bucket_start = bucket_fn(tweet_time)
        bucket = counts.setdefault(
            bucket_start,
            {
                "tweet_count": 0,
                "like_count": 0,
                "bookmark_count": 0,
                "impression_count": 0,
            },
        )
        bucket["tweet_count"] += 1
        bucket["like_count"] += like_count or 0
        bucket["bookmark_count"] += bookmark_count or 0
        bucket["impression_count"] += impression_count or 0

    sorted_buckets = sorted(counts.keys())
    current = range_start if range_start is not None else sorted_buckets[0]
    end = sorted_buckets[-1]
    step = timedelta(days=7 if granularity == "week" else 1)
    series: list[dict[str, object]] = []
    while current <= end:
        series.append(
            {
                "period_start": current.isoformat().replace("+00:00", "Z"),
                "tweet_count": counts.get(current, {}).get("tweet_count", 0),
                "like_count": counts.get(current, {}).get("like_count", 0),
                "bookmark_count": counts.get(current, {}).get("bookmark_count", 0),
                "impression_count": counts.get(current, {}).get("impression_count", 0),
            }
        )
        current += step
    return series


def _build_market_series(
    session: Session,
    *,
    asset_symbol: str,
    quote_currency: str,
    range_start: datetime,
    range_end: datetime,
) -> list[dict[str, object]]:
    rows = session.execute(
        select(MarketPricePoint.observed_at, MarketPricePoint.price)
        .where(
            MarketPricePoint.asset_symbol == asset_symbol,
            MarketPricePoint.quote_currency == quote_currency,
            MarketPricePoint.interval == "day",
            MarketPricePoint.observed_at >= range_start,
            MarketPricePoint.observed_at <= range_end,
        )
        .order_by(MarketPricePoint.observed_at.asc())
    ).all()

    return [
        {
            "timestamp": observed_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "price_usd": price,
        }
        for observed_at, price in rows
    ]
