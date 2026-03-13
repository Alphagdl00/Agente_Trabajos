from __future__ import annotations

from backend.models.skill import JobSkill, Skill, UserSkill


def _normalize_skill_name(name: str) -> str:
    return " ".join(str(name).split()).strip().lower()


def upsert_skill(session, name: str, *, category: str = "") -> Skill:
    normalized_name = _normalize_skill_name(name)
    skill = session.query(Skill).filter(Skill.normalized_name == normalized_name).one_or_none()
    if skill is None:
        skill = Skill(name=" ".join(str(name).split()).strip(), normalized_name=normalized_name, category=category)
        session.add(skill)
        session.flush()
        return skill

    if category and not skill.category:
        skill.category = category
        session.flush()
    return skill


def sync_job_skills(session, job_id: int, skills: list[dict]) -> None:
    session.query(JobSkill).filter(JobSkill.job_id == job_id).delete()
    for item in skills:
        name = item.get("name", "")
        if not _normalize_skill_name(name):
            continue
        skill = upsert_skill(session, name, category=item.get("category", ""))
        session.add(
            JobSkill(
                job_id=job_id,
                skill_id=skill.id,
                evidence_text=str(item.get("evidence_text", "")).strip(),
                confidence=float(item.get("confidence", 1.0) or 1.0),
            )
        )
    session.flush()


def sync_user_skills(session, user_profile_id: int, skills: list[dict]) -> None:
    session.query(UserSkill).filter(UserSkill.user_profile_id == user_profile_id).delete()
    for item in skills:
        name = item.get("name", "")
        if not _normalize_skill_name(name):
            continue
        skill = upsert_skill(session, name, category=item.get("category", ""))
        session.add(
            UserSkill(
                user_profile_id=user_profile_id,
                skill_id=skill.id,
                years_experience=float(item.get("years_experience", 0) or 0),
                evidence_text=str(item.get("evidence_text", "")).strip(),
                confidence=float(item.get("confidence", 1.0) or 1.0),
            )
        )
    session.flush()
