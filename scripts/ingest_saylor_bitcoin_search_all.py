#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

LOGGER = logging.getLogger("ingest_saylor_bitcoin_search_all")
DEFAULT_QUERY = "from:saylor (bitcoin OR btc OR #bitcoin OR #btc)"
API_BASE = "https://api.x.com/2/tweets/search/all"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Bitcoin-scoped Saylor posts via X search/all")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--max-results", type=int, default=100, help="Rows per page (10-100)")
    parser.add_argument("--max-pages", type=int, default=0, help="0 means no page cap")
    parser.add_argument("--output-prefix", default="saylor_bitcoin_search_all")
    return parser.parse_args()


def _request_with_retries(bearer_token: str, params: dict[str, str]) -> tuple[dict, str]:
    request_url = f"{API_BASE}?{urlencode(params)}"
    request = Request(
        url=request_url,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "chartproject-bitcoin-search/0.1",
        },
        method="GET",
    )

    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
            return json.loads(payload), request_url
        except URLError as error:
            LOGGER.warning("urllib TLS request failed (%s); using curl fallback", error)
            result = subprocess.run(
                [
                    "curl",
                    "-fsSL",
                    request_url,
                    "-H",
                    f"Authorization: Bearer {bearer_token}",
                    "-H",
                    "User-Agent: chartproject-bitcoin-search/0.1",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(result.stdout), request_url
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="ignore")
            if error.code == 429 and attempt < 3:
                retry_after = error.headers.get("retry-after")
                wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 15
                LOGGER.warning("Rate limited; sleeping %ss before retry", wait_seconds)
                time.sleep(wait_seconds)
                continue
            raise RuntimeError(f"X search/all failed ({error.code}) at {request_url}: {body}") from error

    raise RuntimeError("Search request failed after retries")


def _normalize_posts(response_payload: dict) -> pd.DataFrame:
    users = {
        str(user.get("id")): user
        for user in (response_payload.get("includes") or {}).get("users", [])
        if isinstance(user, dict)
    }

    rows: list[dict] = []
    for post in response_payload.get("data", []):
        post_id = str(post.get("id", "")).strip()
        if not post_id:
            continue

        created_ts = pd.to_datetime(post.get("created_at"), utc=True, errors="coerce")
        public_metrics = post.get("public_metrics") or {}
        referenced = post.get("referenced_tweets") or []
        referenced_types = {item.get("type") for item in referenced if isinstance(item, dict)}
        media_keys = ((post.get("attachments") or {}).get("media_keys") or [])

        author_id = str(post.get("author_id") or "")
        author = users.get(author_id, {})
        username = author.get("username") or "saylor"

        rows.append(
            {
                "post_id": post_id,
                "created_at": created_ts,
                "created_date": created_ts.date() if pd.notna(created_ts) else None,
                "text": post.get("text") or "",
                "url": f"https://x.com/{username}/status/{post_id}",
                "author_username": username,
                "author_display_name": author.get("name"),
                "like_count": int(public_metrics.get("like_count", 0) or 0),
                "repost_count": int(public_metrics.get("retweet_count", 0) or 0),
                "reply_count": int(public_metrics.get("reply_count", 0) or 0),
                "quote_count": int(public_metrics.get("quote_count", 0) or 0),
                "view_count": None,
                "is_repost": "retweeted" in referenced_types,
                "is_quote": "quoted" in referenced_types,
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

    frame = pd.DataFrame(rows).drop_duplicates(subset=["post_id"], keep="last")
    frame = frame.sort_values("created_at")
    return frame.reset_index(drop=True)


def _upsert_posts(duckdb_path: Path, frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0

    from chartproject.core.storage import connect_duckdb

    connection = connect_duckdb(duckdb_path)
    connection.register("search_posts_df", frame)
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
        FROM search_posts_df
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
    row_count = int(connection.execute("SELECT COUNT(*) FROM search_posts_df").fetchone()[0])
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

    connection = connect_duckdb(config.duckdb_path)
    execute_statements(connection, all_schema_statements())
    connection.close()

    raw_dir = config.paths.raw / "social"
    processed_dir = config.paths.processed / "social"
    processed_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    pages_fetched = 0
    total_upserted = 0
    next_token: str | None = None
    page_frames: list[pd.DataFrame] = []

    while True:
        if args.max_pages and pages_fetched >= args.max_pages:
            break

        pages_fetched += 1
        params = {
            "query": args.query,
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

        payload, request_url = _request_with_retries(config.x_api_bearer_token, params)

        raw_path = raw_dir / f"{args.output_prefix}_page{pages_fetched:04d}_{timestamp}.json"
        raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        frame = _normalize_posts(payload)
        upserted = 0
        if not frame.empty:
            frame["raw_json_path"] = str(raw_path)
            upserted = _upsert_posts(config.duckdb_path, frame)
            page_frames.append(frame)

        total_upserted += upserted
        next_token = (payload.get("meta") or {}).get("next_token")

        LOGGER.info(
            "page=%s upserted=%s total_upserted=%s next_token=%s",
            pages_fetched,
            upserted,
            total_upserted,
            bool(next_token),
        )

        if not next_token:
            break

    if page_frames:
        all_rows = pd.concat(page_frames, ignore_index=True).drop_duplicates(subset=["post_id"], keep="last")
        parquet_path = processed_dir / f"{args.output_prefix}_{timestamp}.parquet"
        all_rows.to_parquet(parquet_path, index=False)
    else:
        parquet_path = processed_dir / f"{args.output_prefix}_{timestamp}.parquet"
        pd.DataFrame().to_parquet(parquet_path, index=False)

    print(
        json.dumps(
            {
                "query": args.query,
                "request_type": "search_all",
                "pages_fetched": pages_fetched,
                "total_upserted": total_upserted,
                "next_token": next_token,
                "output_parquet": str(parquet_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
