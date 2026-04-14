import argparse
from datetime import UTC, datetime
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.tracked_author_refresh import (
    load_json_payload,
    load_tracked_author_by_username,
    parse_iso_timestamp,
    summarize_refresh_fetch_runs,
    write_json_payload,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild a tracked-author refresh fetch-results manifest by re-summarizing the "
            "ingestion runs already created by an earlier fetch pass."
        )
    )
    parser.add_argument(
        "--fetch-results",
        required=True,
        help="Path to a tracked-author refresh fetch-results JSON file.",
    )
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults next to the input file with a .repaired suffix.",
    )
    return parser.parse_args()


def build_default_output_path(fetch_results_path: Path) -> Path:
    return fetch_results_path.with_name(f"{fetch_results_path.stem}.repaired.json")


def main() -> None:
    args = parse_args()
    fetch_results_path = Path(args.fetch_results).expanduser().resolve()
    payload = load_json_payload(fetch_results_path)
    if payload.get("view") != "tracked-author-refresh-fetch-results":
        raise SystemExit(f"{fetch_results_path} is not a tracked-author refresh fetch-results manifest.")

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else build_default_output_path(fetch_results_path)
    )

    session = SessionLocal()
    try:
        repaired_results: list[dict[str, object]] = []
        success_count = 0
        failure_count = 0
        eligible_for_post_process_count = 0

        for item in list(payload.get("results", [])):
            repaired = dict(item)
            status = str(item.get("status", ""))

            if status == "completed":
                username = str(item["username"])
                _managed_author, user = load_tracked_author_by_username(
                    session,
                    username=username,
                )
                fetch_summary = summarize_refresh_fetch_runs(
                    session,
                    username=username,
                    target_user_platform_id=user.platform_user_id,
                    planned_since=parse_iso_timestamp(str(item["since"])),
                    planned_until=parse_iso_timestamp(str(item["until"])),
                    started_at_floor=parse_iso_timestamp(str(item["started_at"])),
                )
                repaired["completed_window_run_count"] = fetch_summary["completed_window_run_count"]
                repaired["pages_fetched"] = fetch_summary["pages_fetched"]
                repaired["new_raw_tweets"] = fetch_summary["raw_tweets_fetched"]
                repaired["run_ids"] = fetch_summary["run_ids"]
                repaired["post_process_eligible"] = bool(fetch_summary["raw_tweets_fetched"] > 0)

            if status == "completed":
                success_count += 1
                if repaired.get("post_process_eligible"):
                    eligible_for_post_process_count += 1
            else:
                failure_count += 1

            repaired_results.append(repaired)

        repaired_payload = {
            "view": "tracked-author-refresh-fetch-results",
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "plan_path": payload.get("plan_path"),
            "dry_run": payload.get("dry_run", False),
            "repaired_from_fetch_results_path": str(fetch_results_path),
            "planned_count": len(repaired_results),
            "success_count": success_count,
            "failure_count": failure_count,
            "eligible_for_post_process_count": eligible_for_post_process_count,
            "results": repaired_results,
        }
        write_json_payload(output_path, repaired_payload)

        print(f"Repaired tracked author refresh fetch results written to {output_path}")
        pprint(
            {
                "planned_count": repaired_payload["planned_count"],
                "success_count": repaired_payload["success_count"],
                "failure_count": repaired_payload["failure_count"],
                "eligible_for_post_process_count": repaired_payload["eligible_for_post_process_count"],
            }
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
