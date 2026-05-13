# Developer guide (English)

## Repository layout

- `backend/` — FastAPI service (`app/` package), Alembic migrations, Celery tasks
- `frontend/` — Next.js UI (French user-facing strings)
- `nginx/` — reverse proxy configuration (WebSocket-ready)
- `docs/` — operational and contributor documentation

## Backend module map

- `app/main.py` — application factory, CORS, SlowAPI limiter, WebSocket endpoint
- `app/routers/` — HTTP routers (`/api/v1/...`)
- `app/models/` — SQLAlchemy ORM models (PostGIS geometries via GeoAlchemy2)
- `app/services/connectors/` — external API clients (Open-Meteo, OpenAQ, NASA POWER, climate archive)
- `app/services/ingestion.py` — merges connector outputs into `environmental_readings`
- `app/services/risk_engine.py` — child health scoring, alert creation, cooldown + targeting rules
- `app/services/notifications.py` — SendGrid + Twilio integration
- `app/tasks/pipeline.py` — Celery task orchestrating ingestion → risk evaluation
- `app/realtime_bridge.py` — Redis subscriber forwarding events to WebSocket clients

## Running tests (backend)

Inside the backend container (or a local venv with dependencies installed):

```bash
pytest -q
```

## IoT / sensors (future)

The ingestion layer persists provider-agnostic JSON in `environmental_readings`. Future LoRaWAN/GSM/Wi-Fi sensors can write similar rows (optionally with per-sensor coordinates) without refactoring the risk engine contract.

## `environmental_readings.payload` extensions

The merged payload is intentionally a **versioned JSON document**. In addition to weather/air-quality sources, ingestion may attach:

- `sentinel_hub`: OAuth + STAC search output from Copernicus Sentinel Hub (optional; see `SENTINEL_HUB_*` settings).
- `earth_engine`: JSON returned by an internal **GEE bridge** HTTP service (optional; see `GEE_BRIDGE_*` settings).

The child risk engine currently treats these keys as **optional context** (it does not hard-require them), so you can roll out EO integrations gradually without breaking scoring.
