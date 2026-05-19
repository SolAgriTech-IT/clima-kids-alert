"""FastAPI entrypoint for CLIMA-KIDS ALERT.

The HTTP API is versioned under ``/api/v1``. WebSocket live updates are exposed
at ``/api/ws/dashboard`` and should be placed behind the same TLS termination
and abuse controls as the REST surface.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import os

from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.config import get_settings
from app.database import SessionLocal
from app.limiter import limiter
from app.models import import_models
from app.realtime_bridge import redis_subscriber_loop
from app.routers import actions, alerts, auth, dashboard, geo, health, public, simulations, users
from app.websocket_manager import manager

import_models()

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks: optional Redis → WebSocket fan-out background task."""
    settings = get_settings()
    task: asyncio.Task[None] | None = None
    if settings.use_redis:
        task = asyncio.create_task(redis_subscriber_loop())
    log.info(
        "CLIMA-KIDS ALERT API started (CORS=%s, use_redis=%s)",
        settings.cors_origin_list(),
        settings.use_redis,
    )
    yield
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CLIMA-KIDS ALERT API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = APIRouter(prefix="/api/v1")
    api.include_router(health.router)
    api.include_router(public.router)
    api.include_router(auth.router)
    api.include_router(users.router)
    api.include_router(dashboard.router)
    api.include_router(geo.router)
    api.include_router(alerts.router)
    api.include_router(actions.router)
    api.include_router(simulations.router)
    app.include_router(api)

    @app.get("/api/v1/meta")
    def meta() -> dict[str, str]:
        return {"service": "clima-kids-alert", "city": settings.default_city_name}

    @app.websocket("/api/ws/dashboard")
    async def dashboard_ws(
        websocket: WebSocket,
        token: str | None = Query(default=None),
    ) -> None:
        """Public live channel for dashboard refresh events (MVP: no JWT required).

        An optional ``token`` query is accepted for future authenticated dashboards;
        it is ignored when absent.
        """
        await websocket.accept()
        if token:
            from app.models.user import User
            from app.services.security import decode_token_safe

            claims = decode_token_safe(token)
            if claims is None or "sub" not in claims:
                await websocket.close(code=4401)
                return
            user_id = int(claims["sub"])
            db = SessionLocal()
            try:
                user = db.get(User, user_id)
            finally:
                db.close()
            if user is None or not user.is_active:
                await websocket.close(code=4401)
                return
        await manager.register(websocket)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            # Normal client disconnects surface as connection errors; always prune.
            pass
        finally:
            await manager.disconnect(websocket)

    static_dir = (settings.static_site_dir or "").strip()
    if static_dir and os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static_site")
        log.info("Serving static UI from %s", static_dir)

    return app


app = create_app()
