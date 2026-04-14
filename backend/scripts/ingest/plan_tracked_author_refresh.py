import argparse
from datetime import UTC, datetime
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.tracked_author_refresh import (
    build_default_refresh_plan_path,
    build_tracked_author_refresh_plan,
    parse_iso_timestamp,
    write_json_payload,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan a tracked-author tweet refresh by computing per-user since/until windows from "
            "the latest successful advanced-search runs."
        )
    )
    parser.add_argument(
        "--output",
        help=(
            "Optional path for the JSON plan manifest. Defaults to "
            "data/exports/refresh-plans/tracked-author-refresh-plan-<timestamp>.json"
        ),
    )
    parser.add_argument(
        "--window-months",
        type=int,
        default=1,
        help="How many calendar months each fetch command should request per window.",
    )
    parser.add_argument(
        "--page-delay-seconds",
        type=float,
        default=0.025,
        help="Delay to encode into the generated fetch plan for advanced-search page requests.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retry budget to encode into the generated fetch plan.",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=1.0,
        help="Retry backoff base to encode into the generated fetch plan.",
    )
    parser.add_argument(
        "--query-fragment",
        default="",
        help="Optional extra advanced-search fragment to include in generated fetch commands.",
    )
    parser.add_argument(
        "--refresh-user-info",
        action="store_true",
        help="Include raw user-info refresh in the later fetch step instead of skipping it.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.window_months < 1:
        raise SystemExit("--window-months must be >= 1")

    payload = build_tracked_author_refresh_plan(
        window_months=args.window_months,
        page_delay_seconds=args.page_delay_seconds,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        query_fragment=args.query_fragment,
        skip_user_info=not args.refresh_user_info,
    )
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else build_default_refresh_plan_path(
            started_at=parse_iso_timestamp(str(payload["plan_started_at"]))
        )
    )
    write_json_payload(output_path, payload)

    print(f"Tracked author refresh plan written to {output_path}")
    pprint(
        {
            "tracked_author_count": payload["tracked_author_count"],
            "planned_count": payload["planned_count"],
            "manual_full_history_required_count": payload["manual_full_history_required_count"],
            "up_to_date_count": payload["up_to_date_count"],
        }
    )
    if payload["manual_full_history_required"]:
        print("\nUsers requiring manual full-history ingest first:")
        for item in payload["manual_full_history_required"]:
            print(f"  - {item['username']} ({item['slug']})")


if __name__ == "__main__":
    main()
