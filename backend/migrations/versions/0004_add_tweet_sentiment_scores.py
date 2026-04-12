"""add tweet sentiment scores

Revision ID: 0004_add_tweet_sentiment_scores
Revises: 0003_add_market_price_points
Create Date: 2026-03-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_add_tweet_sentiment_scores"
down_revision: Union[str, None] = "0003_add_market_price_points"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tweet_sentiment_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tweet_id", sa.Integer(), nullable=False),
        sa.Column("model_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sentiment_label", sa.String(length=32), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("negative_score", sa.Float(), nullable=True),
        sa.Column("neutral_score", sa.Float(), nullable=True),
        sa.Column("positive_score", sa.Float(), nullable=True),
        sa.Column("skip_reason", sa.String(length=64), nullable=True),
        sa.Column("is_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("input_char_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
            name=op.f("fk_tweet_sentiment_scores_tweet_id_tweets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tweet_sentiment_scores")),
        sa.UniqueConstraint(
            "tweet_id",
            "model_key",
            name="uq_tweet_sentiment_scores_tweet_id_model_key",
        ),
    )
    op.create_index(op.f("ix_tweet_sentiment_scores_model_key"), "tweet_sentiment_scores", ["model_key"], unique=False)
    op.create_index(op.f("ix_tweet_sentiment_scores_status"), "tweet_sentiment_scores", ["status"], unique=False)
    op.create_index(op.f("ix_tweet_sentiment_scores_tweet_id"), "tweet_sentiment_scores", ["tweet_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tweet_sentiment_scores_tweet_id"), table_name="tweet_sentiment_scores")
    op.drop_index(op.f("ix_tweet_sentiment_scores_status"), table_name="tweet_sentiment_scores")
    op.drop_index(op.f("ix_tweet_sentiment_scores_model_key"), table_name="tweet_sentiment_scores")
    op.drop_table("tweet_sentiment_scores")
