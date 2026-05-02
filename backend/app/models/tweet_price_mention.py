from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TweetPriceMention(TimestampMixin, Base):
    __tablename__ = "tweet_price_mentions"
    __table_args__ = (
        UniqueConstraint(
            "tweet_id",
            "price_usd",
            "extractor_key",
            "extractor_version",
            name="uq_tweet_price_mentions_dedup",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweets.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    price_usd: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, index=True)
    mention_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unclassified"
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    raw_fragment: Mapped[str] = mapped_column(Text, nullable=False)
    extractor_key: Mapped[str] = mapped_column(
        String(64), nullable=False, default="price-mention-regex"
    )
    extractor_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="v1"
    )
