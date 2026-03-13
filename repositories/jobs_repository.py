from __future__ import annotations

from datetime import datetime

import pandas as pd

from db.connection import get_connection, is_database_enabled


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def make_job_key(row: pd.Series) -> str:
    existing = clean_text(row.get("job_key", "")) or clean_text(row.get("dedupe_key", ""))
    if existing:
        return existing

    parts = [
        clean_text(row.get("url", "")),
        clean_text(row.get("company", "")),
        clean_text(row.get("title", "")),
    ]
    return " | ".join(part.lower() for part in parts if part)


def persist_radar_run(
    companies_df: pd.DataFrame,
    jobs_df: pd.DataFrame,
    summary: dict,
    *,
    profile_scope: list[str] | None = None,
    region_scope: list[str] | None = None,
    country_scope: list[str] | None = None,
) -> bool:
    if not is_database_enabled():
        return False

    profile_scope = profile_scope or []
    region_scope = region_scope or []
    country_scope = country_scope or []

    with get_connection() as conn:
        if conn is None:
            return False

        with conn.cursor() as cur:
            cur.execute(
                """
                insert into job_runs (
                    run_type,
                    started_at,
                    finished_at,
                    status,
                    profile_scope,
                    region_scope,
                    country_scope,
                    total_companies,
                    total_jobs,
                    notes
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    "manual",
                    datetime.now(),
                    datetime.now(),
                    "completed",
                    profile_scope,
                    region_scope,
                    country_scope,
                    int(len(companies_df)),
                    int(len(jobs_df)),
                    "",
                ),
            )
            run_id = cur.fetchone()[0]

            company_id_map: dict[tuple[str, str], int] = {}
            for _, row in companies_df.iterrows():
                company_name = clean_text(row.get("company", ""))
                career_url = clean_text(row.get("career_url", ""))
                if not company_name or not career_url:
                    continue

                cur.execute(
                    """
                    insert into companies (
                        company_name,
                        industry,
                        region,
                        country,
                        priority,
                        international_hiring,
                        profile_fit,
                        salary_band,
                        ats,
                        career_url
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (company_name, career_url)
                    do update set
                        industry = excluded.industry,
                        region = excluded.region,
                        country = excluded.country,
                        priority = excluded.priority,
                        international_hiring = excluded.international_hiring,
                        profile_fit = excluded.profile_fit,
                        salary_band = excluded.salary_band,
                        ats = excluded.ats
                    returning id
                    """,
                    (
                        company_name,
                        clean_text(row.get("industry", "")),
                        clean_text(row.get("region", "")),
                        clean_text(row.get("country", "")),
                        clean_text(row.get("priority", "")),
                        clean_text(row.get("international_hiring", "")),
                        clean_text(row.get("profile_fit", "")),
                        clean_text(row.get("salary_band", "")),
                        clean_text(row.get("ats", "")),
                        career_url,
                    ),
                )
                company_id_map[(company_name, career_url)] = cur.fetchone()[0]

            for _, row in jobs_df.iterrows():
                company_name = clean_text(row.get("company", ""))
                source_url = clean_text(row.get("source_url", ""))
                job_key = make_job_key(row)
                if not job_key:
                    continue

                company_id = company_id_map.get((company_name, source_url))

                cur.execute(
                    """
                    insert into jobs (
                        job_key,
                        company_id,
                        company_name,
                        title,
                        location,
                        region,
                        country,
                        work_mode,
                        seniority_level,
                        ats,
                        department,
                        priority,
                        global_signal,
                        posted_date,
                        description_snippet,
                        source_url,
                        apply_url,
                        last_seen_at
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (job_key)
                    do update set
                        company_id = excluded.company_id,
                        company_name = excluded.company_name,
                        title = excluded.title,
                        location = excluded.location,
                        region = excluded.region,
                        country = excluded.country,
                        work_mode = excluded.work_mode,
                        seniority_level = excluded.seniority_level,
                        ats = excluded.ats,
                        department = excluded.department,
                        priority = excluded.priority,
                        global_signal = excluded.global_signal,
                        posted_date = excluded.posted_date,
                        description_snippet = excluded.description_snippet,
                        source_url = excluded.source_url,
                        apply_url = excluded.apply_url,
                        last_seen_at = excluded.last_seen_at
                    returning id
                    """,
                    (
                        job_key,
                        company_id,
                        company_name,
                        clean_text(row.get("title", "")),
                        clean_text(row.get("location", "")),
                        clean_text(row.get("region", "")),
                        clean_text(row.get("country", "")),
                        clean_text(row.get("work_mode", "")),
                        clean_text(row.get("seniority_level", "")),
                        clean_text(row.get("ats", "")),
                        clean_text(row.get("department", "")),
                        clean_text(row.get("priority", "")),
                        bool(row.get("global_signal", False)),
                        clean_text(row.get("posted_date", "")),
                        clean_text(row.get("description_snippet", "")),
                        source_url,
                        clean_text(row.get("url", "")),
                        datetime.now(),
                    ),
                )
                job_id = cur.fetchone()[0]

                score_reasons = [
                    clean_text(part)
                    for part in clean_text(row.get("score_reasons", "")).split("|")
                    if clean_text(part)
                ]

                cur.execute(
                    """
                    insert into run_jobs (
                        run_id,
                        job_id,
                        score,
                        score_band,
                        score_reasons,
                        is_new_today
                    )
                    values (%s, %s, %s, %s, %s, %s)
                    on conflict (run_id, job_id)
                    do nothing
                    """,
                    (
                        run_id,
                        job_id,
                        int(row.get("score", 0) or 0),
                        "Fuerte" if int(row.get("score", 0) or 0) >= 9 else ("Medio" if int(row.get("score", 0) or 0) >= 6 else "Bajo"),
                        score_reasons,
                        bool(row.get("is_new_today", False)),
                    ),
                )

    return True
