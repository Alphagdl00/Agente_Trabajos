from __future__ import annotations

from dataclasses import asdict
from typing import Callable

import pandas as pd

from backend.core.db import get_session
from backend.repositories.company_repository import upsert_company
from backend.repositories.job_repository import upsert_job, upsert_match
from backend.repositories.profile_repository import ensure_user_profile
from backend.repositories.run_repository import create_ingestion_run
from backend.repositories.skill_repository import sync_job_skills, sync_user_skills
from backend.services.job_normalization_service import normalize_job
from backend.services.matching_service import score_canonical_job
from backend.services.skill_extraction_service import extract_job_skills, extract_profile_skills
from main import collect_jobs_from_companies, load_companies


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def build_phase1_profile(source: dict | None = None) -> dict:
    source = source or {}
    seniority_levels = source.get("seniority_levels", []) or []
    seniority_target = seniority_levels[0] if isinstance(seniority_levels, list) and seniority_levels else _clean_text(source.get("seniority_target", ""))
    practices = source.get("practices", []) or []
    practice_area = practices[0] if isinstance(practices, list) and practices else _clean_text(source.get("practice_area", ""))
    return {
        "user_profile_id": int(source.get("user_profile_id", 1) or 1),
        "email": _clean_text(source.get("email", "demo@northhound.local")) or "demo@northhound.local",
        "full_name": _clean_text(source.get("full_name", "North Hound Demo User")) or "North Hound Demo User",
        "display_name": _clean_text(source.get("display_name", "Default")) or "Default",
        "practice_area": practice_area,
        "seniority_target": seniority_target,
        "preferred_regions": source.get("preferred_regions", []) or [],
        "preferred_countries": source.get("preferred_countries", []) or [],
        "preferred_work_modes": source.get("preferred_work_modes", []) or [],
        "preferred_companies": source.get("preferred_companies", []) or [],
        "keywords": source.get("keywords", []) or [],
        "skills": source.get("skills", []) or [],
        "years_experience": int(source.get("years_experience", 0) or 0),
    }


def _company_payload(row: dict) -> dict:
    company_name = _clean_text(row.get("company", ""))
    career_url = _clean_text(row.get("career_url", ""))
    return {
        "external_key": f"{company_name.lower()}|{career_url.lower()}",
        "name": company_name,
        "industry": _clean_text(row.get("industry", "")),
        "region": _clean_text(row.get("region", "")),
        "country": _clean_text(row.get("country", "")),
        "priority": _clean_text(row.get("priority", "")),
        "ats": _clean_text(row.get("ats", "")),
        "career_url": career_url,
        "international_hiring": _clean_text(row.get("international_hiring", "")),
        "profile_fit": _clean_text(row.get("profile_fit", "")),
        "salary_band": _clean_text(row.get("salary_band", "")),
        "is_active": True,
    }


def _deduplicate_jobs(raw_jobs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for raw_job in raw_jobs:
        canonical = normalize_job(raw_job)
        if not canonical.canonical_key or canonical.canonical_key in seen:
            continue
        seen.add(canonical.canonical_key)
        deduped.append(raw_job)
    return deduped


def run_ingestion_pipeline(
    profile: dict,
    companies_df: pd.DataFrame | None = None,
    *,
    company_limit: int | None = None,
    max_jobs: int | None = None,
    use_parallel: bool = True,
    run_type: str = "manual",
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    companies_df = companies_df if companies_df is not None else load_companies()

    if company_limit is not None and company_limit > 0:
        companies_df = companies_df.head(company_limit).copy()

    raw_jobs = collect_jobs_from_companies(
        companies_df,
        company_limit=None,
        use_parallel=use_parallel,
    )
    deduped_jobs = _deduplicate_jobs(raw_jobs)
    if max_jobs is not None and max_jobs > 0:
        deduped_jobs = deduped_jobs[:max_jobs]

    if progress_callback:
        progress_callback(
            {
                "stage": "scraped",
                "companies_selected": int(len(companies_df)),
                "raw_jobs": int(len(raw_jobs)),
                "deduped_jobs": int(len(deduped_jobs)),
            }
        )

    persisted_companies = 0
    persisted_jobs = 0
    recalculated_matches = 0

    with get_session() as session:
        if session is None:
            profile_preview = build_phase1_profile(profile)
            profile_preview["skills"] = extract_profile_skills(profile_preview)
            return {
                "persisted_companies": 0,
                "persisted_jobs": 0,
                "recalculated_matches": 0,
                "persisted_job_skills": 0,
                "persisted_user_skills": len(profile_preview["skills"]),
                "jobs": [asdict(normalize_job(job)) for job in deduped_jobs],
            }

        phase1_profile = build_phase1_profile(profile)
        profile_skills = extract_profile_skills(phase1_profile)
        phase1_profile["skills"] = profile_skills
        user_profile = ensure_user_profile(session, phase1_profile)
        sync_user_skills(session, user_profile.id, profile_skills)
        if progress_callback:
            progress_callback(
                {
                    "stage": "persisting_companies",
                    "companies_selected": int(len(companies_df)),
                    "deduped_jobs": int(len(deduped_jobs)),
                    "processed_jobs": 0,
                }
            )

        company_ids: dict[str, int] = {}
        for _, row in companies_df.iterrows():
            company = upsert_company(session, _company_payload(row.to_dict()))
            company_ids[company.name.lower()] = company.id
            persisted_companies += 1

        persisted_job_skills = 0
        for idx, raw_job in enumerate(deduped_jobs, start=1):
            canonical = normalize_job(raw_job)
            job_skills = extract_job_skills(canonical, [item["name"] for item in profile_skills] + (phase1_profile.get("keywords", []) or []))
            canonical.skill_evidence = [item["name"] for item in job_skills]
            job_record = upsert_job(session, company_ids.get(canonical.company_name.lower()), canonical)
            sync_job_skills(session, job_record.id, job_skills)
            persisted_job_skills += len(job_skills)
            persisted_jobs += 1

            breakdown = score_canonical_job(canonical, phase1_profile)
            upsert_match(session, job_record.id, user_profile.id, breakdown)
            recalculated_matches += 1
            if progress_callback and (idx == 1 or idx == len(deduped_jobs) or idx % 25 == 0):
                progress_callback(
                    {
                        "stage": "persisting_jobs_and_matches",
                        "companies_selected": int(len(companies_df)),
                        "deduped_jobs": int(len(deduped_jobs)),
                        "processed_jobs": idx,
                        "persisted_companies": persisted_companies,
                        "persisted_jobs": persisted_jobs,
                        "recalculated_matches": recalculated_matches,
                    }
                )

        if progress_callback:
            progress_callback(
                {
                    "stage": "finalizing_run",
                    "companies_selected": int(len(companies_df)),
                    "deduped_jobs": int(len(deduped_jobs)),
                    "processed_jobs": int(len(deduped_jobs)),
                    "persisted_companies": persisted_companies,
                    "persisted_jobs": persisted_jobs,
                    "recalculated_matches": recalculated_matches,
                }
            )
        run_record = create_ingestion_run(
            session,
            {
                "run_type": run_type,
                "profile_name": phase1_profile.get("display_name", "Default"),
                "status": "completed",
                "persisted_companies": persisted_companies,
                "persisted_jobs": persisted_jobs,
                "persisted_job_skills": persisted_job_skills,
                "persisted_user_skills": len(profile_skills),
                "recalculated_matches": recalculated_matches,
                "notes": phase1_profile.get("practice_area", ""),
            },
        )

    return {
        "run_id": run_record.id,
        "persisted_companies": persisted_companies,
        "persisted_jobs": persisted_jobs,
        "recalculated_matches": recalculated_matches,
        "persisted_job_skills": persisted_job_skills,
        "persisted_user_skills": len(profile_skills),
        "run_type": run_type,
        "company_limit": company_limit,
        "max_jobs": max_jobs,
    }
