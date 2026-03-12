# src/ats_detector.py

from __future__ import annotations

from urllib.parse import urlparse


ATS_PATTERNS = {
    "greenhouse": [
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "greenhouse.io",
    ],
    "lever": [
        "jobs.lever.co",
        "lever.co",
    ],
    "workday": [
        "myworkdayjobs.com",
        "workdayjobs.com",
    ],
    "successfactors": [
        "jobs.sap.com",
        "successfactors.com",
        "successfactors.eu",
    ],
    "icims": [
        "icims.com",
    ],
    "smartrecruiters": [
        "smartrecruiters.com",
    ],
    "taleo": [
        "taleo.net",
    ],
    "oraclecloud": [
        "oraclecloud.com",
    ],
    "ashby": [
        "ashbyhq.com",
    ],
}


def normalize_url(url: str) -> str:
    if not url:
        return ""

    url = str(url).strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url.rstrip("/")


def get_domain(url: str) -> str:
    try:
        parsed = urlparse(normalize_url(url))
        return (parsed.netloc or "").lower()
    except Exception:
        return ""


def detect_ats_from_url(url: str) -> str:
    domain = get_domain(url)
    full_url = normalize_url(url).lower()

    if not domain and not full_url:
        return "generic"

    for ats_name, patterns in ATS_PATTERNS.items():
        for pattern in patterns:
            if pattern in domain or pattern in full_url:
                return ats_name

    if "greenhouse" in full_url:
        return "greenhouse"

    if "lever.co" in full_url:
        return "lever"

    if "workdayjobs" in full_url or "myworkdayjobs" in full_url:
        return "workday"

    if "successfactors" in full_url or "jobs.sap.com" in full_url:
        return "successfactors"

    if "icims" in full_url:
        return "icims"

    if "smartrecruiters" in full_url:
        return "smartrecruiters"

    if "taleo" in full_url:
        return "taleo"

    if "oraclecloud" in full_url:
        return "oraclecloud"

    if "ashbyhq" in full_url:
        return "ashby"

    return "generic"


def enrich_company_ats(company_row: dict) -> dict:
    row = dict(company_row)

    current_ats = str(row.get("ats", "") or "").strip().lower()
    career_url = str(row.get("career_url", "") or "").strip()

    if current_ats and current_ats not in {"", "auto", "detect", "unknown", "generic"}:
        row["ats"] = current_ats
        return row

    row["ats"] = detect_ats_from_url(career_url)
    return row