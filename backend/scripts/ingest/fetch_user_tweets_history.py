import argparse
from dataclasses import asdict
from pprint import pprint
from pathlib import Path
import subprocess
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ingestion import (
    RawTweetSearchWindowRequest,
    RawUserInfoRequest,
    archive_tweet_search_window_raw,
    archive_user_info_raw,
)
from scripts.ingest._common import add_months, parse_utc_timestamp


def notify_completion(*, ok: bool) -> None:
    status_message = "Finished" if ok else "Failed"

    try:
        print("\a", end="", flush=True)
    except Exception:
        pass

    if sys.platform != "darwin":
        return

    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                (
                    f'display notification "{status_message}" '
                    'with title "Fetch user tweets history"'
                ),
            ],
            check=False,
        )
    except Exception:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Archive raw twitterapi.io advanced_search pages across multiple UTC windows for a "
            "single X username."
        )
    )
    parser.add_argument("--username", required=True, help="X/Twitter username to backfill")
    parser.add_argument(
        "--since",
        required=True,
        help="UTC history start in ISO format, for example 2024-01-01T00:00:00Z",
    )
    parser.add_argument(
        "--until",
        required=True,
        help="UTC history end in ISO format, for example 2024-04-01T00:00:00Z",
    )
    parser.add_argument(
        "--window-months",
        type=int,
        default=1,
        help="How many calendar months to include in each advanced_search window.",
    )
    parser.add_argument(
        "--query-fragment",
        default="",
        help=(
            "Optional additional advanced_search terms inserted between from:<username> and the "
            "since/until bounds."
        ),
    )
    parser.add_argument(
        "--import-type",
        default="full_backfill",
        choices=["full_backfill", "refresh"],
        help="Whether this run is a larger backfill or a smaller recent refresh.",
    )
    parser.add_argument(
        "--page-delay-seconds",
        type=float,
        default=0.25,
        help="Small delay between advanced_search page requests to reduce transient failures.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="How many times to retry a transient API failure before aborting the run.",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=1.0,
        help="Base delay used for exponential backoff between transient API retries.",
    )
    parser.add_argument(
        "--skip-user-info",
        action="store_true",
        help="Skip the initial raw user info archive step.",
    )
    parser.add_argument(
        "--target-user-platform-id",
        help=(
            "Optional known platform user id. Useful with --skip-user-info so refresh runs still "
            "record target_user_platform_id on ingestion_runs."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print request params and response payload previews to the terminal for diagnosis.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and summarize without writing ingestion runs or raw artifacts to the database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    history_since = parse_utc_timestamp(args.since)
    history_until = parse_utc_timestamp(args.until)
    if args.window_months < 1:
        raise SystemExit("--window-months must be >= 1")
    if history_until <= history_since:
        raise SystemExit("--until must be greater than --since")

    ok = False
    try:
        user_info_summary = None
        target_user_platform_id = args.target_user_platform_id
        if not args.skip_user_info:
            user_info_summary = archive_user_info_raw(
                RawUserInfoRequest(
                    username=args.username,
                    import_type=args.import_type,
                    max_retries=args.max_retries,
                    retry_backoff_seconds=args.retry_backoff_seconds,
                    debug=args.debug,
                    dry_run=args.dry_run,
                )
            )
            pprint({"user_info_summary": asdict(user_info_summary)})
            if user_info_summary.status != "completed":
                raise SystemExit(1)
            target_user_platform_id = user_info_summary.resolved_user_platform_id

        window_summaries = []
        window_since = history_since
        while window_since < history_until:
            window_until = min(add_months(window_since, args.window_months), history_until)
            summary = archive_tweet_search_window_raw(
                RawTweetSearchWindowRequest(
                    username=args.username,
                    since=window_since,
                    until=window_until,
                    import_type=args.import_type,
                    query_fragment=args.query_fragment,
                    page_delay_seconds=args.page_delay_seconds,
                    max_retries=args.max_retries,
                    retry_backoff_seconds=args.retry_backoff_seconds,
                    target_user_platform_id=target_user_platform_id,
                    debug=args.debug,
                    dry_run=args.dry_run,
                )
            )
            window_summaries.append(asdict(summary))
            pprint({"window_summary": asdict(summary)})
            if summary.status != "completed":
                raise SystemExit(1)
            window_since = window_until

        pprint(
            {
                "username": args.username,
                "history_since": history_since.isoformat(),
                "history_until": history_until.isoformat(),
                "window_months": args.window_months,
                "windows_completed": len(window_summaries),
                "tweets_archived": sum(item["tweets_returned"] for item in window_summaries),
                "pages_fetched": sum(item["pages_fetched"] for item in window_summaries),
            }
        )
        ok = True
    finally:
        notify_completion(ok=ok)


if __name__ == "__main__":
    main()
