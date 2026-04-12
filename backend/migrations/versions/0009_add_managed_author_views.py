"""add managed author views

Revision ID: 0009_managed_author_views
Revises: 0008_agg_view_snapshots
Create Date: 2026-04-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_managed_author_views"
down_revision: Union[str, None] = "0008_agg_view_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "managed_author_views",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column(
            "published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column(
            "enable_overview",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enable_moods",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enable_heatmap",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enable_bitcoin_mentions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("overview_analysis_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mood_analysis_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heatmap_analysis_start", sa.DateTime(timezone=True), nullable=True),
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
            ["user_id"],
            ["users.id"],
            name=op.f("fk_managed_author_views_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_managed_author_views")),
        sa.UniqueConstraint("slug", name=op.f("uq_managed_author_views_slug")),
        sa.UniqueConstraint("user_id", name=op.f("uq_managed_author_views_user_id")),
    )
    op.create_index(
        op.f("ix_managed_author_views_user_id"),
        "managed_author_views",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_managed_author_views_slug"),
        "managed_author_views",
        ["slug"],
        unique=False,
    )
    op.create_index(
        op.f("ix_managed_author_views_published"),
        "managed_author_views",
        ["published"],
        unique=False,
    )
    op.create_index(
        op.f("ix_managed_author_views_sort_order"),
        "managed_author_views",
        ["sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_managed_author_views_sort_order"), table_name="managed_author_views")
    op.drop_index(op.f("ix_managed_author_views_published"), table_name="managed_author_views")
    op.drop_index(op.f("ix_managed_author_views_slug"), table_name="managed_author_views")
    op.drop_index(op.f("ix_managed_author_views_user_id"), table_name="managed_author_views")
    op.drop_table("managed_author_views")
