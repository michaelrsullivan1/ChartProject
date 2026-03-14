#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

LOGGER = logging.getLogger("freeze_saylor_bitcoin_snapshot")
SOURCE_NAME = "x_api_v2_search_all_bitcoin"
CANONICAL_TABLE = "processed_saylor_bitcoin_posts"


def main() -> None:
    from chartproject.core.config import ensure_directories, load_config
    from chartproject.core.logging_config import configure_logging
    from chartproject.core.storage import connect_duckdb

    config = load_config()
    configure_logging(config.log_level)
    ensure_directories(config.paths)

    processed_social_dir = config.paths.processed / "social"
    processed_social_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    canonical_parquet = processed_social_dir / "saylor_bitcoin_posts_canonical.parquet"
    canonical_csv = processed_social_dir / "saylor_bitcoin_posts_canonical.csv"
    versioned_parquet = processed_social_dir / f"saylor_bitcoin_posts_snapshot_{timestamp}.parquet"
    metadata_path = processed_social_dir / "saylor_bitcoin_posts_snapshot_metadata.json"

    connection = connect_duckdb(config.duckdb_path)

    connection.execute(f"DROP TABLE IF EXISTS {CANONICAL_TABLE}")
    connection.execute(
        f"""
        CREATE TABLE {CANONICAL_TABLE} AS
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
            raw_json_path,
            ingested_at
        FROM raw_social_posts
        WHERE source = ?
        ORDER BY created_at ASC
        """,
        [SOURCE_NAME],
    )

    connection.execute(
        f"COPY (SELECT * FROM {CANONICAL_TABLE}) TO ? (FORMAT PARQUET)",
        [str(canonical_parquet)],
    )
    connection.execute(
        f"COPY (SELECT * FROM {CANONICAL_TABLE}) TO ? (FORMAT PARQUET)",
        [str(versioned_parquet)],
    )
    connection.execute(
        f"COPY (SELECT * FROM {CANONICAL_TABLE}) TO ? (HEADER, DELIMITER ',')",
        [str(canonical_csv)],
    )

    count, min_date, max_date = connection.execute(
        f"SELECT COUNT(*), MIN(created_date), MAX(created_date) FROM {CANONICAL_TABLE}"
    ).fetchone()
    connection.close()

    metadata = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": SOURCE_NAME,
        "duckdb_table": CANONICAL_TABLE,
        "row_count": int(count),
        "min_created_date": min_date.isoformat() if min_date else None,
        "max_created_date": max_date.isoformat() if max_date else None,
        "canonical_parquet": str(canonical_parquet),
        "canonical_csv": str(canonical_csv),
        "versioned_parquet": str(versioned_parquet),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    LOGGER.info("Snapshot frozen: %s rows", count)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
