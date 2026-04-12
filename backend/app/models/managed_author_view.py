from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ManagedAuthorView(TimestampMixin, Base):
    __tablename__ = "managed_author_views"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, index=True)

    enable_overview: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_moods: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_heatmap: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_bitcoin_mentions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    overview_analysis_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mood_analysis_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heatmap_analysis_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="managed_author_view")
