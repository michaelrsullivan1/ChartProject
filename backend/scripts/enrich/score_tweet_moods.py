import argparse
from dataclasses import asdict
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.moods import (
    DEFAULT_MOOD_MODEL,
    ScoreTweetsMoodsRequest,
    score_tweets_moods,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Score canonical tweets for one or more usernames with a multilabel RoBERTa mood "
            "model and store the results in the database."
        )
    )
    parser.add_argument(
        "--username",
        nargs="+",
        required=True,
        help="One or more canonical usernames to score in this batch.",
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MOOD_MODEL,
        help="Hugging Face model identifier to load for inference.",
    )
    parser.add_argument(
        "--model-key",
        help=(
            "Stored model identifier used for dedupe/versioning. Defaults to the same value as "
            "--model-name."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="How many tweets to score per forward pass.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Delete existing mood rows for this model key and rescore the requested usernames.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Summarize the pending work without writing mood rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_key = args.model_key or args.model_name
    summary = score_tweets_moods(
        ScoreTweetsMoodsRequest(
            usernames=args.username,
            model_key=model_key,
            model_name=args.model_name,
            batch_size=args.batch_size,
            overwrite_existing=args.overwrite_existing,
            dry_run=args.dry_run,
        )
    )
    pprint(asdict(summary))


if __name__ == "__main__":
    main()
