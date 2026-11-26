from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Brand(Base):
    __tablename__ = "brands"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    charts: Mapped[list["SizeChart"]] = relationship(back_populates="brand", lazy="selectin")


class SizeChart(Base):
    """One brand's size chart for a (category, gender) pair. `entries` is a list of
    {label, chest:[min,max], waist:[min,max]?, hip:[min,max]?, shoulder:[min,max]?} in cm
    of *body* measurements (the way most Indian brands publish them)."""

    __tablename__ = "size_charts"
    __table_args__ = (UniqueConstraint("brand_id", "category", "gender", name="uq_chart"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    category: Mapped[str] = mapped_column(String(40))
    gender: Mapped[str] = mapped_column(String(10))
    fit_type: Mapped[str] = mapped_column(String(20), default="regular")
    entries: Mapped[list] = mapped_column(JSON)
    brand: Mapped[Brand] = relationship(back_populates="charts")


class Feedback(Base):
    """Purchase outcomes - the training data for the future ML fit model."""

    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    user_ref: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    brand_slug: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(40))
    size_purchased: Mapped[str] = mapped_column(String(10))
    size_recommended: Mapped[str | None] = mapped_column(String(10), nullable=True)
    kept: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    measurements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
