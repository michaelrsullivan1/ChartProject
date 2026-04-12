"""add tweet keywords

Revision ID: 0005_add_tweet_keywords
Revises: 0004_add_tweet_sentiment_scores
Create Date: 2026-03-31 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_add_tweet_keywords"
down_revision: Union[str, None] = "0004_add_tweet_sentiment_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tweet_keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tweet_id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("normalized_keyword", sa.String(length=255), nullable=False),
        sa.Column("keyword_length", sa.Integer(), nullable=False),
        sa.Column("keyword_type", sa.String(length=32), nullable=False, server_default="exact_ngram"),
        sa.Column("extractor_key", sa.String(length=64), nullable=False),
        sa.Column("extractor_version", sa.String(length=32), nullable=False),
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
            name=op.f("fk_tweet_keywords_tweet_id_tweets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tweet_keywords")),
        sa.UniqueConstraint(
            "tweet_id",
            "normalized_keyword",
            "extractor_key",
            "extractor_version",
            name="uq_tweet_keywords_tweet_keyword_extractor",
        ),
    )
    op.create_index(op.f("ix_tweet_keywords_extractor_key"), "tweet_keywords", ["extractor_key"], unique=False)
    op.create_index(
        op.f("ix_tweet_keywords_extractor_version"),
        "tweet_keywords",
        ["extractor_version"],
        unique=False,
    )
    op.create_index(op.f("ix_tweet_keywords_keyword_length"), "tweet_keywords", ["keyword_length"], unique=False)
    op.create_index(
        op.f("ix_tweet_keywords_normalized_keyword"),
        "tweet_keywords",
        ["normalized_keyword"],
        unique=False,
    )
    op.create_index(op.f("ix_tweet_keywords_tweet_id"), "tweet_keywords", ["tweet_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tweet_keywords_tweet_id"), table_name="tweet_keywords")
    op.drop_index(op.f("ix_tweet_keywords_normalized_keyword"), table_name="tweet_keywords")
    op.drop_index(op.f("ix_tweet_keywords_keyword_length"), table_name="tweet_keywords")
    op.drop_index(op.f("ix_tweet_keywords_extractor_version"), table_name="tweet_keywords")
    op.drop_index(op.f("ix_tweet_keywords_extractor_key"), table_name="tweet_keywords")
    op.drop_table("tweet_keywords")
