from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TweetReference(Base):
    __tablename__ = "tweet_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweets.id"), index=True)
    referenced_tweet_platform_id: Mapped[str] = mapped_column(String(32), index=True)
    reference_type: Mapped[str] = mapped_column(String(32), index=True)
    referenced_user_platform_id: Mapped[str | None] = mapped_column(String(32), index=True)

    tweet: Mapped["Tweet"] = relationship(back_populates="references")
