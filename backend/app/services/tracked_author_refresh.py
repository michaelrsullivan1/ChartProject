from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.managed_author_view import ManagedAuthorView
from app.models.user import User
from app.services.author_registry import _build_mood_scored_tracking_summary
from app.services.moods import DEFAULT_MOOD_MODEL


REPO_ROOT = Path(__file__).resolve().parents[3]
REFRESH_PLAN_DIR = REPO_ROOT / "data" / "exports" / "refresh-plans"
ADVANCED_SEARCH_ENDPOINT_NAME = "tweet_advanced_search_raw_archive"


def ensure_refresh_plan_dir() -> Path:
    REFRESH_PLAN_DIR.mkdir(parents=True, exist_ok=True)
    return REFRESH_PLAN_DIR


def build_default_refresh_plan_path(*, started_at: datetime) -> Path:
    timestamp = _to_filename_timestamp(started_at)
    return ensure_refresh_plan_dir() / f"tracked-author-refresh-plan-{timestamp}.json"


def build_default_fetch_results_path(*, plan_path: Path) -> Path:
    return plan_path.with_name(f"{plan_path.stem}.fetch-results.json")


def build_default_post_process_results_path(*, fetch_results_path: Path) -> Path:
    return fetch_results_path.with_name(f"{fetch_results_path.stem}.post-process-results.json")


def write_json_payload(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=False)}\n", encoding="utf-8")
    return path


def load_json_payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_iso_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).astimezone(UTC)


def build_tracked_author_refresh_plan(
    *,
    plan_started_at: datetime | None = None,
    window_months: int = 1,
    page_delay_seconds: float = 0.025,
    max_retries: int = 3,
    retry_backoff_seconds: float = 1.0,
    query_fragment: str = "",
    import_type: str = "refresh",
    skip_user_info: bool = True,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    started_at = (plan_started_at or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
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
        mood_scored_tracking_summary = _build_mood_scored_tracking_summary(
            session,
            model_key=DEFAULT_MOOD_MODEL,
        )

        planned_items: list[dict[str, object]] = []
        manual_history_required: list[dict[str, object]] = []
        up_to_date_items: list[dict[str, object]] = []

        for managed_author, user in rows:
            latest_requested_until = _load_latest_completed_requested_until(
                session,
                username=user.username,
                target_user_platform_id=user.platform_user_id,
            )

            if latest_requested_until is None:
                manual_history_required.append(
                    {
                        "username": user.username,
                        "slug": managed_author.slug,
                        "platform_user_id": user.platform_user_id,
                        "reason": "missing_successful_advanced_search_history",
                    }
                )
                continue

            if latest_requested_until >= started_at:
                up_to_date_items.append(
                    {
                        "username": user.username,
                        "slug": managed_author.slug,
                        "platform_user_id": user.platform_user_id,
                        "since": _to_iso(latest_requested_until),
                        "until": _to_iso(started_at),
                        "reason": "no_gap_since_last_successful_search_window",
                    }
                )
                continue

            planned_items.append(
                {
                    "username": user.username,
                    "slug": managed_author.slug,
                    "platform_user_id": user.platform_user_id,
                    "latest_completed_requested_until": _to_iso(latest_requested_until),
                    "since": _to_iso(latest_requested_until),
                    "until": _to_iso(started_at),
                    "gap_seconds": int((started_at - latest_requested_until).total_seconds()),
                    "window_months": window_months,
                    "query_fragment": query_fragment,
                    "import_type": import_type,
                    "page_delay_seconds": page_delay_seconds,
                    "max_retries": max_retries,
                    "retry_backoff_seconds": retry_backoff_seconds,
                    "skip_user_info": skip_user_info,
                    "command": _build_fetch_command_preview(
                        username=user.username,
                        since=latest_requested_until,
                        until=started_at,
                        window_months=window_months,
                        page_delay_seconds=page_delay_seconds,
                        query_fragment=query_fragment,
                        import_type=import_type,
                        max_retries=max_retries,
                        retry_backoff_seconds=retry_backoff_seconds,
                        skip_user_info=skip_user_info,
                        target_user_platform_id=user.platform_user_id,
                    ),
                }
            )

        return {
            "view": "tracked-author-refresh-plan",
            "generated_at": _to_iso(datetime.now(UTC)),
            "plan_started_at": _to_iso(started_at),
            "tracked_author_count": len(rows),
            "mood_scored_tracking_summary": mood_scored_tracking_summary,
            "planned_count": len(planned_items),
            "manual_full_history_required_count": len(manual_history_required),
            "up_to_date_count": len(up_to_date_items),
            "planned": planned_items,
            "manual_full_history_required": manual_history_required,
            "up_to_date": up_to_date_items,
        }
    finally:
        session.close()


def load_tracked_author_by_username(
    session: Session,
    *,
    username: str,
) -> tuple[ManagedAuthorView, User]:
    row = session.execute(
        select(ManagedAuthorView, User)
        .join(User, User.id == ManagedAuthorView.user_id)
        .where(
            ManagedAuthorView.is_tracked.is_(True),
            ManagedAuthorView.published.is_(True),
            func.lower(User.username) == username.strip().lower(),
        )
    ).first()
    if row is None:
        raise RuntimeError(f"No published tracked author was found for username={username!r}.")
    return row


def summarize_refresh_fetch_runs(
    session: Session,
    *,
    username: str,
    target_user_platform_id: str,
    planned_since: datetime,
    planned_until: datetime,
    started_at_floor: datetime,
) -> dict[str, object]:
    rows = session.execute(
        select(IngestionRun)
        .where(
            IngestionRun.endpoint_name == ADVANCED_SEARCH_ENDPOINT_NAME,
            IngestionRun.status == "completed",
            IngestionRun.import_type == "refresh",
            IngestionRun.started_at >= started_at_floor,
            IngestionRun.requested_since >= planned_since,
            IngestionRun.requested_until <= planned_until,
            or_(
                IngestionRun.target_user_platform_id == target_user_platform_id,
                func.lower(IngestionRun.notes).like(
                    _build_advanced_search_notes_username_like(username)
                ),
            ),
        )
        .order_by(IngestionRun.requested_since.asc(), IngestionRun.id.asc())
    ).scalars().all()

    return {
        "completed_window_run_count": len(rows),
        "pages_fetched": sum(int(run.pages_fetched or 0) for run in rows),
        "raw_tweets_fetched": sum(int(run.raw_tweets_fetched or 0) for run in rows),
        "run_ids": [int(run.id) for run in rows],
    }


def _load_latest_completed_requested_until(
    session: Session,
    *,
    username: str,
    target_user_platform_id: str | None,
) -> datetime | None:
    if target_user_platform_id:
        latest = session.scalar(
            select(func.max(IngestionRun.requested_until)).where(
                IngestionRun.endpoint_name == ADVANCED_SEARCH_ENDPOINT_NAME,
                IngestionRun.status == "completed",
                IngestionRun.requested_until.is_not(None),
                IngestionRun.target_user_platform_id == target_user_platform_id,
            )
        )
        if latest is not None:
            return latest

    return session.scalar(
        select(func.max(IngestionRun.requested_until)).where(
            IngestionRun.endpoint_name == ADVANCED_SEARCH_ENDPOINT_NAME,
            IngestionRun.status == "completed",
            IngestionRun.requested_until.is_not(None),
            func.lower(IngestionRun.notes).like(_build_advanced_search_notes_username_like(username)),
        )
    )


def _build_fetch_command_preview(
    *,
    username: str,
    since: datetime,
    until: datetime,
    window_months: int,
    page_delay_seconds: float,
    query_fragment: str,
    import_type: str,
    max_retries: int,
    retry_backoff_seconds: float,
    skip_user_info: bool,
    target_user_platform_id: str | None = None,
) -> list[str]:
    command = [
        "python3",
        "backend/scripts/ingest/fetch_user_tweets_history.py",
        "--username",
        username,
        "--since",
        _to_iso(since),
        "--until",
        _to_iso(until),
        "--window-months",
        str(window_months),
        "--page-delay-seconds",
        str(page_delay_seconds),
        "--import-type",
        import_type,
        "--max-retries",
        str(max_retries),
        "--retry-backoff-seconds",
        str(retry_backoff_seconds),
    ]
    if target_user_platform_id:
        command.extend(["--target-user-platform-id", target_user_platform_id])
    if query_fragment:
        command.extend(["--query-fragment", query_fragment])
    if skip_user_info:
        command.append("--skip-user-info")
    return command


def _build_advanced_search_notes_username_like(username: str) -> str:
    return f"%query 'from:{username.strip().lower()}%since:%"


def _to_filename_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _to_iso(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
