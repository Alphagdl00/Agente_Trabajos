from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query

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
