from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Resume(Base):
    __tablename__ = "resumes_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users_v2.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255), default="")
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    parser_version: Mapped[str] = mapped_column(String(80), default="v1")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="resumes")
    evidence_items = relationship("ResumeEvidence", back_populates="resume", cascade="all, delete-orphan")


class ResumeEvidence(Base):
    __tablename__ = "resume_evidence_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes_v2.id", ondelete="CASCADE"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(120), default="")
    evidence_value: Mapped[str] = mapped_column(String(500), default="")
    evidence_text: Mapped[str] = mapped_column(Text, default="")

    resume = relationship("Resume", back_populates="evidence_items")
