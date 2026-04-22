"""add podcast core schema

Revision ID: 0012_add_podcast_core_schema
Revises: 0011_add_managed_narratives
Create Date: 2026-04-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_add_podcast_core_schema"
down_revision: Union[str, None] = "0011_add_managed_narratives"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "podcast_shows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_slug", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_podcast_shows")),
        sa.UniqueConstraint("source_slug", name=op.f("uq_podcast_shows_source_slug")),
    )
    op.create_index(op.f("ix_podcast_shows_source_slug"), "podcast_shows", ["source_slug"], unique=False)

    op.create_table(
        "podcast_episodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_episode_id", sa.String(length=255), nullable=False),
        sa.Column("episode_slug", sa.String(length=255), nullable=False),
        sa.Column("podcast_show_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("audio_url", sa.String(length=1024), nullable=True),
        sa.Column("manifest_status", sa.String(length=64), nullable=True),
        sa.Column("manifest_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manifest_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_manifest_path", sa.String(length=1024), nullable=True),
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
            ["podcast_show_id"],
            ["podcast_shows.id"],
            name=op.f("fk_podcast_episodes_podcast_show_id_podcast_shows"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_podcast_episodes")),
        sa.UniqueConstraint(
            "source_episode_id",
            name=op.f("uq_podcast_episodes_source_episode_id"),
        ),
    )
    op.create_index(
        op.f("ix_podcast_episodes_source_episode_id"),
        "podcast_episodes",
        ["source_episode_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_episodes_episode_slug"),
        "podcast_episodes",
        ["episode_slug"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_episodes_podcast_show_id"),
        "podcast_episodes",
        ["podcast_show_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_episodes_published_at"),
        "podcast_episodes",
        ["published_at"],
        unique=False,
    )

    op.create_table(
        "podcast_persons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_person_id", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("bio_summary", sa.Text(), nullable=True),
        sa.Column("has_wiki", sa.Boolean(), nullable=False),
        sa.Column("wiki_url", sa.String(length=1024), nullable=True),
        sa.Column("total_beliefs_source", sa.Integer(), nullable=True),
        sa.Column("trust_badge", sa.String(length=32), nullable=True),
        sa.Column("trust_score", sa.Float(), nullable=True),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trust_calculated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_podcast_persons")),
        sa.UniqueConstraint(
            "source_person_id",
            name=op.f("uq_podcast_persons_source_person_id"),
        ),
        sa.UniqueConstraint("slug", name=op.f("uq_podcast_persons_slug")),
    )
    op.create_index(
        op.f("ix_podcast_persons_source_person_id"),
        "podcast_persons",
        ["source_person_id"],
        unique=False,
    )
    op.create_index(op.f("ix_podcast_persons_slug"), "podcast_persons", ["slug"], unique=False)

    op.create_table(
        "podcast_appearances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("podcast_person_id", sa.Integer(), nullable=False),
        sa.Column("podcast_episode_id", sa.Integer(), nullable=False),
        sa.Column("source_person_id", sa.String(length=255), nullable=False),
        sa.Column("source_episode_id", sa.String(length=255), nullable=False),
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
            ["podcast_episode_id"],
            ["podcast_episodes.id"],
            name=op.f("fk_podcast_appearances_podcast_episode_id_podcast_episodes"),
        ),
        sa.ForeignKeyConstraint(
            ["podcast_person_id"],
            ["podcast_persons.id"],
            name=op.f("fk_podcast_appearances_podcast_person_id_podcast_persons"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_podcast_appearances")),
        sa.UniqueConstraint(
            "podcast_person_id",
            "podcast_episode_id",
            name="uq_podcast_appearances_podcast_person_id_podcast_episode_id",
        ),
    )
    op.create_index(
        op.f("ix_podcast_appearances_podcast_person_id"),
        "podcast_appearances",
        ["podcast_person_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_appearances_podcast_episode_id"),
        "podcast_appearances",
        ["podcast_episode_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_appearances_source_person_id"),
        "podcast_appearances",
        ["source_person_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_appearances_source_episode_id"),
        "podcast_appearances",
        ["source_episode_id"],
        unique=False,
    )

    op.create_table(
        "podcast_beliefs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_belief_id", sa.String(length=255), nullable=False),
        sa.Column("podcast_person_id", sa.Integer(), nullable=False),
        sa.Column("podcast_episode_id", sa.Integer(), nullable=False),
        sa.Column("podcast_show_id", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("atomic_belief", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("worldview", sa.Text(), nullable=True),
        sa.Column("core_axiom", sa.Text(), nullable=True),
        sa.Column("weights_json", sa.JSON(), nullable=True),
        sa.Column("timestamp_start_seconds", sa.Float(), nullable=True),
        sa.Column("timestamp_end_seconds", sa.Float(), nullable=True),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
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
            ["podcast_episode_id"],
            ["podcast_episodes.id"],
            name=op.f("fk_podcast_beliefs_podcast_episode_id_podcast_episodes"),
        ),
        sa.ForeignKeyConstraint(
            ["podcast_person_id"],
            ["podcast_persons.id"],
            name=op.f("fk_podcast_beliefs_podcast_person_id_podcast_persons"),
        ),
        sa.ForeignKeyConstraint(
            ["podcast_show_id"],
            ["podcast_shows.id"],
            name=op.f("fk_podcast_beliefs_podcast_show_id_podcast_shows"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_podcast_beliefs")),
        sa.UniqueConstraint(
            "source_belief_id",
            name=op.f("uq_podcast_beliefs_source_belief_id"),
        ),
    )
    op.create_index(
        op.f("ix_podcast_beliefs_source_belief_id"),
        "podcast_beliefs",
        ["source_belief_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_beliefs_podcast_person_id"),
        "podcast_beliefs",
        ["podcast_person_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_beliefs_podcast_episode_id"),
        "podcast_beliefs",
        ["podcast_episode_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_beliefs_podcast_show_id"),
        "podcast_beliefs",
        ["podcast_show_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_beliefs_topic"),
        "podcast_beliefs",
        ["topic"],
        unique=False,
    )
    op.create_index(
        op.f("ix_podcast_beliefs_domain"),
        "podcast_beliefs",
        ["domain"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_podcast_beliefs_domain"), table_name="podcast_beliefs")
    op.drop_index(op.f("ix_podcast_beliefs_topic"), table_name="podcast_beliefs")
    op.drop_index(op.f("ix_podcast_beliefs_podcast_show_id"), table_name="podcast_beliefs")
    op.drop_index(
        op.f("ix_podcast_beliefs_podcast_episode_id"),
        table_name="podcast_beliefs",
    )
    op.drop_index(
        op.f("ix_podcast_beliefs_podcast_person_id"),
        table_name="podcast_beliefs",
    )
    op.drop_index(
        op.f("ix_podcast_beliefs_source_belief_id"),
        table_name="podcast_beliefs",
    )
    op.drop_table("podcast_beliefs")

    op.drop_index(
        op.f("ix_podcast_appearances_source_episode_id"),
        table_name="podcast_appearances",
    )
    op.drop_index(
        op.f("ix_podcast_appearances_source_person_id"),
        table_name="podcast_appearances",
    )
    op.drop_index(
        op.f("ix_podcast_appearances_podcast_episode_id"),
        table_name="podcast_appearances",
    )
    op.drop_index(
        op.f("ix_podcast_appearances_podcast_person_id"),
        table_name="podcast_appearances",
    )
    op.drop_table("podcast_appearances")

    op.drop_index(op.f("ix_podcast_persons_slug"), table_name="podcast_persons")
    op.drop_index(
        op.f("ix_podcast_persons_source_person_id"),
        table_name="podcast_persons",
    )
    op.drop_table("podcast_persons")

    op.drop_index(op.f("ix_podcast_episodes_published_at"), table_name="podcast_episodes")
    op.drop_index(
        op.f("ix_podcast_episodes_podcast_show_id"),
        table_name="podcast_episodes",
    )
    op.drop_index(op.f("ix_podcast_episodes_episode_slug"), table_name="podcast_episodes")
    op.drop_index(
        op.f("ix_podcast_episodes_source_episode_id"),
        table_name="podcast_episodes",
    )
    op.drop_table("podcast_episodes")

    op.drop_index(op.f("ix_podcast_shows_source_slug"), table_name="podcast_shows")
    op.drop_table("podcast_shows")
