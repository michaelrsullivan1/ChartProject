import argparse
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.author_registry import (
    SyncManagedAuthorViewRequest,
    sync_managed_author_view_for_username,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create or update a managed author registry entry for a canonical username. "
            "Useful after ingest/enrichment completes."
        )
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Canonical username to sync into managed_author_views.",
    )
    parser.add_argument(
        "--published",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether the author should be published in the registry output.",
    )
    parser.add_argument(
        "--tracked",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether the author should be tracked in the public registry output.",
    )
    parser.add_argument(
        "--ensure-analysis-starts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Populate missing per-view analysis starts from the first canonical tweet timestamp.",
    )
    parser.add_argument(
        "--rebuild-snapshot",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Rebuild the public author-registry snapshot after syncing this author.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = sync_managed_author_view_for_username(
        SyncManagedAuthorViewRequest(
            username=args.username,
            published=args.published,
            tracked=args.tracked,
            ensure_analysis_starts=args.ensure_analysis_starts,
            rebuild_snapshot=args.rebuild_snapshot,
        )
    )
    pprint(payload)


if __name__ == "__main__":
    main()
