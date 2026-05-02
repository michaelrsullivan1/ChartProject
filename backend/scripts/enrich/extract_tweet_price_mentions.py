import argparse
from dataclasses import asdict
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.price_mentions import (
    DEFAULT_PRICE_MENTION_ANALYSIS_START,
    DEFAULT_PRICE_MENTION_EXTRACTOR_KEY,
    DEFAULT_PRICE_MENTION_EXTRACTOR_VERSION,
    ExtractTweetPriceMentionsRequest,
    extract_tweet_price_mentions,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract Bitcoin price mentions from tweet text for one or more usernames "
            "and store the results in tweet_price_mentions."
        )
    )
    parser.add_argument(
        "--username",
        nargs="+",
        required=True,
        help="One or more canonical usernames to process in this batch.",
    )
    parser.add_argument(
        "--analysis-start",
        default=DEFAULT_PRICE_MENTION_ANALYSIS_START,
        help="Only extract from tweets on or after this UTC timestamp.",
    )
    parser.add_argument(
        "--extractor-key",
        default=DEFAULT_PRICE_MENTION_EXTRACTOR_KEY,
        help="Stored extractor identifier used for dedupe/versioning.",
    )
    parser.add_argument(
        "--extractor-version",
        default=DEFAULT_PRICE_MENTION_EXTRACTOR_VERSION,
        help="Stored extractor version identifier.",
    )
    parser.add_argument(
        "--only-missing-tweets",
        action="store_true",
        help="Only process tweets that have no existing rows for this extractor+version.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Delete existing rows for this extractor+version and rebuild them.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Summarize pending extraction work without writing any rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = extract_tweet_price_mentions(
        ExtractTweetPriceMentionsRequest(
            usernames=args.username,
            analysis_start=args.analysis_start,
            extractor_key=args.extractor_key,
            extractor_version=args.extractor_version,
            only_missing_tweets=args.only_missing_tweets,
            overwrite_existing=args.overwrite_existing,
            dry_run=args.dry_run,
        )
    )
    pprint(asdict(summary))


if __name__ == "__main__":
    main()
