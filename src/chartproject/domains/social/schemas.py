from __future__ import annotations

RAW_POSTS_TABLE = "raw_social_posts"
CLASSIFIED_POSTS_TABLE = "classified_social_posts"
SOCIAL_AGGREGATES_TABLE = "social_post_aggregates"


def create_social_table_statements() -> list[str]:
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {RAW_POSTS_TABLE} (
            post_id VARCHAR PRIMARY KEY,
            created_at TIMESTAMP,
            created_date DATE,
            text VARCHAR,
            url VARCHAR,
            author_username VARCHAR,
            author_display_name VARCHAR,
            like_count BIGINT,
            repost_count BIGINT,
            reply_count BIGINT,
            quote_count BIGINT,
            view_count BIGINT,
            is_repost BOOLEAN,
            is_quote BOOLEAN,
            has_media BOOLEAN,
            media_count INTEGER,
            language VARCHAR,
            source VARCHAR NOT NULL,
            conversation_id VARCHAR,
            raw_json_path VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {CLASSIFIED_POSTS_TABLE} (
            post_id VARCHAR PRIMARY KEY,
            created_at TIMESTAMP,
            created_date DATE,
            text VARCHAR,
            url VARCHAR,
            bitcoin_related BOOLEAN,
            bitcoin_adjacent BOOLEAN,
            bitcoin_relevance_score DOUBLE,
            classification_reason VARCHAR,
            matched_terms VARCHAR,
            manual_override VARCHAR,
            iconic_candidate BOOLEAN,
            theme_tags VARCHAR,
            classifier_version VARCHAR,
            classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SOCIAL_AGGREGATES_TABLE} (
            bucket_start DATE,
            bucket_end DATE,
            bucket_label VARCHAR,
            bucket_granularity VARCHAR,
            bitcoin_related_post_count INTEGER,
            bitcoin_adjacent_post_count INTEGER,
            all_post_count INTEGER,
            iconic_post_count INTEGER,
            engagement_sum BIGINT,
            engagement_avg DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (bucket_start, bucket_granularity)
        )
        """,
    ]
