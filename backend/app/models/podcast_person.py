from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PodcastPerson(TimestampMixin, Base):
    __tablename__ = "podcast_persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_person_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio_summary: Mapped[str | None] = mapped_column(Text)
    has_wiki: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    wiki_url: Mapped[str | None] = mapped_column(String(1024))
    total_beliefs_source: Mapped[int | None] = mapped_column(Integer)
    trust_badge: Mapped[str | None] = mapped_column(String(32))
    trust_score: Mapped[float | None] = mapped_column(Float)
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trust_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    appearances: Mapped[list["PodcastAppearance"]] = relationship(back_populates="person")
    beliefs: Mapped[list["PodcastBelief"]] = relationship(back_populates="person")
