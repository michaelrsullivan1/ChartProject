import argparse
from dataclasses import asdict
from pprint import pprint
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ingestion import RawUserInfoRequest, archive_user_info_raw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive raw twitterapi.io user info for a single X username."
    )
    parser.add_argument("--username", required=True, help="X/Twitter username to fetch")
    parser.add_argument(
        "--import-type",
        default="full_backfill",
        choices=["full_backfill", "refresh"],
        help="Whether this run is a larger backfill or a smaller recent refresh.",
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
    request = RawUserInfoRequest(
        username=args.username,
        import_type=args.import_type,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        debug=args.debug,
        dry_run=args.dry_run,
    )
    summary = archive_user_info_raw(request)
    pprint(asdict(summary))
    if summary.status != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
