from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_user_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    profile_url: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    follower_count: Mapped[int | None] = mapped_column(Integer)
    following_count: Mapped[int | None] = mapped_column(Integer)
    favourites_count: Mapped[int | None] = mapped_column(Integer)
    media_count: Mapped[int | None] = mapped_column(Integer)
    statuses_count: Mapped[int | None] = mapped_column(Integer)
    created_at_platform: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blue_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(String(512))
    banner_image_url: Mapped[str | None] = mapped_column(String(512))
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_tweet_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tweets: Mapped[list["Tweet"]] = relationship(back_populates="author")
    ingestion_runs: Mapped[list["IngestionRun"]] = relationship(back_populates="target_user")
