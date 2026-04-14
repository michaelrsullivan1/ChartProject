import argparse
from datetime import UTC, datetime
from pathlib import Path
from pprint import pprint
import subprocess
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.tracked_author_refresh import (
    build_default_post_process_results_path,
    load_json_payload,
    write_json_payload,
)


REPO_ROOT = BACKEND_ROOT.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run tracked-author post-processing for successful refresh fetches with nonzero new "
            "raw tweets."
        )
    )
    parser.add_argument(
        "--fetch-results",
        required=True,
        help="Path to a tracked-author refresh fetch-results JSON file.",
    )
    parser.add_argument(
        "--output",
        help="Optional path for the post-process results JSON manifest. Defaults next to fetch-results.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the usernames that would be post-processed without running the batch script.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fetch_results_path = Path(args.fetch_results).expanduser().resolve()
    fetch_results_payload = load_json_payload(fetch_results_path)
    if fetch_results_payload.get("view") != "tracked-author-refresh-fetch-results":
        raise SystemExit(f"{fetch_results_path} is not a tracked-author refresh fetch-results manifest.")

    results_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else build_default_post_process_results_path(fetch_results_path=fetch_results_path)
    )

    all_results = list(fetch_results_payload.get("results", []))
    eligible_items = [
        item
        for item in all_results
        if item.get("status") == "completed" and bool(item.get("new_raw_tweets", 0) > 0)
    ]

    results: list[dict[str, object]] = []
    success_count = 0
    failure_count = 0

    for index, item in enumerate(eligible_items, start=1):
        username = str(item["username"])
        print(f"[{index}/{len(eligible_items)}] Post-processing @{username}")

        result: dict[str, object] = {
            "username": username,
            "slug": item["slug"],
            "new_raw_tweets": item["new_raw_tweets"],
            "status": "planned",
        }

        if args.dry_run:
            results.append(result)
            continue

        started_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        completed = subprocess.run(
            ["./scripts/run-user-post-ingest-batch.sh", "--username", username],
            cwd=REPO_ROOT,
        )
        completed_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        result["started_at"] = started_at
        result["completed_at"] = completed_at
        result["exit_code"] = int(completed.returncode)
        result["status"] = "completed" if completed.returncode == 0 else "failed"

        if completed.returncode == 0:
            success_count += 1
        else:
            failure_count += 1

        results.append(result)

    payload = {
        "view": "tracked-author-refresh-post-process-results",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "fetch_results_path": str(fetch_results_path),
        "dry_run": args.dry_run,
        "eligible_count": len(eligible_items),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results,
    }
    write_json_payload(results_path, payload)

    print(f"\nTracked author refresh post-process results written to {results_path}")
    pprint(
        {
            "eligible_count": payload["eligible_count"],
            "success_count": payload["success_count"],
            "failure_count": payload["failure_count"],
        }
    )
    failed = [item for item in results if item["status"] == "failed"]
    if failed:
        print("\nFailed users:")
        for item in failed:
            print(f"  - {item['username']} (exit_code={item['exit_code']})")


if __name__ == "__main__":
    main()
