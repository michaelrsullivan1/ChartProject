from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from chartproject.core.storage import connect_duckdb
from chartproject.domains.market.normalization import normalize_daily_market_frame
from chartproject.domains.market.sources.base import MarketDataSource

LOGGER = logging.getLogger(__name__)


def archive_raw_payload(raw_market_dir: Path, source_name: str, extension: str, payload: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    raw_path = raw_market_dir / f"btc_usd_daily_{source_name}_{timestamp}.{extension}"
    raw_path.write_text(payload, encoding="utf-8")
    return raw_path


def write_normalized_parquet(processed_market_dir: Path, source_name: str, frame: pd.DataFrame) -> Path:
    processed_market_dir.mkdir(parents=True, exist_ok=True)
    path = processed_market_dir / f"btc_usd_daily_{source_name}.parquet"
    frame.to_parquet(path, index=False)
    return path


def upsert_raw_prices(connection_path: Path, frame: pd.DataFrame) -> int:
    connection = connect_duckdb(connection_path)
    connection.register("btc_prices_df", frame)
    connection.execute(
        """
        INSERT INTO raw_btc_prices (date, timestamp, open, high, low, close, volume, source)
        SELECT date, timestamp, open, high, low, close, volume, source
        FROM btc_prices_df
        ON CONFLICT (date, source) DO UPDATE SET
            timestamp = EXCLUDED.timestamp,
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            ingested_at = now()
        """
    )
    rows = int(connection.execute("SELECT COUNT(*) FROM btc_prices_df").fetchone()[0])
    connection.close()
    return rows


def ingest_daily_btc_prices(
    source: MarketDataSource,
    raw_market_dir: Path,
    processed_market_dir: Path,
    warehouse_path: Path,
) -> dict[str, str | int]:
    pull = source.fetch_daily_prices()
    raw_path = archive_raw_payload(raw_market_dir, pull.source_name, pull.raw_extension, pull.raw_payload)

    normalized = normalize_daily_market_frame(pull.dataframe, pull.source_name)
    parquet_path = write_normalized_parquet(processed_market_dir, pull.source_name, normalized)
    row_count = upsert_raw_prices(warehouse_path, normalized)

    LOGGER.info("Ingested %s daily BTC rows from %s", row_count, pull.source_name)
    return {
        "source": pull.source_name,
        "source_url": pull.source_url,
        "raw_path": str(raw_path),
        "parquet_path": str(parquet_path),
        "row_count": row_count,
    }
