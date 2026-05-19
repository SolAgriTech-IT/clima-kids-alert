CLIMA-KIDS ALERT — PostgreSQL scripts (open source)
===================================================

These files let you bootstrap subscriber management on YOUR PostgreSQL server
without shipping real user data in the repository.

Apply order:
  1. Run Alembic from backend/ (recommended):  alembic upgrade head
  2. Optional raw SQL extras:  psql -f 001_alert_subscribers_schema.sql
  3. Example row:              psql -f 002_seed_example_subscriber.sql

Docker (service "db"):
  docker compose exec db psql -U clima -d clima_kids -f /path/in/container/...

External PostgreSQL:
  Set DATABASE_URL in .env, then run Alembic from the backend container or host.

See repository README.md for host/port/user/password variables.
