import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.validation import (
    ValidateArchivedUserRequest,
    render_validation_report,
    validate_archived_user,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate canonical users, tweets, and tweet references for a single X/Twitter "
            "username against archived raw artifacts stored in Postgres."
        )
    )
    parser.add_argument("--username", required=True, help="X/Twitter username to validate")
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=10,
        help="Maximum number of mismatch samples to print for each failed check.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = validate_archived_user(
        ValidateArchivedUserRequest(
            username=args.username,
            sample_limit=args.sample_limit,
        )
    )
    print(render_validation_report(summary))
    if summary.status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
