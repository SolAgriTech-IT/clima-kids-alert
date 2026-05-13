# Deployment guide (English)

## Docker Compose (recommended first deploy)

Use `docker compose up --build` on an Ubuntu VPS with Docker Engine + Compose v2 installed.

### TLS / HTTPS (production)

See **`docs/TLS_NGINX_VPS.md`** for a concrete Let’s Encrypt + Nginx workflow.

At a high level:

- Keep HTTP for ACME challenges and (optionally) redirect everything else to HTTPS.
- Terminate TLS in Nginx and mount host certificates read-only (`docker-compose.ssl.yml`).
- Update `CORS_ORIGINS` to your `https://` origin(s).

### Multi-replica API rate limits

Set `RATE_LIMIT_STORAGE_URI` to a Redis DSN (the Compose file defaults to `redis://redis:6379/1` for the API container).
This makes SlowAPI counters shared across all FastAPI replicas.

### Secrets

Never commit real secrets. Prefer:

- `.env` on the server (restricted permissions), or
- a secret manager / systemd environment drop-ins

Rotate at minimum:

- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- provider keys (`SENDGRID_API_KEY`, `TWILIO_*`, optional `OPENWEATHERMAP_API_KEY`)

### Scaling notes

- **API**: run multiple FastAPI replicas behind Nginx; ensure sticky sessions **or** move WebSocket fan-out fully to Redis pub/sub subscribers on each replica (the repository already publishes cross-process events on `clima:events`).
- **Workers**: increase Celery worker concurrency for CPU-bound tasks; keep ingestion polite with upstream rate limits.
