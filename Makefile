# CLIMA-KIDS ALERT — developer shortcuts

.PHONY: up down logs migrate seed test lint

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.scripts.seed

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check app && ruff format --check app
