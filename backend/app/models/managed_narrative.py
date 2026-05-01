from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ManagedNarrative(TimestampMixin, Base):
    __tablename__ = "managed_narratives"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phrase: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    tweet_matches: Mapped[list["TweetNarrativeMatch"]] = relationship(
        back_populates="managed_narrative"
    )
