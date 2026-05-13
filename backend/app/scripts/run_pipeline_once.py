"""Exécute une fois le pipeline d’ingestion + risques (sans Celery).

À placer en crontab sur hébergement mutualisé, par exemple :
  */15 * * * * cd /chemin/vers/backend && .venv/bin/python -m app.scripts.run_pipeline_once
"""

from __future__ import annotations

import logging

from app.tasks.pipeline import run_full_pipeline

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    log.info("Pipeline one-shot (apply)…")
    run_full_pipeline.apply()
    log.info("Pipeline terminé.")


if __name__ == "__main__":
    main()
