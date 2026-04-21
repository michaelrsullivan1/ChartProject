import argparse
from datetime import UTC, datetime
from pathlib import Path
from pprint import pprint
import subprocess
import sys
import time

from sqlalchemy import func, select

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.user import User
from app.services.tracked_author_refresh import (
    build_default_post_process_results_path,
    load_json_payload,
    write_json_payload,
)


REPO_ROOT = BACKEND_ROOT.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run tracked-author post-processing for successful refresh fetches with nonzero new "
            "raw tweets."
        )
    )
    parser.add_argument(
        "--fetch-results",
        required=True,
        help="Path to a tracked-author refresh fetch-results JSON file.",
    )
    parser.add_argument(
        "--output",
        help="Optional path for the post-process results JSON manifest. Defaults next to fetch-results.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the usernames that would be post-processed without running the batch steps.",
    )
    parser.add_argument(
        "--skip-keywords",
        action="store_true",
        help="Skip keyword extraction. Faster, but managed narrative matching may be stale.",
    )
    parser.add_argument(
        "--skip-managed-author-sync",
        action="store_true",
        help="Skip per-user managed author sync and author-registry snapshot rebuild.",
    )
    parser.add_argument(
        "--skip-managed-narrative-sync",
        action="store_true",
        help="Skip per-user managed narrative match sync and aggregate narrative snapshot rebuild.",
    )
    parser.add_argument(
        "--skip-author-registry-snapshot",
        action="store_true",
        help="Skip author-registry snapshot rebuild at the end of post-process.",
    )
    parser.add_argument(
        "--skip-aggregate-narrative-snapshot",
        action="store_true",
        help="Skip aggregate narrative snapshot rebuild at the end of post-process.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    overall_started_at = datetime.now(UTC).replace(microsecond=0)
    fetch_results_path = Path(args.fetch_results).expanduser().resolve()
    fetch_results_payload = load_json_payload(fetch_results_path)
    if fetch_results_payload.get("view") != "tracked-author-refresh-fetch-results":
        raise SystemExit(f"{fetch_results_path} is not a tracked-author refresh fetch-results manifest.")

    results_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else build_default_post_process_results_path(fetch_results_path=fetch_results_path)
    )

    all_results = list(fetch_results_payload.get("results", []))
    eligible_items = [
        item
        for item in all_results
        if item.get("status") == "completed" and bool(item.get("new_raw_tweets", 0) > 0)
    ]

    results_by_username: dict[str, dict[str, object]] = {}
    ordered_usernames: list[str] = []
    preprocess_ready_usernames: list[str] = []
    keyword_and_sync_ready_usernames: list[str] = []
    stage_elapsed_seconds: dict[str, float] = {}

    for item in eligible_items:
        username = str(item["username"])
        ordered_usernames.append(username)
        results_by_username[username] = {
            "username": username,
            "slug": item["slug"],
            "new_raw_tweets": item["new_raw_tweets"],
            "status": "planned",
        }

    if args.dry_run:
        for index, username in enumerate(ordered_usernames, start=1):
            print(f"[{index}/{len(ordered_usernames)}] Would post-process @{username}")
        payload = _build_payload(
            results_by_username=results_by_username,
            ordered_usernames=ordered_usernames,
            overall_started_at=overall_started_at,
            fetch_results_path=fetch_results_path,
            dry_run=True,
            eligible_count=len(eligible_items),
            author_registry_snapshot_rebuild=None,
            aggregate_narrative_snapshot_rebuild=None,
            stage_elapsed_seconds=stage_elapsed_seconds,
        )
        write_json_payload(results_path, payload)
        _print_summary(results_path=results_path, payload=payload)
        return

    for index, username in enumerate(ordered_usernames, start=1):
        result = results_by_username[username]
        result["started_at"] = _to_iso(datetime.now(UTC))
        print(f"[{index}/{len(ordered_usernames)}] Normalizing and validating @{username}")

        normalize_command = [
            "python3",
            "backend/scripts/normalize/normalize_archived_user.py",
            "--username",
            username,
        ]
        normalize_exit_code, normalize_elapsed = _run_command(normalize_command)
        _record_stage_elapsed(stage_elapsed_seconds, "normalize_archived_user", normalize_elapsed)
        result["normalize_exit_code"] = normalize_exit_code
        if normalize_exit_code != 0:
            _mark_failed(result, failed_step="normalize_archived_user", exit_code=normalize_exit_code)
            continue

        validate_command = [
            "python3",
            "backend/scripts/validate/validate_normalized_user.py",
            "--username",
            username,
        ]
        validate_exit_code, validate_elapsed = _run_command(validate_command)
        _record_stage_elapsed(stage_elapsed_seconds, "validate_normalized_user", validate_elapsed)
        result["validate_exit_code"] = validate_exit_code
        if validate_exit_code != 0:
            _mark_failed(result, failed_step="validate_normalized_user", exit_code=validate_exit_code)
            continue

        result["normalized"] = True
        result["validated"] = True
        preprocess_ready_usernames.append(username)

    if preprocess_ready_usernames:
        print(
            f"\nBatch scoring sentiment for {len(preprocess_ready_usernames)} "
            f"users with one model load"
        )
        sentiment_exit_code, sentiment_elapsed = _run_command(
            [
                "python3",
                "backend/scripts/enrich/score_tweet_sentiment.py",
                "--username",
                *preprocess_ready_usernames,
            ]
        )
        _record_stage_elapsed(stage_elapsed_seconds, "score_tweet_sentiment_batch", sentiment_elapsed)
        if sentiment_exit_code != 0:
            for username in preprocess_ready_usernames:
                _mark_failed(
                    results_by_username[username],
                    failed_step="score_tweet_sentiment",
                    exit_code=sentiment_exit_code,
                )
        else:
            print(
                f"\nBatch scoring moods for {len(preprocess_ready_usernames)} "
                f"users with one model load"
            )
            moods_exit_code, moods_elapsed = _run_command(
                [
                    "python3",
                    "backend/scripts/enrich/score_tweet_moods.py",
                    "--username",
                    *preprocess_ready_usernames,
                ]
            )
            _record_stage_elapsed(stage_elapsed_seconds, "score_tweet_moods_batch", moods_elapsed)
            if moods_exit_code != 0:
                for username in preprocess_ready_usernames:
                    _mark_failed(
                        results_by_username[username],
                        failed_step="score_tweet_moods",
                        exit_code=moods_exit_code,
                    )
            else:
                for username in preprocess_ready_usernames:
                    result = results_by_username[username]
                    result["sentiment_scored"] = True
                    result["moods_scored"] = True
                    keyword_and_sync_ready_usernames.append(username)

    managed_author_synced_usernames: list[str] = []
    managed_narratives_synced_usernames: list[str] = []
    for index, username in enumerate(keyword_and_sync_ready_usernames, start=1):
        result = results_by_username[username]
        print(f"\n[{index}/{len(keyword_and_sync_ready_usernames)}] Post-processing @{username}")

        if args.skip_keywords:
            result["keywords_extracted"] = False
            result["keywords_skipped"] = True
        else:
            try:
                analysis_start_started = time.perf_counter()
                analysis_start = _resolve_first_tweet_analysis_start(username)
                _record_stage_elapsed(
                    stage_elapsed_seconds,
                    "resolve_keyword_analysis_start",
                    time.perf_counter() - analysis_start_started,
                )
            except Exception as exc:
                _mark_failed(
                    result,
                    failed_step="resolve_keyword_analysis_start",
                    exit_code=1,
                    error_message=str(exc),
                )
                continue

            result["analysis_start"] = analysis_start
            keyword_exit_code, keyword_elapsed = _run_command(
                [
                    "python3",
                    "backend/scripts/enrich/extract_tweet_keywords.py",
                    "--username",
                    username,
                    "--analysis-start",
                    analysis_start,
                ]
            )
            _record_stage_elapsed(stage_elapsed_seconds, "extract_tweet_keywords", keyword_elapsed)
            result["keyword_exit_code"] = keyword_exit_code
            if keyword_exit_code != 0:
                _mark_failed(result, failed_step="extract_tweet_keywords", exit_code=keyword_exit_code)
                continue

            result["keywords_extracted"] = True

        if args.skip_managed_author_sync:
            result["managed_author_synced"] = False
            result["managed_author_sync_skipped"] = True
        else:
            sync_exit_code, author_sync_elapsed = _run_command(
                [
                    "python3",
                    "backend/scripts/views/sync_managed_author_view.py",
                    "--username",
                    username,
                    "--published",
                    "--no-rebuild-snapshot",
                ]
            )
            _record_stage_elapsed(stage_elapsed_seconds, "sync_managed_author_view", author_sync_elapsed)
            result["sync_managed_author_view_exit_code"] = sync_exit_code
            if sync_exit_code != 0:
                _mark_failed(result, failed_step="sync_managed_author_view", exit_code=sync_exit_code)
                continue
            result["managed_author_synced"] = True
            managed_author_synced_usernames.append(username)

        if args.skip_managed_narrative_sync:
            result["managed_narratives_synced"] = False
            result["managed_narrative_sync_skipped"] = True
        else:
            narrative_exit_code, narrative_sync_elapsed = _run_command(
                [
                    "python3",
                    "backend/scripts/enrich/sync_managed_narrative_matches.py",
                    "--username",
                    username,
                ]
            )
            _record_stage_elapsed(
                stage_elapsed_seconds,
                "sync_managed_narrative_matches",
                narrative_sync_elapsed,
            )
            result["sync_managed_narrative_matches_exit_code"] = narrative_exit_code
            if narrative_exit_code != 0:
                _mark_failed(
                    result,
                    failed_step="sync_managed_narrative_matches",
                    exit_code=narrative_exit_code,
                )
                continue
            result["managed_narratives_synced"] = True
            managed_narratives_synced_usernames.append(username)

        result["status"] = "completed"
        result["completed_at"] = _to_iso(datetime.now(UTC))

    author_registry_snapshot_rebuild: dict[str, object] | None = None
    aggregate_narrative_snapshot_rebuild: dict[str, object] | None = None
    if managed_author_synced_usernames and not args.skip_author_registry_snapshot:
        print(
            f"\nRebuilding author registry snapshot once after syncing "
            f"{len(managed_author_synced_usernames)} users"
        )
        snapshot_exit_code, author_snapshot_elapsed = _run_command(
            [
                "python3",
                "backend/scripts/cache/rebuild_author_registry_snapshot.py",
            ]
        )
        _record_stage_elapsed(
            stage_elapsed_seconds,
            "rebuild_author_registry_snapshot",
            author_snapshot_elapsed,
        )
        author_registry_snapshot_rebuild = {
            "status": "completed" if snapshot_exit_code == 0 else "failed",
            "exit_code": snapshot_exit_code,
            "synced_user_count": len(managed_author_synced_usernames),
        }

    if managed_narratives_synced_usernames and not args.skip_aggregate_narrative_snapshot:
        print(
            "Rebuilding aggregate narrative snapshots once after syncing "
            f"{len(managed_narratives_synced_usernames)} users"
        )
        aggregate_narrative_snapshot_exit_code, aggregate_narrative_snapshot_elapsed = _run_command(
            [
                "python3",
                "backend/scripts/cache/rebuild_aggregate_narrative_snapshots.py",
            ]
        )
        _record_stage_elapsed(
            stage_elapsed_seconds,
            "rebuild_aggregate_narrative_snapshots",
            aggregate_narrative_snapshot_elapsed,
        )
        aggregate_narrative_snapshot_rebuild = {
            "status": "completed" if aggregate_narrative_snapshot_exit_code == 0 else "failed",
            "exit_code": aggregate_narrative_snapshot_exit_code,
            "synced_user_count": len(managed_narratives_synced_usernames),
        }

    payload = _build_payload(
        results_by_username=results_by_username,
        ordered_usernames=ordered_usernames,
        overall_started_at=overall_started_at,
        fetch_results_path=fetch_results_path,
        dry_run=False,
        eligible_count=len(eligible_items),
        author_registry_snapshot_rebuild=author_registry_snapshot_rebuild,
        aggregate_narrative_snapshot_rebuild=aggregate_narrative_snapshot_rebuild,
        stage_elapsed_seconds=stage_elapsed_seconds,
    )
    write_json_payload(results_path, payload)
    _print_summary(results_path=results_path, payload=payload)


def _build_payload(
    *,
    results_by_username: dict[str, dict[str, object]],
    ordered_usernames: list[str],
    overall_started_at: datetime,
    fetch_results_path: Path,
    dry_run: bool,
    eligible_count: int,
    author_registry_snapshot_rebuild: dict[str, object] | None,
    aggregate_narrative_snapshot_rebuild: dict[str, object] | None,
    stage_elapsed_seconds: dict[str, float],
) -> dict[str, object]:
    results = [results_by_username[username] for username in ordered_usernames]
    success_count = sum(1 for item in results if item.get("status") == "completed")
    failure_count = sum(1 for item in results if item.get("status") == "failed")
    overall_completed_at = datetime.now(UTC).replace(microsecond=0)
    return {
        "view": "tracked-author-refresh-post-process-results",
        "generated_at": _to_iso(datetime.now(UTC)),
        "started_at": _to_iso(overall_started_at),
        "completed_at": _to_iso(overall_completed_at),
        "elapsed_seconds": int((overall_completed_at - overall_started_at).total_seconds()),
        "fetch_results_path": str(fetch_results_path),
        "dry_run": dry_run,
        "eligible_count": eligible_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "author_registry_snapshot_rebuild": author_registry_snapshot_rebuild,
        "aggregate_narrative_snapshot_rebuild": aggregate_narrative_snapshot_rebuild,
        "stage_elapsed_seconds": stage_elapsed_seconds,
        "results": results,
    }


def _print_summary(*, results_path: Path, payload: dict[str, object]) -> None:
    print(f"\nTracked author refresh post-process results written to {results_path}")
    summary = {
        "eligible_count": payload["eligible_count"],
        "success_count": payload["success_count"],
        "failure_count": payload["failure_count"],
        "elapsed": _format_elapsed_seconds(int(payload["elapsed_seconds"])),
    }
    snapshot_rebuild = payload.get("author_registry_snapshot_rebuild")
    if isinstance(snapshot_rebuild, dict):
        summary["author_registry_snapshot_rebuild"] = snapshot_rebuild["status"]
    aggregate_narrative_snapshot_rebuild = payload.get("aggregate_narrative_snapshot_rebuild")
    if isinstance(aggregate_narrative_snapshot_rebuild, dict):
        summary["aggregate_narrative_snapshot_rebuild"] = aggregate_narrative_snapshot_rebuild["status"]
    summary["top_elapsed_stages"] = _top_elapsed_stages(payload.get("stage_elapsed_seconds", {}), limit=8)
    pprint(summary)

    failed = [item for item in payload["results"] if item.get("status") == "failed"]
    if failed:
        print("\nFailed users:")
        for item in failed:
            suffix = f", step={item.get('failed_step')}" if item.get("failed_step") else ""
            print(f"  - {item['username']} (exit_code={item.get('exit_code')}{suffix})")


def _mark_failed(
    result: dict[str, object],
    *,
    failed_step: str,
    exit_code: int,
    error_message: str | None = None,
) -> None:
    result["status"] = "failed"
    result["failed_step"] = failed_step
    result["exit_code"] = exit_code
    result["completed_at"] = _to_iso(datetime.now(UTC))
    if error_message:
        result["error_message"] = error_message


def _resolve_first_tweet_analysis_start(username: str) -> str:
    session = SessionLocal()
    try:
        user = session.scalar(select(User).where(func.lower(User.username) == username.lower()))
        if user is None:
            raise RuntimeError(f"No canonical user found for username={username!r}.")

        first_tweet_at = session.scalar(
            select(func.min(Tweet.created_at_platform)).where(Tweet.author_user_id == user.id)
        )
        if first_tweet_at is None:
            raise RuntimeError(
                f"No canonical tweets found for username={username!r}. Run normalization first."
            )
        return _to_iso(first_tweet_at)
    finally:
        session.close()


def _run_command(command: list[str]) -> tuple[int, float]:
    started_at = time.perf_counter()
    exit_code = int(subprocess.run(command, cwd=REPO_ROOT).returncode)
    elapsed = time.perf_counter() - started_at
    return exit_code, elapsed


def _record_stage_elapsed(stage_elapsed_seconds: dict[str, float], stage_name: str, elapsed: float) -> None:
    stage_elapsed_seconds[stage_name] = round(stage_elapsed_seconds.get(stage_name, 0.0) + elapsed, 3)


def _top_elapsed_stages(stage_elapsed_seconds: dict[str, object], *, limit: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for stage_name, seconds in stage_elapsed_seconds.items():
        elapsed = float(seconds)
        rows.append(
            {
                "stage": stage_name,
                "seconds": round(elapsed, 3),
                "elapsed": _format_elapsed_seconds(int(round(elapsed))),
            }
        )
    rows.sort(key=lambda item: item["seconds"], reverse=True)
    return rows[:limit]


def _to_iso(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _format_elapsed_seconds(total_seconds: int) -> str:
    minutes, seconds = divmod(max(total_seconds, 0), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


if __name__ == "__main__":
    main()
