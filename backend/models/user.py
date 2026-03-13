from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class User(Base):
    __tablename__ = "users_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    locale: Mapped[str] = mapped_column(String(16), default="es-MX")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profiles = relationship("UserProfile", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users_v2.id", ondelete="CASCADE"), index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="Default")
    target_role: Mapped[str] = mapped_column(String(255), default="")
    practice_area: Mapped[str] = mapped_column(String(120), default="")
    seniority_target: Mapped[str] = mapped_column(String(80), default="")
    preferred_regions: Mapped[str] = mapped_column(Text, default="")
    preferred_countries: Mapped[str] = mapped_column(Text, default="")
    preferred_work_modes: Mapped[str] = mapped_column(Text, default="")
    preferred_companies: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profiles")
    skills = relationship("UserSkill", back_populates="user_profile", cascade="all, delete-orphan")
    matches = relationship("JobMatch", back_populates="user_profile", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user_profile")


class Alert(Base):
    __tablename__ = "alerts_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users_v2.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(40), default="email")
    minimum_score: Mapped[int] = mapped_column(Integer, default=70)
    cadence: Mapped[str] = mapped_column(String(40), default="daily")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="alerts")


class Event(Base):
    __tablename__ = "events_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users_v2.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(120), default="")
    entity_id: Mapped[str] = mapped_column(String(120), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="events")
