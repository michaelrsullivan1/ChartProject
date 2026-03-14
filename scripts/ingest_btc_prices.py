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

LOGGER = logging.getLogger("ingest_btc_prices")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest BTC daily prices into DuckDB + Parquet")
    parser.add_argument("--source", choices=["stooq"], default="stooq")
    return parser.parse_args()


def main() -> None:
    from chartproject.core.config import ensure_directories, load_config
    from chartproject.core.logging_config import configure_logging
    from chartproject.core.schema_registry import all_schema_statements
    from chartproject.core.storage import connect_duckdb, execute_statements
    from chartproject.domains.market.ingestion import ingest_daily_btc_prices
    from chartproject.domains.market.sources.stooq import StooqBtcUsdDailySource

    args = parse_args()
    config = load_config()
    configure_logging(config.log_level)
    ensure_directories(config.paths)

    connection = connect_duckdb(config.duckdb_path)
    execute_statements(connection, all_schema_statements())
    connection.close()

    source_map = {
        "stooq": StooqBtcUsdDailySource(),
    }
    source = source_map[args.source]

    processed_market_dir = config.paths.processed / "market"
    processed_market_dir.mkdir(parents=True, exist_ok=True)

    result = ingest_daily_btc_prices(
        source=source,
        raw_market_dir=config.paths.raw / "market",
        processed_market_dir=processed_market_dir,
        warehouse_path=config.duckdb_path,
    )

    LOGGER.info("BTC ingestion complete")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
