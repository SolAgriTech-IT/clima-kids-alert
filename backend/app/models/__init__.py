"""ORM models for CLIMA-KIDS ALERT."""


def import_models() -> None:
    """Import all model modules so Alembic and metadata see every table."""
    from app.models import geo  # noqa: F401
    from app.models import subscriber  # noqa: F401
    from app.models import user  # noqa: F401
    from app.models import alerting  # noqa: F401
