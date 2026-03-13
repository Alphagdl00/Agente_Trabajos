from __future__ import annotations

from backend.models.resume import Resume, ResumeEvidence
from backend.models.user import User


def ensure_user(session, *, email: str, full_name: str) -> User:
    normalized_email = (email or "demo@northhound.local").strip().lower() or "demo@northhound.local"
    user = session.query(User).filter(User.email == normalized_email).one_or_none()
    if user is None:
        user = User(email=normalized_email, full_name=(full_name or "North Hound Demo User").strip())
        session.add(user)
        session.flush()
        return user

    if full_name and not user.full_name:
        user.full_name = full_name.strip()
        session.flush()
    return user


def save_resume_parse(session, *, email: str, full_name: str, parsed_resume: dict) -> Resume:
    user = ensure_user(session, email=email, full_name=full_name)
    resume = (
        session.query(Resume)
        .filter(Resume.user_id == user.id, Resume.content_hash == parsed_resume["content_hash"])
        .one_or_none()
    )
    payload = {
        "file_name": parsed_resume.get("file_name", ""),
        "content_hash": parsed_resume.get("content_hash", ""),
        "extracted_text": parsed_resume.get("extracted_text", ""),
        "parser_version": "resume_v1",
    }
    if resume is None:
        resume = Resume(user_id=user.id, **payload)
        session.add(resume)
        session.flush()
    else:
        for key, value in payload.items():
            setattr(resume, key, value)
        session.flush()

    session.query(ResumeEvidence).filter(ResumeEvidence.resume_id == resume.id).delete()
    for item in parsed_resume.get("evidence_items", []):
        session.add(
            ResumeEvidence(
                resume_id=resume.id,
                evidence_type=str(item.get("evidence_type", "")).strip(),
                evidence_value=str(item.get("evidence_value", "")).strip(),
                evidence_text=str(item.get("evidence_text", "")).strip(),
            )
        )
    session.flush()
    return resume
