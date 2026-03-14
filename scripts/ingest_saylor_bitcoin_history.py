#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

LOGGER = logging.getLogger("ingest_saylor_bitcoin_history")
API_BASE = "https://api.x.com/2/tweets/search/all"
DEFAULT_QUERY = "from:saylor (bitcoin OR btc OR #bitcoin OR #btc)"
BTC_PATTERN = re.compile(r"(?i)(#?bitcoin|#?btc)")


@dataclass
class Checkpoint:
    query: str
    start_date: str
    end_date: str
    window_days: int
    window_index: int
    page_in_window: int
    next_token: str | None
    pages_fetched: int
    posts_upserted: int
    completed: bool
    updated_at: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resumable full-history Bitcoin/BTC backfill for @saylor")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--start-date", default="2018-01-01")
    parser.add_argument("--end-date", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--max-windows", type=int, default=0, help="0 means no limit")
    parser.add_argument("--max-pages-per-window", type=int, default=0, help="0 means no limit")
    parser.add_argument("--max-requests", type=int, default=0, help="0 means no limit")
    parser.add_argument(
        "--request-interval-seconds",
        type=float,
        default=2.0,
        help="Sleep interval between successful API requests to reduce rate-limit churn",
    )
    parser.add_argument(
        "--checkpoint",
        default="data/interim/social/saylor_bitcoin_history_checkpoint.json",
    )
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--output-prefix", default="saylor_bitcoin_history")
    return parser.parse_args()


def _load_checkpoint(path: Path) -> Checkpoint | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Checkpoint(
        query=str(payload["query"]),
        start_date=str(payload["start_date"]),
        end_date=str(payload["end_date"]),
        window_days=int(payload["window_days"]),
        window_index=int(payload["window_index"]),
        page_in_window=int(payload["page_in_window"]),
        next_token=payload.get("next_token"),
        pages_fetched=int(payload["pages_fetched"]),
        posts_upserted=int(payload["posts_upserted"]),
        completed=bool(payload["completed"]),
        updated_at=str(payload["updated_at"]),
    )


def _save_checkpoint(path: Path, checkpoint: Checkpoint) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint.__dict__, indent=2), encoding="utf-8")


def _build_windows(start_date: date, end_date: date, window_days: int) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    cursor = start_date
    while cursor <= end_date:
        window_end = min(cursor + timedelta(days=window_days - 1), end_date)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def _request_with_retries(bearer_token: str, params: dict[str, str]) -> tuple[dict, str]:
    request_url = f"{API_BASE}?{urlencode(params)}"
    request = Request(
        url=request_url,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "chartproject-bitcoin-history/0.1",
        },
        method="GET",
    )

    for attempt in range(5):
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
            return json.loads(payload), request_url
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="ignore")
            if error.code == 429 and attempt < 4:
                retry_after = error.headers.get("retry-after")
                wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 20
                LOGGER.warning("Rate limited (429); sleeping %ss", wait_seconds)
                time.sleep(wait_seconds)
                continue
            raise RuntimeError(f"search/all failed ({error.code}) at {request_url}: {body}") from error
        except URLError as error:
            LOGGER.warning("urllib request failed (%s); trying curl fallback", error)

        try:
            result = subprocess.run(
                [
                    "curl",
                    "-fsSL",
                    request_url,
                    "-H",
                    f"Authorization: Bearer {bearer_token}",
                    "-H",
                    "User-Agent: chartproject-bitcoin-history/0.1",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(result.stdout), request_url
        except subprocess.CalledProcessError as error:
            stderr = (error.stderr or "").strip()
            if " 402" in stderr or "error: 402" in stderr.lower():
                raise RuntimeError(
                    f"search/all returned 402 (credits/billing exhausted) at {request_url}: {stderr}"
                )
            wait_seconds = min(10 * (attempt + 1), 60)
            LOGGER.warning(
                "curl fallback failed (exit=%s): %s. sleeping %ss before retry",
                error.returncode,
                stderr,
                wait_seconds,
            )
            if attempt < 4:
                time.sleep(wait_seconds)
                continue
            raise RuntimeError(
                f"search/all curl fallback failed at {request_url}: {stderr}"
            )

    raise RuntimeError("search/all failed after retries")


def _normalize_and_filter(payload: dict) -> pd.DataFrame:
    users = {
        str(user.get("id")): user
        for user in (payload.get("includes") or {}).get("users", [])
        if isinstance(user, dict)
    }
    rows: list[dict] = []
    for post in payload.get("data", []):
        text = post.get("text") or ""
        if not BTC_PATTERN.search(text):
            continue

        post_id = str(post.get("id", "")).strip()
        if not post_id:
            continue

        created_ts = pd.to_datetime(post.get("created_at"), utc=True, errors="coerce")
        metrics = post.get("public_metrics") or {}
        refs = post.get("referenced_tweets") or []
        ref_types = {item.get("type") for item in refs if isinstance(item, dict)}
        media_keys = ((post.get("attachments") or {}).get("media_keys") or [])

        author_id = str(post.get("author_id") or "")
        author = users.get(author_id, {})
        username = author.get("username") or "saylor"

        rows.append(
            {
                "post_id": post_id,
                "created_at": created_ts,
                "created_date": created_ts.date() if pd.notna(created_ts) else None,
                "text": text,
                "url": f"https://x.com/{username}/status/{post_id}",
                "author_username": username,
                "author_display_name": author.get("name"),
                "like_count": int(metrics.get("like_count", 0) or 0),
                "repost_count": int(metrics.get("retweet_count", 0) or 0),
                "reply_count": int(metrics.get("reply_count", 0) or 0),
                "quote_count": int(metrics.get("quote_count", 0) or 0),
                "view_count": None,
                "is_repost": "retweeted" in ref_types,
                "is_quote": "quoted" in ref_types,
                "has_media": len(media_keys) > 0,
                "media_count": len(media_keys),
                "language": post.get("lang"),
                "source": "x_api_v2_search_all_bitcoin",
                "conversation_id": str(post.get("conversation_id") or "") or None,
                "raw_json_path": None,
            }
        )

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    frame = frame.drop_duplicates(subset=["post_id"], keep="last").sort_values("created_at")
    return frame.reset_index(drop=True)


def _upsert_posts(db_path: Path, frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0

    from chartproject.core.storage import connect_duckdb

    connection = connect_duckdb(db_path)
    connection.register("history_posts_df", frame)
    connection.execute(
        """
        INSERT INTO raw_social_posts (
            post_id,
            created_at,
            created_date,
            text,
            url,
            author_username,
            author_display_name,
            like_count,
            repost_count,
            reply_count,
            quote_count,
            view_count,
            is_repost,
            is_quote,
            has_media,
            media_count,
            language,
            source,
            conversation_id,
            raw_json_path
        )
        SELECT
            post_id,
            created_at,
            created_date,
            text,
            url,
            author_username,
            author_display_name,
            like_count,
            repost_count,
            reply_count,
            quote_count,
            view_count,
            is_repost,
            is_quote,
            has_media,
            media_count,
            language,
            source,
            conversation_id,
            raw_json_path
        FROM history_posts_df
        ON CONFLICT (post_id) DO UPDATE SET
            created_at = EXCLUDED.created_at,
            created_date = EXCLUDED.created_date,
            text = EXCLUDED.text,
            url = EXCLUDED.url,
            author_username = EXCLUDED.author_username,
            author_display_name = EXCLUDED.author_display_name,
            like_count = EXCLUDED.like_count,
            repost_count = EXCLUDED.repost_count,
            reply_count = EXCLUDED.reply_count,
            quote_count = EXCLUDED.quote_count,
            view_count = EXCLUDED.view_count,
            is_repost = EXCLUDED.is_repost,
            is_quote = EXCLUDED.is_quote,
            has_media = EXCLUDED.has_media,
            media_count = EXCLUDED.media_count,
            language = EXCLUDED.language,
            source = EXCLUDED.source,
            conversation_id = EXCLUDED.conversation_id,
            raw_json_path = EXCLUDED.raw_json_path,
            ingested_at = now()
        """
    )
    row_count = int(connection.execute("SELECT COUNT(*) FROM history_posts_df").fetchone()[0])
    connection.close()
    return row_count


def main() -> None:
    from chartproject.core.config import ensure_directories, load_config
    from chartproject.core.logging_config import configure_logging
    from chartproject.core.schema_registry import all_schema_statements
    from chartproject.core.storage import connect_duckdb, execute_statements

    args = parse_args()
    config = load_config()
    configure_logging(config.log_level)
    ensure_directories(config.paths)

    if not config.x_api_bearer_token:
        raise SystemExit("X_API_BEARER_TOKEN is not set in .env")

    # Ensure schema exists before writes.
    connection = connect_duckdb(config.duckdb_path)
    execute_statements(connection, all_schema_statements())
    connection.close()

    raw_dir = config.paths.raw / "social"
    processed_dir = config.paths.processed / "social"
    processed_dir.mkdir(parents=True, exist_ok=True)

    start_date = date.fromisoformat(args.start_date)
    end_date = min(date.fromisoformat(args.end_date), datetime.now(UTC).date())
    windows = _build_windows(start_date, end_date, args.window_days)

    checkpoint_path = Path(args.checkpoint)
    checkpoint = None if args.no_resume else _load_checkpoint(checkpoint_path)

    window_index = 0
    page_in_window = 0
    pages_fetched = 0
    posts_upserted = 0
    next_token = None

    if checkpoint and not checkpoint.completed:
        if (
            checkpoint.query == args.query
            and checkpoint.start_date == args.start_date
            and checkpoint.end_date == end_date.isoformat()
            and checkpoint.window_days == args.window_days
        ):
            window_index = checkpoint.window_index
            page_in_window = checkpoint.page_in_window
            pages_fetched = checkpoint.pages_fetched
            posts_upserted = checkpoint.posts_upserted
            next_token = checkpoint.next_token
            LOGGER.info(
                "Resuming from checkpoint at window %s/%s page %s",
                window_index + 1,
                len(windows),
                page_in_window + 1,
            )
        else:
            LOGGER.info("Ignoring checkpoint because parameters changed")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    touched_windows = 0
    parquet_frames: list[pd.DataFrame] = []
    requests_this_run = 0

    while window_index < len(windows):
        if args.max_windows and touched_windows >= args.max_windows:
            break

        window_start, window_end = windows[window_index]
        touched_windows += 1
        stop_run = False
        window_complete = False

        while True:
            if args.max_requests and requests_this_run >= args.max_requests:
                LOGGER.info("Reached max request budget (%s); stopping safely", args.max_requests)
                stop_run = True
                break
            if args.max_pages_per_window and page_in_window >= args.max_pages_per_window:
                stop_run = True
                break

            params = {
                "query": args.query,
                "start_time": f"{window_start.isoformat()}T00:00:00Z",
                "end_time": f"{window_end.isoformat()}T23:59:59Z",
                "max_results": str(max(10, min(args.max_results, 100))),
                "tweet.fields": (
                    "id,text,created_at,lang,conversation_id,public_metrics,"
                    "referenced_tweets,attachments,author_id"
                ),
                "expansions": "author_id,attachments.media_keys",
                "user.fields": "id,name,username",
                "media.fields": "media_key,type,url,preview_image_url",
            }
            if next_token:
                params["next_token"] = next_token

            payload, _ = _request_with_retries(config.x_api_bearer_token, params)
            pages_fetched += 1
            requests_this_run += 1
            page_in_window += 1

            raw_path = raw_dir / (
                f"{args.output_prefix}_{window_start.isoformat()}_{window_end.isoformat()}"
                f"_page{page_in_window:04d}_{timestamp}.json"
            )
            raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            frame = _normalize_and_filter(payload)
            upserted = 0
            if not frame.empty:
                frame["raw_json_path"] = str(raw_path)
                upserted = _upsert_posts(config.duckdb_path, frame)
                parquet_frames.append(frame)
            posts_upserted += upserted

            meta = payload.get("meta") or {}
            next_token = meta.get("next_token")
            LOGGER.info(
                "window=%s..%s page=%s upserted=%s total=%s next=%s",
                window_start,
                window_end,
                page_in_window,
                upserted,
                posts_upserted,
                bool(next_token),
            )

            completed = window_index == len(windows) - 1 and next_token is None
            _save_checkpoint(
                checkpoint_path,
                Checkpoint(
                    query=args.query,
                    start_date=args.start_date,
                    end_date=end_date.isoformat(),
                    window_days=args.window_days,
                    window_index=window_index,
                    page_in_window=page_in_window,
                    next_token=next_token,
                    pages_fetched=pages_fetched,
                    posts_upserted=posts_upserted,
                    completed=completed and (window_index == len(windows) - 1),
                    updated_at=datetime.now(UTC).isoformat(),
                ),
            )

            # Gentle pacing significantly reduces 429 retries/cost churn.
            if args.request_interval_seconds > 0:
                time.sleep(args.request_interval_seconds)

            if not next_token:
                window_complete = True
                break

        if window_complete:
            # move to next window only after fully consuming current pagination.
            window_index += 1
            page_in_window = 0
            next_token = None

        if stop_run:
            break

    finished = window_index >= len(windows)
    _save_checkpoint(
        checkpoint_path,
        Checkpoint(
            query=args.query,
            start_date=args.start_date,
            end_date=end_date.isoformat(),
            window_days=args.window_days,
            window_index=min(window_index, len(windows) - 1),
            page_in_window=page_in_window,
            next_token=next_token,
            pages_fetched=pages_fetched,
            posts_upserted=posts_upserted,
            completed=finished,
            updated_at=datetime.now(UTC).isoformat(),
        ),
    )

    parquet_path = processed_dir / f"{args.output_prefix}_{timestamp}.parquet"
    if parquet_frames:
        combined = pd.concat(parquet_frames, ignore_index=True).drop_duplicates(subset=["post_id"], keep="last")
        combined.to_parquet(parquet_path, index=False)
        run_rows = len(combined)
    else:
        pd.DataFrame().to_parquet(parquet_path, index=False)
        run_rows = 0

    print(
        json.dumps(
            {
                "query": args.query,
                "start_date": args.start_date,
                "end_date": end_date.isoformat(),
                "window_days": args.window_days,
                "windows_total": len(windows),
                "finished": finished,
                "pages_fetched": pages_fetched,
                "requests_this_run": requests_this_run,
                "posts_upserted_total": posts_upserted,
                "rows_in_this_run_parquet": run_rows,
                "checkpoint": str(checkpoint_path),
                "run_parquet": str(parquet_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
