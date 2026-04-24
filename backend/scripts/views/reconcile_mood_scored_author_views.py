import argparse
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.author_registry import (
    ReconcileMoodScoredAuthorsRequest,
    reconcile_mood_scored_authors,
)
from app.services.moods import DEFAULT_MOOD_MODEL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile managed_author_views so all mood-scored users are tracked and published."
        )
    )
    parser.add_argument(
        "--model-key",
        default=DEFAULT_MOOD_MODEL,
        help="Mood model key used to determine which users are considered scored.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Summarize the reconciliation without committing changes.",
    )
    parser.add_argument(
        "--no-rebuild-snapshot",
        action="store_true",
        help="Do not rebuild the cached author-registry snapshot after applying changes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pprint(
        reconcile_mood_scored_authors(
            ReconcileMoodScoredAuthorsRequest(
                model_key=args.model_key,
                dry_run=args.dry_run,
                rebuild_snapshot=not args.no_rebuild_snapshot,
            )
        )
    )


if __name__ == "__main__":
    main()
