from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TweetMoodScore(TimestampMixin, Base):
    __tablename__ = "tweet_mood_scores"
    __table_args__ = (
        UniqueConstraint(
            "tweet_id",
            "model_key",
            "mood_label",
            name="uq_tweet_mood_scores_tweet_id_model_key_label",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweets.id"), nullable=False, index=True)
    model_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mood_label: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    score: Mapped[float | None] = mapped_column(Float)
    skip_reason: Mapped[str | None] = mapped_column(String(64))
    is_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    input_char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tweet: Mapped["Tweet"] = relationship(back_populates="mood_scores")
