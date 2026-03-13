from __future__ import annotations

from backend.models.job import IngestionRun


def create_ingestion_run(session, payload: dict) -> IngestionRun:
    run = IngestionRun(**payload)
    session.add(run)
    session.flush()
    return run
