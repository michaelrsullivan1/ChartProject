from __future__ import annotations

from chartproject.domains.market.schemas import (
    BTC_PRICE_AGGREGATES_TABLE,
    RAW_BTC_PRICES_TABLE,
    create_market_table_statements,
)
from chartproject.domains.social.schemas import (
    CLASSIFIED_POSTS_TABLE,
    RAW_POSTS_TABLE,
    SOCIAL_AGGREGATES_TABLE,
    create_social_table_statements,
)
from chartproject.projects.saylor_btc.schemas import (
    ALIGNED_SERIES_TABLE,
    MANUAL_ICONIC_EVENTS_TABLE,
    create_project_table_statements,
)


def all_schema_statements() -> list[str]:
    statements: list[str] = []
    statements.extend(create_social_table_statements())
    statements.extend(create_market_table_statements())
    statements.extend(create_project_table_statements())
    return statements


def expected_tables() -> set[str]:
    return {
        RAW_POSTS_TABLE,
        CLASSIFIED_POSTS_TABLE,
        SOCIAL_AGGREGATES_TABLE,
        RAW_BTC_PRICES_TABLE,
        BTC_PRICE_AGGREGATES_TABLE,
        MANUAL_ICONIC_EVENTS_TABLE,
        ALIGNED_SERIES_TABLE,
    }
