from __future__ import annotations

from typing import Any

from fastapi import Body, FastAPI, Query

from backend.pipelines.ingest_jobs import build_phase1_profile, run_ingestion_pipeline
from backend.repositories.application_repository import list_applications, upsert_application
from backend.repositories.phase1_query_repository import latest_phase1_run, list_phase1_jobs, list_phase1_matches
from backend.tasks.background_ingest import get_ingest_state, start_background_ingest
from backend.core.db import get_session
from repositories.jobs_repository import load_latest_run_bundle
from repositories.profile_repository import load_active_profile


app = FastAPI(title="North Hound API", version="0.1.0")


def _serialize_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return value


def _df_to_records(df, limit: int | None = None) -> list[dict]:
    if df is None or df.empty:
        return []
    if limit is not None:
        df = df.head(limit)
    records = df.to_dict(orient="records")
    return [{key: _serialize_value(val) for key, val in record.items()} for record in records]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "north-hound-api"}


@app.get("/profile")
def profile() -> dict:
    return load_active_profile()


@app.post("/phase1/ingest")
def phase1_ingest(
    payload: dict | None = Body(default=None),
    fast: bool = Query(False),
    company_limit: int | None = Query(default=None, ge=1, le=100),
    max_jobs: int | None = Query(default=None, ge=1, le=2000),
) -> dict:
    source_profile = payload or load_active_profile() or {}
    phase1_profile = build_phase1_profile(source_profile)
    effective_limit = company_limit
    effective_max_jobs = max_jobs
    run_type = "manual"
    if fast and effective_limit is None:
        effective_limit = 4
        effective_max_jobs = effective_max_jobs or 200
        run_type = "manual_fast"
    elif fast:
        effective_max_jobs = effective_max_jobs or 200
        run_type = "manual_fast"

    result = run_ingestion_pipeline(
        phase1_profile,
        company_limit=effective_limit,
        max_jobs=effective_max_jobs,
        use_parallel=True,
        run_type=run_type,
    )
    return {
        "status": "ok",
        "profile": phase1_profile,
        "fast": fast,
        "company_limit": effective_limit,
        "max_jobs": effective_max_jobs,
        "result": result,
    }


@app.post("/phase1/ingest/start")
def phase1_ingest_start(
    payload: dict | None = Body(default=None),
    fast: bool = Query(True),
    company_limit: int | None = Query(default=None, ge=1, le=100),
    max_jobs: int | None = Query(default=None, ge=1, le=2000),
) -> dict:
    source_profile = payload or load_active_profile() or {}
    phase1_profile = build_phase1_profile(source_profile)
    effective_limit = company_limit
    effective_max_jobs = max_jobs
    run_type = "manual_background"
    if fast and effective_limit is None:
        effective_limit = 4
        effective_max_jobs = effective_max_jobs or 200
        run_type = "manual_background_fast"
    elif fast:
        effective_max_jobs = effective_max_jobs or 200
        run_type = "manual_background_fast"

    result = start_background_ingest(
        phase1_profile,
        company_limit=effective_limit,
        max_jobs=effective_max_jobs,
        fast=fast,
        run_type=run_type,
    )
    return {
        "status": "accepted" if result["started"] else "busy",
        "profile": phase1_profile,
        "fast": fast,
        "company_limit": effective_limit,
        "max_jobs": effective_max_jobs,
        **result,
    }


@app.get("/phase1/ingest/status")
def phase1_ingest_status() -> dict:
    return {"item": get_ingest_state()}


@app.get("/phase1/jobs")
def phase1_jobs(limit: int = Query(50, ge=1, le=500)) -> dict:
    with get_session() as session:
        if session is None:
            return {"items": [], "count": 0}
        items = [{key: _serialize_value(val) for key, val in row.items()} for row in list_phase1_jobs(session, limit=limit)]
        return {"items": items, "count": len(items)}


@app.get("/phase1/matches")
def phase1_matches(limit: int = Query(50, ge=1, le=500)) -> dict:
    with get_session() as session:
        if session is None:
            return {"items": [], "count": 0}
        items = [{key: _serialize_value(val) for key, val in row.items()} for row in list_phase1_matches(session, limit=limit)]
        return {"items": items, "count": len(items)}


@app.get("/phase1/runs/latest")
def phase1_latest_run() -> dict:
    with get_session() as session:
        if session is None:
            return {"item": None}
        item = latest_phase1_run(session)
        return {"item": {key: _serialize_value(val) for key, val in item.items()} if item else None}


@app.post("/phase1/applications")
def phase1_save_application(payload: dict = Body(...)) -> dict:
    with get_session() as session:
        if session is None:
            return {"status": "unavailable"}
        application = upsert_application(
            session,
            job_id=int(payload.get("job_id", 0) or 0),
            status=str(payload.get("status", "saved")).strip() or "saved",
            notes=str(payload.get("notes", "")).strip(),
            reminder_days=payload.get("reminder_days"),
        )
        return {"status": "ok", "application_id": application.id}


@app.get("/phase1/applications")
def phase1_list_applications(
    due_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    with get_session() as session:
        if session is None:
            return {"items": [], "count": 0}
        items = [{key: _serialize_value(val) for key, val in row.items()} for row in list_applications(session, due_only=due_only, limit=limit)]
        return {"items": items, "count": len(items)}


@app.get("/runs/latest")
def latest_run() -> dict:
    bundle = load_latest_run_bundle()
    if not bundle:
        return {"meta": {}, "summary": {}, "counts": {"jobs": 0}}
    return {
        "meta": bundle["meta"],
        "summary": bundle["result"].get("summary", {}),
        "counts": {"jobs": int(len(bundle["result"].get("all_jobs", [])))},
    }


@app.get("/jobs/latest")
def latest_jobs(
    view: str = Query("all", pattern="^(all|filtered|strong|priority|global|new)$"),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    bundle = load_latest_run_bundle()
    if not bundle:
        return {"items": [], "count": 0}

    view_map = {
        "all": "all_jobs",
        "filtered": "filtered_jobs",
        "strong": "strong_jobs",
        "priority": "priority_jobs",
        "global": "global_jobs",
        "new": "new_jobs_today",
    }
    df = bundle["result"].get(view_map[view])
    items = _df_to_records(df, limit=limit)
    return {"items": items, "count": len(items), "view": view}
