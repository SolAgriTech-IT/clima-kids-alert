# API overview (English)

Base URL (via Nginx): `/api/v1`

## Authentication

- `POST /auth/register` — create a standard user account
- `POST /auth/login` — returns a JWT bearer token

Authenticated requests:

`Authorization: Bearer <token>`

## Core resources

- `GET /health` — liveness + DB connectivity
- `GET /users/me` — profile
- `PATCH /users/me` — update contact fields + notification toggles
- `GET /dashboard/summary` — KPIs for the French dashboard
- `GET /dashboard/risk-cards` — three risk cards (heat / dust / rain)
- `GET /dashboard/tables` — zone score table + recent alerts table
- `GET /geo/zones` — zones GeoJSON (with latest score properties)
- `GET /geo/schools` — schools GeoJSON
- `GET /geo/health-centers` — health centers GeoJSON
- `GET /geo/hazards` — hazard polygons GeoJSON
- `GET /alerts/recent` — raw alert list

## Admin actions (admin role only)

- `POST /actions/run-pipeline` — enqueue ingestion + risk evaluation
- `POST /actions/send-alert` — create a manual alert and dispatch notifications
- `POST /actions/send-report` — email a text report snapshot (SendGrid if configured)

## WebSocket

- `WS /api/ws/dashboard?token=<jwt>` — live refresh hints (`alerts_refresh`)

## Environmental payload extensions (ingestion)

Downstream consumers (risk engine, analytics) should treat `environmental_readings.payload` as JSON that may include optional keys such as `sentinel_hub` and `earth_engine` when those integrations are enabled (see `docs/DEVELOPER.md`).
