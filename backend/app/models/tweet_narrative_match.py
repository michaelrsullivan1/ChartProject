from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TweetNarrativeMatch(TimestampMixin, Base):
    __tablename__ = "tweet_narrative_matches"
    __table_args__ = (
        UniqueConstraint(
            "tweet_id",
            "managed_narrative_id",
            name="uq_tweet_narrative_matches_tweet_id_managed_narrative_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweets.id"), nullable=False, index=True)
    managed_narrative_id: Mapped[int] = mapped_column(
        ForeignKey("managed_narratives.id"),
        nullable=False,
        index=True,
    )
    matched_phrase: Mapped[str] = mapped_column(String(255), nullable=False)

    tweet: Mapped["Tweet"] = relationship(back_populates="narrative_matches")
    managed_narrative: Mapped["ManagedNarrative"] = relationship(back_populates="tweet_matches")
