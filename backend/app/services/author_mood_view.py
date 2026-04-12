from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.tweet_mood_score import TweetMoodScore
from app.models.user import User
from app.services.author_sentiment_view import _parse_utc_datetime
from app.services.market_data import floor_to_day, floor_to_week
from app.services.moods import DEFAULT_MOOD_MODEL, DEFAULT_VISIBLE_MOOD_LABELS


@dataclass(slots=True)
class AuthorMoodViewRequest:
    username: str
    granularity: str = "week"
    model_key: str = DEFAULT_MOOD_MODEL
    mood_labels: tuple[str, ...] = DEFAULT_VISIBLE_MOOD_LABELS
    view_name: str = "author-moods"
    analysis_start: str | None = None


def build_author_mood_view(
    request: AuthorMoodViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    granularity = request.granularity.strip().lower()
    if granularity not in {"day", "week"}:
        raise RuntimeError("author-moods view only supports granularity=day or granularity=week.")
    analysis_start = (
        _parse_utc_datetime(request.analysis_start) if request.analysis_start is not None else None
    )

    session = session_factory()
    try:
        user = session.scalar(select(User).where(User.username == request.username))
        if user is None:
            raise RuntimeError(f"No canonical user found for username={request.username!r}.")

        mood_labels = tuple(label.strip().lower() for label in request.mood_labels if label.strip())
        if not mood_labels:
            raise RuntimeError("author-moods view requires at least one mood label.")

        mood_query = (
            select(
                Tweet.id,
                Tweet.created_at_platform,
                TweetMoodScore.mood_label,
                TweetMoodScore.score,
            )
            .join(TweetMoodScore, TweetMoodScore.tweet_id == Tweet.id)
            .where(
                Tweet.author_user_id == user.id,
                TweetMoodScore.model_key == request.model_key,
                TweetMoodScore.status == "scored",
                TweetMoodScore.mood_label.in_(mood_labels),
            )
            .order_by(Tweet.created_at_platform.asc(), Tweet.id.asc(), TweetMoodScore.mood_label.asc())
        )
        if analysis_start is not None:
            mood_query = mood_query.where(Tweet.created_at_platform >= analysis_start)

        rows = session.execute(mood_query).all()
        if not rows:
            raise RuntimeError(
                f"No scored tweet mood rows found for username={request.username!r} and "
                f"model_key={request.model_key!r}."
            )

        bucket_fn = floor_to_week if granularity == "week" else floor_to_day
        step = timedelta(days=7 if granularity == "week" else 1)
        bucket_map: dict[datetime, dict[str, object]] = {}
        overall_tweet_ids: set[int] = set()
        overall_label_totals = {
            mood_label: {"sum_score": 0.0, "score_count": 0}
            for mood_label in mood_labels
        }

        for tweet_id, created_at, mood_label, score in rows:
            bucket_start = bucket_fn(created_at.astimezone(UTC))
            bucket = bucket_map.setdefault(
                bucket_start,
                {
                    "tweet_ids": set(),
                    "moods": {
                        label: {"sum_score": 0.0, "score_count": 0}
                        for label in mood_labels
                    },
                },
            )

            bucket["tweet_ids"].add(int(tweet_id))
            mood_bucket = bucket["moods"][mood_label]
            mood_bucket["sum_score"] += float(score)
            mood_bucket["score_count"] += 1

            overall_tweet_ids.add(int(tweet_id))
            overall_label_totals[mood_label]["sum_score"] += float(score)
            overall_label_totals[mood_label]["score_count"] += 1

        summary_moods = {
            mood_label: {
                "average_score": (
                    overall_label_totals[mood_label]["sum_score"]
                    / overall_label_totals[mood_label]["score_count"]
                    if overall_label_totals[mood_label]["score_count"] > 0
                    else 0.0
                ),
                "score_count": int(overall_label_totals[mood_label]["score_count"]),
            }
            for mood_label in mood_labels
        }

        sorted_buckets = sorted(bucket_map.keys())
        current = bucket_fn(analysis_start) if analysis_start is not None else sorted_buckets[0]
        end = sorted_buckets[-1]
        mood_series: list[dict[str, object]] = []
        while current <= end:
            bucket = bucket_map.get(current)
            if bucket is None:
                mood_series.append(
                    {
                        "period_start": current.isoformat().replace("+00:00", "Z"),
                        "scored_tweet_count": 0,
                        "moods": {
                            mood_label: {
                                "average_score": 0.0,
                                "score_count": 0,
                            }
                            for mood_label in mood_labels
                        },
                    }
                )
            else:
                bucket_moods = bucket["moods"]
                mood_series.append(
                    {
                        "period_start": current.isoformat().replace("+00:00", "Z"),
                        "scored_tweet_count": len(bucket["tweet_ids"]),
                        "moods": {
                            mood_label: {
                                "average_score": (
                                    bucket_moods[mood_label]["sum_score"]
                                    / bucket_moods[mood_label]["score_count"]
                                    if bucket_moods[mood_label]["score_count"] > 0
                                    else 0.0
                                ),
                                "score_count": int(bucket_moods[mood_label]["score_count"]),
                            }
                            for mood_label in mood_labels
                        },
                    }
                )
            current += step

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
                "mood_labels": list(mood_labels),
            },
            "range": {
                "start": mood_series[0]["period_start"],
                "end": mood_series[-1]["period_start"],
            },
            "summary": {
                "scored_tweet_count": len(overall_tweet_ids),
                "moods": summary_moods,
            },
            "mood_series": mood_series,
        }
    finally:
        session.close()
