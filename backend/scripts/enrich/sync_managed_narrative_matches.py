import argparse
from dataclasses import asdict
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.managed_narratives import (
    SyncManagedNarrativeMatchesRequest,
    sync_managed_narrative_matches,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Match canonical tweets against managed narrative phrases and store one row per "
            "tweet and narrative."
        )
    )
    parser.add_argument(
        "--username",
        nargs="+",
        help="Optional canonical usernames to limit the sync scope.",
    )
    parser.add_argument(
        "--narrative-slug",
        action="append",
        dest="narrative_slugs",
        help="Optional narrative slug to limit the sync scope. Repeat for multiple narratives.",
    )
    parser.add_argument(
        "--created-since",
        help="Optional UTC timestamp to restrict matching to tweets created on or after this time.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Delete existing narrative match rows in scope before rebuilding them.",
    )
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="Do not restrict the sync to tracked and published users.",
    )
    parser.add_argument(
        "--include-unpublished",
        action="store_true",
        help="Do not require managed authors to be published.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Summarize the sync work without writing narrative match rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = sync_managed_narrative_matches(
        SyncManagedNarrativeMatchesRequest(
            usernames=args.username,
            narrative_slugs=args.narrative_slugs,
            created_since=args.created_since,
            overwrite_existing=args.overwrite_existing,
            tracked_only=not args.all_users,
            published_only=not args.include_unpublished,
            dry_run=args.dry_run,
        )
    )
    pprint(asdict(summary))


if __name__ == "__main__":
    main()
