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

LOGGER = logging.getLogger("aggregate_btc_prices")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate BTC prices into weekly/monthly candles")
    parser.add_argument("--source", default="stooq")
    parser.add_argument(
        "--granularities",
        nargs="+",
        default=["weekly", "monthly"],
        choices=["weekly", "monthly"],
    )
    return parser.parse_args()


def main() -> None:
    from chartproject.core.config import load_config
    from chartproject.core.logging_config import configure_logging
    from chartproject.domains.market.aggregation import rebuild_btc_aggregates

    args = parse_args()
    config = load_config()
    configure_logging(config.log_level)

    results: dict[str, int] = {}
    for granularity in args.granularities:
        row_count = rebuild_btc_aggregates(
            warehouse_path=config.duckdb_path,
            source=args.source,
            granularity=granularity,
        )
        results[granularity] = row_count
        LOGGER.info("Built %s BTC %s buckets", row_count, granularity)

    print(json.dumps({"source": args.source, "rows": results}, indent=2))


if __name__ == "__main__":
    main()
