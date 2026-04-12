import argparse
from dataclasses import asdict
from pprint import pprint
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ingestion import RawTweetSearchWindowRequest, archive_tweet_search_window_raw
from scripts.ingest._common import parse_utc_timestamp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Archive raw twitterapi.io advanced_search pages for a single X username within a "
            "single UTC time window before any normalization occurs."
        )
    )
    parser.add_argument("--username", required=True, help="X/Twitter username to backfill")
    parser.add_argument(
        "--since",
        required=True,
        help="UTC window start in ISO format, for example 2024-01-01T00:00:00Z",
    )
    parser.add_argument(
        "--until",
        required=True,
        help="UTC window end in ISO format, for example 2024-02-01T00:00:00Z",
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
        "--resume-run-id",
        type=int,
        help="Resume a previously failed raw archive run from its stored cursor progress.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print request params and response payload previews to the terminal for diagnosis.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and summarize without writing an ingestion run or raw artifacts to the database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    request = RawTweetSearchWindowRequest(
        username=args.username,
        since=parse_utc_timestamp(args.since),
        until=parse_utc_timestamp(args.until),
        query_fragment=args.query_fragment,
        import_type=args.import_type,
        page_delay_seconds=args.page_delay_seconds,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        resume_run_id=args.resume_run_id,
        debug=args.debug,
        dry_run=args.dry_run,
    )
    summary = archive_tweet_search_window_raw(request)
    pprint(asdict(summary))
    if summary.status != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
