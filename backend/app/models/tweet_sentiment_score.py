from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TweetSentimentScore(TimestampMixin, Base):
    __tablename__ = "tweet_sentiment_scores"
    __table_args__ = (
        UniqueConstraint(
            "tweet_id",
            "model_key",
            name="uq_tweet_sentiment_scores_tweet_id_model_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweets.id"), nullable=False, index=True)
    model_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(Float)
    negative_score: Mapped[float | None] = mapped_column(Float)
    neutral_score: Mapped[float | None] = mapped_column(Float)
    positive_score: Mapped[float | None] = mapped_column(Float)
    skip_reason: Mapped[str | None] = mapped_column(String(64))
    is_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    input_char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tweet: Mapped["Tweet"] = relationship(back_populates="sentiment_scores")
