"""Celery application for asynchronous ingestion and notification tasks."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "clima_kids",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.pipeline"],
)

celery_app.conf.beat_schedule = {
    "environment-pipeline-every-5-minutes": {
        "task": "app.tasks.pipeline.run_full_pipeline",
        "schedule": crontab(minute="*/5"),
    },
}

celery_app.conf.timezone = "UTC"
