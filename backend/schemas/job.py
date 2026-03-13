from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CanonicalJob:
    canonical_key: str
    company_name: str
    title: str
    source_url: str
    apply_url: str
    ats: str = ""
    location_text: str = ""
    country: str = ""
    region: str = ""
    work_mode: str = ""
    department: str = ""
    seniority_level: str = ""
    employment_type: str = ""
    posted_date_raw: str = ""
    description_raw: str = ""
    description_snippet: str = ""
    priority: str = ""
    global_signal: bool = False
    source_job_id: str = ""
    skill_evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MatchBreakdown:
    total_score: float
    score_band: str
    keyword_score: float
    seniority_score: float
    geography_score: float
    work_mode_score: float
    company_score: float
    explanation: str
