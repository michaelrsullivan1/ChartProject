import argparse
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.author_registry import AuditTrackedAuthorsRequest, audit_tracked_authors
from app.services.moods import DEFAULT_MOOD_MODEL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit tracked author coverage, including whether mood-scored users are tracked "
            "and published."
        )
    )
    parser.add_argument(
        "--model-key",
        default=DEFAULT_MOOD_MODEL,
        help="Mood model key used to determine which users are considered scored.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = audit_tracked_authors(
        AuditTrackedAuthorsRequest(model_key=args.model_key)
    )
    pprint(payload)
    if not payload["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
