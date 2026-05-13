# CLIMA-KIDS ALERT

**CLIMA-KIDS ALERT** is a production-oriented, open-source platform for real-time climate and environmental risk monitoring focused on protecting children’s health. The reference deployment context is **Kolwezi (DRC)**, with mining dust, seasonal winds, rainfall/flood exposure, and informal urban growth explicitly reflected in the risk model and map layers—while keeping the architecture reusable for other cities.

**Repository:** [github.com/SolAgriTech-IT/clima-kids-alert](https://github.com/SolAgriTech-IT/clima-kids-alert)

Do not commit `.env`, API keys, tokens, or certificates; use `.env.example` as a template only.

## Quick start (Docker)

1. Copy environment template (optional; Compose provides safe defaults for local demos):

```bash
cp .env.example .env
```

2. Start the stack:

```bash
docker compose up --build
```

3. Open the app:

- Web UI: `http://localhost`
- API docs: `http://localhost/api/docs`

### Default administrator (seeded)

- Email: `mulombodi@sol-agri-tech.org`

The admin account is **created on every backend startup if it is missing** (even when geo data already exists). If login still fails (for example you registered the same email earlier, or a partial DB state), set **`SEED_RESET_ADMIN_PASSWORD=true`** once in `.env` / Compose, restart, log in, then turn it back to **`false`**.

Change this password immediately in any shared or production environment.

## Déploiement sans Docker (VPS, mutualisé)

Pour une mise en production **sans conteneurs** (FastAPI seul ou FastAPI + fichiers statiques Next.js, options Redis/Celery), suivez **`docs/DEPLOYMENT.md`** et le guide développeur **`docs/DEVELOPER.md`** (variables `USE_REDIS`, `USE_CELERY`, `STATIC_SITE_DIR`, etc.).

## Architecture

- **Frontend**: Next.js 14 (React + TypeScript + Tailwind) with Leaflet + OpenStreetMap.
- **Backend**: FastAPI (Python 3.12) + SQLAlchemy + Alembic + JWT auth + SlowAPI rate limiting.
- **Database**: PostgreSQL **16** with **PostGIS 3.4**.
- **Tasks**: Redis + Celery worker + Celery beat (5-minute ingestion cadence).
- **Proxy**: Nginx terminates HTTP on port 80 and routes `/api/*` to FastAPI and `/` to Next.js.
- **Realtime**: Redis pub/sub bridge from workers to the API process, forwarded to dashboard WebSockets.

### Production hardening (VPS)

- **HTTPS**: Nginx is split under `nginx/conf.d/` with a TLS example (`50-https.conf.example`) and an optional overlay `docker-compose.ssl.yml`. Follow `docs/TLS_NGINX_VPS.md`.
- **Shared rate limits**: set `RATE_LIMIT_STORAGE_URI` to Redis (Compose defaults the API to `redis://redis:6379/1`) so multiple API replicas share SlowAPI counters.
- **EO integrations**: optional `sentinel_hub` + `earth_engine` keys are merged into `environmental_readings.payload` (see `docs/DEVELOPER.md`).

## Notifications

Email (SendGrid) and Twilio (SMS + WhatsApp) are implemented end-to-end. If credentials are missing, deliveries are recorded as `skipped` with explicit error messages so operators can distinguish misconfiguration from provider failures.

## Documentation

- `docs/DEVELOPER.md` — local development, module map, contribution notes
- `docs/DEPLOYMENT.md` — Ubuntu VPS guidance (TLS, secrets, scaling)
- `docs/TLS_NGINX_VPS.md` — Let’s Encrypt + Nginx TLS wiring
- `docs/API.md` — high-level endpoint overview

## License

MIT — see `LICENSE`.
