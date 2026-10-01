# Predict-11 v2 dev commands
.PHONY: setup db-up db-down migrate api test lint web

setup:            ## install backend deps
	cd backend && uv sync

db-up:            ## start Postgres (port 5433)
	docker compose -f infra/docker-compose.yml up -d --wait

db-down:
	docker compose -f infra/docker-compose.yml down

migrate:          ## apply DB migrations
	cd backend && uv run alembic upgrade head

api:              ## run the API on :8000
	cd backend && uv run p11 serve --reload

test:             ## unit + integration tests
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check src tests && uv run ruff format --check src tests

web:              ## run the Next.js app on :3000
	cd web && pnpm dev
