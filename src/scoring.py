from __future__ import annotations

from typing import Iterable


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def keyword_match_details(title: str, description: str, keywords: Iterable[str]) -> list[str]:
    blob = f"{clean_text(title)} {clean_text(description)}".lower()
    matches: list[str] = []

    for keyword in keywords:
        normalized = clean_text(keyword).lower()
        if normalized and normalized in blob:
            matches.append(normalized)

    return matches


def seniority_score(title: str) -> tuple[int, list[str]]:
    normalized = clean_text(title).lower()
    reasons: list[str] = []
    score = 0

    if any(term in normalized for term in ["vp", "vice president", "head of", "director", "sr director", "senior director"]):
        score += 3
        reasons.append("seniority alta")
    elif any(term in normalized for term in ["manager", "lead", "principal", "program manager", "senior manager"]):
        score += 2
        reasons.append("seniority media-alta")

    return score, reasons


def priority_score(priority: str) -> tuple[int, list[str]]:
    normalized = clean_text(priority).upper()
    if normalized == "A":
        return 2, ["empresa prioridad A"]
    if normalized == "B":
        return 1, ["empresa prioridad B"]
    return 0, []


def global_signal_score(global_signal: bool) -> tuple[int, list[str]]:
    if global_signal:
        return 2, ["señal internacional/remota"]
    return 0, []


def keyword_score(matches: list[str]) -> tuple[int, list[str]]:
    if not matches:
        return 0, []

    unique_matches = list(dict.fromkeys(matches))
    if len(unique_matches) >= 3:
        return 6, [f"match fuerte de keywords: {', '.join(unique_matches[:3])}"]
    return 5, [f"match de keywords: {', '.join(unique_matches[:2])}"]


def recency_score(posted_date: str, title: str, description: str) -> tuple[int, list[str]]:
    blob = f"{clean_text(posted_date)} {clean_text(title)} {clean_text(description)}".lower()

    if any(token in blob for token in ["today", "just posted", "posted today"]):
        return 4, ["publicada hoy"]
    if any(token in blob for token in ["yesterday", "1 day ago", "2 days ago", "3 days ago", "new"]):
        return 3, ["publicación reciente"]

    return 0, []


def detect_seniority_band(title: str) -> str:
    normalized = clean_text(title).lower()
    if any(token in normalized for token in ["vp", "vice president", "head of", "director", "senior director", "sr director"]):
        return "executive"
    if any(token in normalized for token in ["manager", "lead", "principal", "senior manager"]):
        return "manager"
    if any(token in normalized for token in ["senior", "sr ", "specialist", "staff"]):
        return "senior_individual"
    if normalized:
        return "individual"
    return ""


def extract_geo_preferences(location: str) -> set[str]:
    normalized = clean_text(location).lower()
    if not normalized:
        return set()

    tokens: set[str] = set()
    if any(term in normalized for term in ["mexico", "cdmx", "guadalajara", "monterrey"]):
        tokens.add("mexico")
    if any(term in normalized for term in ["latam", "latin america", "mexico", "brazil", "colombia", "argentina", "chile"]):
        tokens.add("latam")
    if any(term in normalized for term in ["united states", "usa", "us ", "new york", "california", "texas"]):
        tokens.add("us")
    if any(term in normalized for term in ["europe", "spain", "germany", "netherlands", "switzerland", "france", "ireland", "uk", "united kingdom"]):
        tokens.add("europe")
    if "remote" in normalized or "anywhere" in normalized:
        tokens.add("remote_geo")
    return tokens


def feedback_score(job: dict, feedback_profile: dict | None) -> tuple[int, list[str]]:
    if not feedback_profile:
        return 0, []

    title = clean_text(job.get("title", "")).lower()
    company = clean_text(job.get("company", "")).lower()
    work_mode = clean_text(job.get("work_mode", "")).lower()
    location = clean_text(job.get("location", "")).lower()
    seniority = detect_seniority_band(title)
    geo_tokens = extract_geo_preferences(location)
    reasons: list[str] = []
    score = 0

    positive_titles = feedback_profile.get("positive_titles", set())
    negative_titles = feedback_profile.get("negative_titles", set())
    positive_companies = feedback_profile.get("positive_companies", set())
    negative_companies = feedback_profile.get("negative_companies", set())
    positive_work_modes = feedback_profile.get("positive_work_modes", set())
    negative_work_modes = feedback_profile.get("negative_work_modes", set())
    positive_geos = feedback_profile.get("positive_geos", set())
    negative_geos = feedback_profile.get("negative_geos", set())
    positive_seniority = feedback_profile.get("positive_seniority", set())
    negative_seniority = feedback_profile.get("negative_seniority", set())

    if any(token and token in title for token in positive_titles):
        score += 3
        reasons.append("alineado con vacantes guardadas/aplicadas")
    if any(token and token in title for token in negative_titles):
        score -= 3
        reasons.append("parecido a vacantes descartadas")

    if company and company in positive_companies:
        score += 2
        reasons.append("empresa con interés previo")
    if company and company in negative_companies:
        score -= 2
        reasons.append("empresa descartada previamente")

    if work_mode and work_mode in positive_work_modes:
        score += 1
        reasons.append("modalidad alineada con tu feedback")
    if work_mode and work_mode in negative_work_modes:
        score -= 1
        reasons.append("modalidad menos preferida por tu feedback")

    if seniority and seniority in positive_seniority:
        score += 2
        reasons.append("seniority alineado con tu feedback")
    if seniority and seniority in negative_seniority:
        score -= 2
        reasons.append("seniority menos alineado con tu feedback")

    if geo_tokens & positive_geos:
        score += 2
        reasons.append("geografía alineada con tu feedback")
    if geo_tokens & negative_geos:
        score -= 2
        reasons.append("geografía menos alineada con tu feedback")

    return score, reasons


def score_job(job: dict, keywords: Iterable[str], feedback_profile: dict | None = None) -> dict:
    title = clean_text(job.get("title", ""))
    description = clean_text(job.get("description_snippet", ""))
    priority = clean_text(job.get("priority", ""))
    posted_date = clean_text(job.get("posted_date", ""))
    global_signal = bool(job.get("global_signal", False))

    matches = keyword_match_details(title, description, keywords)

    total_score = 0
    reasons: list[str] = []

    for scorer in (
        lambda: keyword_score(matches),
        lambda: seniority_score(title),
        lambda: global_signal_score(global_signal),
        lambda: priority_score(priority),
        lambda: recency_score(posted_date, title, description),
        lambda: feedback_score(job, feedback_profile),
    ):
        points, score_reasons = scorer()
        total_score += points
        reasons.extend(score_reasons)

    return {
        "score": total_score,
        "keyword_matches": matches,
        "score_reasons": reasons,
    }
