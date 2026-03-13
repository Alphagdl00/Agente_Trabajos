from __future__ import annotations

import json

from backend.models.company import Company
from backend.models.job import IngestionRun, Job, JobMatch
from backend.models.skill import JobSkill, UserSkill
from backend.models.user import UserProfile
from backend.services.application_intelligence_service import build_skill_gap_summary


def _json_list(raw_value: str) -> list[str]:
    try:
        loaded = json.loads(raw_value or "[]")
        return loaded if isinstance(loaded, list) else []
    except Exception:
        return []


def list_phase1_jobs(session, *, limit: int | None = 50) -> list[dict]:
    query = (
        session.query(Job, Company)
        .outerjoin(Company, Company.id == Job.company_id)
        .order_by(Job.last_seen_at.desc(), Job.id.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    rows = query.all()

    items: list[dict] = []
    for job, company in rows:
        items.append(
            {
                "job_id": job.id,
                "company": company.name if company else "",
                "title": job.title,
                "location": job.location_text,
                "country": job.country,
                "region": job.region,
                "work_mode": job.work_mode,
                "seniority_level": job.seniority_level,
                "priority": job.priority,
                "ats": job.ats,
                "url": job.apply_url,
                "canonical_key": job.canonical_key,
                "last_seen_at": job.last_seen_at,
            }
        )
    return items


def list_phase1_matches(session, *, limit: int | None = 50) -> list[dict]:
    query = (
        session.query(JobMatch, Job, UserProfile, Company)
        .join(Job, Job.id == JobMatch.job_id)
        .join(UserProfile, UserProfile.id == JobMatch.user_profile_id)
        .outerjoin(Company, Company.id == Job.company_id)
        .order_by(JobMatch.created_at.desc(), JobMatch.total_score.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    rows = query.all()

    items: list[dict] = []
    for match, job, profile, company in rows:
        profile_skill_names = [
            item.skill.name
            for item in session.query(UserSkill)
            .filter(UserSkill.user_profile_id == profile.id)
            .all()
            if item.skill and item.skill.name
        ]
        job_skill_names = [
            item.skill.name
            for item in session.query(JobSkill)
            .filter(JobSkill.job_id == job.id)
            .all()
            if item.skill and item.skill.name
        ]
        gap_summary = build_skill_gap_summary(profile_skill_names, job_skill_names)
        items.append(
            {
                "match_id": match.id,
                "job_id": job.id,
                "profile_id": profile.id,
                "profile_name": profile.display_name,
                "practice_area": profile.practice_area,
                "preferred_regions": _json_list(profile.preferred_regions),
                "preferred_countries": _json_list(profile.preferred_countries),
                "company": company.name if company else "",
                "title": job.title,
                "country": job.country,
                "region": job.region,
                "work_mode": job.work_mode,
                "total_score": match.total_score,
                "score_band": match.score_band,
                "keyword_score": match.keyword_score,
                "seniority_score": match.seniority_score,
                "geography_score": match.geography_score,
                "work_mode_score": match.work_mode_score,
                "company_score": match.company_score,
                "explanation": match.explanation,
                "profile_skills": profile_skill_names,
                "job_skills": job_skill_names,
                "matched_skills": gap_summary["matched_skills"],
                "missing_skills": gap_summary["missing_skills"],
                "skill_coverage_ratio": gap_summary["coverage_ratio"],
                "url": job.apply_url,
                "created_at": match.created_at,
            }
        )
    return items


def latest_phase1_run(session) -> dict | None:
    run = session.query(IngestionRun).order_by(IngestionRun.created_at.desc(), IngestionRun.id.desc()).first()
    if run is None:
        return None
    return {
        "run_id": run.id,
        "run_type": run.run_type,
        "profile_name": run.profile_name,
        "status": run.status,
        "persisted_companies": run.persisted_companies,
        "persisted_jobs": run.persisted_jobs,
        "persisted_job_skills": run.persisted_job_skills,
        "persisted_user_skills": run.persisted_user_skills,
        "recalculated_matches": run.recalculated_matches,
        "notes": run.notes,
        "created_at": run.created_at,
    }
