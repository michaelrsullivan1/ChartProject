from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PodcastBelief(TimestampMixin, Base):
    __tablename__ = "podcast_beliefs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_belief_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    podcast_person_id: Mapped[int] = mapped_column(
        ForeignKey("podcast_persons.id"),
        nullable=False,
        index=True,
    )
    podcast_episode_id: Mapped[int] = mapped_column(
        ForeignKey("podcast_episodes.id"),
        nullable=False,
        index=True,
    )
    podcast_show_id: Mapped[int] = mapped_column(
        ForeignKey("podcast_shows.id"),
        nullable=False,
        index=True,
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    atomic_belief: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(255), index=True)
    domain: Mapped[str | None] = mapped_column(String(255), index=True)
    worldview: Mapped[str | None] = mapped_column(Text)
    core_axiom: Mapped[str | None] = mapped_column(Text)
    weights_json: Mapped[list[Any] | None] = mapped_column(JSON)
    timestamp_start_seconds: Mapped[float | None] = mapped_column(Float)
    timestamp_end_seconds: Mapped[float | None] = mapped_column(Float)
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    person: Mapped["PodcastPerson"] = relationship(back_populates="beliefs")
    episode: Mapped["PodcastEpisode"] = relationship(back_populates="beliefs")
    show: Mapped["PodcastShow"] = relationship(back_populates="beliefs")
