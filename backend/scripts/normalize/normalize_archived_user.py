import argparse
from dataclasses import asdict
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.normalization import NormalizeArchivedUserRequest, normalize_archived_user


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize archived raw twitterapi.io artifacts for a single X/Twitter username into "
            "the canonical relational tables."
        )
    )
    parser.add_argument("--username", required=True, help="X/Twitter username to normalize")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and validate archived artifacts without modifying canonical tables.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = normalize_archived_user(
        NormalizeArchivedUserRequest(
            username=args.username,
            dry_run=args.dry_run,
        )
    )
    pprint(asdict(summary))


if __name__ == "__main__":
    main()
