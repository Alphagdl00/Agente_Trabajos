# src/parallel_scraper.py

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from config.settings import settings
from src.ats_router import scrape_company_jobs


def _scrape_one_company(company_row: dict) -> tuple[str, list[dict]]:
    company_name = str(company_row.get("company", "Unknown")).strip()

    try:
        jobs = scrape_company_jobs(company_row)
        if not isinstance(jobs, list):
            jobs = []
        return company_name, jobs
    except Exception as exc:
        print(f"[PARALLEL] ERROR in {company_name}: {exc}")
        return company_name, []


def collect_jobs_parallel(companies_df: pd.DataFrame) -> list[dict]:
    all_jobs: list[dict] = []

    if companies_df.empty:
        return all_jobs

    rows = [row.to_dict() for _, row in companies_df.iterrows()]
    total = len(rows)

    print(f"[PARALLEL] Starting parallel scrape for {total} companies with {settings.MAX_WORKERS} workers")

    with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
        future_to_row = {
            executor.submit(_scrape_one_company, row): row
            for row in rows
        }

        completed = 0
        for future in as_completed(future_to_row):
            row = future_to_row[future]
            company_name = str(row.get("company", "Unknown")).strip()

            try:
                _, jobs = future.result()
            except Exception as exc:
                print(f"[PARALLEL] Future failed for {company_name}: {exc}")
                jobs = []

            for job in jobs:
                job = dict(job)

                job.setdefault("company", company_name)
                job.setdefault("industry", row.get("industry", ""))
                job.setdefault("region", row.get("region", ""))
                job.setdefault("country", row.get("country", ""))
                job.setdefault("priority", row.get("priority", ""))
                job.setdefault("international_hiring", row.get("international_hiring", ""))
                job.setdefault("profile_fit", row.get("profile_fit", ""))
                job.setdefault("salary_band", row.get("salary_band", ""))
                job.setdefault("source_url", row.get("career_url", ""))
                job.setdefault("ats", row.get("ats", ""))

                all_jobs.append(job)

            completed += 1
            print(f"[PARALLEL] ({completed}/{total}) {company_name}: {len(jobs)} jobs")

    return all_jobs
