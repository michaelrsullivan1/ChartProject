from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Tweet(TimestampMixin, Base):
    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_tweet_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    url: Mapped[str | None] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(255))
    created_at_platform: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    language: Mapped[str | None] = mapped_column(String(16))
    conversation_id_platform: Mapped[str | None] = mapped_column(String(32), index=True)
    in_reply_to_platform_tweet_id: Mapped[str | None] = mapped_column(String(32), index=True)
    quoted_platform_tweet_id: Mapped[str | None] = mapped_column(String(32), index=True)
    like_count: Mapped[int | None] = mapped_column(Integer)
    reply_count: Mapped[int | None] = mapped_column(Integer)
    repost_count: Mapped[int | None] = mapped_column(Integer)
    quote_count: Mapped[int | None] = mapped_column(Integer)
    bookmark_count: Mapped[int | None] = mapped_column(Integer)
    impression_count: Mapped[int | None] = mapped_column(Integer)

    author: Mapped["User"] = relationship(back_populates="tweets")
    references: Mapped[list["TweetReference"]] = relationship(back_populates="tweet")
    sentiment_scores: Mapped[list["TweetSentimentScore"]] = relationship(back_populates="tweet")
    mood_scores: Mapped[list["TweetMoodScore"]] = relationship(back_populates="tweet")
    keywords: Mapped[list["TweetKeyword"]] = relationship(back_populates="tweet")
