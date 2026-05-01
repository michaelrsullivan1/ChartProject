from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PodcastShow(TimestampMixin, Base):
    __tablename__ = "podcast_shows"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    episodes: Mapped[list["PodcastEpisode"]] = relationship(back_populates="show")
    beliefs: Mapped[list["PodcastBelief"]] = relationship(back_populates="show")
