from __future__ import annotations

RAW_BTC_PRICES_TABLE = "raw_btc_prices"
BTC_PRICE_AGGREGATES_TABLE = "btc_price_aggregates"


def create_market_table_statements() -> list[str]:
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {RAW_BTC_PRICES_TABLE} (
            date DATE,
            timestamp TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            source VARCHAR NOT NULL,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date, source)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {BTC_PRICE_AGGREGATES_TABLE} (
            bucket_start DATE,
            bucket_end DATE,
            bucket_label VARCHAR,
            bucket_granularity VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            source VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (bucket_start, bucket_granularity, source)
        )
        """,
    ]
