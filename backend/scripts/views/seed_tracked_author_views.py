import argparse
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.author_registry import SyncTrackedAuthorsRequest, sync_tracked_authors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed or reconcile the backend tracked-author set into managed_author_views."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Summarize tracked-author changes without committing them.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pprint(sync_tracked_authors(SyncTrackedAuthorsRequest(dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
