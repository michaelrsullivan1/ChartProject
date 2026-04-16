"""add managed narratives

Revision ID: 0011_add_managed_narratives
Revises: 0010_add_is_tracked_to_managed_author_views
Create Date: 2026-04-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_add_managed_narratives"
down_revision: Union[str, None] = "0010_add_is_tracked_to_managed_author_views"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "managed_narratives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phrase", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_managed_narratives")),
        sa.UniqueConstraint("slug", name=op.f("uq_managed_narratives_slug")),
        sa.UniqueConstraint("name", name=op.f("uq_managed_narratives_name")),
        sa.UniqueConstraint("phrase", name=op.f("uq_managed_narratives_phrase")),
    )
    op.create_index(op.f("ix_managed_narratives_slug"), "managed_narratives", ["slug"], unique=False)
    op.create_index(
        op.f("ix_managed_narratives_phrase"),
        "managed_narratives",
        ["phrase"],
        unique=False,
    )

    op.create_table(
        "tweet_narrative_matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tweet_id", sa.Integer(), nullable=False),
        sa.Column("managed_narrative_id", sa.Integer(), nullable=False),
        sa.Column("matched_phrase", sa.String(length=255), nullable=False),
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
            ["managed_narrative_id"],
            ["managed_narratives.id"],
            name=op.f(
                "fk_tweet_narrative_matches_managed_narrative_id_managed_narratives"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["tweet_id"],
            ["tweets.id"],
            name=op.f("fk_tweet_narrative_matches_tweet_id_tweets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tweet_narrative_matches")),
        sa.UniqueConstraint(
            "tweet_id",
            "managed_narrative_id",
            name="uq_tweet_narrative_matches_tweet_id_managed_narrative_id",
        ),
    )
    op.create_index(
        op.f("ix_tweet_narrative_matches_tweet_id"),
        "tweet_narrative_matches",
        ["tweet_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tweet_narrative_matches_managed_narrative_id"),
        "tweet_narrative_matches",
        ["managed_narrative_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tweet_narrative_matches_managed_narrative_id"),
        table_name="tweet_narrative_matches",
    )
    op.drop_index(
        op.f("ix_tweet_narrative_matches_tweet_id"),
        table_name="tweet_narrative_matches",
    )
    op.drop_table("tweet_narrative_matches")

    op.drop_index(op.f("ix_managed_narratives_phrase"), table_name="managed_narratives")
    op.drop_index(op.f("ix_managed_narratives_slug"), table_name="managed_narratives")
    op.drop_table("managed_narratives")
