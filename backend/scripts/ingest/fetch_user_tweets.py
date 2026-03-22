import argparse
from pprint import pprint

from app.services.ingestion import IngestionRequest, build_ingestion_summary
from app.services.twitterapi_client import TwitterApiClient, TwitterUserFetchRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch tweets for a single X user ID through the generic ingestion boundary."
    )
    parser.add_argument("--user-id", required=True, help="X/Twitter platform user ID")
    parser.add_argument(
        "--import-type",
        default="backfill",
        choices=["backfill", "refresh"],
        help="Whether this run is a larger backfill or a recent refresh.",
    )
    parser.add_argument("--since", help="Optional lower bound timestamp or provider token.")
    parser.add_argument("--until", help="Optional upper bound timestamp or provider token.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not commit anything. Useful while the provider integration is still being finalized.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    request = IngestionRequest(
        user_id=args.user_id,
        import_type=args.import_type,
        since=args.since,
        until=args.until,
        dry_run=args.dry_run,
    )

    raw_payload = None
    if not request.dry_run:
        client = TwitterApiClient()
        raw_payload = client.fetch_user_tweets(
            TwitterUserFetchRequest(
                user_id=request.user_id,
                since=request.since,
                until=request.until,
            )
        )

    summary = build_ingestion_summary(request, raw_payload=raw_payload)
    pprint(summary)


if __name__ == "__main__":
    main()
