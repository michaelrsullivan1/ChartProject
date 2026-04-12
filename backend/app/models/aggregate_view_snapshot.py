from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class AggregateViewSnapshot(TimestampMixin, Base):
    __tablename__ = "aggregate_view_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "view_type",
            "cohort_tag_slug",
            "granularity",
            "model_key",
            "cache_version",
            name="uq_aggregate_view_snapshots_lookup",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    view_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cohort_tag_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    granularity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    model_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cache_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_signature: Mapped[str | None] = mapped_column(String(255))
    build_meta_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)
