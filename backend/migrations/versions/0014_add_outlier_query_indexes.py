"""add outlier query indexes

Revision ID: 0014_outlier_query_indexes
Revises: 0013_tweet_price_mentions
Create Date: 2026-05-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0014_outlier_query_indexes"
down_revision: Union[str, None] = "0013_tweet_price_mentions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tweet_mood_scores_scored_model_label_tweet
        ON tweet_mood_scores (model_key, mood_label, tweet_id)
        INCLUDE (score)
        WHERE status = 'scored'
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tweets_author_created_id
        ON tweets (author_user_id, created_at_platform, id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tweets_author_created_id")
    op.execute("DROP INDEX IF EXISTS ix_tweet_mood_scores_scored_model_label_tweet")
