from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.managed_author_view import ManagedAuthorView
from app.models.tweet import Tweet
from app.models.tweet_keyword import TweetKeyword
from app.models.tweet_mood_score import TweetMoodScore
from app.models.user import User
from app.services.keywords import (
    DEFAULT_KEYWORD_EXTRACTOR_KEY,
    DEFAULT_KEYWORD_EXTRACTOR_VERSION,
)
from app.services.moods import DEFAULT_MOOD_MODEL


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(slots=True)
class ManagedAuthorContext:
    user_id: int
    username: str
    slug: str
    overview_analysis_start: str | None
    mood_analysis_start: str | None
    heatmap_analysis_start: str | None


@dataclass(slots=True)
class UpdateManagedAuthorViewRequest:
    user_id: int
    slug: str | None = None
    published: bool | None = None
    sort_order: int | None = None
    enable_overview: bool | None = None
    enable_moods: bool | None = None
    enable_heatmap: bool | None = None
    enable_bitcoin_mentions: bool | None = None
    overview_analysis_start: str | None = None
    mood_analysis_start: str | None = None
    heatmap_analysis_start: str | None = None


@dataclass(slots=True)
class SyncManagedAuthorViewRequest:
    username: str
    published: bool = True
    ensure_analysis_starts: bool = True


def build_public_author_registry(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        rows = session.execute(
            select(ManagedAuthorView, User)
            .join(User, User.id == ManagedAuthorView.user_id)
            .where(ManagedAuthorView.published.is_(True))
            .order_by(
                ManagedAuthorView.sort_order.asc().nullslast(),
                func.lower(ManagedAuthorView.slug).asc(),
            )
        ).all()

        authors: list[dict[str, object]] = []
        overviews: list[dict[str, str]] = []
        moods: list[dict[str, str]] = []
        heatmaps: list[dict[str, str]] = []
        bitcoin_mentions: list[dict[str, str]] = []

        for mav, user in rows:
            readiness = _load_author_readiness(session, user_id=int(user.id))
            starts = _resolve_analysis_starts(session, managed_author_view=mav, user_id=int(user.id))

            author_payload = {
                "user_id": int(user.id),
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "slug": mav.slug,
                "published": bool(mav.published),
                "sort_order": mav.sort_order,
                "analysis_start": starts,
                "readiness": readiness,
                "views": {
                    "overview": {
                        "enabled": bool(mav.enable_overview),
                        "ready": readiness["overview_ready"],
                        "api_base_path": f"/api/views/authors/{mav.slug}/overview",
                    },
                    "moods": {
                        "enabled": bool(mav.enable_moods),
                        "ready": readiness["moods_ready"],
                        "api_base_path": f"/api/views/authors/{mav.slug}/moods",
                    },
                    "heatmap": {
                        "enabled": bool(mav.enable_heatmap),
                        "ready": readiness["heatmap_ready"],
                        "api_base_path": f"/api/views/authors/{mav.slug}/heatmap",
                    },
                    "bitcoin_mentions": {
                        "enabled": bool(mav.enable_bitcoin_mentions),
                        "ready": readiness["bitcoin_mentions_ready"],
                    },
                },
            }
            authors.append(author_payload)

            if bool(mav.enable_overview) and readiness["overview_ready"]:
                overviews.append(
                    {
                        "slug": mav.slug,
                        "username": user.username,
                        "api_base_path": f"/api/views/authors/{mav.slug}/overview",
                    }
                )
            if bool(mav.enable_moods) and readiness["moods_ready"]:
                moods.append(
                    {
                        "slug": mav.slug,
                        "username": user.username,
                        "api_base_path": f"/api/views/authors/{mav.slug}/moods",
                    }
                )
            if bool(mav.enable_heatmap) and readiness["heatmap_ready"]:
                heatmaps.append(
                    {
                        "slug": mav.slug,
                        "username": user.username,
                        "api_base_path": f"/api/views/authors/{mav.slug}/heatmap",
                    }
                )
            if bool(mav.enable_bitcoin_mentions) and readiness["bitcoin_mentions_ready"]:
                bitcoin_mentions.append(
                    {
                        "slug": mav.slug,
                        "username": user.username,
                    }
                )

        return {
            "view": "author-registry",
            "generated_at": _to_iso(datetime.now(UTC)),
            "authors": authors,
            "overviews": overviews,
            "moods": moods,
            "heatmaps": heatmaps,
            "bitcoin_mentions": bitcoin_mentions,
        }
    finally:
        session.close()


def build_admin_author_registry(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        rows = session.execute(
            select(ManagedAuthorView, User)
            .join(User, User.id == ManagedAuthorView.user_id)
            .order_by(
                ManagedAuthorView.sort_order.asc().nullslast(),
                func.lower(ManagedAuthorView.slug).asc(),
            )
        ).all()

        authors: list[dict[str, object]] = []
        for mav, user in rows:
            readiness = _load_author_readiness(session, user_id=int(user.id))
            starts = _resolve_analysis_starts(session, managed_author_view=mav, user_id=int(user.id))
            authors.append(
                {
                    "user_id": int(user.id),
                    "platform_user_id": user.platform_user_id,
                    "username": user.username,
                    "display_name": user.display_name,
                    "slug": mav.slug,
                    "published": bool(mav.published),
                    "sort_order": mav.sort_order,
                    "enable_overview": bool(mav.enable_overview),
                    "enable_moods": bool(mav.enable_moods),
                    "enable_heatmap": bool(mav.enable_heatmap),
                    "enable_bitcoin_mentions": bool(mav.enable_bitcoin_mentions),
                    "stored_analysis_start": {
                        "overview": _to_iso_nullable(mav.overview_analysis_start),
                        "moods": _to_iso_nullable(mav.mood_analysis_start),
                        "heatmap": _to_iso_nullable(mav.heatmap_analysis_start),
                    },
                    "analysis_start": starts,
                    "readiness": readiness,
                }
            )

        return {
            "view": "author-registry-admin",
            "generated_at": _to_iso(datetime.now(UTC)),
            "authors": authors,
        }
    finally:
        session.close()


def build_update_managed_author_view(
    request: UpdateManagedAuthorViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        managed_author = session.scalar(
            select(ManagedAuthorView).where(ManagedAuthorView.user_id == request.user_id)
        )
        if managed_author is None:
            raise RuntimeError(f"No managed author view exists for user_id={request.user_id}.")

        if request.slug is not None:
            normalized_slug = _normalize_slug(request.slug)
            _assert_slug_available(
                session,
                slug=normalized_slug,
                exclude_user_id=request.user_id,
            )
            managed_author.slug = normalized_slug

        if request.published is not None:
            managed_author.published = bool(request.published)
        if request.sort_order is not None:
            managed_author.sort_order = int(request.sort_order)
        if request.enable_overview is not None:
            managed_author.enable_overview = bool(request.enable_overview)
        if request.enable_moods is not None:
            managed_author.enable_moods = bool(request.enable_moods)
        if request.enable_heatmap is not None:
            managed_author.enable_heatmap = bool(request.enable_heatmap)
        if request.enable_bitcoin_mentions is not None:
            managed_author.enable_bitcoin_mentions = bool(request.enable_bitcoin_mentions)

        if request.overview_analysis_start is not None:
            managed_author.overview_analysis_start = _parse_optional_utc_datetime(
                request.overview_analysis_start
            )
        if request.mood_analysis_start is not None:
            managed_author.mood_analysis_start = _parse_optional_utc_datetime(
                request.mood_analysis_start
            )
        if request.heatmap_analysis_start is not None:
            managed_author.heatmap_analysis_start = _parse_optional_utc_datetime(
                request.heatmap_analysis_start
            )

        session.commit()
        session.refresh(managed_author)

        user = session.scalar(select(User).where(User.id == request.user_id))
        if user is None:
            raise RuntimeError(f"No canonical user exists for user_id={request.user_id}.")

        readiness = _load_author_readiness(session, user_id=int(user.id))
        starts = _resolve_analysis_starts(session, managed_author_view=managed_author, user_id=int(user.id))

        return {
            "view": "author-registry-update",
            "author": {
                "user_id": int(user.id),
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "slug": managed_author.slug,
                "published": bool(managed_author.published),
                "sort_order": managed_author.sort_order,
                "enable_overview": bool(managed_author.enable_overview),
                "enable_moods": bool(managed_author.enable_moods),
                "enable_heatmap": bool(managed_author.enable_heatmap),
                "enable_bitcoin_mentions": bool(managed_author.enable_bitcoin_mentions),
                "stored_analysis_start": {
                    "overview": _to_iso_nullable(managed_author.overview_analysis_start),
                    "moods": _to_iso_nullable(managed_author.mood_analysis_start),
                    "heatmap": _to_iso_nullable(managed_author.heatmap_analysis_start),
                },
                "analysis_start": starts,
                "readiness": readiness,
            },
        }
    finally:
        session.close()


def sync_managed_author_view_for_username(
    request: SyncManagedAuthorViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    normalized_username = request.username.strip()
    if not normalized_username:
        raise RuntimeError("sync_managed_author_view_for_username requires a username.")

    session = session_factory()
    try:
        user = session.scalar(
            select(User).where(func.lower(User.username) == normalized_username.lower())
        )
        if user is None:
            raise RuntimeError(f"No canonical user found for username={normalized_username!r}.")

        existing = session.scalar(
            select(ManagedAuthorView).where(ManagedAuthorView.user_id == user.id)
        )
        first_tweet_at = _load_first_tweet_at(session, user_id=int(user.id))

        created = False
        if existing is None:
            slug_base = _slug_base_from_user(user=user)
            slug = _generate_unique_slug(session, slug_base=slug_base)
            existing = ManagedAuthorView(
                user_id=user.id,
                slug=slug,
                published=request.published,
            )
            created = True
            session.add(existing)

        if request.ensure_analysis_starts:
            if existing.overview_analysis_start is None:
                existing.overview_analysis_start = first_tweet_at
            if existing.mood_analysis_start is None:
                existing.mood_analysis_start = first_tweet_at
            if existing.heatmap_analysis_start is None:
                existing.heatmap_analysis_start = first_tweet_at

        session.commit()
        session.refresh(existing)

        readiness = _load_author_readiness(session, user_id=int(user.id))
        starts = _resolve_analysis_starts(session, managed_author_view=existing, user_id=int(user.id))

        return {
            "view": "author-registry-sync",
            "created": created,
            "author": {
                "user_id": int(user.id),
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "slug": existing.slug,
                "published": bool(existing.published),
                "sort_order": existing.sort_order,
                "analysis_start": starts,
                "readiness": readiness,
            },
        }
    finally:
        session.close()


def resolve_managed_author_by_slug(
    slug: str,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    require_published: bool = False,
) -> ManagedAuthorContext:
    normalized_slug = _normalize_slug(slug)

    session = session_factory()
    try:
        query = (
            select(ManagedAuthorView, User)
            .join(User, User.id == ManagedAuthorView.user_id)
            .where(ManagedAuthorView.slug == normalized_slug)
        )
        if require_published:
            query = query.where(ManagedAuthorView.published.is_(True))

        row = session.execute(query).first()
        if row is None:
            raise RuntimeError(f"No managed author view found for slug={normalized_slug!r}.")
        managed_author, user = row

        starts = _resolve_analysis_starts(session, managed_author_view=managed_author, user_id=int(user.id))
        return ManagedAuthorContext(
            user_id=int(user.id),
            username=user.username,
            slug=managed_author.slug,
            overview_analysis_start=starts["overview"],
            mood_analysis_start=starts["moods"],
            heatmap_analysis_start=starts["heatmap"],
        )
    finally:
        session.close()


def _resolve_analysis_starts(
    session: Session,
    *,
    managed_author_view: ManagedAuthorView,
    user_id: int,
) -> dict[str, str | None]:
    default_start = _load_first_tweet_at(session, user_id=user_id)
    return {
        "overview": _to_iso_nullable(managed_author_view.overview_analysis_start or default_start),
        "moods": _to_iso_nullable(managed_author_view.mood_analysis_start or default_start),
        "heatmap": _to_iso_nullable(managed_author_view.heatmap_analysis_start or default_start),
    }


def _load_author_readiness(session: Session, *, user_id: int) -> dict[str, object]:
    tweet_count = int(
        session.scalar(select(func.count(Tweet.id)).where(Tweet.author_user_id == user_id)) or 0
    )
    mood_scored_tweet_count = int(
        session.scalar(
            select(func.count(func.distinct(TweetMoodScore.tweet_id)))
            .join(Tweet, Tweet.id == TweetMoodScore.tweet_id)
            .where(
                Tweet.author_user_id == user_id,
                TweetMoodScore.model_key == DEFAULT_MOOD_MODEL,
                TweetMoodScore.status == "scored",
            )
        )
        or 0
    )
    keyword_tweet_count = int(
        session.scalar(
            select(func.count(func.distinct(TweetKeyword.tweet_id)))
            .join(Tweet, Tweet.id == TweetKeyword.tweet_id)
            .where(
                Tweet.author_user_id == user_id,
                TweetKeyword.extractor_key == DEFAULT_KEYWORD_EXTRACTOR_KEY,
                TweetKeyword.extractor_version == DEFAULT_KEYWORD_EXTRACTOR_VERSION,
            )
        )
        or 0
    )

    return {
        "tweet_count": tweet_count,
        "mood_scored_tweet_count": mood_scored_tweet_count,
        "keyword_tweet_count": keyword_tweet_count,
        "overview_ready": tweet_count > 0,
        "moods_ready": mood_scored_tweet_count > 0,
        "heatmap_ready": keyword_tweet_count > 0,
        "bitcoin_mentions_ready": tweet_count > 0,
    }


def _load_first_tweet_at(session: Session, *, user_id: int) -> datetime | None:
    first_tweet_at = session.scalar(
        select(func.min(Tweet.created_at_platform)).where(Tweet.author_user_id == user_id)
    )
    if first_tweet_at is None:
        return None
    normalized = first_tweet_at.astimezone(UTC)
    return normalized.replace(hour=0, minute=0, second=0, microsecond=0)


def _slug_base_from_user(*, user: User) -> str:
    candidate = (user.display_name or user.username or "").strip()
    normalized = _normalize_slug(candidate) if candidate else ""
    if normalized:
        return normalized
    return f"user-{user.id}"


def _generate_unique_slug(session: Session, *, slug_base: str) -> str:
    normalized_base = _normalize_slug(slug_base)
    candidate = normalized_base
    suffix = 2
    while session.scalar(
        select(ManagedAuthorView.id).where(ManagedAuthorView.slug == candidate)
    ):
        candidate = f"{normalized_base}-{suffix}"
        suffix += 1
    return candidate


def _assert_slug_available(
    session: Session,
    *,
    slug: str,
    exclude_user_id: int | None = None,
) -> None:
    query = select(ManagedAuthorView.id).where(ManagedAuthorView.slug == slug)
    if exclude_user_id is not None:
        query = query.where(ManagedAuthorView.user_id != exclude_user_id)
    existing_id = session.scalar(query)
    if existing_id is not None:
        raise RuntimeError(f"A managed author view already exists for slug={slug!r}.")


def _normalize_slug(value: str) -> str:
    lowered = value.strip().lower()
    slug = _SLUG_PATTERN.sub("-", lowered).strip("-")
    if not slug:
        raise RuntimeError("Author slug cannot be empty.")
    if len(slug) > 128:
        raise RuntimeError("Author slug cannot exceed 128 characters.")
    return slug


def _parse_optional_utc_datetime(value: str) -> datetime | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    return _parse_utc_datetime(cleaned)


def _parse_utc_datetime(value: str) -> datetime:
    cleaned = value.strip()
    if not cleaned:
        raise RuntimeError("Datetime value cannot be empty.")

    candidate = cleaned[:-1] + "+00:00" if cleaned.endswith("Z") else cleaned
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise RuntimeError(f"Invalid UTC datetime {value!r}.") from exc

    if parsed.tzinfo is None:
        raise RuntimeError(f"Datetime {value!r} must include timezone information.")
    return parsed.astimezone(UTC)


def _to_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _to_iso_nullable(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _to_iso(value)
