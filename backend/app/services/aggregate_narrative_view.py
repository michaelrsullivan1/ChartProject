from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.cohort_tag import CohortTag
from app.models.managed_author_view import ManagedAuthorView
from app.models.managed_narrative import ManagedNarrative
from app.models.tweet import Tweet
from app.models.tweet_narrative_match import TweetNarrativeMatch
from app.models.user import User
from app.models.user_cohort_tag import UserCohortTag
from app.services.aggregate_snapshot_cache import (
    AGGREGATE_ALL_COHORT_SLUG,
    attach_generated_at,
    delete_stale_aggregate_snapshots,
    get_aggregate_snapshot,
    upsert_aggregate_snapshot,
)
from app.services.managed_narratives import MANAGED_NARRATIVE_MODEL_KEY
from app.services.market_data import floor_to_week


AGGREGATE_NARRATIVE_COHORTS_VIEW_TYPE = "aggregate-narrative-cohorts"
AGGREGATE_NARRATIVE_SERIES_VIEW_TYPE = "aggregate-narrative-series"


@dataclass(slots=True)
class AggregateNarrativeCohortsRequest:
    view_name: str = "aggregate-narratives-cohorts"


@dataclass(slots=True)
class AggregateNarrativeViewRequest:
    granularity: str = "week"
    cohort_tag_slug: str | None = None
    view_name: str = "aggregate-narratives"


def build_aggregate_narrative_cohorts(
    request: AggregateNarrativeCohortsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        eligible_user_ids = _load_aggregate_narrative_eligible_user_ids(session)
        if not eligible_user_ids:
            return {
                "view": request.view_name,
                "cohorts": [],
                "default_selection": {
                    "type": "all",
                    "tag_slug": None,
                    "tag_name": "All tracked users",
                },
            }

        rows = session.execute(
            select(
                CohortTag.slug,
                CohortTag.name,
                User.username,
                User.id,
            )
            .join(UserCohortTag, UserCohortTag.cohort_tag_id == CohortTag.id)
            .join(User, User.id == UserCohortTag.user_id)
            .where(User.id.in_(eligible_user_ids))
            .order_by(
                func.lower(CohortTag.name).asc(),
                func.lower(User.username).asc(),
            )
        ).all()

        cohorts_by_slug: dict[str, dict[str, object]] = {}
        for slug, name, username, user_id in rows:
            cohort = cohorts_by_slug.setdefault(
                slug,
                {
                    "tag_slug": slug,
                    "tag_name": name,
                    "usernames": [],
                    "user_ids": set(),
                },
            )
            if int(user_id) not in cohort["user_ids"]:
                cohort["user_ids"].add(int(user_id))
                cohort["usernames"].append(username)

        cohorts = [
            {
                "tag_slug": cohort["tag_slug"],
                "tag_name": cohort["tag_name"],
                "user_count": len(cohort["user_ids"]),
                "usernames": cohort["usernames"],
            }
            for cohort in cohorts_by_slug.values()
        ]
        return {
            "view": request.view_name,
            "cohorts": cohorts,
            "default_selection": {
                "type": "all",
                "tag_slug": None,
                "tag_name": "All tracked users",
            },
        }
    finally:
        session.close()


def build_cached_aggregate_narrative_cohorts(
    request: AggregateNarrativeCohortsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    snapshot = get_aggregate_snapshot(
        view_type=AGGREGATE_NARRATIVE_COHORTS_VIEW_TYPE,
        cohort_tag_slug=None,
        granularity="week",
        model_key=MANAGED_NARRATIVE_MODEL_KEY,
        session_factory=session_factory,
    )
    if snapshot is not None:
        return snapshot

    return attach_generated_at(
        build_aggregate_narrative_cohorts(request, session_factory=session_factory)
    )


def build_aggregate_narrative_view(
    request: AggregateNarrativeViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    granularity = request.granularity.strip().lower()
    if granularity != "week":
        raise RuntimeError("aggregate-narratives view only supports granularity=week.")

    session = session_factory()
    try:
        cohort_user_ids, cohort_usernames, cohort_selection = _resolve_aggregate_narrative_cohort_user_scope(
            session,
            cohort_tag_slug=request.cohort_tag_slug,
        )
        narratives = list(
            session.scalars(
                select(ManagedNarrative).order_by(
                    func.lower(ManagedNarrative.name).asc(),
                    ManagedNarrative.id.asc(),
                )
            )
        )

        earliest_tweet_at, latest_tweet_at = session.execute(
            select(
                func.min(Tweet.created_at_platform),
                func.max(Tweet.created_at_platform),
            ).where(Tweet.author_user_id.in_(cohort_user_ids))
        ).one()

        if earliest_tweet_at is None or latest_tweet_at is None:
            raise RuntimeError("No tracked tweets are available for aggregate narratives.")

        weeks = _build_week_series(
            floor_to_week(earliest_tweet_at),
            floor_to_week(latest_tweet_at),
        )
        week_index = {week: index for index, week in enumerate(weeks)}
        weekly_total_tweet_counts = [0] * len(weeks)
        counts_by_narrative_id = {
            narrative.id: [0] * len(weeks)
            for narrative in narratives
        }

        week_start_expr = func.date_trunc("week", Tweet.created_at_platform).label("week_start")
        weekly_tweet_rows = session.execute(
            select(
                week_start_expr,
                func.count(Tweet.id).label("total_tweet_count"),
            )
            .where(Tweet.author_user_id.in_(cohort_user_ids))
            .group_by(week_start_expr)
            .order_by(week_start_expr.asc())
        ).all()
        for week_start, total_tweet_count in weekly_tweet_rows:
            normalized_week = floor_to_week(week_start.astimezone(UTC))
            index = week_index.get(normalized_week)
            if index is None:
                continue
            weekly_total_tweet_counts[index] = int(total_tweet_count)

        total_tweets_in_range = sum(weekly_total_tweet_counts)
        latest_period_total_tweets = weekly_total_tweet_counts[-1] if weekly_total_tweet_counts else 0

        if narratives:
            weekly_counts_subquery = (
                select(
                    TweetNarrativeMatch.managed_narrative_id.label("managed_narrative_id"),
                    week_start_expr,
                    func.count().label("matching_tweet_count"),
                )
                .join(Tweet, Tweet.id == TweetNarrativeMatch.tweet_id)
                .where(
                    Tweet.author_user_id.in_(cohort_user_ids),
                    TweetNarrativeMatch.managed_narrative_id.in_(
                        [narrative.id for narrative in narratives]
                    ),
                )
                .group_by(
                    TweetNarrativeMatch.managed_narrative_id,
                    week_start_expr,
                )
                .subquery()
            )
            rows = session.execute(
                select(
                    weekly_counts_subquery.c.managed_narrative_id,
                    weekly_counts_subquery.c.week_start,
                    weekly_counts_subquery.c.matching_tweet_count,
                )
                .order_by(
                    weekly_counts_subquery.c.managed_narrative_id.asc(),
                    weekly_counts_subquery.c.week_start.asc(),
                )
            ).all()

            for narrative_id, week_start, matching_tweet_count in rows:
                normalized_week = floor_to_week(week_start.astimezone(UTC))
                index = week_index.get(normalized_week)
                if index is None:
                    continue
                counts_by_narrative_id[int(narrative_id)][index] = int(matching_tweet_count)

        narrative_payloads = []
        for narrative in narratives:
            weekly_counts = counts_by_narrative_id.get(narrative.id, [0] * len(weeks))
            total_matching_tweets = sum(weekly_counts)
            latest_period_count = weekly_counts[-1] if weekly_counts else 0
            peak_period_count = max(weekly_counts) if weekly_counts else 0
            peak_period_index = (
                weekly_counts.index(peak_period_count)
                if weekly_counts
                else None
            )
            peak_period_total_tweets = (
                weekly_total_tweet_counts[peak_period_index]
                if peak_period_index is not None
                else 0
            )
            peak_period_mention_rate = (
                max(
                    _safe_rate(matching_tweet_count, total_tweet_count)
                    for matching_tweet_count, total_tweet_count in zip(
                        weekly_counts,
                        weekly_total_tweet_counts,
                        strict=False,
                    )
                )
                if weekly_counts
                else 0.0
            )
            narrative_payloads.append(
                {
                    "id": int(narrative.id),
                    "slug": narrative.slug,
                    "name": narrative.name,
                    "phrase": narrative.phrase,
                    "summary": {
                        "total_matching_tweets": total_matching_tweets,
                        "total_tweet_count": total_tweets_in_range,
                        "total_mention_rate": _safe_rate(total_matching_tweets, total_tweets_in_range),
                        "latest_period_count": latest_period_count,
                        "latest_period_total_tweets": latest_period_total_tweets,
                        "latest_period_mention_rate": _safe_rate(
                            latest_period_count,
                            latest_period_total_tweets,
                        ),
                        "peak_period_count": peak_period_count,
                        "peak_period_total_tweets": peak_period_total_tweets,
                        "peak_period_mention_rate": peak_period_mention_rate,
                    },
                    "series": [
                        {
                            "period_start": week.isoformat().replace("+00:00", "Z"),
                            "matching_tweet_count": weekly_counts[index],
                            "total_tweet_count": weekly_total_tweet_counts[index],
                            "mention_rate": _safe_rate(
                                weekly_counts[index],
                                weekly_total_tweet_counts[index],
                            ),
                        }
                        for index, week in enumerate(weeks)
                    ],
                }
            )

        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": "aggregate-narratives",
                "username": "aggregate-narratives",
                "display_name": "Aggregate Narratives",
            },
            "cohort": {
                "user_count": len(cohort_usernames),
                "usernames": cohort_usernames,
                "total_tweet_count": total_tweets_in_range,
                "selection": cohort_selection,
            },
            "granularity": "week",
            "range": {
                "start": weeks[0].isoformat().replace("+00:00", "Z"),
                "end": weeks[-1].isoformat().replace("+00:00", "Z"),
            },
            "cohort_series": [
                {
                    "period_start": week.isoformat().replace("+00:00", "Z"),
                    "total_tweet_count": weekly_total_tweet_counts[index],
                }
                for index, week in enumerate(weeks)
            ],
            "default_narrative_slug": narrative_payloads[0]["slug"] if narrative_payloads else None,
            "narratives": narrative_payloads,
        }
    finally:
        session.close()


def build_cached_aggregate_narrative_view(
    request: AggregateNarrativeViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    granularity = request.granularity.strip().lower()
    if granularity == "week":
        snapshot = get_aggregate_snapshot(
            view_type=AGGREGATE_NARRATIVE_SERIES_VIEW_TYPE,
            cohort_tag_slug=request.cohort_tag_slug,
            granularity=granularity,
            model_key=MANAGED_NARRATIVE_MODEL_KEY,
            session_factory=session_factory,
        )
        if snapshot is not None and _aggregate_narrative_snapshot_supports_metric_toggle(snapshot):
            return snapshot

    payload = build_aggregate_narrative_view(request, session_factory=session_factory)
    if granularity == "week":
        generated_at = datetime.now(UTC)
        upsert_aggregate_snapshot(
            view_type=AGGREGATE_NARRATIVE_SERIES_VIEW_TYPE,
            cohort_tag_slug=request.cohort_tag_slug,
            granularity=granularity,
            model_key=MANAGED_NARRATIVE_MODEL_KEY,
            payload=payload,
            build_meta={
                "narrative_count": len(payload.get("narratives", [])),
                "refresh_reason": "cache_miss_or_schema_upgrade",
            },
            generated_at=generated_at,
            session_factory=session_factory,
        )
        return attach_generated_at(payload, generated_at=generated_at)

    return attach_generated_at(payload)


def rebuild_aggregate_narrative_snapshots(
    *,
    cohort_slugs: Iterable[str] | None = None,
    dry_run: bool = False,
    delete_stale: bool = True,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    started_at = datetime.now(UTC)
    cohort_payload = build_aggregate_narrative_cohorts(
        AggregateNarrativeCohortsRequest(),
        session_factory=session_factory,
    )
    available_cohort_slugs = sorted(
        cohort["tag_slug"] for cohort in cohort_payload.get("cohorts", []) if cohort.get("tag_slug")
    )
    requested_cohort_slugs = sorted(
        _normalize_requested_cohorts(cohort_slugs or [AGGREGATE_ALL_COHORT_SLUG, *available_cohort_slugs], available_cohort_slugs)
    )

    rebuilt_cache_keys: list[str] = []
    generated_at = datetime.now(UTC)

    if not dry_run:
        rebuilt_cache_keys.append(
            upsert_aggregate_snapshot(
                view_type=AGGREGATE_NARRATIVE_COHORTS_VIEW_TYPE,
                cohort_tag_slug=None,
                granularity="week",
                model_key=MANAGED_NARRATIVE_MODEL_KEY,
                payload=cohort_payload,
                generated_at=generated_at,
                session_factory=session_factory,
            )
        )
    else:
        rebuilt_cache_keys.append(
            f"dry-run:{AGGREGATE_NARRATIVE_COHORTS_VIEW_TYPE}:all"
        )

    for cohort_slug in requested_cohort_slugs:
        request_cohort_slug = None if cohort_slug == AGGREGATE_ALL_COHORT_SLUG else cohort_slug
        payload = build_aggregate_narrative_view(
            AggregateNarrativeViewRequest(
                granularity="week",
                cohort_tag_slug=request_cohort_slug,
                view_name="aggregate-narratives",
            ),
            session_factory=session_factory,
        )
        if dry_run:
            rebuilt_cache_keys.append(
                f"dry-run:{AGGREGATE_NARRATIVE_SERIES_VIEW_TYPE}:{cohort_slug}"
            )
            continue

        rebuilt_cache_keys.append(
            upsert_aggregate_snapshot(
                view_type=AGGREGATE_NARRATIVE_SERIES_VIEW_TYPE,
                cohort_tag_slug=request_cohort_slug,
                granularity="week",
                model_key=MANAGED_NARRATIVE_MODEL_KEY,
                payload=payload,
                build_meta={
                    "narrative_count": len(payload.get("narratives", [])),
                    "rebuilt_at": generated_at.isoformat().replace("+00:00", "Z"),
                },
                generated_at=generated_at,
                session_factory=session_factory,
            )
        )

    deleted_rows = 0
    if delete_stale and not dry_run:
        deleted_rows = delete_stale_aggregate_snapshots(
            model_key=MANAGED_NARRATIVE_MODEL_KEY,
            granularity="week",
            rebuilt_cache_keys=rebuilt_cache_keys,
            view_types=(
                AGGREGATE_NARRATIVE_COHORTS_VIEW_TYPE,
                AGGREGATE_NARRATIVE_SERIES_VIEW_TYPE,
            ),
            session_factory=session_factory,
        )

    return {
        "model_key": MANAGED_NARRATIVE_MODEL_KEY,
        "granularity": "week",
        "dry_run": dry_run,
        "requested_cohorts": requested_cohort_slugs,
        "rebuilt_cache_keys": rebuilt_cache_keys,
        "deleted_stale_rows": deleted_rows,
        "duration_seconds": round((datetime.now(UTC) - started_at).total_seconds(), 3),
    }


def _build_week_series(start: datetime, end: datetime) -> list[datetime]:
    weeks: list[datetime] = []
    current = start.astimezone(UTC)
    final = end.astimezone(UTC)
    while current <= final:
        weeks.append(current)
        current += timedelta(days=7)
    return weeks


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _aggregate_narrative_snapshot_supports_metric_toggle(snapshot: dict[str, object]) -> bool:
    narratives = snapshot.get("narratives")
    if not isinstance(narratives, list):
        return False
    if not narratives:
        return True

    first_narrative = narratives[0]
    if not isinstance(first_narrative, dict):
        return False

    summary = first_narrative.get("summary")
    if not isinstance(summary, dict) or "total_mention_rate" not in summary:
        return False

    series = first_narrative.get("series")
    if not isinstance(series, list):
        return False
    if not series:
        return True

    first_series_point = series[0]
    if not isinstance(first_series_point, dict):
        return False
    return "mention_rate" in first_series_point


def _resolve_aggregate_narrative_cohort_user_scope(
    session: Session,
    *,
    cohort_tag_slug: str | None,
) -> tuple[set[int], list[str], dict[str, object]]:
    eligible_rows = session.execute(
        select(User.id, User.username)
        .join(ManagedAuthorView, ManagedAuthorView.user_id == User.id)
        .join(Tweet, Tweet.author_user_id == User.id)
        .where(
            ManagedAuthorView.is_tracked.is_(True),
            ManagedAuthorView.published.is_(True),
        )
        .group_by(User.id, User.username)
        .order_by(func.lower(User.username).asc())
    ).all()
    if not eligible_rows:
        raise RuntimeError("No published tracked users with tweets are available for aggregate narratives.")

    eligible_user_ids = {int(user_id) for user_id, _username in eligible_rows}
    eligible_usernames = [username for _user_id, username in eligible_rows]
    if cohort_tag_slug is None:
        return (
            eligible_user_ids,
            eligible_usernames,
            {
                "type": "all",
                "tag_slug": None,
                "tag_name": "All tracked users",
            },
        )

    normalized_slug = cohort_tag_slug.strip().lower()
    if not normalized_slug:
        return (
            eligible_user_ids,
            eligible_usernames,
            {
                "type": "all",
                "tag_slug": None,
                "tag_name": "All tracked users",
            },
        )

    cohort_tag = session.scalar(select(CohortTag).where(CohortTag.slug == normalized_slug))
    if cohort_tag is None:
        raise RuntimeError(f"Unknown aggregate cohort tag slug={normalized_slug!r}.")

    filtered_rows = session.execute(
        select(User.id, User.username)
        .join(UserCohortTag, UserCohortTag.user_id == User.id)
        .where(
            UserCohortTag.cohort_tag_id == cohort_tag.id,
            User.id.in_(eligible_user_ids),
        )
        .order_by(func.lower(User.username).asc())
    ).all()
    filtered_user_ids = {int(user_id) for user_id, _username in filtered_rows}
    filtered_usernames = [username for _user_id, username in filtered_rows]
    if not filtered_user_ids:
        raise RuntimeError(
            f"No tracked users with tweets are assigned to aggregate cohort tag slug={normalized_slug!r}."
        )

    return (
        filtered_user_ids,
        filtered_usernames,
        {
            "type": "tag",
            "tag_slug": cohort_tag.slug,
            "tag_name": cohort_tag.name,
        },
    )


def _load_aggregate_narrative_eligible_user_ids(session: Session) -> set[int]:
    rows = session.execute(
        select(User.id)
        .join(ManagedAuthorView, ManagedAuthorView.user_id == User.id)
        .join(Tweet, Tweet.author_user_id == User.id)
        .where(
            ManagedAuthorView.is_tracked.is_(True),
            ManagedAuthorView.published.is_(True),
        )
        .group_by(User.id)
    ).all()
    return {int(row.id) for row in rows}


def _normalize_requested_cohorts(
    requested_cohorts: Iterable[str],
    available_cohort_slugs: Iterable[str],
) -> set[str]:
    normalized_available = {slug.strip().lower() for slug in available_cohort_slugs if slug.strip()}
    normalized_requested = {slug.strip().lower() for slug in requested_cohorts if slug.strip()}
    invalid = sorted(
        slug
        for slug in normalized_requested
        if slug != AGGREGATE_ALL_COHORT_SLUG and slug not in normalized_available
    )
    if invalid:
        raise RuntimeError(f"Unknown aggregate narrative cohort slug(s) requested: {invalid!r}.")
    return normalized_requested
