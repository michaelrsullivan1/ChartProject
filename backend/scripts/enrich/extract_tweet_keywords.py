import argparse
from dataclasses import asdict
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.keywords import (
    DEFAULT_KEYWORD_ANALYSIS_START,
    DEFAULT_KEYWORD_EXTRACTOR_KEY,
    DEFAULT_KEYWORD_EXTRACTOR_VERSION,
    ExtractTweetKeywordsRequest,
    extract_tweet_keywords,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract exact 1-3 word phrases from canonical tweets for one or more usernames and "
            "store the results in the database."
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
        default=DEFAULT_KEYWORD_ANALYSIS_START,
        help="Only extract phrases from tweets on or after this UTC timestamp.",
    )
    parser.add_argument(
        "--extractor-key",
        default=DEFAULT_KEYWORD_EXTRACTOR_KEY,
        help="Stored extractor identifier used for dedupe/versioning.",
    )
    parser.add_argument(
        "--extractor-version",
        default=DEFAULT_KEYWORD_EXTRACTOR_VERSION,
        help="Stored extractor version identifier used for dedupe/versioning.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Delete existing phrase rows for this extractor and rebuild them.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Summarize the pending extraction work without writing phrase rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = extract_tweet_keywords(
        ExtractTweetKeywordsRequest(
            usernames=args.username,
            analysis_start=args.analysis_start,
            extractor_key=args.extractor_key,
            extractor_version=args.extractor_version,
            overwrite_existing=args.overwrite_existing,
            dry_run=args.dry_run,
        )
    )
    pprint(asdict(summary))


if __name__ == "__main__":
    main()
