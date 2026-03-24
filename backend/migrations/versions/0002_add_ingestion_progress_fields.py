"""add ingestion progress fields

Revision ID: 0002_ingest_progress
Revises: 0001_initial_core_schema
Create Date: 2026-03-24 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_ingest_progress"
down_revision: Union[str, None] = "0001_initial_core_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ingestion_runs", sa.Column("last_cursor", sa.String(length=512), nullable=True))
    op.add_column(
        "ingestion_runs",
        sa.Column("pages_fetched", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column("raw_tweets_fetched", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("ingestion_runs", "pages_fetched", server_default=None)
    op.alter_column("ingestion_runs", "raw_tweets_fetched", server_default=None)


def downgrade() -> None:
    op.drop_column("ingestion_runs", "raw_tweets_fetched")
    op.drop_column("ingestion_runs", "pages_fetched")
    op.drop_column("ingestion_runs", "last_cursor")
