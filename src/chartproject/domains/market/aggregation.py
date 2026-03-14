from __future__ import annotations

from pathlib import Path

from chartproject.core.storage import connect_duckdb


def _bucket_expression(granularity: str) -> str:
    if granularity not in {"weekly", "monthly"}:
        raise ValueError("granularity must be one of: weekly, monthly")
    unit = "week" if granularity == "weekly" else "month"
    return f"date_trunc('{unit}', date)::DATE"


def rebuild_btc_aggregates(warehouse_path: Path, source: str, granularity: str) -> int:
    bucket_expr = _bucket_expression(granularity)
    bucket_label_expr = (
        "strftime(bucket_start, '%Y-W%V')" if granularity == "weekly" else "strftime(bucket_start, '%Y-%m')"
    )

    connection = connect_duckdb(warehouse_path)
    connection.execute(
        "DELETE FROM btc_price_aggregates WHERE source = ? AND bucket_granularity = ?",
        [source, granularity],
    )

    connection.execute(
        f"""
        INSERT INTO btc_price_aggregates (
            bucket_start,
            bucket_end,
            bucket_label,
            bucket_granularity,
            open,
            high,
            low,
            close,
            volume,
            source
        )
        WITH bucketed AS (
            SELECT
                date,
                {bucket_expr} AS bucket_start,
                open,
                high,
                low,
                close,
                volume,
                source
            FROM raw_btc_prices
            WHERE source = ?
        ), ranked AS (
            SELECT
                *,
                row_number() OVER (PARTITION BY bucket_start ORDER BY date ASC) AS rn_open,
                row_number() OVER (PARTITION BY bucket_start ORDER BY date DESC) AS rn_close
            FROM bucketed
        )
        SELECT
            bucket_start,
            max(date) AS bucket_end,
            {bucket_label_expr} AS bucket_label,
            ? AS bucket_granularity,
            max(CASE WHEN rn_open = 1 THEN open END) AS open,
            max(high) AS high,
            min(low) AS low,
            max(CASE WHEN rn_close = 1 THEN close END) AS close,
            sum(volume) AS volume,
            ? AS source
        FROM ranked
        GROUP BY bucket_start
        ORDER BY bucket_start
        """,
        [source, granularity, source],
    )

    inserted = int(
        connection.execute(
            "SELECT COUNT(*) FROM btc_price_aggregates WHERE source = ? AND bucket_granularity = ?",
            [source, granularity],
        ).fetchone()[0]
    )
    connection.close()
    return inserted
