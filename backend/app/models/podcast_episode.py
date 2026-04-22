from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PodcastEpisode(TimestampMixin, Base):
    __tablename__ = "podcast_episodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_episode_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    episode_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    podcast_show_id: Mapped[int] = mapped_column(
        ForeignKey("podcast_shows.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    audio_url: Mapped[str | None] = mapped_column(String(1024))
    manifest_status: Mapped[str | None] = mapped_column(String(64))
    manifest_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manifest_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_manifest_path: Mapped[str | None] = mapped_column(String(1024))

    show: Mapped["PodcastShow"] = relationship(back_populates="episodes")
    appearances: Mapped[list["PodcastAppearance"]] = relationship(back_populates="episode")
    beliefs: Mapped[list["PodcastBelief"]] = relationship(back_populates="episode")
