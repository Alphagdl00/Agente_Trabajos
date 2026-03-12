# src/ats_router.py

from __future__ import annotations

from src.ats_detector import enrich_company_ats, detect_ats_from_url
from src.ats_generic import scrape_generic

import src.ats_greenhouse as ats_greenhouse
import src.ats_lever as ats_lever
import src.ats_workday as ats_workday
import src.ats_successfactors as ats_successfactors


def _resolve_scraper_function(module, candidates: list[str]):
    for name in candidates:
        func = getattr(module, name, None)
        if callable(func):
            return func
    return None


def _safe_scrape(module, function_names: list[str], company_name: str, career_url: str) -> list[dict]:
    scraper_func = _resolve_scraper_function(module, function_names)

    if scraper_func is None:
        print(
            f"[ROUTER] No scraper function found in module '{module.__name__}'. "
            f"Tried: {function_names}"
        )
        return []

    try:
        results = scraper_func(company_name, career_url)
        return results if isinstance(results, list) else []
    except Exception as exc:
        print(
            f"[ROUTER] Error scraping {company_name} with "
            f"{module.__name__}.{scraper_func.__name__}: {exc}"
        )
        return []


def scrape_company_jobs(company_row: dict) -> list[dict]:
    row = enrich_company_ats(company_row)

    company_name = row.get("company", "Unknown Company")
    career_url = row.get("career_url", "")
    ats = str(row.get("ats", "") or "").strip().lower()

    if not career_url:
        print(f"[ROUTER] {company_name} skipped: missing career_url")
        return []

    if not ats or ats in {"unknown", "auto", "detect"}:
        ats = detect_ats_from_url(career_url)

    print(f"[ROUTER] {company_name} -> ATS detected: {ats}")

    if ats == "greenhouse":
        jobs = _safe_scrape(
            ats_greenhouse,
            [
                "scrape_greenhouse",
                "get_greenhouse_jobs",
                "fetch_greenhouse_jobs",
                "scrape_jobs",
            ],
            company_name,
            career_url,
        )
        if jobs:
            return jobs

    elif ats == "lever":
        jobs = _safe_scrape(
            ats_lever,
            [
                "scrape_lever",
                "get_lever_jobs",
                "fetch_lever_jobs",
                "scrape_jobs",
            ],
            company_name,
            career_url,
        )
        if jobs:
            return jobs

    elif ats == "workday":
        jobs = _safe_scrape(
            ats_workday,
            [
                "scrape_workday",
                "get_workday_jobs",
                "fetch_workday_jobs",
                "scrape_jobs",
            ],
            company_name,
            career_url,
        )
        if jobs:
            return jobs

    elif ats == "successfactors":
        jobs = _safe_scrape(
            ats_successfactors,
            [
                "scrape_successfactors",
                "get_successfactors_jobs",
                "fetch_successfactors_jobs",
                "scrape_jobs",
            ],
            company_name,
            career_url,
        )
        if jobs:
            return jobs

    elif ats in {"icims", "smartrecruiters", "taleo", "oraclecloud", "ashby"}:
        print(f"[ROUTER] {company_name}: ATS '{ats}' sin conector dedicado. Using generic fallback.")
        jobs = scrape_generic(company_name, career_url)
        if jobs:
            return jobs

    print(f"[ROUTER] {company_name}: falling back to generic scraper.")
    return scrape_generic(company_name, career_url)