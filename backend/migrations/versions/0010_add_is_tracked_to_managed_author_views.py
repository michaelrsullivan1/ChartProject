"""add is_tracked to managed author views

Revision ID: 0010_managed_author_is_tracked
Revises: 0009_managed_author_views
Create Date: 2026-04-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_managed_author_is_tracked"
down_revision: Union[str, None] = "0009_managed_author_views"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "managed_author_views",
        sa.Column(
            "is_tracked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        op.f("ix_managed_author_views_is_tracked"),
        "managed_author_views",
        ["is_tracked"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_managed_author_views_is_tracked"), table_name="managed_author_views")
    op.drop_column("managed_author_views", "is_tracked")
