from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.raw_ingestion_artifact import RawIngestionArtifact
from app.models.tweet import Tweet
from app.models.tweet_reference import TweetReference
from app.models.user import User


@dataclass(slots=True)
class NormalizeArchivedUserRequest:
    username: str
    dry_run: bool = False


@dataclass(slots=True)
class NormalizeArchivedUserSummary:
    username: str
    target_platform_user_id: str
    users_upserted: int
    tweets_upserted: int
    references_inserted: int
    raw_user_artifacts_matched: int
    raw_tweet_artifacts_scanned: int
    raw_distinct_tweets: int
    raw_first_tweet_at: datetime | None
    raw_last_tweet_at: datetime | None
    normalized_user_id: int | None
    normalized_tweet_count: int
    normalized_first_tweet_at: datetime | None
    normalized_last_tweet_at: datetime | None
    dry_run: bool
    notes: str


@dataclass(slots=True)
class UserSnapshot:
    platform_user_id: str
    username: str
    display_name: str | None = None
    profile_url: str | None = None
    description: str | None = None
    location: str | None = None
    follower_count: int | None = None
    following_count: int | None = None
    favourites_count: int | None = None
    media_count: int | None = None
    statuses_count: int | None = None
    created_at_platform: datetime | None = None
    is_verified: bool = False
    is_blue_verified: bool = False
    profile_image_url: str | None = None
    banner_image_url: str | None = None
    last_ingested_at: datetime | None = None
    last_tweet_seen_at: datetime | None = None


@dataclass(slots=True)
class TweetReferenceSnapshot:
    reference_type: str
    referenced_tweet_platform_id: str
    referenced_user_platform_id: str | None = None


@dataclass(slots=True)
class TweetSnapshot:
    platform_tweet_id: str
    author_platform_user_id: str
    url: str | None
    text: str
    source: str | None
    created_at_platform: datetime
    language: str | None
    conversation_id_platform: str | None
    in_reply_to_platform_tweet_id: str | None
    quoted_platform_tweet_id: str | None
    like_count: int | None
    reply_count: int | None
    repost_count: int | None
    quote_count: int | None
    bookmark_count: int | None
    impression_count: int | None
    references: list[TweetReferenceSnapshot] = field(default_factory=list)


def normalize_archived_user(
    request: NormalizeArchivedUserRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> NormalizeArchivedUserSummary:
    username_key = request.username.strip().casefold()
    if not username_key:
        raise RuntimeError("normalize_archived_user requires a non-empty username.")

    session = session_factory()
    try:
        artifacts = session.execute(
            _build_archived_artifact_query(session, username_key=username_key)
        ).all()

        user_snapshots: dict[str, UserSnapshot] = {}
        tweet_snapshots: dict[str, TweetSnapshot] = {}
        raw_user_artifacts_matched = 0
        raw_tweet_artifacts_scanned = 0
        raw_first_tweet_at: datetime | None = None
        raw_last_tweet_at: datetime | None = None
        target_platform_user_id: str | None = None

        for artifact, _run in artifacts:
            if artifact.artifact_type == "user_info":
                user_payload = _extract_user_info_payload(artifact.payload_json)
                if user_payload is None:
                    continue
                if _normalize_username(_coerce_string(user_payload.get("userName"))) != username_key:
                    continue

                raw_user_artifacts_matched += 1
                snapshot = _build_user_snapshot_from_user_info(
                    user_payload,
                    observed_at=artifact.created_at,
                )
                _merge_user_snapshot(user_snapshots, snapshot)
                target_platform_user_id = snapshot.platform_user_id
                continue

            tweets = _extract_search_tweets(artifact.payload_json)
            if tweets is None:
                continue

            raw_tweet_artifacts_scanned += 1
            for tweet_payload in tweets:
                if not isinstance(tweet_payload, dict):
                    continue

                author_payload = tweet_payload.get("author")
                if not isinstance(author_payload, dict):
                    continue

                if _normalize_username(_coerce_string(author_payload.get("userName"))) != username_key:
                    continue

                author_snapshot = _build_user_snapshot_from_tweet_author(
                    author_payload,
                    observed_at=artifact.created_at,
                    tweet_created_at=_parse_platform_datetime(tweet_payload.get("createdAt")),
                )
                _merge_user_snapshot(user_snapshots, author_snapshot)
                target_platform_user_id = author_snapshot.platform_user_id

                quoted_tweet_payload = tweet_payload.get("quoted_tweet")
                if isinstance(quoted_tweet_payload, dict):
                    quoted_author_payload = quoted_tweet_payload.get("author")
                    if isinstance(quoted_author_payload, dict) and _can_build_user_snapshot(
                        quoted_author_payload
                    ):
                        _merge_user_snapshot(
                            user_snapshots,
                            _build_user_snapshot_from_tweet_author(
                                quoted_author_payload,
                                observed_at=artifact.created_at,
                                tweet_created_at=_parse_platform_datetime(
                                    quoted_tweet_payload.get("createdAt")
                                ),
                            ),
                        )

                snapshot = _build_tweet_snapshot(tweet_payload)
                existing_snapshot = tweet_snapshots.get(snapshot.platform_tweet_id)
                tweet_snapshots[snapshot.platform_tweet_id] = _merge_tweet_snapshot(
                    existing_snapshot,
                    snapshot,
                )

                raw_first_tweet_at = _min_datetime(raw_first_tweet_at, snapshot.created_at_platform)
                raw_last_tweet_at = _max_datetime(raw_last_tweet_at, snapshot.created_at_platform)

        if not tweet_snapshots:
            raise RuntimeError(
                f"No archived advanced_search tweets were found for username={request.username!r}."
            )
        if target_platform_user_id is None:
            raise RuntimeError(
                f"Unable to resolve a platform user id from archived artifacts for {request.username!r}."
            )

        if request.dry_run:
            notes = (
                "Dry run completed. Canonical tables were not modified. "
                f"Prepared {len(user_snapshots)} users, {len(tweet_snapshots)} tweets, and "
                f"{sum(len(tweet.references) for tweet in tweet_snapshots.values())} references."
            )
            return NormalizeArchivedUserSummary(
                username=request.username,
                target_platform_user_id=target_platform_user_id,
                users_upserted=len(user_snapshots),
                tweets_upserted=len(tweet_snapshots),
                references_inserted=sum(len(tweet.references) for tweet in tweet_snapshots.values()),
                raw_user_artifacts_matched=raw_user_artifacts_matched,
                raw_tweet_artifacts_scanned=raw_tweet_artifacts_scanned,
                raw_distinct_tweets=len(tweet_snapshots),
                raw_first_tweet_at=raw_first_tweet_at,
                raw_last_tweet_at=raw_last_tweet_at,
                normalized_user_id=None,
                normalized_tweet_count=0,
                normalized_first_tweet_at=None,
                normalized_last_tweet_at=None,
                dry_run=True,
                notes=notes,
            )

        _upsert_users(session, list(user_snapshots.values()))
        user_id_by_platform_id = _load_user_id_map(session, list(user_snapshots.keys()))
        if target_platform_user_id not in user_id_by_platform_id:
            raise RuntimeError(
                f"Canonical user row was not available after upsert for {target_platform_user_id}."
            )

        _upsert_tweets(session, list(tweet_snapshots.values()), user_id_by_platform_id)
        tweet_id_by_platform_id = _load_tweet_id_map(session, list(tweet_snapshots.keys()))
        _replace_tweet_references(
            session,
            tweet_snapshots=list(tweet_snapshots.values()),
            tweet_id_by_platform_id=tweet_id_by_platform_id,
        )
        session.commit()

        normalized_user_id = user_id_by_platform_id[target_platform_user_id]
        normalized_tweet_count, normalized_first_tweet_at, normalized_last_tweet_at = (
            session.execute(
                select(
                    func.count(Tweet.id),
                    func.min(Tweet.created_at_platform),
                    func.max(Tweet.created_at_platform),
                ).where(Tweet.author_user_id == normalized_user_id)
            ).one()
        )

        notes = (
            "Normalization completed. "
            f"Raw distinct tweets={len(tweet_snapshots)}; normalized tweets={normalized_tweet_count}."
        )
        return NormalizeArchivedUserSummary(
            username=request.username,
            target_platform_user_id=target_platform_user_id,
            users_upserted=len(user_snapshots),
            tweets_upserted=len(tweet_snapshots),
            references_inserted=sum(len(tweet.references) for tweet in tweet_snapshots.values()),
            raw_user_artifacts_matched=raw_user_artifacts_matched,
            raw_tweet_artifacts_scanned=raw_tweet_artifacts_scanned,
            raw_distinct_tweets=len(tweet_snapshots),
            raw_first_tweet_at=raw_first_tweet_at,
            raw_last_tweet_at=raw_last_tweet_at,
            normalized_user_id=normalized_user_id,
            normalized_tweet_count=normalized_tweet_count,
            normalized_first_tweet_at=normalized_first_tweet_at,
            normalized_last_tweet_at=normalized_last_tweet_at,
            dry_run=False,
            notes=notes,
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _extract_user_info_payload(payload_json: dict[str, Any]) -> dict[str, Any] | None:
    response_payload = payload_json.get("response")
    if not isinstance(response_payload, dict):
        return None
    data = response_payload.get("data")
    if not isinstance(data, dict):
        return None
    return data


def _extract_search_tweets(payload_json: dict[str, Any]) -> list[dict[str, Any]] | None:
    response_payload = payload_json.get("response")
    if not isinstance(response_payload, dict):
        return None

    tweets = response_payload.get("tweets")
    if isinstance(tweets, list):
        return [item for item in tweets if isinstance(item, dict)]

    data = response_payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("tweets"), list):
        return [item for item in data["tweets"] if isinstance(item, dict)]

    return None


def _build_archived_artifact_query(
    session: Session,
    *,
    username_key: str,
) -> object:
    target_platform_user_id = session.scalar(
        select(User.platform_user_id).where(func.lower(User.username) == username_key)
    )
    username_notes_like = _build_ingestion_notes_username_like(username_key)
    advanced_search_notes_like = _build_advanced_search_notes_username_like(username_key)

    query = (
        select(RawIngestionArtifact, IngestionRun)
        .join(IngestionRun, IngestionRun.id == RawIngestionArtifact.ingestion_run_id)
        .where(
            (RawIngestionArtifact.artifact_type == "user_info")
            | (RawIngestionArtifact.artifact_type.like("tweet_advanced_search_page%"))
        )
    )
    if target_platform_user_id:
        query = query.where(
            or_(
                IngestionRun.target_user_platform_id == target_platform_user_id,
                func.lower(IngestionRun.notes).like(username_notes_like),
                func.lower(IngestionRun.notes).like(advanced_search_notes_like),
            )
        )
    else:
        query = query.where(
            or_(
                func.lower(IngestionRun.notes).like(username_notes_like),
                func.lower(IngestionRun.notes).like(advanced_search_notes_like),
            )
        )

    return query.order_by(RawIngestionArtifact.id.asc())


def _build_ingestion_notes_username_like(username_key: str) -> str:
    return f"username={username_key};%"


def _build_advanced_search_notes_username_like(username_key: str) -> str:
    return f"%query 'from:{username_key}%since:%"


def _build_user_snapshot_from_user_info(
    payload: dict[str, Any],
    *,
    observed_at: datetime,
) -> UserSnapshot:
    return UserSnapshot(
        platform_user_id=_require_string(payload, "id", context="user info"),
        username=_require_string(payload, "userName", context="user info"),
        display_name=_coerce_string(payload.get("name")),
        description=_coerce_string(payload.get("description")),
        location=_coerce_string(payload.get("location")),
        follower_count=_coerce_int(payload.get("followers")),
        following_count=_coerce_int(payload.get("following")),
        favourites_count=_coerce_int(payload.get("favouritesCount")),
        media_count=_coerce_int(payload.get("mediaCount")),
        statuses_count=_coerce_int(payload.get("statusesCount")),
        created_at_platform=_parse_platform_datetime(payload.get("createdAt")),
        is_verified=bool(payload.get("isVerified")),
        is_blue_verified=bool(payload.get("isBlueVerified")),
        profile_image_url=_coerce_string(payload.get("profilePicture")),
        banner_image_url=_coerce_string(payload.get("coverPicture")),
        last_ingested_at=observed_at,
    )


def _build_user_snapshot_from_tweet_author(
    payload: dict[str, Any],
    *,
    observed_at: datetime,
    tweet_created_at: datetime | None,
) -> UserSnapshot:
    profile_url = _coerce_string(payload.get("url"))
    if profile_url is None or "/status/" in profile_url:
        profile_url = _coerce_string(payload.get("twitterUrl"))

    return UserSnapshot(
        platform_user_id=_require_string(payload, "id", context="tweet author"),
        username=_require_string(payload, "userName", context="tweet author"),
        display_name=_coerce_string(payload.get("name")),
        profile_url=profile_url,
        description=_coerce_string(payload.get("description")),
        location=_coerce_string(payload.get("location")),
        follower_count=_coerce_int(payload.get("followers")),
        following_count=_coerce_int(payload.get("following")),
        favourites_count=_coerce_int(payload.get("favouritesCount")),
        media_count=_coerce_int(payload.get("mediaCount")),
        statuses_count=_coerce_int(payload.get("statusesCount")),
        created_at_platform=_parse_platform_datetime(payload.get("createdAt")),
        is_verified=bool(payload.get("isVerified")),
        is_blue_verified=bool(payload.get("isBlueVerified")),
        profile_image_url=_coerce_string(payload.get("profilePicture")),
        banner_image_url=_coerce_string(payload.get("coverPicture")),
        last_ingested_at=observed_at,
        last_tweet_seen_at=tweet_created_at,
    )


def _merge_user_snapshot(
    snapshots: dict[str, UserSnapshot],
    snapshot: UserSnapshot,
) -> None:
    existing = snapshots.get(snapshot.platform_user_id)
    if existing is None:
        snapshots[snapshot.platform_user_id] = snapshot
        return

    existing.username = _prefer_string(snapshot.username, existing.username) or existing.username
    existing.display_name = _prefer_string(snapshot.display_name, existing.display_name)
    existing.profile_url = _prefer_string(snapshot.profile_url, existing.profile_url)
    existing.description = _prefer_string(snapshot.description, existing.description)
    existing.location = _prefer_string(snapshot.location, existing.location)
    existing.follower_count = _prefer_value(snapshot.follower_count, existing.follower_count)
    existing.following_count = _prefer_value(snapshot.following_count, existing.following_count)
    existing.favourites_count = _prefer_value(
        snapshot.favourites_count,
        existing.favourites_count,
    )
    existing.media_count = _prefer_value(snapshot.media_count, existing.media_count)
    existing.statuses_count = _prefer_value(snapshot.statuses_count, existing.statuses_count)
    existing.created_at_platform = _prefer_value(
        snapshot.created_at_platform,
        existing.created_at_platform,
    )
    existing.is_verified = snapshot.is_verified or existing.is_verified
    existing.is_blue_verified = snapshot.is_blue_verified or existing.is_blue_verified
    existing.profile_image_url = _prefer_string(
        snapshot.profile_image_url,
        existing.profile_image_url,
    )
    existing.banner_image_url = _prefer_string(snapshot.banner_image_url, existing.banner_image_url)
    existing.last_ingested_at = _max_datetime(existing.last_ingested_at, snapshot.last_ingested_at)
    existing.last_tweet_seen_at = _max_datetime(
        existing.last_tweet_seen_at,
        snapshot.last_tweet_seen_at,
    )


def _build_tweet_snapshot(payload: dict[str, Any]) -> TweetSnapshot:
    platform_tweet_id = _require_string(payload, "id", context="tweet")
    author_payload = payload.get("author")
    if not isinstance(author_payload, dict):
        raise RuntimeError(f"Tweet {platform_tweet_id} did not include an author object.")

    quoted_tweet_payload = payload.get("quoted_tweet")
    quoted_tweet_id = None
    quoted_user_id = None
    if isinstance(quoted_tweet_payload, dict):
        quoted_tweet_id = _coerce_string(quoted_tweet_payload.get("id"))
        quoted_author_payload = quoted_tweet_payload.get("author")
        if isinstance(quoted_author_payload, dict):
            quoted_user_id = _coerce_string(quoted_author_payload.get("id"))

    retweeted_tweet_payload = payload.get("retweeted_tweet")
    retweeted_tweet_id = None
    retweeted_user_id = None
    if isinstance(retweeted_tweet_payload, dict):
        retweeted_tweet_id = _coerce_string(retweeted_tweet_payload.get("id"))
        retweeted_author_payload = retweeted_tweet_payload.get("author")
        if isinstance(retweeted_author_payload, dict):
            retweeted_user_id = _coerce_string(retweeted_author_payload.get("id"))

    references: list[TweetReferenceSnapshot] = []
    in_reply_to_id = _coerce_string(payload.get("inReplyToId"))
    if in_reply_to_id is not None:
        references.append(
            TweetReferenceSnapshot(
                reference_type="replied_to",
                referenced_tweet_platform_id=in_reply_to_id,
                referenced_user_platform_id=_coerce_string(payload.get("inReplyToUserId")),
            )
        )
    if quoted_tweet_id is not None:
        references.append(
            TweetReferenceSnapshot(
                reference_type="quoted",
                referenced_tweet_platform_id=quoted_tweet_id,
                referenced_user_platform_id=quoted_user_id,
            )
        )
    if retweeted_tweet_id is not None:
        references.append(
            TweetReferenceSnapshot(
                reference_type="retweeted",
                referenced_tweet_platform_id=retweeted_tweet_id,
                referenced_user_platform_id=retweeted_user_id,
            )
        )

    return TweetSnapshot(
        platform_tweet_id=platform_tweet_id,
        author_platform_user_id=_require_string(author_payload, "id", context=f"tweet {platform_tweet_id} author"),
        url=_prefer_string(
            _coerce_string(payload.get("url")),
            _coerce_string(payload.get("twitterUrl")),
        ),
        text=_coerce_string(payload.get("text"), allow_empty=True) or "",
        source=_coerce_string(payload.get("source")),
        created_at_platform=_require_datetime(payload.get("createdAt"), context=f"tweet {platform_tweet_id}"),
        language=_coerce_string(payload.get("lang")),
        conversation_id_platform=_coerce_string(payload.get("conversationId")),
        in_reply_to_platform_tweet_id=in_reply_to_id,
        quoted_platform_tweet_id=quoted_tweet_id,
        like_count=_coerce_int(payload.get("likeCount")),
        reply_count=_coerce_int(payload.get("replyCount")),
        repost_count=_coerce_int(payload.get("retweetCount")),
        quote_count=_coerce_int(payload.get("quoteCount")),
        bookmark_count=_coerce_int(payload.get("bookmarkCount")),
        impression_count=_coerce_int(payload.get("viewCount")),
        references=references,
    )


def _merge_tweet_snapshot(
    existing: TweetSnapshot | None,
    incoming: TweetSnapshot,
) -> TweetSnapshot:
    if existing is None:
        return incoming

    existing.url = _prefer_string(incoming.url, existing.url)
    existing.text = incoming.text if incoming.text != "" else existing.text
    existing.source = _prefer_string(incoming.source, existing.source)
    existing.created_at_platform = incoming.created_at_platform
    existing.language = _prefer_string(incoming.language, existing.language)
    existing.conversation_id_platform = _prefer_string(
        incoming.conversation_id_platform,
        existing.conversation_id_platform,
    )
    existing.in_reply_to_platform_tweet_id = _prefer_string(
        incoming.in_reply_to_platform_tweet_id,
        existing.in_reply_to_platform_tweet_id,
    )
    existing.quoted_platform_tweet_id = _prefer_string(
        incoming.quoted_platform_tweet_id,
        existing.quoted_platform_tweet_id,
    )
    existing.like_count = _prefer_value(incoming.like_count, existing.like_count)
    existing.reply_count = _prefer_value(incoming.reply_count, existing.reply_count)
    existing.repost_count = _prefer_value(incoming.repost_count, existing.repost_count)
    existing.quote_count = _prefer_value(incoming.quote_count, existing.quote_count)
    existing.bookmark_count = _prefer_value(incoming.bookmark_count, existing.bookmark_count)
    existing.impression_count = _prefer_value(incoming.impression_count, existing.impression_count)
    existing.references = _merge_references(existing.references, incoming.references)
    return existing


def _upsert_users(session: Session, snapshots: list[UserSnapshot]) -> None:
    if not snapshots:
        return

    for chunk in _chunked(
        [
            {
                "platform_user_id": snapshot.platform_user_id,
                "username": snapshot.username,
                "display_name": snapshot.display_name,
                "profile_url": snapshot.profile_url,
                "description": snapshot.description,
                "location": snapshot.location,
                "follower_count": snapshot.follower_count,
                "following_count": snapshot.following_count,
                "favourites_count": snapshot.favourites_count,
                "media_count": snapshot.media_count,
                "statuses_count": snapshot.statuses_count,
                "created_at_platform": snapshot.created_at_platform,
                "is_verified": snapshot.is_verified,
                "is_blue_verified": snapshot.is_blue_verified,
                "profile_image_url": snapshot.profile_image_url,
                "banner_image_url": snapshot.banner_image_url,
                "last_ingested_at": snapshot.last_ingested_at,
                "last_tweet_seen_at": snapshot.last_tweet_seen_at,
            }
            for snapshot in snapshots
        ],
        size=500,
    ):
        insert_stmt = insert(User).values(chunk)
        session.execute(
            insert_stmt.on_conflict_do_update(
                index_elements=[User.platform_user_id],
                set_={
                    "username": insert_stmt.excluded.username,
                    "display_name": insert_stmt.excluded.display_name,
                    "profile_url": insert_stmt.excluded.profile_url,
                    "description": insert_stmt.excluded.description,
                    "location": insert_stmt.excluded.location,
                    "follower_count": insert_stmt.excluded.follower_count,
                    "following_count": insert_stmt.excluded.following_count,
                    "favourites_count": insert_stmt.excluded.favourites_count,
                    "media_count": insert_stmt.excluded.media_count,
                    "statuses_count": insert_stmt.excluded.statuses_count,
                    "created_at_platform": insert_stmt.excluded.created_at_platform,
                    "is_verified": insert_stmt.excluded.is_verified,
                    "is_blue_verified": insert_stmt.excluded.is_blue_verified,
                    "profile_image_url": insert_stmt.excluded.profile_image_url,
                    "banner_image_url": insert_stmt.excluded.banner_image_url,
                    "last_ingested_at": insert_stmt.excluded.last_ingested_at,
                    "last_tweet_seen_at": insert_stmt.excluded.last_tweet_seen_at,
                    "updated_at": func.now(),
                },
            )
        )


def _load_user_id_map(session: Session, platform_user_ids: list[str]) -> dict[str, int]:
    return _load_platform_id_map(
        session,
        platform_ids=platform_user_ids,
        platform_id_column=User.platform_user_id,
        id_column=User.id,
    )


def _upsert_tweets(
    session: Session,
    snapshots: list[TweetSnapshot],
    user_id_by_platform_id: dict[str, int],
) -> None:
    rows = []
    for snapshot in snapshots:
        author_user_id = user_id_by_platform_id.get(snapshot.author_platform_user_id)
        if author_user_id is None:
            raise RuntimeError(
                f"Missing canonical user row for author {snapshot.author_platform_user_id}."
            )
        rows.append(
            {
                "platform_tweet_id": snapshot.platform_tweet_id,
                "author_user_id": author_user_id,
                "url": snapshot.url,
                "text": snapshot.text,
                "source": snapshot.source,
                "created_at_platform": snapshot.created_at_platform,
                "language": snapshot.language,
                "conversation_id_platform": snapshot.conversation_id_platform,
                "in_reply_to_platform_tweet_id": snapshot.in_reply_to_platform_tweet_id,
                "quoted_platform_tweet_id": snapshot.quoted_platform_tweet_id,
                "like_count": snapshot.like_count,
                "reply_count": snapshot.reply_count,
                "repost_count": snapshot.repost_count,
                "quote_count": snapshot.quote_count,
                "bookmark_count": snapshot.bookmark_count,
                "impression_count": snapshot.impression_count,
            }
        )

    for chunk in _chunked(rows, size=500):
        insert_stmt = insert(Tweet).values(chunk)
        session.execute(
            insert_stmt.on_conflict_do_update(
                index_elements=[Tweet.platform_tweet_id],
                set_={
                    "author_user_id": insert_stmt.excluded.author_user_id,
                    "url": insert_stmt.excluded.url,
                    "text": insert_stmt.excluded.text,
                    "source": insert_stmt.excluded.source,
                    "created_at_platform": insert_stmt.excluded.created_at_platform,
                    "language": insert_stmt.excluded.language,
                    "conversation_id_platform": insert_stmt.excluded.conversation_id_platform,
                    "in_reply_to_platform_tweet_id": insert_stmt.excluded.in_reply_to_platform_tweet_id,
                    "quoted_platform_tweet_id": insert_stmt.excluded.quoted_platform_tweet_id,
                    "like_count": insert_stmt.excluded.like_count,
                    "reply_count": insert_stmt.excluded.reply_count,
                    "repost_count": insert_stmt.excluded.repost_count,
                    "quote_count": insert_stmt.excluded.quote_count,
                    "bookmark_count": insert_stmt.excluded.bookmark_count,
                    "impression_count": insert_stmt.excluded.impression_count,
                    "updated_at": func.now(),
                },
            )
        )


def _load_tweet_id_map(session: Session, platform_tweet_ids: list[str]) -> dict[str, int]:
    return _load_platform_id_map(
        session,
        platform_ids=platform_tweet_ids,
        platform_id_column=Tweet.platform_tweet_id,
        id_column=Tweet.id,
    )


def _load_platform_id_map(
    session: Session,
    *,
    platform_ids: list[str],
    platform_id_column,
    id_column,
) -> dict[str, int]:
    # Large backfills can exceed PostgreSQL's bind-parameter ceiling if we query all ids at once.
    loaded: dict[str, int] = {}
    for chunk in _chunked(platform_ids, size=1000):
        if not chunk:
            continue
        rows = session.execute(
            select(platform_id_column, id_column).where(platform_id_column.in_(chunk))
        ).all()
        loaded.update({platform_id: row_id for platform_id, row_id in rows})
    return loaded


def _replace_tweet_references(
    session: Session,
    *,
    tweet_snapshots: list[TweetSnapshot],
    tweet_id_by_platform_id: dict[str, int],
) -> None:
    touched_tweet_ids = [
        tweet_id_by_platform_id[snapshot.platform_tweet_id]
        for snapshot in tweet_snapshots
        if snapshot.platform_tweet_id in tweet_id_by_platform_id
    ]
    for chunk in _chunked(touched_tweet_ids, size=1000):
        session.execute(delete(TweetReference).where(TweetReference.tweet_id.in_(chunk)))

    rows = []
    for snapshot in tweet_snapshots:
        tweet_id = tweet_id_by_platform_id.get(snapshot.platform_tweet_id)
        if tweet_id is None:
            raise RuntimeError(
                f"Missing canonical tweet row for platform_tweet_id={snapshot.platform_tweet_id}."
            )
        for reference in snapshot.references:
            rows.append(
                {
                    "tweet_id": tweet_id,
                    "referenced_tweet_platform_id": reference.referenced_tweet_platform_id,
                    "reference_type": reference.reference_type,
                    "referenced_user_platform_id": reference.referenced_user_platform_id,
                }
            )

    for chunk in _chunked(rows, size=1000):
        session.execute(insert(TweetReference).values(chunk))


def _chunked(values: list[Any], *, size: int) -> list[list[Any]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _merge_references(
    existing: list[TweetReferenceSnapshot],
    incoming: list[TweetReferenceSnapshot],
) -> list[TweetReferenceSnapshot]:
    merged: dict[tuple[str, str], TweetReferenceSnapshot] = {}
    for reference in existing + incoming:
        key = (reference.reference_type, reference.referenced_tweet_platform_id)
        current = merged.get(key)
        if current is None:
            merged[key] = reference
            continue
        if current.referenced_user_platform_id is None and reference.referenced_user_platform_id is not None:
            current.referenced_user_platform_id = reference.referenced_user_platform_id
    return list(merged.values())


def _can_build_user_snapshot(payload: dict[str, Any]) -> bool:
    return _coerce_string(payload.get("id")) is not None and _coerce_string(payload.get("userName")) is not None


def _require_string(payload: dict[str, Any], key: str, *, context: str) -> str:
    value = _coerce_string(payload.get(key))
    if value is None:
        raise RuntimeError(f"Missing required string {key!r} in {context}.")
    return value


def _require_datetime(value: Any, *, context: str) -> datetime:
    parsed = _parse_platform_datetime(value)
    if parsed is None:
        raise RuntimeError(f"Missing or invalid datetime in {context}.")
    return parsed


def _coerce_string(value: Any, *, allow_empty: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized == "" and not allow_empty:
        return None
    return normalized


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _parse_platform_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if normalized == "":
        return None
    if normalized.endswith("Z"):
        iso_value = normalized[:-1] + "+00:00"
        return datetime.fromisoformat(iso_value).astimezone(UTC)
    try:
        return datetime.strptime(normalized, "%a %b %d %H:%M:%S %z %Y").astimezone(UTC)
    except ValueError:
        return datetime.fromisoformat(normalized).astimezone(UTC)


def _normalize_username(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    return normalized.casefold()


def _prefer_string(new_value: str | None, existing_value: str | None) -> str | None:
    return new_value if new_value not in (None, "") else existing_value


def _prefer_value(new_value: Any, existing_value: Any) -> Any:
    return new_value if new_value is not None else existing_value


def _min_datetime(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return min(current, candidate)


def _max_datetime(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return max(current, candidate)
