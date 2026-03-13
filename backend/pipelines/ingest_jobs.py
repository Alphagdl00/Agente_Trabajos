from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from backend.core.db import get_session
from backend.repositories.company_repository import upsert_company
from backend.repositories.job_repository import upsert_job, upsert_match
from backend.services.job_normalization_service import normalize_job
from backend.services.matching_service import score_canonical_job
from main import collect_jobs_from_companies, load_companies


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


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


def run_ingestion_pipeline(profile: dict, companies_df: pd.DataFrame | None = None) -> dict:
    companies_df = companies_df if companies_df is not None else load_companies()
    raw_jobs = collect_jobs_from_companies(companies_df, use_parallel=True)
    deduped_jobs = _deduplicate_jobs(raw_jobs)

    persisted_companies = 0
    persisted_jobs = 0
    recalculated_matches = 0

    with get_session() as session:
        if session is None:
            return {
                "persisted_companies": 0,
                "persisted_jobs": 0,
                "recalculated_matches": 0,
                "jobs": [asdict(normalize_job(job)) for job in deduped_jobs],
            }

        company_ids: dict[str, int] = {}
        for _, row in companies_df.iterrows():
            company = upsert_company(session, _company_payload(row.to_dict()))
            company_ids[company.name.lower()] = company.id
            persisted_companies += 1

        for raw_job in deduped_jobs:
            canonical = normalize_job(raw_job)
            job_record = upsert_job(session, company_ids.get(canonical.company_name.lower()), canonical)
            persisted_jobs += 1

            user_profile_id = int(profile.get("user_profile_id", 1) or 1)
            breakdown = score_canonical_job(canonical, profile)
            upsert_match(session, job_record.id, user_profile_id, breakdown)
            recalculated_matches += 1

    return {
        "persisted_companies": persisted_companies,
        "persisted_jobs": persisted_jobs,
        "recalculated_matches": recalculated_matches,
    }
