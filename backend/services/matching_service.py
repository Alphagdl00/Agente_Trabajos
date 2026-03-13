from __future__ import annotations

from backend.schemas.job import CanonicalJob, MatchBreakdown


WEIGHTS = {
    "keywords": 45,
    "seniority": 20,
    "geography": 15,
    "work_mode": 10,
    "company": 10,
}


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _keyword_component(job: CanonicalJob, profile: dict) -> tuple[float, str]:
    keywords = [_clean_text(item).lower() for item in profile.get("keywords", []) if _clean_text(item)]
    if not keywords:
        return 0.0, "sin keywords configuradas"
    blob = f"{job.title} {job.description_snippet}".lower()
    matches = [keyword for keyword in keywords if keyword in blob]
    if not matches:
        return 0.0, "sin match de keywords"
    score = min(1.0, len(matches) / max(1, min(len(keywords), 4)))
    return score, f"match de keywords: {', '.join(matches[:3])}"


def _seniority_component(job: CanonicalJob, profile: dict) -> tuple[float, str]:
    target = _clean_text(profile.get("seniority_target", "")).lower()
    current = _clean_text(job.seniority_level).lower()
    if not target or not current:
        return 0.0, "sin evidencia de seniority"
    if target == current:
        return 1.0, "seniority alineado"
    adjacent = {("ejecutivo", "senior"), ("senior", "intermedio"), ("intermedio", "principiante")}
    if (target, current) in adjacent or (current, target) in adjacent:
        return 0.5, "seniority cercano"
    return 0.0, "seniority distante"


def _geography_component(job: CanonicalJob, profile: dict) -> tuple[float, str]:
    countries = {_clean_text(item).lower() for item in profile.get("preferred_countries", []) if _clean_text(item)}
    regions = {_clean_text(item).lower() for item in profile.get("preferred_regions", []) if _clean_text(item)}
    if countries and _clean_text(job.country).lower() in countries:
        return 1.0, "país alineado"
    if regions and _clean_text(job.region).lower() in regions:
        return 0.8, "región alineada"
    if not countries and not regions:
        return 0.0, "sin preferencia geográfica"
    return 0.0, "geografía fuera de preferencia"


def _work_mode_component(job: CanonicalJob, profile: dict) -> tuple[float, str]:
    preferred = {_clean_text(item).lower() for item in profile.get("preferred_work_modes", []) if _clean_text(item)}
    if not preferred:
        return 0.0, "sin preferencia de modalidad"
    if _clean_text(job.work_mode).lower() in preferred:
        return 1.0, "modalidad alineada"
    return 0.0, "modalidad no preferida"


def _company_component(job: CanonicalJob, profile: dict) -> tuple[float, str]:
    preferred = {_clean_text(item).lower() for item in profile.get("preferred_companies", []) if _clean_text(item)}
    if not preferred:
        return 0.0, "sin empresa preferida"
    if _clean_text(job.company_name).lower() in preferred:
        return 1.0, "empresa preferida"
    return 0.0, "empresa no prioritaria"


def score_canonical_job(job: CanonicalJob, profile: dict) -> MatchBreakdown:
    keyword_factor, keyword_reason = _keyword_component(job, profile)
    seniority_factor, seniority_reason = _seniority_component(job, profile)
    geography_factor, geography_reason = _geography_component(job, profile)
    work_mode_factor, work_mode_reason = _work_mode_component(job, profile)
    company_factor, company_reason = _company_component(job, profile)

    keyword_score = WEIGHTS["keywords"] * keyword_factor
    seniority_score = WEIGHTS["seniority"] * seniority_factor
    geography_score = WEIGHTS["geography"] * geography_factor
    work_mode_score = WEIGHTS["work_mode"] * work_mode_factor
    company_score = WEIGHTS["company"] * company_factor
    total_score = keyword_score + seniority_score + geography_score + work_mode_score + company_score

    if total_score >= 75:
        score_band = "strong"
    elif total_score >= 45:
        score_band = "medium"
    else:
        score_band = "low"

    explanation = " | ".join([keyword_reason, seniority_reason, geography_reason, work_mode_reason, company_reason])

    return MatchBreakdown(
        total_score=round(total_score, 2),
        score_band=score_band,
        keyword_score=round(keyword_score, 2),
        seniority_score=round(seniority_score, 2),
        geography_score=round(geography_score, 2),
        work_mode_score=round(work_mode_score, 2),
        company_score=round(company_score, 2),
        explanation=explanation,
    )
