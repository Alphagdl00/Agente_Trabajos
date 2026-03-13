from __future__ import annotations

from datetime import datetime, timedelta

from backend.models.application import Application, ApplicationReminder
from backend.models.job import Job
from backend.models.user import User, UserProfile


def ensure_demo_profile(session) -> tuple[User, UserProfile]:
    email = "demo@northhound.local"
    user = session.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(email=email, full_name="North Hound Demo User")
        session.add(user)
        session.flush()

    profile = (
        session.query(UserProfile)
        .filter(UserProfile.user_id == user.id, UserProfile.display_name == "Default")
        .one_or_none()
    )
    if profile is None:
        profile = UserProfile(user_id=user.id, display_name="Default", is_default=True)
        session.add(profile)
        session.flush()
    return user, profile


def upsert_application(session, *, job_id: int, status: str, notes: str = "", reminder_days: int | None = None) -> Application:
    user, profile = ensure_demo_profile(session)
    application = (
        session.query(Application)
        .filter(Application.user_id == user.id, Application.job_id == job_id)
        .one_or_none()
    )

    if application is None:
        application = Application(
            user_id=user.id,
            user_profile_id=profile.id,
            job_id=job_id,
            status=status,
            notes=notes,
        )
        session.add(application)
        session.flush()
    else:
        application.status = status
        application.notes = notes
        application.last_updated_at = datetime.utcnow()

    if status in {"applied", "interview"} and application.applied_at is None:
        application.applied_at = datetime.utcnow()

    if reminder_days is not None and reminder_days >= 0:
        due_at = datetime.utcnow() + timedelta(days=reminder_days)
        reminder = (
            session.query(ApplicationReminder)
            .filter(ApplicationReminder.application_id == application.id, ApplicationReminder.status == "pending")
            .order_by(ApplicationReminder.due_at.asc(), ApplicationReminder.id.asc())
            .first()
        )
        if reminder is None:
            reminder = ApplicationReminder(
                application_id=application.id,
                reminder_type="follow_up",
                due_at=due_at,
                status="pending",
                notes="",
            )
            session.add(reminder)
        else:
            reminder.due_at = due_at
            reminder.status = "pending"
        session.flush()

    session.flush()
    return application


def list_applications(session, *, due_only: bool = False, limit: int = 20) -> list[dict]:
    query = (
        session.query(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .order_by(Application.last_updated_at.desc(), Application.id.desc())
    )
    rows = query.limit(limit).all()

    items: list[dict] = []
    now = datetime.utcnow()
    for application, job in rows:
        pending_reminder = (
            session.query(ApplicationReminder)
            .filter(ApplicationReminder.application_id == application.id, ApplicationReminder.status == "pending")
            .order_by(ApplicationReminder.due_at.asc(), ApplicationReminder.id.asc())
            .first()
        )
        if due_only and (pending_reminder is None or pending_reminder.due_at > now):
            continue
        items.append(
            {
                "application_id": application.id,
                "job_id": job.id,
                "title": job.title,
                "company": job.company.name if job.company else "",
                "status": application.status,
                "notes": application.notes,
                "applied_at": application.applied_at,
                "last_updated_at": application.last_updated_at,
                "url": job.apply_url,
                "reminder_due_at": pending_reminder.due_at if pending_reminder else None,
                "reminder_status": pending_reminder.status if pending_reminder else "",
            }
        )
    return items
