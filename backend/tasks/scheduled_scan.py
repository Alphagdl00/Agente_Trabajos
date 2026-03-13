from __future__ import annotations

from backend.pipelines.ingest_jobs import run_ingestion_pipeline


def run_scheduled_scan(profile: dict) -> dict:
    return run_ingestion_pipeline(profile)
