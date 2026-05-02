"""add tweet price mentions

Revision ID: 0013_tweet_price_mentions
Revises: 0012_add_podcast_core_schema
Create Date: 2026-05-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_tweet_price_mentions"
down_revision: Union[str, None] = "0012_add_podcast_core_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tweet_price_mentions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tweet_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("price_usd", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column(
            "mention_type",
            sa.String(length=20),
            nullable=False,
            server_default="unclassified",
        ),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("raw_fragment", sa.Text(), nullable=False),
        sa.Column(
            "extractor_key",
            sa.String(length=64),
            nullable=False,
            server_default="price-mention-regex",
        ),
        sa.Column(
            "extractor_version",
            sa.String(length=16),
            nullable=False,
            server_default="v1",
        ),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["tweet_id"],
            ["tweets.id"],
            name=op.f("fk_tweet_price_mentions_tweet_id_tweets"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_tweet_price_mentions_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tweet_price_mentions")),
        sa.UniqueConstraint(
            "tweet_id",
            "price_usd",
            "extractor_key",
            "extractor_version",
            name="uq_tweet_price_mentions_dedup",
        ),
    )
    op.create_index(
        op.f("ix_tweet_price_mentions_tweet_id"),
        "tweet_price_mentions",
        ["tweet_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tweet_price_mentions_user_id"),
        "tweet_price_mentions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tweet_price_mentions_price_usd"),
        "tweet_price_mentions",
        ["price_usd"],
        unique=False,
    )
    # Composite index optimized for the primary cohort query pattern:
    # WHERE user_id IN (...) AND extractor_key = ? AND extractor_version = ? AND confidence >= ?
    op.create_index(
        "ix_tweet_price_mentions_cohort_query",
        "tweet_price_mentions",
        ["user_id", "extractor_key", "extractor_version", "confidence"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tweet_price_mentions_cohort_query", table_name="tweet_price_mentions")
    op.drop_index(
        op.f("ix_tweet_price_mentions_price_usd"), table_name="tweet_price_mentions"
    )
    op.drop_index(
        op.f("ix_tweet_price_mentions_user_id"), table_name="tweet_price_mentions"
    )
    op.drop_index(
        op.f("ix_tweet_price_mentions_tweet_id"), table_name="tweet_price_mentions"
    )
    op.drop_table("tweet_price_mentions")
