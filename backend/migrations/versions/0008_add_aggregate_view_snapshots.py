"""add aggregate view snapshots

Revision ID: 0008_agg_view_snapshots
Revises: 0007_add_user_cohort_tags
Create Date: 2026-04-09 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_agg_view_snapshots"
down_revision: Union[str, None] = "0007_add_user_cohort_tags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aggregate_view_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cache_key", sa.String(length=512), nullable=False),
        sa.Column("view_type", sa.String(length=64), nullable=False),
        sa.Column("cohort_tag_slug", sa.String(length=64), nullable=False),
        sa.Column("granularity", sa.String(length=16), nullable=False),
        sa.Column("model_key", sa.String(length=255), nullable=False),
        sa.Column("cache_version", sa.Integer(), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_signature", sa.String(length=255), nullable=True),
        sa.Column("build_meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_aggregate_view_snapshots")),
        sa.UniqueConstraint("cache_key", name=op.f("uq_aggregate_view_snapshots_cache_key")),
        sa.UniqueConstraint(
            "view_type",
            "cohort_tag_slug",
            "granularity",
            "model_key",
            "cache_version",
            name="uq_aggregate_view_snapshots_lookup",
        ),
    )
    op.create_index(
        op.f("ix_aggregate_view_snapshots_cache_key"),
        "aggregate_view_snapshots",
        ["cache_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aggregate_view_snapshots_view_type"),
        "aggregate_view_snapshots",
        ["view_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aggregate_view_snapshots_cohort_tag_slug"),
        "aggregate_view_snapshots",
        ["cohort_tag_slug"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aggregate_view_snapshots_granularity"),
        "aggregate_view_snapshots",
        ["granularity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_aggregate_view_snapshots_model_key"),
        "aggregate_view_snapshots",
        ["model_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_aggregate_view_snapshots_model_key"),
        table_name="aggregate_view_snapshots",
    )
    op.drop_index(
        op.f("ix_aggregate_view_snapshots_granularity"),
        table_name="aggregate_view_snapshots",
    )
    op.drop_index(
        op.f("ix_aggregate_view_snapshots_cohort_tag_slug"),
        table_name="aggregate_view_snapshots",
    )
    op.drop_index(
        op.f("ix_aggregate_view_snapshots_view_type"),
        table_name="aggregate_view_snapshots",
    )
    op.drop_index(
        op.f("ix_aggregate_view_snapshots_cache_key"),
        table_name="aggregate_view_snapshots",
    )
    op.drop_table("aggregate_view_snapshots")
