from __future__ import annotations

from datetime import date
from pathlib import Path

from chartproject.core.schema_registry import all_schema_statements
from chartproject.core.storage import connect_duckdb, execute_statements
from chartproject.domains.market.aggregation import rebuild_btc_aggregates


def _seed_prices(db_path: Path) -> None:
    connection = connect_duckdb(db_path)
    execute_statements(connection, all_schema_statements())
    connection.execute(
        """
        INSERT INTO raw_btc_prices (date, timestamp, open, high, low, close, volume, source)
        VALUES
            ('2024-01-01', '2024-01-01 00:00:00', 100, 110, 90, 105, 10, 'stooq'),
            ('2024-01-02', '2024-01-02 00:00:00', 105, 120, 100, 115, 20, 'stooq'),
            ('2024-01-07', '2024-01-07 00:00:00', 115, 130, 110, 125, 30, 'stooq'),
            ('2024-01-08', '2024-01-08 00:00:00', 130, 140, 120, 135, 40, 'stooq')
        """
    )
    connection.close()


def test_rebuild_weekly_btc_aggregates(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    _seed_prices(db_path)

    rows = rebuild_btc_aggregates(db_path, source="stooq", granularity="weekly")
    assert rows == 2

    connection = connect_duckdb(db_path)
    result = connection.execute(
        """
        SELECT bucket_start, bucket_end, open, high, low, close, volume
        FROM btc_price_aggregates
        WHERE source = 'stooq' AND bucket_granularity = 'weekly'
        ORDER BY bucket_start
        """
    ).fetchall()
    connection.close()

    assert result[0] == (date(2024, 1, 1), date(2024, 1, 7), 100.0, 130.0, 90.0, 125.0, 60.0)
    assert result[1] == (date(2024, 1, 8), date(2024, 1, 8), 130.0, 140.0, 120.0, 135.0, 40.0)


def test_rebuild_monthly_btc_aggregates(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    _seed_prices(db_path)

    rows = rebuild_btc_aggregates(db_path, source="stooq", granularity="monthly")
    assert rows == 1

    connection = connect_duckdb(db_path)
    result = connection.execute(
        """
        SELECT bucket_start, bucket_end, open, high, low, close, volume
        FROM btc_price_aggregates
        WHERE source = 'stooq' AND bucket_granularity = 'monthly'
        """
    ).fetchone()
    connection.close()

    assert result == (date(2024, 1, 1), date(2024, 1, 8), 100.0, 140.0, 90.0, 135.0, 100.0)
