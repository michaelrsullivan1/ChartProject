from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class CohortTag(TimestampMixin, Base):
    __tablename__ = "cohort_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)

    user_links: Mapped[list["UserCohortTag"]] = relationship(back_populates="cohort_tag")
