"""add market price points

Revision ID: 0003_add_market_price_points
Revises: 0002_add_ingestion_progress_fields
Create Date: 2026-03-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_market_price_points"
down_revision: Union[str, None] = "0002_ingest_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_price_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("asset_symbol", sa.String(length=16), nullable=False),
        sa.Column("quote_currency", sa.String(length=16), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("market_cap", sa.Float(), nullable=True),
        sa.Column("total_volume", sa.Float(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_price_points")),
        sa.UniqueConstraint(
            "asset_symbol",
            "quote_currency",
            "interval",
            "observed_at",
            name="uq_market_price_points_asset_quote_interval_observed_at",
        ),
    )
    op.create_index(op.f("ix_market_price_points_asset_symbol"), "market_price_points", ["asset_symbol"], unique=False)
    op.create_index(op.f("ix_market_price_points_interval"), "market_price_points", ["interval"], unique=False)
    op.create_index(
        op.f("ix_market_price_points_observed_at"),
        "market_price_points",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_market_price_points_quote_currency"),
        "market_price_points",
        ["quote_currency"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_market_price_points_quote_currency"), table_name="market_price_points")
    op.drop_index(op.f("ix_market_price_points_observed_at"), table_name="market_price_points")
    op.drop_index(op.f("ix_market_price_points_interval"), table_name="market_price_points")
    op.drop_index(op.f("ix_market_price_points_asset_symbol"), table_name="market_price_points")
    op.drop_table("market_price_points")
