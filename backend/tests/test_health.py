from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app


class _DummySession:
    def execute(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


def _override_db() -> Generator[Session, None, None]:
    yield _DummySession()  # type: ignore[misc]


def test_health() -> None:
    app.dependency_overrides[get_db] = _override_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
    finally:
        app.dependency_overrides.clear()
