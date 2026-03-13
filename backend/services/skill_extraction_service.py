from __future__ import annotations


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


DEFAULT_SKILL_CATALOG = {
    "finance": "domain",
    "fp&a": "domain",
    "financial planning": "domain",
    "strategic finance": "domain",
    "commercial finance": "domain",
    "corporate finance": "domain",
    "supply chain": "domain",
    "operations": "domain",
    "strategy": "domain",
    "compliance": "domain",
    "legal": "domain",
    "contracts": "domain",
    "talent acquisition": "domain",
    "hr": "domain",
    "human resources": "domain",
    "recruiting": "domain",
    "data": "domain",
    "analytics": "domain",
    "business intelligence": "domain",
    "sql": "tool",
    "python": "tool",
    "sap": "tool",
    "erp": "tool",
    "jde": "tool",
    "power bi": "tool",
    "tableau": "tool",
}


def extract_job_skills(job, seed_skills: list[str] | None = None) -> list[dict]:
    blob = " ".join(
        [
            _clean_text(getattr(job, "title", "")),
            _clean_text(getattr(job, "department", "")),
            _clean_text(getattr(job, "description_snippet", "")),
            _clean_text(getattr(job, "description_raw", "")),
        ]
    ).lower()

    catalog = dict(DEFAULT_SKILL_CATALOG)
    for item in seed_skills or []:
        cleaned = _clean_text(item).lower()
        if cleaned:
            catalog.setdefault(cleaned, "custom")

    found: list[dict] = []
    for term, category in catalog.items():
        if term and term in blob:
            found.append(
                {
                    "name": term,
                    "category": category,
                    "evidence_text": term,
                    "confidence": 1.0,
                }
            )

    unique: dict[str, dict] = {}
    for item in found:
        unique[item["name"]] = item
    return list(unique.values())


def extract_profile_skills(profile: dict) -> list[dict]:
    items: list[dict] = []
    seed_values = list(profile.get("keywords", []) or [])
    for skill in profile.get("skills", []) or []:
        if isinstance(skill, dict):
            seed_values.append(skill.get("name", ""))
            items.append(
                {
                    "name": _clean_text(skill.get("name", "")).lower(),
                    "category": DEFAULT_SKILL_CATALOG.get(_clean_text(skill.get("name", "")).lower(), skill.get("category", "custom")),
                    "years_experience": float(skill.get("years_experience", profile.get("years_experience", 0)) or 0),
                    "evidence_text": _clean_text(skill.get("evidence_text", skill.get("name", ""))),
                    "confidence": float(skill.get("confidence", 1.0) or 1.0),
                }
            )
        else:
            seed_values.append(skill)

    for keyword in seed_values:
        cleaned = _clean_text(keyword).lower()
        if not cleaned:
            continue
        items.append(
            {
                "name": cleaned,
                "category": DEFAULT_SKILL_CATALOG.get(cleaned, "custom"),
                "years_experience": float(profile.get("years_experience", 0) or 0),
                "evidence_text": cleaned,
                "confidence": 1.0,
            }
        )

    unique: dict[str, dict] = {}
    for item in items:
        unique[item["name"]] = item
    return list(unique.values())
