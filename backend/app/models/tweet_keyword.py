from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TweetKeyword(TimestampMixin, Base):
    __tablename__ = "tweet_keywords"
    __table_args__ = (
        UniqueConstraint(
            "tweet_id",
            "normalized_keyword",
            "extractor_key",
            "extractor_version",
            name="uq_tweet_keywords_tweet_keyword_extractor",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweets.id"), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    keyword_length: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    keyword_type: Mapped[str] = mapped_column(String(32), nullable=False, default="exact_ngram")
    extractor_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    extractor_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    tweet: Mapped["Tweet"] = relationship(back_populates="keywords")
