from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from backend.pipelines.ingest_jobs import run_ingestion_pipeline


_state_lock = threading.Lock()
_ingest_state: dict[str, Any] = {
    "status": "idle",
    "stage": None,
    "started_at": None,
    "finished_at": None,
    "updated_at": None,
    "fast": False,
    "company_limit": None,
    "max_jobs": None,
    "run_type": None,
    "companies_selected": 0,
    "raw_jobs": 0,
    "deduped_jobs": 0,
    "processed_jobs": 0,
    "result": None,
    "error": None,
}


def _serialize_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return value


def get_ingest_state() -> dict[str, Any]:
    with _state_lock:
        return {key: _serialize_value(value) for key, value in _ingest_state.items()}


def _update_progress(payload: dict[str, Any]) -> None:
    with _state_lock:
        _ingest_state.update(payload)
        _ingest_state["updated_at"] = datetime.utcnow()


def _run_background_ingest(
    profile: dict,
    *,
    company_limit: int | None,
    max_jobs: int | None,
    fast: bool,
    run_type: str,
) -> None:
    try:
        _update_progress({"stage": "scrape_and_persist"})
        result = run_ingestion_pipeline(
            profile,
            company_limit=company_limit,
            max_jobs=max_jobs,
            use_parallel=True,
            run_type=run_type,
            progress_callback=_update_progress,
        )
        with _state_lock:
            _ingest_state.update(
                {
                    "status": "completed",
                    "stage": "completed",
                    "finished_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "result": result,
                    "error": None,
                }
            )
    except Exception as exc:
        with _state_lock:
            _ingest_state.update(
                {
                    "status": "failed",
                    "stage": "failed",
                    "finished_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "error": str(exc),
                }
            )


def start_background_ingest(
    profile: dict,
    *,
    company_limit: int | None,
    max_jobs: int | None,
    fast: bool,
    run_type: str,
) -> dict[str, Any]:
    with _state_lock:
        if _ingest_state["status"] == "running":
            return {
                "started": False,
                "reason": "already_running",
                "state": {key: _serialize_value(value) for key, value in _ingest_state.items()},
            }

        _ingest_state.update(
            {
                "status": "running",
                "stage": "queued",
                "started_at": datetime.utcnow(),
                "finished_at": None,
                "updated_at": datetime.utcnow(),
                "fast": fast,
                "company_limit": company_limit,
                "max_jobs": max_jobs,
                "run_type": run_type,
                "companies_selected": 0,
                "raw_jobs": 0,
                "deduped_jobs": 0,
                "processed_jobs": 0,
                "result": None,
                "error": None,
            }
        )

    thread = threading.Thread(
        target=_run_background_ingest,
        kwargs={
            "profile": profile,
            "company_limit": company_limit,
            "max_jobs": max_jobs,
            "fast": fast,
            "run_type": run_type,
        },
        daemon=True,
        name="northhound-phase1-ingest",
    )
    thread.start()
    return {
        "started": True,
        "reason": None,
        "state": get_ingest_state(),
    }
