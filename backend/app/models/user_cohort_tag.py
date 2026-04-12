from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class UserCohortTag(TimestampMixin, Base):
    __tablename__ = "user_cohort_tags"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "cohort_tag_id",
            name="uq_user_cohort_tags_user_id_cohort_tag_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    cohort_tag_id: Mapped[int] = mapped_column(ForeignKey("cohort_tags.id"), index=True)

    user: Mapped["User"] = relationship(back_populates="cohort_tag_links")
    cohort_tag: Mapped["CohortTag"] = relationship(back_populates="user_links")
