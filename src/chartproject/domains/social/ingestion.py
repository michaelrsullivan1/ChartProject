from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from chartproject.core.storage import connect_duckdb
from chartproject.domains.social.normalization import normalize_social_page
from chartproject.domains.social.sources.base import SocialDataSource

LOGGER = logging.getLogger(__name__)


@dataclass
class IngestionCheckpoint:
    source: str
    username: str
    next_cursor: str | None
    pages_fetched: int
    posts_seen: int
    updated_at: str
    completed: bool


def load_checkpoint(path: Path) -> IngestionCheckpoint | None:
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    return IngestionCheckpoint(
        source=str(payload.get("source", "")),
        username=str(payload.get("username", "")),
        next_cursor=payload.get("next_cursor"),
        pages_fetched=int(payload.get("pages_fetched", 0)),
        posts_seen=int(payload.get("posts_seen", 0)),
        updated_at=str(payload.get("updated_at", "")),
        completed=bool(payload.get("completed", False)),
    )


def save_checkpoint(path: Path, checkpoint: IngestionCheckpoint) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "source": checkpoint.source,
                "username": checkpoint.username,
                "next_cursor": checkpoint.next_cursor,
                "pages_fetched": checkpoint.pages_fetched,
                "posts_seen": checkpoint.posts_seen,
                "updated_at": checkpoint.updated_at,
                "completed": checkpoint.completed,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def archive_social_page(raw_social_dir: Path, source: str, username: str, page_number: int, payload: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    file_path = raw_social_dir / f"{username}_{source}_page{page_number:04d}_{timestamp}.json"
    file_path.write_text(payload, encoding="utf-8")
    return file_path


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "post_id",
            "created_at",
            "created_date",
            "text",
            "url",
            "author_username",
            "author_display_name",
            "like_count",
            "repost_count",
            "reply_count",
            "quote_count",
            "view_count",
            "is_repost",
            "is_quote",
            "has_media",
            "media_count",
            "language",
            "source",
            "conversation_id",
            "raw_json_path",
        ]
    )


def upsert_raw_posts(warehouse_path: Path, frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0

    connection = connect_duckdb(warehouse_path)
    connection.register("social_posts_df", frame)
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
        FROM social_posts_df
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
    inserted = int(connection.execute("SELECT COUNT(*) FROM social_posts_df").fetchone()[0])
    connection.close()
    return inserted


def ingest_social_posts(
    source: SocialDataSource,
    username: str,
    raw_social_dir: Path,
    warehouse_path: Path,
    checkpoint_path: Path,
    *,
    max_pages: int | None = None,
    max_results: int = 100,
    resume: bool = True,
) -> dict[str, int | str | bool | None]:
    raw_social_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = load_checkpoint(checkpoint_path) if resume else None
    if checkpoint and checkpoint.completed:
        LOGGER.info("Checkpoint indicates completed ingestion; nothing to fetch")
        return {
            "source": checkpoint.source,
            "username": checkpoint.username,
            "pages_fetched": checkpoint.pages_fetched,
            "posts_seen": checkpoint.posts_seen,
            "next_cursor": checkpoint.next_cursor,
            "completed": checkpoint.completed,
            "resumed": True,
        }

    cursor = checkpoint.next_cursor if checkpoint else None
    pages_fetched = checkpoint.pages_fetched if checkpoint else 0
    posts_seen = checkpoint.posts_seen if checkpoint else 0

    while True:
        if max_pages is not None and pages_fetched >= max_pages:
            break

        page = source.fetch_page(cursor=cursor, max_results=max_results)
        pages_fetched += 1

        raw_path = archive_social_page(
            raw_social_dir=raw_social_dir,
            source=page.source_name,
            username=username,
            page_number=pages_fetched,
            payload=page.raw_payload,
        )

        normalized = normalize_social_page(page, raw_json_path=raw_path)
        if normalized.empty:
            upserted_count = 0
            normalized = _empty_frame()
        else:
            upserted_count = upsert_raw_posts(warehouse_path, normalized)
        posts_seen += upserted_count

        cursor = page.next_cursor
        completed = cursor is None
        save_checkpoint(
            checkpoint_path,
            IngestionCheckpoint(
                source=page.source_name,
                username=username,
                next_cursor=cursor,
                pages_fetched=pages_fetched,
                posts_seen=posts_seen,
                updated_at=datetime.now(UTC).isoformat(),
                completed=completed,
            ),
        )

        LOGGER.info(
            "Fetched page %s, upserted %s posts (running total %s)",
            pages_fetched,
            upserted_count,
            posts_seen,
        )

        if completed:
            break

    final_checkpoint = load_checkpoint(checkpoint_path)
    return {
        "source": final_checkpoint.source if final_checkpoint else source.source_name,
        "username": username,
        "pages_fetched": pages_fetched,
        "posts_seen": posts_seen,
        "next_cursor": final_checkpoint.next_cursor if final_checkpoint else cursor,
        "completed": final_checkpoint.completed if final_checkpoint else (cursor is None),
        "resumed": checkpoint is not None,
    }
