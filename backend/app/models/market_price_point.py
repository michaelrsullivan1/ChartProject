from datetime import datetime

from sqlalchemy import DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class MarketPricePoint(TimestampMixin, Base):
    __tablename__ = "market_price_points"
    __table_args__ = (
        UniqueConstraint(
            "asset_symbol",
            "quote_currency",
            "interval",
            "observed_at",
            name="uq_market_price_points_asset_quote_interval_observed_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False, default="fred")
    asset_symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    quote_currency: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    interval: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    market_cap: Mapped[float | None] = mapped_column(Float)
    total_volume: Mapped[float | None] = mapped_column(Float)
