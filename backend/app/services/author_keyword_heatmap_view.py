from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.tweet_keyword import TweetKeyword
from app.models.user import User
from app.services.keywords import (
    DEFAULT_KEYWORD_ANALYSIS_START,
    DEFAULT_KEYWORD_EXTRACTOR_KEY,
    DEFAULT_KEYWORD_EXTRACTOR_VERSION,
)


@dataclass(slots=True)
class AuthorKeywordHeatmapViewRequest:
    username: str
    mode: str = "common"
    word_count: str = "all"
    granularity: str = "month"
    limit: int = 48
    analysis_start: str = DEFAULT_KEYWORD_ANALYSIS_START
    extractor_key: str = DEFAULT_KEYWORD_EXTRACTOR_KEY
    extractor_version: str = DEFAULT_KEYWORD_EXTRACTOR_VERSION
    view_name: str = "author-keyword-heatmap"


@dataclass(slots=True)
class AuthorKeywordTrendViewRequest:
    username: str
    phrase: str
    granularity: str = "month"
    analysis_start: str = DEFAULT_KEYWORD_ANALYSIS_START
    extractor_key: str = DEFAULT_KEYWORD_EXTRACTOR_KEY
    extractor_version: str = DEFAULT_KEYWORD_EXTRACTOR_VERSION
    view_name: str = "author-keyword-heatmap-trend"


@dataclass(slots=True)
class AuthorKeywordTopTweetsRequest:
    username: str
    phrase: str
    month_start: str
    limit: int = 3
    extractor_key: str = DEFAULT_KEYWORD_EXTRACTOR_KEY
    extractor_version: str = DEFAULT_KEYWORD_EXTRACTOR_VERSION
    view_name: str = "author-keyword-heatmap-top-liked-tweets"


def build_author_keyword_heatmap_view(
    request: AuthorKeywordHeatmapViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    mode = request.mode.strip().lower()
    if mode not in {"common", "rising"}:
        raise RuntimeError("author-keyword-heatmap only supports mode=common or mode=rising.")
    if request.granularity.strip().lower() != "month":
        raise RuntimeError("author-keyword-heatmap only supports granularity=month.")
    if request.limit < 1:
        raise RuntimeError("author-keyword-heatmap requires limit >= 1.")

    keyword_length = _parse_word_count_filter(request.word_count)
    analysis_start = _floor_to_month(_parse_utc_datetime(request.analysis_start))

    session = session_factory()
    try:
        user = session.scalar(select(User).where(User.username == request.username))
        if user is None:
            raise RuntimeError(f"No canonical user found for username={request.username!r}.")

        month_start_expr = func.date_trunc("month", Tweet.created_at_platform)
        where_conditions = [
            Tweet.author_user_id == user.id,
            Tweet.created_at_platform >= analysis_start,
            TweetKeyword.extractor_key == request.extractor_key,
            TweetKeyword.extractor_version == request.extractor_version,
        ]
        if keyword_length is not None:
            where_conditions.append(TweetKeyword.keyword_length == keyword_length)

        month_rows = session.execute(
            select(
                TweetKeyword.normalized_keyword,
                TweetKeyword.keyword_length,
                month_start_expr.label("month_start"),
                func.count().label("matching_tweet_count"),
            )
            .join(Tweet, Tweet.id == TweetKeyword.tweet_id)
            .where(*where_conditions)
            .group_by(
                TweetKeyword.normalized_keyword,
                TweetKeyword.keyword_length,
                month_start_expr,
            )
            .order_by(TweetKeyword.normalized_keyword.asc(), month_start_expr.asc())
        ).all()

        latest_tweet_at = session.scalar(
            select(func.max(Tweet.created_at_platform)).where(
                Tweet.author_user_id == user.id,
                Tweet.created_at_platform >= analysis_start,
            )
        )
        if latest_tweet_at is None:
            raise RuntimeError(f"No normalized tweets found for username={request.username!r}.")

        months = _build_month_series(analysis_start, _floor_to_month(latest_tweet_at))
        month_index = {month: index for index, month in enumerate(months)}
        phrase_meta: dict[str, dict[str, int]] = {}
        phrase_counts: dict[str, list[int]] = {}

        for normalized_keyword, keyword_length_value, month_start, matching_tweet_count in month_rows:
            month_start_utc = month_start.astimezone(UTC)
            counts = phrase_counts.setdefault(normalized_keyword, [0] * len(months))
            month_position = month_index.get(month_start_utc)
            if month_position is None:
                continue
            counts[month_position] = int(matching_tweet_count)
            phrase_meta[normalized_keyword] = {
                "word_count": int(keyword_length_value),
            }

        if not phrase_counts:
            raise RuntimeError(
                f"No extracted keyword rows found for username={request.username!r} and "
                f"extractor={request.extractor_key}:{request.extractor_version}."
            )

        ranked_phrases = _rank_phrases(phrase_counts, mode=mode)
        selected_phrases = ranked_phrases[: request.limit]

        rows = []
        for normalized_keyword, score in selected_phrases:
            monthly_counts = phrase_counts[normalized_keyword]
            rows.append(
                {
                    "phrase": normalized_keyword,
                    "normalized_phrase": normalized_keyword,
                    "word_count": phrase_meta[normalized_keyword]["word_count"],
                    "total_matching_tweets": sum(monthly_counts),
                    "ranking_score": round(score, 6),
                    "monthly_counts": monthly_counts,
                }
            )

        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
            },
            "mode": mode,
            "granularity": "month",
            "range": {
                "start": months[0].isoformat().replace("+00:00", "Z"),
                "end": months[-1].isoformat().replace("+00:00", "Z"),
            },
            "filters": {
                "word_count": request.word_count,
                "limit": request.limit,
                "analysis_start": analysis_start.isoformat().replace("+00:00", "Z"),
                "extractor_key": request.extractor_key,
                "extractor_version": request.extractor_version,
            },
            "months": [month.isoformat().replace("+00:00", "Z") for month in months],
            "rows": rows,
        }
    finally:
        session.close()


def build_author_keyword_trend_view(
    request: AuthorKeywordTrendViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    if request.granularity.strip().lower() != "month":
        raise RuntimeError("author-keyword-heatmap trend only supports granularity=month.")

    analysis_start = _floor_to_month(_parse_utc_datetime(request.analysis_start))
    normalized_phrase = _normalize_phrase(request.phrase)
    if not normalized_phrase:
        raise RuntimeError("author-keyword-heatmap trend requires a phrase.")

    session = session_factory()
    try:
        user = session.scalar(select(User).where(User.username == request.username))
        if user is None:
            raise RuntimeError(f"No canonical user found for username={request.username!r}.")

        month_start_expr = func.date_trunc("month", Tweet.created_at_platform)
        trend_rows = session.execute(
            select(
                TweetKeyword.keyword_length,
                month_start_expr.label("month_start"),
                func.count().label("matching_tweet_count"),
            )
            .join(Tweet, Tweet.id == TweetKeyword.tweet_id)
            .where(
                Tweet.author_user_id == user.id,
                Tweet.created_at_platform >= analysis_start,
                TweetKeyword.extractor_key == request.extractor_key,
                TweetKeyword.extractor_version == request.extractor_version,
                TweetKeyword.normalized_keyword == normalized_phrase,
            )
            .group_by(
                TweetKeyword.keyword_length,
                month_start_expr,
            )
            .order_by(month_start_expr.asc())
        ).all()
        if not trend_rows:
            raise RuntimeError(
                f"No extracted phrase rows found for username={request.username!r} and phrase={normalized_phrase!r}."
            )

        latest_tweet_at = session.scalar(
            select(func.max(Tweet.created_at_platform)).where(
                Tweet.author_user_id == user.id,
                Tweet.created_at_platform >= analysis_start,
            )
        )
        if latest_tweet_at is None:
            raise RuntimeError(f"No normalized tweets found for username={request.username!r}.")

        months = _build_month_series(analysis_start, _floor_to_month(latest_tweet_at))
        month_index = {month: index for index, month in enumerate(months)}
        counts = [0] * len(months)
        word_count = int(trend_rows[0][0])
        for _, month_start, matching_tweet_count in trend_rows:
            month_start_utc = month_start.astimezone(UTC)
            month_position = month_index.get(month_start_utc)
            if month_position is None:
                continue
            counts[month_position] = int(matching_tweet_count)

        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
            },
            "phrase": normalized_phrase,
            "normalized_phrase": normalized_phrase,
            "word_count": word_count,
            "granularity": "month",
            "range": {
                "start": months[0].isoformat().replace("+00:00", "Z"),
                "end": months[-1].isoformat().replace("+00:00", "Z"),
            },
            "summary": {
                "total_matching_tweets": sum(counts),
                "peak_month_count": max(counts),
            },
            "series": [
                {
                    "period_start": month.isoformat().replace("+00:00", "Z"),
                    "matching_tweet_count": counts[index],
                }
                for index, month in enumerate(months)
            ],
        }
    finally:
        session.close()


def build_author_keyword_top_tweets_for_month(
    request: AuthorKeywordTopTweetsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    month_start = _floor_to_month(_parse_utc_datetime(request.month_start))
    month_end = _add_months(month_start, 1)
    normalized_phrase = _normalize_phrase(request.phrase)
    if not normalized_phrase:
        raise RuntimeError("author-keyword-heatmap top tweets requires a phrase.")
    if request.limit < 1:
        raise RuntimeError("author-keyword-heatmap top tweets requires limit >= 1.")

    session = session_factory()
    try:
        user = session.scalar(select(User).where(User.username == request.username))
        if user is None:
            raise RuntimeError(f"No canonical user found for username={request.username!r}.")

        rows = session.execute(
            select(Tweet)
            .join(TweetKeyword, TweetKeyword.tweet_id == Tweet.id)
            .where(
                Tweet.author_user_id == user.id,
                Tweet.created_at_platform >= month_start,
                Tweet.created_at_platform < month_end,
                TweetKeyword.normalized_keyword == normalized_phrase,
                TweetKeyword.extractor_key == request.extractor_key,
                TweetKeyword.extractor_version == request.extractor_version,
            )
            .order_by(Tweet.like_count.desc().nullslast(), Tweet.created_at_platform.asc())
            .limit(request.limit)
        ).scalars().all()

        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "profile_image_url": user.profile_image_url,
            },
            "phrase": normalized_phrase,
            "month": {
                "start": month_start.isoformat().replace("+00:00", "Z"),
                "end": month_end.isoformat().replace("+00:00", "Z"),
            },
            "tweets": [
                {
                    "platform_tweet_id": tweet.platform_tweet_id,
                    "url": tweet.url,
                    "text": tweet.text,
                    "created_at_platform": tweet.created_at_platform.astimezone(UTC)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "reply_count": tweet.reply_count,
                    "repost_count": tweet.repost_count,
                    "like_count": tweet.like_count,
                    "bookmark_count": tweet.bookmark_count,
                    "impression_count": tweet.impression_count,
                }
                for tweet in rows
            ],
        }
    finally:
        session.close()


def _rank_phrases(
    phrase_counts: dict[str, list[int]],
    *,
    mode: str,
) -> list[tuple[str, float]]:
    ranked: list[tuple[str, float]] = []
    recent_window = 6
    for normalized_keyword, counts in phrase_counts.items():
        total = sum(counts)
        if total == 0:
            continue
        if mode == "common":
            score = float(total)
        else:
            recent_slice = counts[-recent_window:]
            prior_slice = counts[:-recent_window]
            recent_average = sum(recent_slice) / max(len(recent_slice), 1)
            prior_average = sum(prior_slice) / max(len(prior_slice), 1) if prior_slice else 0.0
            score = recent_average - prior_average
            if score <= 0:
                continue
        ranked.append((normalized_keyword, score))
    return sorted(
        ranked,
        key=lambda item: (item[1], sum(phrase_counts[item[0]]), item[0]),
        reverse=True,
    )


def _parse_word_count_filter(value: str) -> int | None:
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    if normalized not in {"1", "2", "3"}:
        raise RuntimeError("author-keyword-heatmap word_count must be all, 1, 2, or 3.")
    return int(normalized)


def _normalize_phrase(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _parse_utc_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"Invalid datetime value {value!r}.") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _floor_to_month(value: datetime) -> datetime:
    normalized = value.astimezone(UTC)
    return normalized.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(value: datetime, count: int) -> datetime:
    year = value.year
    month = value.month - 1 + count
    year += month // 12
    month = month % 12 + 1
    return value.replace(year=year, month=month, day=1)


def _build_month_series(start: datetime, end: datetime) -> list[datetime]:
    months: list[datetime] = []
    current = _floor_to_month(start)
    end_month = _floor_to_month(end)
    while current <= end_month:
        months.append(current)
        current = _add_months(current, 1)
    return months
