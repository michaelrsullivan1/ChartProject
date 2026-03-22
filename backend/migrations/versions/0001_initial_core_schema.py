"""initial core schema

Revision ID: 0001_initial_core_schema
Revises:
Create Date: 2026-03-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_core_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform_user_id", sa.String(length=32), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("profile_url", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("follower_count", sa.Integer(), nullable=True),
        sa.Column("following_count", sa.Integer(), nullable=True),
        sa.Column("favourites_count", sa.Integer(), nullable=True),
        sa.Column("media_count", sa.Integer(), nullable=True),
        sa.Column("statuses_count", sa.Integer(), nullable=True),
        sa.Column("created_at_platform", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_blue_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("profile_image_url", sa.String(length=512), nullable=True),
        sa.Column("banner_image_url", sa.String(length=512), nullable=True),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_tweet_seen_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("platform_user_id", name=op.f("uq_users_platform_user_id")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_index(op.f("ix_users_platform_user_id"), "users", ["platform_user_id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=64), nullable=False, server_default="twitterapi.io"),
        sa.Column("endpoint_name", sa.String(length=128), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("target_user_platform_id", sa.String(length=32), nullable=True),
        sa.Column("import_type", sa.String(length=32), nullable=False, server_default="backfill"),
        sa.Column("requested_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="started"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name=op.f("fk_ingestion_runs_target_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_runs")),
    )
    op.create_index(op.f("ix_ingestion_runs_target_user_id"), "ingestion_runs", ["target_user_id"], unique=False)
    op.create_index(
        op.f("ix_ingestion_runs_target_user_platform_id"),
        "ingestion_runs",
        ["target_user_platform_id"],
        unique=False,
    )

    op.create_table(
        "tweets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform_tweet_id", sa.String(length=32), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("created_at_platform", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("conversation_id_platform", sa.String(length=32), nullable=True),
        sa.Column("in_reply_to_platform_tweet_id", sa.String(length=32), nullable=True),
        sa.Column("quoted_platform_tweet_id", sa.String(length=32), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("reply_count", sa.Integer(), nullable=True),
        sa.Column("repost_count", sa.Integer(), nullable=True),
        sa.Column("quote_count", sa.Integer(), nullable=True),
        sa.Column("bookmark_count", sa.Integer(), nullable=True),
        sa.Column("impression_count", sa.Integer(), nullable=True),
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
            ["author_user_id"],
            ["users.id"],
            name=op.f("fk_tweets_author_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tweets")),
        sa.UniqueConstraint("platform_tweet_id", name=op.f("uq_tweets_platform_tweet_id")),
    )
    op.create_index(op.f("ix_tweets_author_user_id"), "tweets", ["author_user_id"], unique=False)
    op.create_index(
        op.f("ix_tweets_conversation_id_platform"),
        "tweets",
        ["conversation_id_platform"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tweets_created_at_platform"),
        "tweets",
        ["created_at_platform"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tweets_in_reply_to_platform_tweet_id"),
        "tweets",
        ["in_reply_to_platform_tweet_id"],
        unique=False,
    )
    op.create_index(op.f("ix_tweets_platform_tweet_id"), "tweets", ["platform_tweet_id"], unique=False)
    op.create_index(
        op.f("ix_tweets_quoted_platform_tweet_id"),
        "tweets",
        ["quoted_platform_tweet_id"],
        unique=False,
    )

    op.create_table(
        "tweet_references",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tweet_id", sa.Integer(), nullable=False),
        sa.Column("referenced_tweet_platform_id", sa.String(length=32), nullable=False),
        sa.Column("reference_type", sa.String(length=32), nullable=False),
        sa.Column("referenced_user_platform_id", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["tweet_id"],
            ["tweets.id"],
            name=op.f("fk_tweet_references_tweet_id_tweets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tweet_references")),
    )
    op.create_index(op.f("ix_tweet_references_reference_type"), "tweet_references", ["reference_type"], unique=False)
    op.create_index(
        op.f("ix_tweet_references_referenced_tweet_platform_id"),
        "tweet_references",
        ["referenced_tweet_platform_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tweet_references_referenced_user_platform_id"),
        "tweet_references",
        ["referenced_user_platform_id"],
        unique=False,
    )
    op.create_index(op.f("ix_tweet_references_tweet_id"), "tweet_references", ["tweet_id"], unique=False)

    op.create_table(
        "raw_ingestion_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingestion_run_id", sa.Integer(), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("record_count_estimate", sa.Integer(), nullable=True),
        sa.Column("source_path", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_raw_ingestion_artifacts_ingestion_run_id_ingestion_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_ingestion_artifacts")),
    )
    op.create_index(
        op.f("ix_raw_ingestion_artifacts_ingestion_run_id"),
        "raw_ingestion_artifacts",
        ["ingestion_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_raw_ingestion_artifacts_ingestion_run_id"), table_name="raw_ingestion_artifacts")
    op.drop_table("raw_ingestion_artifacts")

    op.drop_index(op.f("ix_tweet_references_tweet_id"), table_name="tweet_references")
    op.drop_index(
        op.f("ix_tweet_references_referenced_user_platform_id"),
        table_name="tweet_references",
    )
    op.drop_index(
        op.f("ix_tweet_references_referenced_tweet_platform_id"),
        table_name="tweet_references",
    )
    op.drop_index(op.f("ix_tweet_references_reference_type"), table_name="tweet_references")
    op.drop_table("tweet_references")

    op.drop_index(op.f("ix_tweets_quoted_platform_tweet_id"), table_name="tweets")
    op.drop_index(op.f("ix_tweets_platform_tweet_id"), table_name="tweets")
    op.drop_index(op.f("ix_tweets_in_reply_to_platform_tweet_id"), table_name="tweets")
    op.drop_index(op.f("ix_tweets_created_at_platform"), table_name="tweets")
    op.drop_index(op.f("ix_tweets_conversation_id_platform"), table_name="tweets")
    op.drop_index(op.f("ix_tweets_author_user_id"), table_name="tweets")
    op.drop_table("tweets")

    op.drop_index(
        op.f("ix_ingestion_runs_target_user_platform_id"),
        table_name="ingestion_runs",
    )
    op.drop_index(op.f("ix_ingestion_runs_target_user_id"), table_name="ingestion_runs")
    op.drop_table("ingestion_runs")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_platform_user_id"), table_name="users")
    op.drop_table("users")
