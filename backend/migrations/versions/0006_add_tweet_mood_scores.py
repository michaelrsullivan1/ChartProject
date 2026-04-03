"""add tweet mood scores

Revision ID: 0006_add_tweet_mood_scores
Revises: 0005_add_tweet_keywords
Create Date: 2026-04-03 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_add_tweet_mood_scores"
down_revision: Union[str, None] = "0005_add_tweet_keywords"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tweet_mood_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tweet_id", sa.Integer(), nullable=False),
        sa.Column("model_key", sa.String(length=255), nullable=False),
        sa.Column("mood_label", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("skip_reason", sa.String(length=64), nullable=True),
        sa.Column("is_truncated", sa.Boolean(), nullable=False),
        sa.Column("input_char_count", sa.Integer(), nullable=False),
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
            name=op.f("fk_tweet_mood_scores_tweet_id_tweets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tweet_mood_scores")),
        sa.UniqueConstraint(
            "tweet_id",
            "model_key",
            "mood_label",
            name="uq_tweet_mood_scores_tweet_id_model_key_label",
        ),
    )
    op.create_index(op.f("ix_tweet_mood_scores_model_key"), "tweet_mood_scores", ["model_key"], unique=False)
    op.create_index(op.f("ix_tweet_mood_scores_mood_label"), "tweet_mood_scores", ["mood_label"], unique=False)
    op.create_index(op.f("ix_tweet_mood_scores_status"), "tweet_mood_scores", ["status"], unique=False)
    op.create_index(op.f("ix_tweet_mood_scores_tweet_id"), "tweet_mood_scores", ["tweet_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tweet_mood_scores_tweet_id"), table_name="tweet_mood_scores")
    op.drop_index(op.f("ix_tweet_mood_scores_status"), table_name="tweet_mood_scores")
    op.drop_index(op.f("ix_tweet_mood_scores_mood_label"), table_name="tweet_mood_scores")
    op.drop_index(op.f("ix_tweet_mood_scores_model_key"), table_name="tweet_mood_scores")
    op.drop_table("tweet_mood_scores")
