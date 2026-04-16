import argparse
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.aggregate_narrative_view import rebuild_aggregate_narrative_snapshots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild cached aggregate narrative snapshot payloads in Postgres."
    )
    parser.add_argument(
        "--cohort",
        action="append",
        dest="cohorts",
        help="Optional cohort slug to rebuild. Repeat to target multiple cohorts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which snapshots would be rebuilt without writing them.",
    )
    parser.add_argument(
        "--keep-stale",
        action="store_true",
        help="Do not delete stale aggregate narrative snapshot rows after rebuild.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pprint(
        rebuild_aggregate_narrative_snapshots(
            cohort_slugs=args.cohorts,
            dry_run=args.dry_run,
            delete_stale=not args.keep_stale,
        )
    )


if __name__ == "__main__":
    main()
