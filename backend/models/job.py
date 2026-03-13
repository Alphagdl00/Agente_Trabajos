from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Job(Base):
    __tablename__ = "jobs_v2"
    __table_args__ = (UniqueConstraint("canonical_key", name="jobs_v2_canonical_key_uq"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    canonical_key: Mapped[str] = mapped_column(String(500), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies_v2.id", ondelete="SET NULL"))
    source_job_id: Mapped[str] = mapped_column(String(255), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    apply_url: Mapped[str] = mapped_column(Text, default="")
    ats: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(500), index=True)
    normalized_title: Mapped[str] = mapped_column(String(500), default="", index=True)
    location_text: Mapped[str] = mapped_column(String(500), default="")
    country: Mapped[str] = mapped_column(String(120), default="", index=True)
    region: Mapped[str] = mapped_column(String(120), default="", index=True)
    work_mode: Mapped[str] = mapped_column(String(40), default="")
    department: Mapped[str] = mapped_column(String(255), default="")
    seniority_level: Mapped[str] = mapped_column(String(80), default="", index=True)
    employment_type: Mapped[str] = mapped_column(String(80), default="")
    posted_date_raw: Mapped[str] = mapped_column(String(120), default="")
    posted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description_raw: Mapped[str] = mapped_column(Text, default="")
    description_snippet: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(8), default="")
    global_signal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="jobs")
    skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class JobMatch(Base):
    __tablename__ = "job_matches_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs_v2.id", ondelete="CASCADE"), index=True)
    user_profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles_v2.id", ondelete="CASCADE"), index=True)
    total_score: Mapped[float] = mapped_column(Float, default=0)
    score_band: Mapped[str] = mapped_column(String(40), default="low")
    keyword_score: Mapped[float] = mapped_column(Float, default=0)
    seniority_score: Mapped[float] = mapped_column(Float, default=0)
    geography_score: Mapped[float] = mapped_column(Float, default=0)
    work_mode_score: Mapped[float] = mapped_column(Float, default=0)
    company_score: Mapped[float] = mapped_column(Float, default=0)
    explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="matches")
    user_profile = relationship("UserProfile", back_populates="matches")
