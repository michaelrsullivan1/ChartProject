from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PodcastAppearance(TimestampMixin, Base):
    __tablename__ = "podcast_appearances"
    __table_args__ = (
        UniqueConstraint(
            "podcast_person_id",
            "podcast_episode_id",
            name="uq_podcast_appearances_podcast_person_id_podcast_episode_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
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
    source_person_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_episode_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    person: Mapped["PodcastPerson"] = relationship(back_populates="appearances")
    episode: Mapped["PodcastEpisode"] = relationship(back_populates="appearances")
