import argparse
from datetime import UTC, datetime
from pathlib import Path
from pprint import pprint
import subprocess
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.tracked_author_refresh import (
    build_default_fetch_results_path,
    load_json_payload,
    load_tracked_author_by_username,
    parse_iso_timestamp,
    summarize_refresh_fetch_runs,
    write_json_payload,
)


REPO_ROOT = BACKEND_ROOT.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run tracked-author refresh fetches from a JSON plan manifest using the existing "
            "single-user history ingest command."
        )
    )
    parser.add_argument("--plan", required=True, help="Path to a tracked-author refresh plan JSON file.")
    parser.add_argument(
        "--output",
        help="Optional path for the fetch-results JSON manifest. Defaults next to the plan file.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Pass --debug through to each underlying single-user fetch command.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run through to each underlying single-user fetch command.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan_path = Path(args.plan).expanduser().resolve()
    plan_payload = load_json_payload(plan_path)
    if plan_payload.get("view") != "tracked-author-refresh-plan":
        raise SystemExit(f"{plan_path} is not a tracked-author refresh plan manifest.")

    results_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else build_default_fetch_results_path(plan_path=plan_path)
    )

    planned_items = list(plan_payload.get("planned", []))
    session = SessionLocal()
    try:
        results: list[dict[str, object]] = []
        success_count = 0
        failure_count = 0
        eligible_for_post_process_count = 0

        for index, item in enumerate(planned_items, start=1):
            username = str(item["username"])
            slug = str(item["slug"])
            print(
                f"[{index}/{len(planned_items)}] Fetching @{username} "
                f"from {item['since']} until {item['until']}"
            )
            fetch_started_at = datetime.now(UTC).replace(microsecond=0)
            command = list(item["command"])
            if args.debug:
                command.append("--debug")
            if args.dry_run:
                command.append("--dry-run")

            completed = subprocess.run(command, cwd=REPO_ROOT)
            fetch_completed_at = datetime.now(UTC).replace(microsecond=0)

            result: dict[str, object] = {
                "username": username,
                "slug": slug,
                "platform_user_id": item["platform_user_id"],
                "since": item["since"],
                "until": item["until"],
                "started_at": fetch_started_at.isoformat().replace("+00:00", "Z"),
                "completed_at": fetch_completed_at.isoformat().replace("+00:00", "Z"),
                "exit_code": int(completed.returncode),
                "status": "completed" if completed.returncode == 0 else "failed",
                "post_process_eligible": False,
            }

            if completed.returncode == 0:
                success_count += 1
                if args.dry_run:
                    result["completed_window_run_count"] = None
                    result["pages_fetched"] = None
                    result["new_raw_tweets"] = None
                else:
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
                        started_at_floor=fetch_started_at,
                    )
                    result["completed_window_run_count"] = fetch_summary["completed_window_run_count"]
                    result["pages_fetched"] = fetch_summary["pages_fetched"]
                    result["new_raw_tweets"] = fetch_summary["raw_tweets_fetched"]
                    result["run_ids"] = fetch_summary["run_ids"]
                    result["post_process_eligible"] = bool(fetch_summary["raw_tweets_fetched"] > 0)
                    if result["post_process_eligible"]:
                        eligible_for_post_process_count += 1
            else:
                failure_count += 1

            results.append(result)

        payload = {
            "view": "tracked-author-refresh-fetch-results",
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "plan_path": str(plan_path),
            "dry_run": args.dry_run,
            "planned_count": len(planned_items),
            "success_count": success_count,
            "failure_count": failure_count,
            "eligible_for_post_process_count": eligible_for_post_process_count,
            "results": results,
        }
        write_json_payload(results_path, payload)

        print(f"\nTracked author refresh fetch results written to {results_path}")
        pprint(
            {
                "planned_count": payload["planned_count"],
                "success_count": payload["success_count"],
                "failure_count": payload["failure_count"],
                "eligible_for_post_process_count": payload["eligible_for_post_process_count"],
            }
        )
        failed = [item for item in results if item["status"] != "completed"]
        if failed:
            print("\nFailed users:")
            for item in failed:
                print(f"  - {item['username']} (exit_code={item['exit_code']})")
    finally:
        session.close()


if __name__ == "__main__":
    main()
