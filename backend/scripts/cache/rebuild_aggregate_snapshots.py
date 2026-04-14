import argparse
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from pprint import pprint
import time
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.aggregate_mood_view import (
    AggregateMoodCohortsRequest,
    AggregateMoodOverviewRequest,
    AggregateMoodViewRequest,
    build_aggregate_mood_cohorts,
    build_aggregate_mood_overview,
    build_aggregate_mood_view,
)
from app.services.aggregate_snapshot_cache import (
    AGGREGATE_COHORTS_VIEW_TYPE,
    AGGREGATE_MOOD_SERIES_VIEW_TYPE,
    AGGREGATE_OVERVIEW_VIEW_TYPE,
    AGGREGATE_SNAPSHOT_CACHE_VERSION,
    build_aggregate_snapshot_cache_key,
    delete_stale_aggregate_snapshots,
    upsert_aggregate_snapshot,
)
from app.services.author_registry import rebuild_public_author_registry_snapshot
from app.services.moods import DEFAULT_MOOD_MODEL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild cached aggregate mood snapshot payloads in Postgres."
    )
    parser.add_argument(
        "--model-key",
        default=DEFAULT_MOOD_MODEL,
        help="Mood model key to rebuild snapshots for.",
    )
    parser.add_argument(
        "--granularity",
        choices=["week"],
        default="week",
        help="Granularity to cache. Only week is supported in the snapshot rebuild flow.",
    )
    parser.add_argument(
        "--cohort",
        action="append",
        dest="cohorts",
        help="Optional cohort slug to rebuild. Repeat to target multiple cohorts.",
    )
    parser.add_argument(
        "--view",
        action="append",
        dest="views",
        choices=[
            AGGREGATE_COHORTS_VIEW_TYPE,
            AGGREGATE_OVERVIEW_VIEW_TYPE,
            AGGREGATE_MOOD_SERIES_VIEW_TYPE,
        ],
        help="Optional view type to rebuild. Repeat to target multiple view types.",
    )
    parser.add_argument(
        "--clear-first",
        action="store_true",
        help=(
            "Delete existing snapshot rows for this model/granularity before rebuilding. "
            "Only supported for full rebuilds without --cohort or --view."
        ),
    )
    parser.add_argument(
        "--delete-stale",
        action="store_true",
        help="Delete stale snapshot rows for this model/granularity after a full rebuild.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which snapshot keys would be rebuilt without writing them.",
    )
    parser.add_argument(
        "--no-bell",
        action="store_true",
        help="Do not emit a terminal bell when the rebuild finishes.",
    )
    parser.add_argument(
        "--author-registry",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also rebuild the cached public author-registry payload.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.delete_stale and (args.cohorts or args.views):
        raise RuntimeError("--delete-stale only supports full rebuilds without --cohort or --view.")
    if args.clear_first and (args.cohorts or args.views):
        raise RuntimeError("--clear-first only supports full rebuilds without --cohort or --view.")

    requested_views = tuple(
        args.views
        or [
            AGGREGATE_COHORTS_VIEW_TYPE,
            AGGREGATE_OVERVIEW_VIEW_TYPE,
            AGGREGATE_MOOD_SERIES_VIEW_TYPE,
        ]
    )

    started_at = datetime.now(UTC)
    generated_at = datetime.now(UTC)
    cleared_rows = 0
    rebuilt_cache_keys: list[str] = []

    if args.clear_first and not args.dry_run:
        print("Clearing existing aggregate snapshot rows before rebuild...", flush=True)
        cleared_rows = delete_stale_aggregate_snapshots(
            model_key=args.model_key,
            granularity=args.granularity,
            rebuilt_cache_keys=(),
            view_types=requested_views,
        )

    cohort_payload = build_aggregate_mood_cohorts(
        AggregateMoodCohortsRequest(
            model_key=args.model_key,
            view_name="aggregate-moods-cohorts",
        )
    )
    available_cohort_slugs = sorted(
        cohort["tag_slug"] for cohort in cohort_payload.get("cohorts", []) if cohort.get("tag_slug")
    )
    requested_cohorts = sorted(
        _normalize_requested_cohorts(
            args.cohorts or ["all", *available_cohort_slugs],
            available_cohort_slugs,
        )
    )
    task_specs = _build_task_specs(
        requested_views=requested_views,
        requested_cohorts=requested_cohorts,
        granularity=args.granularity,
        model_key=args.model_key,
        generated_at=generated_at,
        cohort_payload=cohort_payload,
    )

    print(
        (
            f"Starting aggregate snapshot rebuild: {len(task_specs)} snapshot task(s), "
            f"model_key={args.model_key}, granularity={args.granularity}, "
            f"dry_run={args.dry_run}"
        ),
        flush=True,
    )

    for index, task_spec in enumerate(task_specs, start=1):
        task_started_at = time.perf_counter()
        percent_complete = (index - 1) / len(task_specs) * 100 if task_specs else 100.0
        print(
            f"[{index}/{len(task_specs)}] {percent_complete:5.1f}% starting "
            f"{task_spec['view_type']} ({task_spec['cohort_tag_slug']})",
            flush=True,
        )
        cache_key = _execute_task(task_spec=task_spec, dry_run=args.dry_run)
        rebuilt_cache_keys.append(cache_key)
        task_duration_seconds = time.perf_counter() - task_started_at
        completed_percent = index / len(task_specs) * 100 if task_specs else 100.0
        print(
            f"[{index}/{len(task_specs)}] {completed_percent:5.1f}% finished "
            f"{task_spec['view_type']} ({task_spec['cohort_tag_slug']}) in "
            f"{task_duration_seconds:.2f}s",
            flush=True,
        )

    deleted_rows = 0
    author_registry_snapshot = None
    if args.delete_stale and not args.dry_run:
        print("Deleting stale aggregate snapshot rows...", flush=True)
        deleted_rows = delete_stale_aggregate_snapshots(
            model_key=args.model_key,
            granularity=args.granularity,
            rebuilt_cache_keys=rebuilt_cache_keys,
            view_types=requested_views,
        )

    if args.author_registry:
        print("Rebuilding author registry snapshot...", flush=True)
        author_registry_snapshot = rebuild_public_author_registry_snapshot(dry_run=args.dry_run)

    pprint(
        {
            "model_key": args.model_key,
            "granularity": args.granularity,
            "cache_version": AGGREGATE_SNAPSHOT_CACHE_VERSION,
            "dry_run": args.dry_run,
            "requested_views": list(requested_views),
            "requested_cohorts": requested_cohorts,
            "cleared_rows_before_rebuild": cleared_rows,
            "rebuilt_cache_keys": rebuilt_cache_keys,
            "author_registry_snapshot": author_registry_snapshot,
            "deleted_stale_rows": deleted_rows,
            "duration_seconds": round((datetime.now(UTC) - started_at).total_seconds(), 3),
        }
    )
    if not args.no_bell:
        sys.stdout.write("\a")
        sys.stdout.flush()


def _normalize_requested_cohorts(
    requested_cohorts: Iterable[str],
    available_cohort_slugs: Iterable[str],
) -> set[str]:
    normalized_available = {slug.strip().lower() for slug in available_cohort_slugs if slug.strip()}
    normalized_requested = {slug.strip().lower() for slug in requested_cohorts if slug.strip()}
    invalid = sorted(slug for slug in normalized_requested if slug != "all" and slug not in normalized_available)
    if invalid:
        raise RuntimeError(f"Unknown cohort slug(s) requested for snapshot rebuild: {invalid!r}.")
    return normalized_requested


def _build_task_specs(
    *,
    requested_views: tuple[str, ...],
    requested_cohorts: list[str],
    granularity: str,
    model_key: str,
    generated_at: datetime,
    cohort_payload: dict[str, object],
) -> list[dict[str, object]]:
    task_specs: list[dict[str, object]] = []

    if AGGREGATE_COHORTS_VIEW_TYPE in requested_views:
        task_specs.append(
            {
                "view_type": AGGREGATE_COHORTS_VIEW_TYPE,
                "cohort_tag_slug": "all",
                "granularity": granularity,
                "model_key": model_key,
                "payload_builder": lambda: cohort_payload,
                "build_meta_builder": lambda payload: {
                    "cohort_count": len(payload.get("cohorts", [])),
                    "rebuilt_at": generated_at.isoformat().replace("+00:00", "Z"),
                },
                "generated_at": generated_at,
            }
        )

    for cohort_slug in requested_cohorts:
        request_cohort_slug = None if cohort_slug == "all" else cohort_slug
        if AGGREGATE_OVERVIEW_VIEW_TYPE in requested_views:
            task_specs.append(
                {
                    "view_type": AGGREGATE_OVERVIEW_VIEW_TYPE,
                    "cohort_tag_slug": cohort_slug,
                    "granularity": granularity,
                    "model_key": model_key,
                    "payload_builder": lambda request_cohort_slug=request_cohort_slug: build_aggregate_mood_overview(
                        AggregateMoodOverviewRequest(
                            granularity=granularity,
                            model_key=model_key,
                            view_name="aggregate-moods",
                            analysis_start="2016-01-01T00:00:00Z",
                            cohort_tag_slug=request_cohort_slug,
                        )
                    ),
                    "build_meta_builder": lambda payload: {
                        "cohort_user_count": payload["cohort"]["user_count"],
                        "rebuilt_at": generated_at.isoformat().replace("+00:00", "Z"),
                    },
                    "generated_at": generated_at,
                }
            )

        if AGGREGATE_MOOD_SERIES_VIEW_TYPE in requested_views:
            task_specs.append(
                {
                    "view_type": AGGREGATE_MOOD_SERIES_VIEW_TYPE,
                    "cohort_tag_slug": cohort_slug,
                    "granularity": granularity,
                    "model_key": model_key,
                    "payload_builder": lambda request_cohort_slug=request_cohort_slug: build_aggregate_mood_view(
                        AggregateMoodViewRequest(
                            granularity=granularity,
                            model_key=model_key,
                            view_name="aggregate-moods-mood-series",
                            analysis_start="2016-01-01T00:00:00Z",
                            cohort_tag_slug=request_cohort_slug,
                        )
                    ),
                    "build_meta_builder": lambda payload: {
                        "cohort_user_count": payload["summary"]["cohort_user_count"],
                        "scored_tweet_count": payload["summary"]["scored_tweet_count"],
                        "rebuilt_at": generated_at.isoformat().replace("+00:00", "Z"),
                    },
                    "generated_at": generated_at,
                }
            )

    return task_specs


def _execute_task(
    *,
    task_spec: dict[str, object],
    dry_run: bool,
) -> str:
    payload = task_spec["payload_builder"]()
    build_meta = task_spec["build_meta_builder"](payload)
    return _write_snapshot(
        dry_run=dry_run,
        view_type=task_spec["view_type"],
        cohort_tag_slug=task_spec["cohort_tag_slug"],
        granularity=task_spec["granularity"],
        model_key=task_spec["model_key"],
        payload=payload,
        generated_at=task_spec["generated_at"],
        build_meta=build_meta,
    )


def _write_snapshot(
    *,
    dry_run: bool,
    view_type: str,
    cohort_tag_slug: str,
    granularity: str,
    model_key: str,
    payload: dict[str, object],
    generated_at: datetime,
    build_meta: dict[str, object],
) -> str:
    cache_key = build_aggregate_snapshot_cache_key(
        view_type=view_type,
        cohort_tag_slug=cohort_tag_slug,
        granularity=granularity,
        model_key=model_key,
    )
    if dry_run:
        return cache_key

    return upsert_aggregate_snapshot(
        view_type=view_type,
        cohort_tag_slug=cohort_tag_slug,
        granularity=granularity,
        model_key=model_key,
        payload=payload,
        generated_at=generated_at,
        build_meta=build_meta,
    )


if __name__ == "__main__":
    main()
