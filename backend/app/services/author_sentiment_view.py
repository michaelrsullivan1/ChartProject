from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.tweet_sentiment_score import TweetSentimentScore
from app.models.user import User
from app.services.market_data import floor_to_day, floor_to_week
from app.services.sentiment import DEFAULT_SENTIMENT_MODEL


@dataclass(slots=True)
class AuthorSentimentViewRequest:
    username: str
    granularity: str = "week"
    model_key: str = DEFAULT_SENTIMENT_MODEL
    view_name: str = "author-sentiment"
    analysis_start: str | None = None


def build_author_sentiment_view(
    request: AuthorSentimentViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    granularity = request.granularity.strip().lower()
    if granularity not in {"day", "week"}:
        raise RuntimeError("author-sentiment view only supports granularity=day or granularity=week.")
    analysis_start = (
        _parse_utc_datetime(request.analysis_start) if request.analysis_start is not None else None
    )

    session = session_factory()
    try:
        user = session.scalar(select(User).where(User.username == request.username))
        if user is None:
            raise RuntimeError(f"No canonical user found for username={request.username!r}.")

        sentiment_query = (
            select(
                Tweet.created_at_platform,
                TweetSentimentScore.sentiment_label,
                TweetSentimentScore.confidence,
                TweetSentimentScore.negative_score,
                TweetSentimentScore.neutral_score,
                TweetSentimentScore.positive_score,
            )
            .join(TweetSentimentScore, TweetSentimentScore.tweet_id == Tweet.id)
            .where(
                Tweet.author_user_id == user.id,
                TweetSentimentScore.model_key == request.model_key,
                TweetSentimentScore.status == "scored",
            )
            .order_by(Tweet.created_at_platform.asc(), Tweet.id.asc())
        )
        if analysis_start is not None:
            sentiment_query = sentiment_query.where(Tweet.created_at_platform >= analysis_start)

        rows = session.execute(sentiment_query).all()
        if not rows:
            raise RuntimeError(
                f"No scored tweet sentiment rows found for username={request.username!r} and "
                f"model_key={request.model_key!r}."
            )

        bucket_fn = floor_to_week if granularity == "week" else floor_to_day
        step = timedelta(days=7 if granularity == "week" else 1)
        bucket_map: dict[datetime, dict[str, float | int]] = {}
        total_negative = 0
        total_neutral = 0
        total_positive = 0
        total_confidence = 0.0
        total_sentiment_index = 0.0

        for created_at, label, confidence, negative_score, neutral_score, positive_score in rows:
            bucket_start = bucket_fn(created_at.astimezone(UTC))
            bucket = bucket_map.setdefault(
                bucket_start,
                {
                    "scored_tweet_count": 0,
                    "sum_confidence": 0.0,
                    "sum_sentiment_index": 0.0,
                    "negative_tweet_count": 0,
                    "neutral_tweet_count": 0,
                    "positive_tweet_count": 0,
                    "sum_negative_score": 0.0,
                    "sum_neutral_score": 0.0,
                    "sum_positive_score": 0.0,
                },
            )

            sentiment_index = float(positive_score) - float(negative_score)
            bucket["scored_tweet_count"] += 1
            bucket["sum_confidence"] += float(confidence)
            bucket["sum_sentiment_index"] += sentiment_index
            bucket["sum_negative_score"] += float(negative_score)
            bucket["sum_neutral_score"] += float(neutral_score)
            bucket["sum_positive_score"] += float(positive_score)

            if label == "negative":
                bucket["negative_tweet_count"] += 1
                total_negative += 1
            elif label == "positive":
                bucket["positive_tweet_count"] += 1
                total_positive += 1
            else:
                bucket["neutral_tweet_count"] += 1
                total_neutral += 1

            total_confidence += float(confidence)
            total_sentiment_index += sentiment_index

        sorted_buckets = sorted(bucket_map.keys())
        current = bucket_fn(analysis_start) if analysis_start is not None else sorted_buckets[0]
        end = sorted_buckets[-1]
        sentiment_series: list[dict[str, object]] = []
        while current <= end:
            bucket = bucket_map.get(current)
            if bucket is None:
                sentiment_series.append(
                    {
                        "period_start": current.isoformat().replace("+00:00", "Z"),
                        "scored_tweet_count": 0,
                        "average_sentiment_index": 0.0,
                        "average_confidence": 0.0,
                        "average_negative_score": 0.0,
                        "average_neutral_score": 0.0,
                        "average_positive_score": 0.0,
                        "negative_tweet_count": 0,
                        "neutral_tweet_count": 0,
                        "positive_tweet_count": 0,
                    }
                )
            else:
                scored_tweet_count = int(bucket["scored_tweet_count"])
                sentiment_series.append(
                    {
                        "period_start": current.isoformat().replace("+00:00", "Z"),
                        "scored_tweet_count": scored_tweet_count,
                        "average_sentiment_index": bucket["sum_sentiment_index"] / scored_tweet_count,
                        "average_confidence": bucket["sum_confidence"] / scored_tweet_count,
                        "average_negative_score": bucket["sum_negative_score"] / scored_tweet_count,
                        "average_neutral_score": bucket["sum_neutral_score"] / scored_tweet_count,
                        "average_positive_score": bucket["sum_positive_score"] / scored_tweet_count,
                        "negative_tweet_count": int(bucket["negative_tweet_count"]),
                        "neutral_tweet_count": int(bucket["neutral_tweet_count"]),
                        "positive_tweet_count": int(bucket["positive_tweet_count"]),
                    }
                )
            current += step

        scored_tweet_count = len(rows)
        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
            },
            "model": {
                "model_key": request.model_key,
                "granularity": granularity,
                "status_filter": "scored",
            },
            "range": {
                "start": sentiment_series[0]["period_start"],
                "end": sentiment_series[-1]["period_start"],
            },
            "summary": {
                "scored_tweet_count": scored_tweet_count,
                "average_sentiment_index": total_sentiment_index / scored_tweet_count,
                "average_confidence": total_confidence / scored_tweet_count,
                "negative_tweet_count": total_negative,
                "neutral_tweet_count": total_neutral,
                "positive_tweet_count": total_positive,
            },
            "sentiment_series": sentiment_series,
        }
    finally:
        session.close()


def _parse_utc_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"Invalid analysis_start datetime {value!r}.") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)
