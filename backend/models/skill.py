from __future__ import annotations

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Skill(Base):
    __tablename__ = "skills_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobSkill(Base):
    __tablename__ = "job_skills_v2"
    __table_args__ = (UniqueConstraint("job_id", "skill_id", name="job_skills_v2_job_skill_uq"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs_v2.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills_v2.id", ondelete="CASCADE"), index=True)
    evidence_text: Mapped[str] = mapped_column(String(500), default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    job = relationship("Job", back_populates="skills")
    skill = relationship("Skill")


class UserSkill(Base):
    __tablename__ = "user_skills_v2"
    __table_args__ = (UniqueConstraint("user_profile_id", "skill_id", name="user_skills_v2_profile_skill_uq"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles_v2.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills_v2.id", ondelete="CASCADE"), index=True)
    years_experience: Mapped[float] = mapped_column(Float, default=0)
    evidence_text: Mapped[str] = mapped_column(String(500), default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    user_profile = relationship("UserProfile", back_populates="skills")
    skill = relationship("Skill")
