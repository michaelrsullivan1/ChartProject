from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.aggregate_view_snapshot import AggregateViewSnapshot


AGGREGATE_SNAPSHOT_CACHE_VERSION = 1
AGGREGATE_ALL_COHORT_SLUG = "all"
AGGREGATE_COHORTS_VIEW_TYPE = "aggregate-cohorts"
AGGREGATE_OVERVIEW_VIEW_TYPE = "aggregate-overview"
AGGREGATE_MOOD_SERIES_VIEW_TYPE = "aggregate-mood-series"
AGGREGATE_MOOD_OUTLIERS_VIEW_TYPE = "aggregate-mood-outliers"
AGGREGATE_NARRATIVE_COHORTS_VIEW_TYPE = "aggregate-narrative-cohorts"
AGGREGATE_NARRATIVE_SERIES_VIEW_TYPE = "aggregate-narrative-series"
AUTHOR_REGISTRY_VIEW_TYPE = "author-registry"
AUTHOR_REGISTRY_SCOPE = "all"
AUTHOR_REGISTRY_GRANULARITY = "registry"
AUTHOR_REGISTRY_MODEL_KEY = "tracked-authors"


def normalize_aggregate_cohort_slug(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return normalized or AGGREGATE_ALL_COHORT_SLUG


def build_aggregate_snapshot_cache_key(
    *,
    view_type: str,
    cohort_tag_slug: str | None,
    granularity: str,
    model_key: str,
    cache_version: int = AGGREGATE_SNAPSHOT_CACHE_VERSION,
) -> str:
    return (
        f"aggregate:{cache_version}:{model_key}:{granularity}:{view_type}:"
        f"{normalize_aggregate_cohort_slug(cohort_tag_slug)}"
    )


def attach_generated_at(
    payload: dict[str, object],
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    stamped_at = (generated_at or datetime.now(UTC)).astimezone(UTC)
    return {
        **payload,
        "generated_at": stamped_at.isoformat().replace("+00:00", "Z"),
    }


def get_aggregate_snapshot(
    *,
    view_type: str,
    cohort_tag_slug: str | None,
    granularity: str,
    model_key: str,
    cache_version: int = AGGREGATE_SNAPSHOT_CACHE_VERSION,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object] | None:
    session = session_factory()
    try:
        snapshot = session.scalar(
            select(AggregateViewSnapshot).where(
                AggregateViewSnapshot.view_type == view_type,
                AggregateViewSnapshot.cohort_tag_slug
                == normalize_aggregate_cohort_slug(cohort_tag_slug),
                AggregateViewSnapshot.granularity == granularity,
                AggregateViewSnapshot.model_key == model_key,
                AggregateViewSnapshot.cache_version == cache_version,
            )
        )
        return dict(snapshot.payload_json) if snapshot is not None else None
    finally:
        session.close()


def upsert_aggregate_snapshot(
    *,
    view_type: str,
    cohort_tag_slug: str | None,
    granularity: str,
    model_key: str,
    payload: dict[str, object],
    source_signature: str | None = None,
    build_meta: dict[str, object] | None = None,
    generated_at: datetime | None = None,
    cache_version: int = AGGREGATE_SNAPSHOT_CACHE_VERSION,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> str:
    normalized_cohort_slug = normalize_aggregate_cohort_slug(cohort_tag_slug)
    cache_key = build_aggregate_snapshot_cache_key(
        view_type=view_type,
        cohort_tag_slug=normalized_cohort_slug,
        granularity=granularity,
        model_key=model_key,
        cache_version=cache_version,
    )
    stamped_at = (generated_at or datetime.now(UTC)).astimezone(UTC)
    payload_with_timestamp = attach_generated_at(payload, generated_at=stamped_at)

    stmt = insert(AggregateViewSnapshot).values(
        cache_key=cache_key,
        view_type=view_type,
        cohort_tag_slug=normalized_cohort_slug,
        granularity=granularity,
        model_key=model_key,
        cache_version=cache_version,
        payload_json=payload_with_timestamp,
        generated_at=stamped_at,
        source_signature=source_signature,
        build_meta_json=build_meta,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_aggregate_view_snapshots_lookup",
        set_={
            "cache_key": cache_key,
            "payload_json": payload_with_timestamp,
            "generated_at": stamped_at,
            "source_signature": source_signature,
            "build_meta_json": build_meta,
            "updated_at": stamped_at,
        },
    )

    session = session_factory()
    try:
        session.execute(stmt)
        session.commit()
        return cache_key
    finally:
        session.close()


def delete_stale_aggregate_snapshots(
    *,
    model_key: str,
    granularity: str,
    rebuilt_cache_keys: Iterable[str],
    view_types: Iterable[str],
    cache_version: int = AGGREGATE_SNAPSHOT_CACHE_VERSION,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> int:
    rebuilt_keys = tuple(rebuilt_cache_keys)
    session = session_factory()
    try:
        stmt = delete(AggregateViewSnapshot).where(
            AggregateViewSnapshot.model_key == model_key,
            AggregateViewSnapshot.granularity == granularity,
            AggregateViewSnapshot.cache_version == cache_version,
            AggregateViewSnapshot.view_type.in_(tuple(view_types)),
        )
        if rebuilt_keys:
            stmt = stmt.where(AggregateViewSnapshot.cache_key.not_in(rebuilt_keys))
        result = session.execute(stmt)
        session.commit()
        return int(result.rowcount or 0)
    finally:
        session.close()
