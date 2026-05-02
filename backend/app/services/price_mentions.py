from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.tweet_price_mention import TweetPriceMention
from app.models.tweet_reference import TweetReference
from app.models.user import User
from app.services.price_mention_extractor import (
    DEFAULT_EXTRACTOR_KEY,
    DEFAULT_EXTRACTOR_VERSION,
    extract_mentions_from_text,
)


DEFAULT_PRICE_MENTION_EXTRACTOR_KEY = DEFAULT_EXTRACTOR_KEY
DEFAULT_PRICE_MENTION_EXTRACTOR_VERSION = DEFAULT_EXTRACTOR_VERSION
DEFAULT_PRICE_MENTION_ANALYSIS_START = "2020-08-01T00:00:00Z"


@dataclass(slots=True)
class ExtractTweetPriceMentionsRequest:
    usernames: list[str]
    analysis_start: str = DEFAULT_PRICE_MENTION_ANALYSIS_START
    extractor_key: str = DEFAULT_PRICE_MENTION_EXTRACTOR_KEY
    extractor_version: str = DEFAULT_PRICE_MENTION_EXTRACTOR_VERSION
    only_missing_tweets: bool = False
    overwrite_existing: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class ExtractTweetPriceMentionsSummary:
    usernames_requested: list[str]
    usernames_matched: list[str]
    extractor_key: str
    extractor_version: str
    tweets_considered: int
    retweets_excluded: int
    before_analysis_start: int
    tweets_with_mentions: int
    candidates_found: int
    rows_written: int
    by_type: dict[str, int]
    by_confidence_band: dict[str, int]
    dry_run: bool
    notes: str


def extract_tweet_price_mentions(
    request: ExtractTweetPriceMentionsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> ExtractTweetPriceMentionsSummary:
    normalized_usernames = [u.strip().lower() for u in request.usernames if u.strip()]
    if not normalized_usernames:
        raise RuntimeError("extract_tweet_price_mentions requires at least one username.")

    analysis_start = _parse_utc_datetime(request.analysis_start)
    session = session_factory()
    try:
        matched_users = session.execute(
            select(User.id, User.username)
            .where(func.lower(User.username).in_(normalized_usernames))
            .order_by(User.username.asc())
        ).all()
        if not matched_users:
            raise RuntimeError(
                f"No canonical users found for usernames={sorted(normalized_usernames)!r}."
            )

        matched_user_ids = [uid for uid, _ in matched_users]
        matched_usernames = [uname for _, uname in matched_users]

        if request.overwrite_existing and not request.dry_run:
            session.execute(
                delete(TweetPriceMention).where(
                    TweetPriceMention.extractor_key == request.extractor_key,
                    TweetPriceMention.extractor_version == request.extractor_version,
                    TweetPriceMention.tweet_id.in_(
                        select(Tweet.id).where(
                            Tweet.author_user_id.in_(matched_user_ids),
                            Tweet.created_at_platform >= analysis_start,
                        )
                    ),
                )
            )
            session.commit()

        # Subquery: retweet tweet IDs to exclude
        retweet_ids_sq = (
            select(TweetReference.tweet_id)
            .where(TweetReference.reference_type == "retweeted")
            .subquery()
        )

        tweet_query = (
            select(Tweet.id, Tweet.text, Tweet.author_user_id)
            .where(
                Tweet.author_user_id.in_(matched_user_ids),
                Tweet.created_at_platform >= analysis_start,
                Tweet.id.not_in(select(retweet_ids_sq.c.tweet_id)),
            )
        )

        if request.only_missing_tweets and not request.overwrite_existing:
            processed_tweet_ids = (
                select(TweetPriceMention.tweet_id)
                .where(
                    TweetPriceMention.extractor_key == request.extractor_key,
                    TweetPriceMention.extractor_version == request.extractor_version,
                )
                .group_by(TweetPriceMention.tweet_id)
                .subquery()
            )
            tweet_query = (
                tweet_query.outerjoin(
                    processed_tweet_ids,
                    processed_tweet_ids.c.tweet_id == Tweet.id,
                ).where(processed_tweet_ids.c.tweet_id.is_(None))
            )

        tweet_rows = session.execute(
            tweet_query.order_by(
                Tweet.author_user_id.asc(),
                Tweet.created_at_platform.asc(),
                Tweet.id.asc(),
            )
        ).all()

        prepared_rows: list[dict] = []
        tweets_with_mentions = 0
        by_type: dict[str, int] = {
            "prediction": 0,
            "conditional": 0,
            "current": 0,
            "historical": 0,
            "unclassified": 0,
        }
        by_band: dict[str, int] = {"high": 0, "medium": 0, "low": 0}

        for tweet_id, text, user_id in tweet_rows:
            candidates = extract_mentions_from_text(text or "")
            if candidates:
                tweets_with_mentions += 1
            for c in candidates:
                prepared_rows.append(
                    {
                        "tweet_id": tweet_id,
                        "user_id": user_id,
                        "price_usd": c.price_usd,
                        "mention_type": c.mention_type,
                        "confidence": c.confidence,
                        "raw_fragment": c.raw_fragment,
                        "extractor_key": request.extractor_key,
                        "extractor_version": request.extractor_version,
                    }
                )
                by_type[c.mention_type] = by_type.get(c.mention_type, 0) + 1
                if c.confidence >= 0.80:
                    by_band["high"] += 1
                elif c.confidence >= 0.50:
                    by_band["medium"] += 1
                else:
                    by_band["low"] += 1

        if request.dry_run:
            return ExtractTweetPriceMentionsSummary(
                usernames_requested=sorted(normalized_usernames),
                usernames_matched=matched_usernames,
                extractor_key=request.extractor_key,
                extractor_version=request.extractor_version,
                tweets_considered=len(tweet_rows),
                retweets_excluded=0,  # not counted separately in this query path
                before_analysis_start=0,
                tweets_with_mentions=tweets_with_mentions,
                candidates_found=len(prepared_rows),
                rows_written=0,
                by_type=by_type,
                by_confidence_band=by_band,
                dry_run=True,
                notes="Dry run completed. No rows were written.",
            )

        for chunk in _chunked(prepared_rows, size=2000):
            if not chunk:
                continue
            stmt = insert(TweetPriceMention).values(chunk)
            session.execute(
                stmt.on_conflict_do_nothing(constraint="uq_tweet_price_mentions_dedup")
            )

        session.commit()

        rows_written = session.scalar(
            select(func.count())
            .select_from(TweetPriceMention)
            .where(
                TweetPriceMention.user_id.in_(matched_user_ids),
                TweetPriceMention.extractor_key == request.extractor_key,
                TweetPriceMention.extractor_version == request.extractor_version,
            )
        ) or 0

        return ExtractTweetPriceMentionsSummary(
            usernames_requested=sorted(normalized_usernames),
            usernames_matched=matched_usernames,
            extractor_key=request.extractor_key,
            extractor_version=request.extractor_version,
            tweets_considered=len(tweet_rows),
            retweets_excluded=0,
            before_analysis_start=0,
            tweets_with_mentions=tweets_with_mentions,
            candidates_found=len(prepared_rows),
            rows_written=rows_written,
            by_type=by_type,
            by_confidence_band=by_band,
            dry_run=False,
            notes="Price mention extraction completed.",
        )
    finally:
        session.close()


def _parse_utc_datetime(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)


def _chunked(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
