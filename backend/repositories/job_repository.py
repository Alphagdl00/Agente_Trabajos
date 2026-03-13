from __future__ import annotations

from backend.models.job import Job, JobMatch
from backend.schemas.job import CanonicalJob, MatchBreakdown


def upsert_job(session, company_id: int | None, job: CanonicalJob) -> Job:
    record = session.query(Job).filter(Job.canonical_key == job.canonical_key).one_or_none()
    payload = {
        "company_id": company_id,
        "source_job_id": job.source_job_id,
        "source_url": job.source_url,
        "apply_url": job.apply_url,
        "ats": job.ats,
        "title": job.title,
        "normalized_title": job.title.lower(),
        "location_text": job.location_text,
        "country": job.country,
        "region": job.region,
        "work_mode": job.work_mode,
        "department": job.department,
        "seniority_level": job.seniority_level,
        "employment_type": job.employment_type,
        "posted_date_raw": job.posted_date_raw,
        "description_raw": job.description_raw,
        "description_snippet": job.description_snippet,
        "priority": job.priority,
        "global_signal": job.global_signal,
        "is_active": True,
    }
    if record is None:
        record = Job(canonical_key=job.canonical_key, **payload)
        session.add(record)
        session.flush()
        return record

    for key, value in payload.items():
        setattr(record, key, value)
    session.flush()
    return record


def upsert_match(session, job_id: int, user_profile_id: int, breakdown: MatchBreakdown) -> JobMatch:
    match = session.query(JobMatch).filter(
        JobMatch.job_id == job_id,
        JobMatch.user_profile_id == user_profile_id,
    ).one_or_none()
    payload = {
        "total_score": breakdown.total_score,
        "score_band": breakdown.score_band,
        "keyword_score": breakdown.keyword_score,
        "seniority_score": breakdown.seniority_score,
        "geography_score": breakdown.geography_score,
        "work_mode_score": breakdown.work_mode_score,
        "company_score": breakdown.company_score,
        "explanation": breakdown.explanation,
    }
    if match is None:
        match = JobMatch(job_id=job_id, user_profile_id=user_profile_id, **payload)
        session.add(match)
        session.flush()
        return match

    for key, value in payload.items():
        setattr(match, key, value)
    session.flush()
    return match
