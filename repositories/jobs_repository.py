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
                        has_keyword_match,
                        is_new_today
                    )
                    values (%s, %s, %s, %s, %s, %s, %s)
                    on conflict (run_id, job_id)
                    do nothing
                    """,
                    (
                        run_id,
                        job_id,
                        int(row.get("score", 0) or 0),
                        "Fuerte" if int(row.get("score", 0) or 0) >= 9 else ("Medio" if int(row.get("score", 0) or 0) >= 6 else "Bajo"),
                        score_reasons,
                        bool(row.get("has_keyword_match", False)),
                        bool(row.get("is_new_today", False)),
                    ),
                )

    return True


def _score_band_from_value(score: object) -> str:
    try:
        value = int(score)
    except Exception:
        return "Bajo"
    if value >= 9:
        return "Fuerte"
    if value >= 6:
        return "Medio"
    return "Bajo"


def _base_jobs_query(*, include_keyword_flag: bool = True) -> str:
    keyword_select = "rj.has_keyword_match," if include_keyword_flag else "false as has_keyword_match,"
    return f"""
        select
            j.job_key,
            j.company_name as company,
            j.title,
            j.location,
            j.region,
            j.country,
            j.work_mode,
            j.seniority_level,
            j.ats,
            j.department,
            j.priority,
            j.global_signal,
            j.posted_date,
            j.description_snippet,
            j.source_url,
            j.apply_url as url,
            rj.score,
            rj.score_band,
            rj.score_reasons,
            {keyword_select}
            rj.is_new_today
        from run_jobs rj
        join jobs j on j.id = rj.job_id
        where rj.run_id = %s
    """


def load_latest_run_bundle() -> dict | None:
    if not is_database_enabled():
        return None

    with get_connection() as conn:
        if conn is None:
            return None

        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    id,
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
                from job_runs
                where status = 'completed'
                order by coalesce(finished_at, started_at) desc, id desc
                limit 1
                """
            )
            run_row = cur.fetchone()
            if not run_row:
                return None

            run_id = run_row[0]
            try:
                cur.execute(_base_jobs_query(include_keyword_flag=True), (run_id,))
            except Exception:
                conn.rollback()
                cur = conn.cursor()
                cur.execute(_base_jobs_query(include_keyword_flag=False), (run_id,))
            records = cur.fetchall()
            columns = [desc.name for desc in cur.description]

    df_all = pd.DataFrame(records, columns=columns)
    if df_all.empty:
        summary = {
            "all_jobs": 0,
            "filtered": 0,
            "strong": 0,
            "priority": 0,
            "global": 0,
            "new_today": 0,
            "keywords_used": [],
        }
        meta = {
            "last_run_date": run_row[3].strftime("%Y-%m-%d") if run_row[3] else "",
            "last_run_timestamp": run_row[3].isoformat() if run_row[3] else "",
            "profile_name": run_row[5] or [],
            "selected_regions": run_row[6] or [],
            "selected_countries": run_row[7] or [],
        }
        return {"result": {"all_jobs": df_all, "filtered_jobs": df_all.copy(), "strong_jobs": df_all.copy(), "priority_jobs": df_all.copy(), "global_jobs": df_all.copy(), "new_jobs_today": df_all.copy(), "summary": summary}, "meta": meta}

    for text_col in [
        "job_key",
        "company",
        "title",
        "location",
        "region",
        "country",
        "work_mode",
        "seniority_level",
        "ats",
        "department",
        "priority",
        "posted_date",
        "description_snippet",
        "source_url",
        "url",
    ]:
        if text_col not in df_all.columns:
            df_all[text_col] = ""
        df_all[text_col] = df_all[text_col].fillna("").map(clean_text)

    if "score_reasons" not in df_all.columns:
        df_all["score_reasons"] = ""
    df_all["score_reasons"] = df_all["score_reasons"].apply(
        lambda items: " | ".join(clean_text(item) for item in (items or []) if clean_text(item))
        if isinstance(items, list)
        else clean_text(items)
    )
    df_all["score"] = pd.to_numeric(df_all.get("score", 0), errors="coerce").fillna(0).astype(int)
    df_all["score_band"] = df_all.get("score_band", "").map(clean_text)
    df_all["score_band"] = df_all["score_band"].replace("", pd.NA).fillna(df_all["score"].map(_score_band_from_value))
    df_all["has_keyword_match"] = df_all.get("has_keyword_match", False).fillna(False).astype(bool)
    df_all["is_new_today"] = df_all.get("is_new_today", False).fillna(False).astype(bool)
    df_all["global_signal"] = df_all.get("global_signal", False).fillna(False).astype(bool)

    df_filtered = df_all[df_all["has_keyword_match"]].copy()
    df_strong = df_filtered[df_filtered["score"] >= 9].copy()
    df_priority = df_filtered[df_filtered["priority"].str.upper() == "A"].copy()
    df_global = df_filtered[df_filtered["global_signal"] == True].copy()
    df_new_today = df_all[df_all["is_new_today"] == True].copy()

    summary = {
        "all_jobs": int(len(df_all)),
        "filtered": int(len(df_filtered)),
        "strong": int(len(df_strong)),
        "priority": int(len(df_priority)),
        "global": int(len(df_global)),
        "new_today": int(len(df_new_today)),
        "keywords_used": [],
    }

    finished_at = run_row[3] or run_row[2]
    meta = {
        "last_run_date": finished_at.strftime("%Y-%m-%d") if finished_at else "",
        "last_run_timestamp": finished_at.isoformat() if finished_at else "",
        "profile_name": run_row[5] or [],
        "selected_regions": run_row[6] or [],
        "selected_countries": run_row[7] or [],
        "run_type": clean_text(run_row[1]),
        "status": clean_text(run_row[4]),
        "total_companies": int(run_row[8] or 0),
        "total_jobs": int(run_row[9] or 0),
        "notes": clean_text(run_row[10]),
    }

    return {
        "result": {
            "all_jobs": df_all,
            "filtered_jobs": df_filtered,
            "strong_jobs": df_strong,
            "priority_jobs": df_priority,
            "global_jobs": df_global,
            "new_jobs_today": df_new_today,
            "summary": summary,
        },
        "meta": meta,
    }
