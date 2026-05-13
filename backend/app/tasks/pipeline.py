"""Scheduled pipeline: ingest environmental APIs, evaluate risks, dispatch alerts."""

from __future__ import annotations

import logging

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services import ingestion
from app.services.risk_engine import evaluate_and_persist

log = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.pipeline.run_full_pipeline")
def run_full_pipeline() -> str:
    db = SessionLocal()
    try:
        reading = ingestion.fetch_and_store_reading(db)
        evaluate_and_persist(db, reading.payload)
        return "ok"
    except Exception:
        log.exception("Pipeline failed")
        db.rollback()
        raise
    finally:
        db.close()
