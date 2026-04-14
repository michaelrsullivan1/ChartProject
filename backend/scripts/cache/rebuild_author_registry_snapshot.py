import argparse
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.author_registry import rebuild_public_author_registry_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild the cached public author-registry payload in Postgres."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the registry payload and report counts without writing the snapshot row.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pprint(rebuild_public_author_registry_snapshot(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
