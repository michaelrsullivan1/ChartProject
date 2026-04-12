from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False, default="twitterapi.io")
    endpoint_name: Mapped[str] = mapped_column(String(128), nullable=False)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    target_user_platform_id: Mapped[str | None] = mapped_column(String(32), index=True)
    import_type: Mapped[str] = mapped_column(String(32), nullable=False, default="backfill")
    requested_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="started")
    last_cursor: Mapped[str | None] = mapped_column(String(512))
    pages_fetched: Mapped[int] = mapped_column(nullable=False, default=0)
    raw_tweets_fetched: Mapped[int] = mapped_column(nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)

    target_user: Mapped["User | None"] = relationship(back_populates="ingestion_runs")
    artifacts: Mapped[list["RawIngestionArtifact"]] = relationship(back_populates="ingestion_run")
