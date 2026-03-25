import argparse
from dataclasses import asdict
from pprint import pprint

from app.services.ingestion import IngestionRequest, archive_user_timeline_raw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Archive raw twitterapi.io user info and paginated last_tweets responses for a single X "
            "username before any normalization occurs."
        )
    )
    parser.add_argument("--username", required=True, help="X/Twitter username to backfill")
    parser.add_argument(
        "--import-type",
        default="full_backfill",
        choices=["full_backfill", "refresh"],
        help="Whether this run is a larger backfill or a smaller recent refresh.",
    )
    parser.add_argument(
        "--exclude-replies",
        action="store_true",
        help="Exclude replies from the timeline request. Default behavior is to include them.",
    )
    parser.add_argument(
        "--page-delay-seconds",
        type=float,
        default=0.25,
        help="Small delay between timeline page requests to reduce the chance of transient failures.",
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
    request = IngestionRequest(
        username=args.username,
        import_type=args.import_type,
        include_replies=not args.exclude_replies,
        page_delay_seconds=args.page_delay_seconds,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        resume_run_id=args.resume_run_id,
        debug=args.debug,
        dry_run=args.dry_run,
    )
    summary = archive_user_timeline_raw(request)
    pprint(asdict(summary))
    if summary.status != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
