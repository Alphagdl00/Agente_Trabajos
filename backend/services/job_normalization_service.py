from __future__ import annotations

from backend.schemas.job import CanonicalJob


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def build_canonical_key(company_name: str, title: str, apply_url: str, source_job_id: str = "") -> str:
    parts = [
        _clean_text(company_name).lower(),
        _clean_text(title).lower(),
        _clean_text(source_job_id).lower(),
        _clean_text(apply_url).lower(),
    ]
    return " | ".join(part for part in parts if part)


def normalize_job(raw_job: dict) -> CanonicalJob:
    company_name = _clean_text(raw_job.get("company", ""))
    title = _clean_text(raw_job.get("title", ""))
    apply_url = _clean_text(raw_job.get("url", ""))
    source_job_id = _clean_text(raw_job.get("job_id", "")) or _clean_text(raw_job.get("external_job_id", ""))
    description_raw = _clean_text(raw_job.get("description", "")) or _clean_text(raw_job.get("description_snippet", ""))
    description_snippet = _clean_text(raw_job.get("description_snippet", "")) or description_raw[:400]

    return CanonicalJob(
        canonical_key=build_canonical_key(company_name, title, apply_url, source_job_id),
        company_name=company_name,
        title=title,
        source_url=_clean_text(raw_job.get("source_url", "")),
        apply_url=apply_url,
        ats=_clean_text(raw_job.get("ats", "")),
        location_text=_clean_text(raw_job.get("location", "")),
        country=_clean_text(raw_job.get("country", "")),
        region=_clean_text(raw_job.get("region", "")),
        work_mode=_clean_text(raw_job.get("work_mode", "")),
        department=_clean_text(raw_job.get("department", "")),
        seniority_level=_clean_text(raw_job.get("seniority_level", "")),
        employment_type=_clean_text(raw_job.get("employment_type", "")),
        posted_date_raw=_clean_text(raw_job.get("posted_date", "")),
        description_raw=description_raw,
        description_snippet=description_snippet,
        priority=_clean_text(raw_job.get("priority", "")),
        global_signal=bool(raw_job.get("global_signal", False)),
        source_job_id=source_job_id,
        skill_evidence=[],
    )
