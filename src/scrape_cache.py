from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import settings
from src.ats_router import scrape_company_jobs


CACHE_DIR = settings.CACHE_DIR / "jobs"


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _cache_key(company_row: dict) -> str:
    company = _clean_text(company_row.get("company", ""))
    career_url = _clean_text(company_row.get("career_url", ""))
    ats = _clean_text(company_row.get("ats", ""))
    raw = f"{company}|{career_url}|{ats}".lower()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _cache_file(company_row: dict) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{_cache_key(company_row)}.json"


def _is_fresh(payload: dict) -> bool:
    cached_at = _clean_text(payload.get("cached_at", ""))
    if not cached_at:
        return False
    try:
        timestamp = datetime.fromisoformat(cached_at)
    except Exception:
        return False
    return datetime.now() - timestamp <= timedelta(hours=settings.SCRAPE_CACHE_TTL_HOURS)


def is_company_cache_fresh(company_row: dict) -> bool:
    if not settings.SCRAPE_CACHE_ENABLED:
        return False

    cache_file = _cache_file(company_row)
    if not cache_file.exists():
        return False

    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return False

    return _is_fresh(payload)


def load_cached_jobs(company_row: dict) -> list[dict] | None:
    if not settings.SCRAPE_CACHE_ENABLED:
        return None

    cache_file = _cache_file(company_row)
    if not cache_file.exists():
        return None

    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not _is_fresh(payload):
        return None

    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        return None

    company_name = _clean_text(company_row.get("company", "Unknown"))
    print(f"[CACHE] HIT {company_name}: {len(jobs)} jobs")
    return jobs


def save_cached_jobs(company_row: dict, jobs: list[dict]) -> None:
    if not settings.SCRAPE_CACHE_ENABLED:
        return

    cache_file = _cache_file(company_row)
    payload = {
        "cached_at": datetime.now().isoformat(),
        "company": _clean_text(company_row.get("company", "")),
        "career_url": _clean_text(company_row.get("career_url", "")),
        "ats": _clean_text(company_row.get("ats", "")),
        "jobs": jobs,
    }
    cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def scrape_company_jobs_cached(company_row: dict) -> list[dict]:
    cached_jobs = load_cached_jobs(company_row)
    if cached_jobs is not None:
        return cached_jobs

    jobs = scrape_company_jobs(company_row)
    if not isinstance(jobs, list):
        jobs = []

    save_cached_jobs(company_row, jobs)
    return jobs
