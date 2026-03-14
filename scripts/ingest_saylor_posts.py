#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

LOGGER = logging.getLogger("ingest_saylor_posts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Michael Saylor posts into raw_social_posts")
    parser.add_argument("--username", default="saylor", help="X username to ingest")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional max page limit")
    parser.add_argument("--max-results", type=int, default=100, help="Page size (5-100)")
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Optional checkpoint path (defaults to data/interim/social/<username>_x_api_checkpoint.json)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore checkpoint and start from first page",
    )
    return parser.parse_args()


def main() -> None:
    from chartproject.core.config import ensure_directories, load_config
    from chartproject.core.logging_config import configure_logging
    from chartproject.core.schema_registry import all_schema_statements
    from chartproject.core.storage import connect_duckdb, execute_statements
    from chartproject.domains.social.ingestion import ingest_social_posts
    from chartproject.domains.social.sources.x_api import XApiV2UserPostsSource

    args = parse_args()
    config = load_config()
    configure_logging(config.log_level)
    ensure_directories(config.paths)

    if not config.x_api_bearer_token:
        raise SystemExit(
            "X_API_BEARER_TOKEN is not set. Add it to your .env before running social ingestion."
        )

    connection = connect_duckdb(config.duckdb_path)
    execute_statements(connection, all_schema_statements())
    connection.close()

    checkpoint_path = (
        Path(args.checkpoint)
        if args.checkpoint
        else config.paths.interim / "social" / f"{args.username}_x_api_checkpoint.json"
    )

    source = XApiV2UserPostsSource(
        bearer_token=config.x_api_bearer_token,
        username=args.username,
    )

    result = ingest_social_posts(
        source=source,
        username=args.username,
        raw_social_dir=config.paths.raw / "social",
        warehouse_path=config.duckdb_path,
        checkpoint_path=checkpoint_path,
        max_pages=args.max_pages,
        max_results=args.max_results,
        resume=not args.no_resume,
    )

    LOGGER.info("Social ingestion complete")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
