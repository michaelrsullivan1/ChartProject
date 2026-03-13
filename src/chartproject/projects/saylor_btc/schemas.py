from __future__ import annotations

MANUAL_ICONIC_EVENTS_TABLE = "manual_iconic_events"
ALIGNED_SERIES_TABLE = "aligned_saylor_btc_series"


def create_project_table_statements() -> list[str]:
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {MANUAL_ICONIC_EVENTS_TABLE} (
            post_id VARCHAR PRIMARY KEY,
            date DATE,
            title VARCHAR,
            summary VARCHAR,
            importance_score DOUBLE,
            include_in_animation BOOLEAN,
            notes VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {ALIGNED_SERIES_TABLE} (
            bucket_start DATE,
            bucket_end DATE,
            bucket_label VARCHAR,
            bucket_granularity VARCHAR,
            btc_close DOUBLE,
            bitcoin_related_post_count INTEGER,
            bitcoin_adjacent_post_count INTEGER,
            all_post_count INTEGER,
            iconic_post_count INTEGER,
            has_iconic_event BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (bucket_start, bucket_granularity)
        )
        """,
    ]
