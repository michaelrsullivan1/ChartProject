"""add user cohort tag tables

Revision ID: 0007_add_user_cohort_tags
Revises: 0006_add_tweet_mood_scores
Create Date: 2026-04-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_add_user_cohort_tags"
down_revision: Union[str, None] = "0006_add_tweet_mood_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cohort_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cohort_tags")),
        sa.UniqueConstraint("slug", name=op.f("uq_cohort_tags_slug")),
        sa.UniqueConstraint("name", name=op.f("uq_cohort_tags_name")),
    )
    op.create_index(op.f("ix_cohort_tags_slug"), "cohort_tags", ["slug"], unique=False)

    op.create_table(
        "user_cohort_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("cohort_tag_id", sa.Integer(), nullable=False),
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
            ["cohort_tag_id"],
            ["cohort_tags.id"],
            name=op.f("fk_user_cohort_tags_cohort_tag_id_cohort_tags"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_cohort_tags_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_cohort_tags")),
        sa.UniqueConstraint(
            "user_id",
            "cohort_tag_id",
            name="uq_user_cohort_tags_user_id_cohort_tag_id",
        ),
    )
    op.create_index(op.f("ix_user_cohort_tags_user_id"), "user_cohort_tags", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_user_cohort_tags_cohort_tag_id"),
        "user_cohort_tags",
        ["cohort_tag_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_cohort_tags_cohort_tag_id"), table_name="user_cohort_tags")
    op.drop_index(op.f("ix_user_cohort_tags_user_id"), table_name="user_cohort_tags")
    op.drop_table("user_cohort_tags")

    op.drop_index(op.f("ix_cohort_tags_slug"), table_name="cohort_tags")
    op.drop_table("cohort_tags")
