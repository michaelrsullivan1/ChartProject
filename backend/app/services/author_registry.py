from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.tracked_authors import TRACKED_AUTHOR_SEEDS
from app.db.session import SessionLocal
from app.models.managed_author_view import ManagedAuthorView
from app.models.tweet import Tweet
from app.models.tweet_keyword import TweetKeyword
from app.models.tweet_mood_score import TweetMoodScore
from app.models.user import User
from app.services.aggregate_snapshot_cache import (
    AUTHOR_REGISTRY_GRANULARITY,
    AUTHOR_REGISTRY_MODEL_KEY,
    AUTHOR_REGISTRY_SCOPE,
    AUTHOR_REGISTRY_VIEW_TYPE,
    build_aggregate_snapshot_cache_key,
    get_aggregate_snapshot,
    upsert_aggregate_snapshot,
)
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
    tracked: bool = True
    ensure_analysis_starts: bool = True
    rebuild_snapshot: bool = True


@dataclass(slots=True)
class SyncTrackedAuthorsRequest:
    dry_run: bool = False


@dataclass(slots=True)
class AuditTrackedAuthorsRequest:
    model_key: str = DEFAULT_MOOD_MODEL


@dataclass(slots=True)
class ReconcileMoodScoredAuthorsRequest:
    model_key: str = DEFAULT_MOOD_MODEL
    dry_run: bool = False
    rebuild_snapshot: bool = True


def build_public_author_registry(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    snapshot = get_public_author_registry_snapshot(session_factory=session_factory)
    if snapshot is not None:
        return snapshot
    return _build_public_author_registry_payload(session_factory=session_factory)


def get_public_author_registry_snapshot(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object] | None:
    return get_aggregate_snapshot(
        view_type=AUTHOR_REGISTRY_VIEW_TYPE,
        cohort_tag_slug=AUTHOR_REGISTRY_SCOPE,
        granularity=AUTHOR_REGISTRY_GRANULARITY,
        model_key=AUTHOR_REGISTRY_MODEL_KEY,
        session_factory=session_factory,
    )


def rebuild_public_author_registry_snapshot(
    *,
    dry_run: bool = False,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    payload = _build_public_author_registry_payload(session_factory=session_factory)
    cache_key = build_aggregate_snapshot_cache_key(
        view_type=AUTHOR_REGISTRY_VIEW_TYPE,
        cohort_tag_slug=AUTHOR_REGISTRY_SCOPE,
        granularity=AUTHOR_REGISTRY_GRANULARITY,
        model_key=AUTHOR_REGISTRY_MODEL_KEY,
    )
    build_meta = {
        "tracked_author_count": len(payload["authors"]),
        "overview_count": len(payload["overviews"]),
        "mood_count": len(payload["moods"]),
        "heatmap_count": len(payload["heatmaps"]),
        "bitcoin_mentions_count": len(payload["bitcoin_mentions"]),
        "rebuilt_at": _to_iso(datetime.now(UTC)),
    }
    if not dry_run:
        cache_key = upsert_aggregate_snapshot(
            view_type=AUTHOR_REGISTRY_VIEW_TYPE,
            cohort_tag_slug=AUTHOR_REGISTRY_SCOPE,
            granularity=AUTHOR_REGISTRY_GRANULARITY,
            model_key=AUTHOR_REGISTRY_MODEL_KEY,
            payload=payload,
            build_meta=build_meta,
            session_factory=session_factory,
        )

    return {
        "view": "author-registry-snapshot-rebuild",
        "dry_run": dry_run,
        "cache_key": cache_key,
        "tracked_author_count": len(payload["authors"]),
        "overview_count": len(payload["overviews"]),
        "mood_count": len(payload["moods"]),
        "heatmap_count": len(payload["heatmaps"]),
        "bitcoin_mentions_count": len(payload["bitcoin_mentions"]),
    }


def _build_public_author_registry_payload(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        rows = session.execute(
            select(ManagedAuthorView, User)
            .join(User, User.id == ManagedAuthorView.user_id)
            .where(
                ManagedAuthorView.is_tracked.is_(True),
                ManagedAuthorView.published.is_(True),
            )
            .order_by(
                ManagedAuthorView.sort_order.asc().nullslast(),
                func.lower(ManagedAuthorView.slug).asc(),
            )
        ).all()

        user_ids = [int(user.id) for _mav, user in rows]
        first_tweet_at_by_user_id = _load_first_tweet_at_map(session, user_ids=user_ids)
        readiness_by_user_id = _load_author_readiness_map(session, user_ids=user_ids)

        authors: list[dict[str, object]] = []
        overviews: list[dict[str, str]] = []
        moods: list[dict[str, str]] = []
        heatmaps: list[dict[str, str]] = []
        bitcoin_mentions: list[dict[str, str]] = []

        for mav, user in rows:
            default_start = first_tweet_at_by_user_id.get(int(user.id))
            readiness = readiness_by_user_id.get(int(user.id), _empty_author_readiness())
            starts = _resolve_analysis_starts(
                managed_author_view=mav,
                default_start=default_start,
            )

            author_payload = {
                "user_id": int(user.id),
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "slug": mav.slug,
                "is_tracked": bool(mav.is_tracked),
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
                        "api_base_path": f"/api/views/authors/{mav.slug}/bitcoin-mentions",
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
                        "api_base_path": f"/api/views/authors/{mav.slug}/bitcoin-mentions",
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

        user_ids = [int(user.id) for _mav, user in rows]
        first_tweet_at_by_user_id = _load_first_tweet_at_map(session, user_ids=user_ids)
        readiness_by_user_id = _load_author_readiness_map(session, user_ids=user_ids)

        authors: list[dict[str, object]] = []
        for mav, user in rows:
            default_start = first_tweet_at_by_user_id.get(int(user.id))
            readiness = readiness_by_user_id.get(int(user.id), _empty_author_readiness())
            starts = _resolve_analysis_starts(
                managed_author_view=mav,
                default_start=default_start,
            )
            authors.append(
                {
                    "user_id": int(user.id),
                    "platform_user_id": user.platform_user_id,
                    "username": user.username,
                    "display_name": user.display_name,
                    "slug": mav.slug,
                    "is_tracked": bool(mav.is_tracked),
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
        rebuild_public_author_registry_snapshot(session_factory=session_factory)

        user = session.scalar(select(User).where(User.id == request.user_id))
        if user is None:
            raise RuntimeError(f"No canonical user exists for user_id={request.user_id}.")

        default_start = _load_first_tweet_at(session, user_id=int(user.id))
        readiness = _load_author_readiness(session, user_id=int(user.id))
        starts = _resolve_analysis_starts(
            managed_author_view=managed_author,
            default_start=default_start,
        )

        return {
            "view": "author-registry-update",
            "author": {
                "user_id": int(user.id),
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "slug": managed_author.slug,
                "is_tracked": bool(managed_author.is_tracked),
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
                is_tracked=request.tracked,
                published=request.published,
            )
            created = True
            session.add(existing)

        existing.published = request.published
        existing.is_tracked = request.tracked

        if request.ensure_analysis_starts:
            if existing.overview_analysis_start is None:
                existing.overview_analysis_start = first_tweet_at
            if existing.mood_analysis_start is None:
                existing.mood_analysis_start = first_tweet_at
            if existing.heatmap_analysis_start is None:
                existing.heatmap_analysis_start = first_tweet_at

        session.commit()
        session.refresh(existing)
        if request.rebuild_snapshot:
            rebuild_public_author_registry_snapshot(session_factory=session_factory)

        default_start = _load_first_tweet_at(session, user_id=int(user.id))
        readiness = _load_author_readiness(session, user_id=int(user.id))
        starts = _resolve_analysis_starts(
            managed_author_view=existing,
            default_start=default_start,
        )

        return {
            "view": "author-registry-sync",
            "created": created,
            "author": {
                "user_id": int(user.id),
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "slug": existing.slug,
                "is_tracked": bool(existing.is_tracked),
                "published": bool(existing.published),
                "sort_order": existing.sort_order,
                "analysis_start": starts,
                "readiness": readiness,
            },
        }
    finally:
        session.close()


def sync_tracked_authors(
    request: SyncTrackedAuthorsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        created = 0
        updated = 0
        unchanged = 0
        results: list[dict[str, object]] = []

        for seed in TRACKED_AUTHOR_SEEDS:
            user = session.scalar(
                select(User).where(func.lower(User.username) == seed.username.lower())
            )
            if user is None:
                raise RuntimeError(
                    f"Tracked author seed username={seed.username!r} was not found in canonical users."
                )

            managed_author = session.scalar(
                select(ManagedAuthorView).where(ManagedAuthorView.user_id == user.id)
            )
            first_tweet_at = _load_first_tweet_at(session, user_id=int(user.id))

            if managed_author is None:
                _assert_slug_available(session, slug=seed.slug)
                session.add(
                    ManagedAuthorView(
                        user_id=user.id,
                        slug=seed.slug,
                        is_tracked=True,
                        published=True,
                        sort_order=seed.sort_order,
                        enable_overview=True,
                        enable_moods=True,
                        enable_heatmap=True,
                        enable_bitcoin_mentions=True,
                        overview_analysis_start=first_tweet_at,
                        mood_analysis_start=first_tweet_at,
                        heatmap_analysis_start=first_tweet_at,
                    )
                )
                created += 1
                results.append(
                    {
                        "username": user.username,
                        "slug": seed.slug,
                        "status": "created",
                    }
                )
                continue

            changed_fields: list[str] = []
            if managed_author.slug != seed.slug:
                _assert_slug_available(session, slug=seed.slug, exclude_user_id=int(user.id))
                managed_author.slug = seed.slug
                changed_fields.append("slug")
            if not managed_author.is_tracked:
                managed_author.is_tracked = True
                changed_fields.append("is_tracked")
            if not managed_author.published:
                managed_author.published = True
                changed_fields.append("published")
            if managed_author.sort_order != seed.sort_order:
                managed_author.sort_order = seed.sort_order
                changed_fields.append("sort_order")
            if not managed_author.enable_overview:
                managed_author.enable_overview = True
                changed_fields.append("enable_overview")
            if not managed_author.enable_moods:
                managed_author.enable_moods = True
                changed_fields.append("enable_moods")
            if not managed_author.enable_heatmap:
                managed_author.enable_heatmap = True
                changed_fields.append("enable_heatmap")
            if not managed_author.enable_bitcoin_mentions:
                managed_author.enable_bitcoin_mentions = True
                changed_fields.append("enable_bitcoin_mentions")
            if managed_author.overview_analysis_start is None and first_tweet_at is not None:
                managed_author.overview_analysis_start = first_tweet_at
                changed_fields.append("overview_analysis_start")
            if managed_author.mood_analysis_start is None and first_tweet_at is not None:
                managed_author.mood_analysis_start = first_tweet_at
                changed_fields.append("mood_analysis_start")
            if managed_author.heatmap_analysis_start is None and first_tweet_at is not None:
                managed_author.heatmap_analysis_start = first_tweet_at
                changed_fields.append("heatmap_analysis_start")

            if changed_fields:
                updated += 1
                results.append(
                    {
                        "username": user.username,
                        "slug": managed_author.slug,
                        "status": "updated",
                        "changed_fields": changed_fields,
                    }
                )
            else:
                unchanged += 1
                results.append(
                    {
                        "username": user.username,
                        "slug": managed_author.slug,
                        "status": "unchanged",
                    }
                )

        if request.dry_run:
            session.rollback()
        else:
            session.commit()
            rebuild_public_author_registry_snapshot(session_factory=session_factory)

        return {
            "view": "tracked-author-sync",
            "dry_run": request.dry_run,
            "tracked_author_seed_count": len(TRACKED_AUTHOR_SEEDS),
            "created_count": created,
            "updated_count": updated,
            "unchanged_count": unchanged,
            "results": results,
        }
    finally:
        session.close()


def audit_tracked_authors(
    request: AuditTrackedAuthorsRequest | None = None,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    request = request or AuditTrackedAuthorsRequest()
    session = session_factory()
    try:
        expected_by_username = {seed.username.casefold(): seed for seed in TRACKED_AUTHOR_SEEDS}
        expected_by_slug = {seed.slug: seed for seed in TRACKED_AUTHOR_SEEDS}
        issues: list[dict[str, object]] = []

        canonical_rows = session.execute(
            select(User.id, User.username)
            .where(func.lower(User.username).in_(list(expected_by_username.keys())))
            .order_by(func.lower(User.username).asc())
        ).all()
        canonical_by_username = {row.username.casefold(): row for row in canonical_rows}
        for seed in TRACKED_AUTHOR_SEEDS:
            if seed.username.casefold() not in canonical_by_username:
                issues.append(
                    {
                        "severity": "fail",
                        "username": seed.username,
                        "slug": seed.slug,
                        "issue": "missing_canonical_user",
                    }
                )

        tracked_rows = session.execute(
            select(ManagedAuthorView, User)
            .join(User, User.id == ManagedAuthorView.user_id)
            .where(ManagedAuthorView.is_tracked.is_(True))
            .order_by(func.lower(ManagedAuthorView.slug).asc())
        ).all()
        tracked_by_username = {user.username.casefold(): (mav, user) for mav, user in tracked_rows}

        for seed in TRACKED_AUTHOR_SEEDS:
            row = tracked_by_username.get(seed.username.casefold())
            if row is None:
                issues.append(
                    {
                        "severity": "fail",
                        "username": seed.username,
                        "slug": seed.slug,
                        "issue": "missing_tracked_managed_author_view",
                    }
                )
                continue

            mav, user = row
            if mav.slug != seed.slug:
                issues.append(
                    {
                        "severity": "fail",
                        "username": user.username,
                        "expected_slug": seed.slug,
                        "actual_slug": mav.slug,
                        "issue": "slug_mismatch",
                    }
                )
            if not mav.published:
                issues.append(
                    {
                        "severity": "fail",
                        "username": user.username,
                        "slug": mav.slug,
                        "issue": "not_published",
                    }
                )
            if mav.sort_order != seed.sort_order:
                issues.append(
                    {
                        "severity": "warn",
                        "username": user.username,
                        "slug": mav.slug,
                        "expected_sort_order": seed.sort_order,
                        "actual_sort_order": mav.sort_order,
                        "issue": "sort_order_mismatch",
                    }
                )
            for field_name in (
                "enable_overview",
                "enable_moods",
                "enable_heatmap",
                "enable_bitcoin_mentions",
            ):
                if not getattr(mav, field_name):
                    issues.append(
                        {
                            "severity": "fail",
                            "username": user.username,
                            "slug": mav.slug,
                            "issue": f"{field_name}_disabled",
                        }
                    )

        for mav, user in tracked_rows:
            if user.username.casefold() not in expected_by_username:
                issues.append(
                    {
                        "severity": "warn",
                        "username": user.username,
                        "slug": mav.slug,
                        "issue": "extra_tracked_author_not_in_seed",
                    }
                )
            if mav.slug not in expected_by_slug:
                issues.append(
                    {
                        "severity": "warn",
                        "username": user.username,
                        "slug": mav.slug,
                        "issue": "extra_tracked_slug_not_in_seed",
                    }
                )

        mood_scored_tracking_summary = _build_mood_scored_tracking_summary(
            session,
            model_key=request.model_key,
        )
        for item in mood_scored_tracking_summary["excluded_users"]:
            issues.append(
                {
                    "severity": "fail",
                    "username": item["username"],
                    "slug": item["slug"],
                    "issue": item["issue"],
                }
            )

        return {
            "view": "tracked-author-audit",
            "model": {"model_key": request.model_key},
            "tracked_author_seed_count": len(TRACKED_AUTHOR_SEEDS),
            "tracked_author_db_count": len(tracked_rows),
            "mood_scored_tracking_summary": mood_scored_tracking_summary,
            "ok": not any(issue["severity"] == "fail" for issue in issues),
            "issues": issues,
            "tracked_authors": [
                {
                    "username": user.username,
                    "slug": mav.slug,
                    "published": bool(mav.published),
                    "sort_order": mav.sort_order,
                }
                for mav, user in tracked_rows
            ],
        }
    finally:
        session.close()


def reconcile_mood_scored_authors(
    request: ReconcileMoodScoredAuthorsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    precheck_session = session_factory()
    try:
        before = _build_mood_scored_tracking_summary(precheck_session, model_key=request.model_key)
    finally:
        precheck_session.close()

    if request.dry_run:
        planned = [
            {
                "username": item["username"],
                "slug": item["slug"],
                "issue": item["issue"],
                "action": "sync_managed_author_view_as_tracked_and_published",
            }
            for item in before["excluded_users"]
        ]
        return {
            "view": "mood-scored-author-reconcile",
            "model": {"model_key": request.model_key},
            "dry_run": True,
            "rebuild_snapshot": request.rebuild_snapshot,
            "reconciled_count": 0,
            "reconciled": [],
            "planned": planned,
            "before": before,
            "after": before,
        }

    reconciled: list[dict[str, object]] = []
    for item in before["excluded_users"]:
        payload = sync_managed_author_view_for_username(
            SyncManagedAuthorViewRequest(
                username=str(item["username"]),
                published=True,
                tracked=True,
                ensure_analysis_starts=True,
                rebuild_snapshot=False,
            ),
            session_factory=session_factory,
        )
        reconciled.append(
            {
                "username": item["username"],
                "slug": payload["author"]["slug"],
                "changed_fields": ["is_tracked", "published"],
                "created": bool(payload["created"]),
            }
        )

    if request.rebuild_snapshot and reconciled:
        rebuild_public_author_registry_snapshot(session_factory=session_factory)

    postcheck_session = session_factory()
    try:
        after = _build_mood_scored_tracking_summary(postcheck_session, model_key=request.model_key)
    finally:
        postcheck_session.close()

    return {
        "view": "mood-scored-author-reconcile",
        "model": {"model_key": request.model_key},
        "dry_run": request.dry_run,
        "rebuild_snapshot": request.rebuild_snapshot,
        "reconciled_count": len(reconciled),
        "reconciled": reconciled,
        "before": before,
        "after": after,
    }


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

        default_start = _load_first_tweet_at(session, user_id=int(user.id))
        starts = _resolve_analysis_starts(
            managed_author_view=managed_author,
            default_start=default_start,
        )
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


def _build_mood_scored_tracking_summary(session: Session, *, model_key: str) -> dict[str, object]:
    mood_scored_user_ids = _load_mood_scored_user_ids(session, model_key=model_key)
    if not mood_scored_user_ids:
        return {
            "mood_scored_user_count": 0,
            "tracked_published_mood_scored_user_count": 0,
            "excluded_mood_scored_user_count": 0,
            "excluded_users": [],
        }

    rows = session.execute(
        select(
            User.id,
            User.username,
            ManagedAuthorView.slug,
            ManagedAuthorView.is_tracked,
            ManagedAuthorView.published,
        )
        .outerjoin(ManagedAuthorView, ManagedAuthorView.user_id == User.id)
        .where(User.id.in_(mood_scored_user_ids))
        .order_by(func.lower(User.username).asc())
    ).all()

    tracked_published_count = 0
    excluded_users: list[dict[str, object]] = []
    for user_id, username, slug, is_tracked, published in rows:
        if slug is None:
            excluded_users.append(
                {
                    "user_id": int(user_id),
                    "username": username,
                    "slug": None,
                    "issue": "missing_managed_author_view",
                }
            )
            continue
        if is_tracked and published:
            tracked_published_count += 1
            continue

        issue = "not_tracked"
        if is_tracked and not published:
            issue = "not_published"
        elif not is_tracked and not published:
            issue = "not_tracked_or_published"

        excluded_users.append(
            {
                "user_id": int(user_id),
                "username": username,
                "slug": slug,
                "issue": issue,
            }
        )

    return {
        "mood_scored_user_count": len(mood_scored_user_ids),
        "tracked_published_mood_scored_user_count": tracked_published_count,
        "excluded_mood_scored_user_count": len(excluded_users),
        "excluded_users": excluded_users,
    }


def _load_mood_scored_user_ids(session: Session, *, model_key: str) -> set[int]:
    session.execute(text("SET LOCAL max_parallel_workers_per_gather = 0"))
    rows = session.execute(
        select(Tweet.author_user_id)
        .join(TweetMoodScore, TweetMoodScore.tweet_id == Tweet.id)
        .where(
            TweetMoodScore.model_key == model_key,
            TweetMoodScore.status == "scored",
        )
        .group_by(Tweet.author_user_id)
    ).all()
    return {int(row.author_user_id) for row in rows}


def _resolve_analysis_starts(
    *,
    managed_author_view: ManagedAuthorView,
    default_start: datetime | None,
) -> dict[str, str | None]:
    return {
        "overview": _to_iso_nullable(managed_author_view.overview_analysis_start or default_start),
        "moods": _to_iso_nullable(managed_author_view.mood_analysis_start or default_start),
        "heatmap": _to_iso_nullable(managed_author_view.heatmap_analysis_start or default_start),
    }


def _load_author_readiness(session: Session, *, user_id: int) -> dict[str, object]:
    readiness_map = _load_author_readiness_map(session, user_ids=[user_id])
    return readiness_map.get(user_id, _empty_author_readiness())


def _load_author_readiness_map(
    session: Session,
    *,
    user_ids: list[int],
) -> dict[int, dict[str, object]]:
    if not user_ids:
        return {}

    tweet_counts = {
        int(user_id): int(count)
        for user_id, count in session.execute(
            select(Tweet.author_user_id, func.count(Tweet.id))
            .where(Tweet.author_user_id.in_(user_ids))
            .group_by(Tweet.author_user_id)
        ).all()
    }
    mood_counts = {
        int(user_id): int(count)
        for user_id, count in session.execute(
            select(Tweet.author_user_id, func.count(func.distinct(TweetMoodScore.tweet_id)))
            .join(TweetMoodScore, TweetMoodScore.tweet_id == Tweet.id)
            .where(
                Tweet.author_user_id.in_(user_ids),
                TweetMoodScore.model_key == DEFAULT_MOOD_MODEL,
                TweetMoodScore.status == "scored",
            )
            .group_by(Tweet.author_user_id)
        ).all()
    }
    keyword_counts = {
        int(user_id): int(count)
        for user_id, count in session.execute(
            select(Tweet.author_user_id, func.count(func.distinct(TweetKeyword.tweet_id)))
            .join(TweetKeyword, TweetKeyword.tweet_id == Tweet.id)
            .where(
                Tweet.author_user_id.in_(user_ids),
                TweetKeyword.extractor_key == DEFAULT_KEYWORD_EXTRACTOR_KEY,
                TweetKeyword.extractor_version == DEFAULT_KEYWORD_EXTRACTOR_VERSION,
            )
            .group_by(Tweet.author_user_id)
        ).all()
    }

    readiness_by_user_id: dict[int, dict[str, object]] = {}
    for user_id in user_ids:
        tweet_count = tweet_counts.get(user_id, 0)
        mood_scored_tweet_count = mood_counts.get(user_id, 0)
        keyword_tweet_count = keyword_counts.get(user_id, 0)
        readiness_by_user_id[user_id] = {
            "tweet_count": tweet_count,
            "mood_scored_tweet_count": mood_scored_tweet_count,
            "keyword_tweet_count": keyword_tweet_count,
            "overview_ready": tweet_count > 0,
            "moods_ready": mood_scored_tweet_count > 0,
            "heatmap_ready": keyword_tweet_count > 0,
            "bitcoin_mentions_ready": tweet_count > 0,
        }

    return readiness_by_user_id


def _empty_author_readiness() -> dict[str, object]:
    tweet_count = int(
        0
    )
    return {
        "tweet_count": tweet_count,
        "mood_scored_tweet_count": 0,
        "keyword_tweet_count": 0,
        "overview_ready": tweet_count > 0,
        "moods_ready": False,
        "heatmap_ready": False,
        "bitcoin_mentions_ready": tweet_count > 0,
    }


def _load_first_tweet_at(session: Session, *, user_id: int) -> datetime | None:
    first_tweet_at_by_user_id = _load_first_tweet_at_map(session, user_ids=[user_id])
    return first_tweet_at_by_user_id.get(user_id)


def _load_first_tweet_at_map(
    session: Session,
    *,
    user_ids: list[int],
) -> dict[int, datetime]:
    if not user_ids:
        return {}

    rows = session.execute(
        select(Tweet.author_user_id, func.min(Tweet.created_at_platform))
        .where(Tweet.author_user_id.in_(user_ids))
        .group_by(Tweet.author_user_id)
    ).all()

    first_tweet_at_by_user_id: dict[int, datetime] = {}
    for user_id, first_tweet_at in rows:
        if first_tweet_at is None:
            continue
        normalized = first_tweet_at.astimezone(UTC).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        first_tweet_at_by_user_id[int(user_id)] = normalized
    return first_tweet_at_by_user_id


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
