#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

LOGGER = logging.getLogger("repair_incomplete_bitcoin_windows")
RAW_PATTERN = re.compile(
    r"^saylor_bitcoin_history(?:_repair_\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2})?_"
    r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})_page(\d{4})_"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair incomplete BTC/BTC hashtag history windows")
    parser.add_argument("--raw-dir", default="data/raw/social")
    parser.add_argument("--checkpoint-dir", default="data/interim/social/repairs")
    parser.add_argument("--summary-path", default="data/interim/social/repair_incomplete_summary.json")
    parser.add_argument("--request-interval-seconds", type=float, default=4.0)
    parser.add_argument("--max-total-requests", type=int, default=30)
    parser.add_argument("--max-requests-per-window", type=int, default=20)
    return parser.parse_args()


def _window_sort_key(window: tuple[str, str]) -> tuple[str, str]:
    return window[0], window[1]


def discover_incomplete_windows(raw_dir: Path) -> list[tuple[str, str]]:
    by_window_page: dict[tuple[str, str], dict[int, list[Path]]] = defaultdict(lambda: defaultdict(list))

    for path in raw_dir.glob("saylor_bitcoin_history_*.json"):
        match = RAW_PATTERN.match(path.name)
        if not match:
            continue
        start_date, end_date, page_num = match.group(1), match.group(2), int(match.group(3))
        by_window_page[(start_date, end_date)][page_num].append(path)

    incomplete: list[tuple[str, str]] = []
    for window, pages_map in sorted(by_window_page.items(), key=lambda x: _window_sort_key(x[0])):
        pages = sorted(pages_map.keys())
        if not pages:
            incomplete.append(window)
            continue

        max_page = pages[-1]
        has_gap = pages != list(range(1, max_page + 1))

        max_page_complete = False
        for candidate in pages_map[max_page]:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            if not (payload.get("meta") or {}).get("next_token"):
                max_page_complete = True
                break

        if has_gap or not max_page_complete:
            incomplete.append(window)

    return incomplete


def run_repair_for_window(
    python_bin: str,
    root: Path,
    start_date: str,
    end_date: str,
    checkpoint_dir: Path,
    request_interval_seconds: float,
    max_requests_per_window: int,
    max_total_requests_remaining: int,
) -> tuple[dict, int, bool]:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / f"repair_{start_date}_{end_date}.json"
    output_prefix = f"saylor_bitcoin_history_repair_{start_date}_{end_date}"

    requests_used = 0
    run_logs: list[dict] = []

    while requests_used < max_requests_per_window and requests_used < max_total_requests_remaining:
        command = [
            python_bin,
            "scripts/ingest_saylor_bitcoin_history.py",
            "--start-date",
            start_date,
            "--end-date",
            end_date,
            "--window-days",
            "5000",
            "--max-results",
            "100",
            "--max-requests",
            "1",
            "--request-interval-seconds",
            str(request_interval_seconds),
            "--checkpoint",
            str(checkpoint_path),
            "--output-prefix",
            output_prefix,
        ]

        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        requests_used += 1

        if result.returncode != 0:
            run_logs.append(
                {
                    "attempt": requests_used,
                    "ok": False,
                    "stderr": result.stderr[-2000:],
                    "stdout": result.stdout[-2000:],
                }
            )
            return (
                {
                    "window": [start_date, end_date],
                    "completed": False,
                    "requests_used": requests_used,
                    "error": "ingestion command failed",
                    "logs": run_logs,
                },
                requests_used,
                False,
            )

        payload = json.loads(result.stdout)
        run_logs.append(
            {
                "attempt": requests_used,
                "ok": True,
                "requests_this_run": payload.get("requests_this_run"),
                "posts_upserted_total": payload.get("posts_upserted_total"),
                "finished": payload.get("finished"),
            }
        )

        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint.get("completed"):
            return (
                {
                    "window": [start_date, end_date],
                    "completed": True,
                    "requests_used": requests_used,
                    "logs": run_logs,
                },
                requests_used,
                True,
            )

    return (
        {
            "window": [start_date, end_date],
            "completed": False,
            "requests_used": requests_used,
            "error": "request budget reached",
            "logs": run_logs,
        },
        requests_used,
        True,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    args = parse_args()

    root = Path(__file__).resolve().parents[1]
    raw_dir = (root / args.raw_dir).resolve()
    checkpoint_dir = (root / args.checkpoint_dir).resolve()
    summary_path = (root / args.summary_path).resolve()

    windows = discover_incomplete_windows(raw_dir)
    LOGGER.info("Discovered %s incomplete windows", len(windows))

    python_bin = sys.executable
    total_requests_used = 0
    repaired: list[dict] = []
    success = True

    for start_date, end_date in windows:
        remaining = args.max_total_requests - total_requests_used
        if remaining <= 0:
            success = False
            break

        LOGGER.info(
            "Repairing window %s..%s (remaining request budget=%s)",
            start_date,
            end_date,
            remaining,
        )
        result, used, continue_ok = run_repair_for_window(
            python_bin=python_bin,
            root=root,
            start_date=start_date,
            end_date=end_date,
            checkpoint_dir=checkpoint_dir,
            request_interval_seconds=args.request_interval_seconds,
            max_requests_per_window=args.max_requests_per_window,
            max_total_requests_remaining=remaining,
        )
        repaired.append(result)
        total_requests_used += used

        if not continue_ok:
            success = False
            break

    summary = {
        "success": success,
        "incomplete_windows_initial": len(windows),
        "windows_processed": len(repaired),
        "total_requests_used": total_requests_used,
        "results": repaired,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
