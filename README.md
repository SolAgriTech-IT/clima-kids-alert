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

If login fails (wrong password or account registered earlier as a normal user), set **`SEED_RESET_ADMIN_PASSWORD=true`** once, restart the backend, sign in, then set it back to **`false`**.

### Administrateurs (open source)

| Méthode | Action |
|--------|--------|
| Variables d’environnement | `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD` dans `.env` / `docker-compose.yml` (service `backend`) |
| Récupération mot de passe | `SEED_RESET_ADMIN_PASSWORD=true` (une fois) |
| CLI | `docker compose exec backend python -m app.scripts.manage_admin create email@domaine.org 'MotDePasseSecurise12!'` |
| CLI liste / rôles | `manage_admin list`, `manage_admin promote`, `manage_admin demote` |
| Interface web (connecté admin) | `POST /api/v1/admin/simulations/admins`, `DELETE /api/v1/admin/simulations/admins/{id}` |

Page admin après connexion : **`/admin/simulations`** (simulateur climat, alerte de test, message officiel aux abonnés).

## Base PostgreSQL des abonnés

Le dépôt **ne contient aucune donnée utilisateur réelle**. Vous déployez votre propre base :

### Cas 1 — PostgreSQL dans Docker (défaut)

Fichiers à modifier :

| Fichier | Variables |
|---------|-----------|
| `.env` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL` |
| `docker-compose.yml` | service `db` (`environment`, volume `postgres_data`), service `backend` (`DATABASE_URL`) |

Schéma applicatif : migrations Alembic (`backend/alembic/versions/`, dont `003_subscriber_enhancements.py`).

Scripts SQL optionnels (triggers de fusion) : `db/postgresql/001_alert_subscribers_schema.sql`, `002_seed_example_subscriber.sql`.

Exemple après démarrage :

```bash
docker compose exec db psql -U clima -d clima_kids -f /path/mounted/001_alert_subscribers_schema.sql
```

Abonné exemple (e-mail seul) : `mulombodi@sol-agri-tech.org` — créé au seed si absent.

### Cas 2 — PostgreSQL externe

1. Créez une base PostGIS sur votre serveur.
2. Dans `.env` : `DATABASE_URL=postgresql+psycopg2://USER:PASS@HOST:5432/DBNAME`
3. Commentez ou supprimez le service `db` dans `docker-compose.yml` si vous n’utilisez pas le conteneur local.
4. Lancez les migrations : `docker compose run --rm backend alembic upgrade head`
5. Appliquez les scripts `db/postgresql/*.sql` si vous voulez les triggers PL/pgSQL de fusion.

Fusion intelligente : même numéro + canal SMS puis WhatsApp → une seule ligne, canaux cumulés (voir `backend/app/services/subscriber_merge.py` et triggers SQL).

### Formspree → PostgreSQL (import automatique)

Formulaire public : `https://formspree.io/f/xeenyjld` (également envoyé en parallèle à l’API).

Pour alimenter PostgreSQL sans webhook payant :

1. Exportez les soumissions Formspree en CSV vers `data/inbox/formspree_export.csv` (dossier gitignoré).
2. Import : `docker compose exec backend python -m app.scripts.formspree_import data/inbox/formspree_export.csv`
3. Les CSV traités sont archivés sous `data/inbox/processed/` et supprimés après 24 h.

Alternative : workflow **n8n** (e-mail Formspree → HTTP `POST /api/v1/public/subscribe`).

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

Les **inscriptions Formspree** et les **alertes** (simulation admin, risques, broadcast) sont des circuits distincts. Les alertes partent via **e-mail** (SendGrid ou SMTP) et **Twilio** (SMS / WhatsApp).

| Canal | Gratuit / local | Variables |
|-------|-----------------|-----------|
| E-mail local Docker | **Mailpit** → http://localhost:8025 | `SMTP_HOST=mailpit`, `SMTP_PORT=1025`, `SMTP_USE_TLS=false` (défaut Compose) |
| E-mail production | [SendGrid](https://sendgrid.com) (~100/j) ou [Brevo](https://www.brevo.com) SMTP (~300/j) | `SENDGRID_API_KEY` ou `SMTP_HOST` + identifiants |
| SMS / WhatsApp | [Twilio essai](https://www.twilio.com/try-twilio) (numéros vérifiés en test) | `TWILIO_*` |

Sans configuration, les envois sont enregistrés en base avec le statut `skipped` et le motif (visible sur la page **Simulations** après chaque envoi).

## Documentation

- `docs/DEVELOPER.md` — local development, module map, contribution notes
- `docs/DEPLOYMENT.md` — Ubuntu VPS guidance (TLS, secrets, scaling)
- `docs/TLS_NGINX_VPS.md` — Let’s Encrypt + Nginx TLS wiring
- `docs/API.md` — high-level endpoint overview

## License

MIT — see `LICENSE`.
