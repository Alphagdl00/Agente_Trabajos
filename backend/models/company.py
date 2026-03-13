from __future__ import annotations

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Company(Base):
    __tablename__ = "companies_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    industry: Mapped[str] = mapped_column(String(255), default="")
    region: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    priority: Mapped[str] = mapped_column(String(8), default="")
    ats: Mapped[str] = mapped_column(String(80), default="")
    career_url: Mapped[str] = mapped_column(Text)
    international_hiring: Mapped[str] = mapped_column(String(60), default="")
    profile_fit: Mapped[str] = mapped_column(String(60), default="")
    salary_band: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    jobs = relationship("Job", back_populates="company")
