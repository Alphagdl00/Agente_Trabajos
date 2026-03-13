from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Application(Base):
    __tablename__ = "applications_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users_v2.id", ondelete="CASCADE"), index=True)
    user_profile_id: Mapped[int | None] = mapped_column(ForeignKey("user_profiles_v2.id", ondelete="SET NULL"), nullable=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs_v2.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(80), default="saved", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    applied_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="applications")
    user_profile = relationship("UserProfile", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    reminders = relationship("ApplicationReminder", back_populates="application", cascade="all, delete-orphan")


class ApplicationReminder(Base):
    __tablename__ = "application_reminders_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications_v2.id", ondelete="CASCADE"), index=True)
    reminder_type: Mapped[str] = mapped_column(String(80), default="follow_up")
    due_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="pending")
    notes: Mapped[str] = mapped_column(Text, default="")

    application = relationship("Application", back_populates="reminders")
