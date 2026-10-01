# Predict-11 v2 dev commands
.PHONY: setup db-up db-down db-backup db-restore migrate api test lint web

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

db-backup:        ## dump Postgres to data/backups/p11-<timestamp>.sql.gz (keeps last 14)
	mkdir -p data/backups
	docker compose -f infra/docker-compose.yml exec -T postgres pg_dump -U p11 -d p11 | gzip > data/backups/p11-$$(date +%Y%m%d-%H%M%S).sql.gz
	ls -1t data/backups/p11-*.sql.gz | tail -n +15 | xargs -r rm --

db-restore:       ## restore from FILE=data/backups/p11-....sql.gz into the running Postgres
	gunzip -c $(FILE) | docker compose -f infra/docker-compose.yml exec -T postgres psql -U p11 -d p11
