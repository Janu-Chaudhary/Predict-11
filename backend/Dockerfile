# Predict-11 API (FastAPI + LightGBM), deployed on Render (render.yaml). Build context = repo root:
#   docker build -f backend/Dockerfile -t predict11-api .
# Layout mirrors the repo (/app/backend/src, /app/models) because p11.core.settings derives
# REPO_ROOT from its own path. Config comes from env vars (P11_DATABASE_URL, P11_ENV=prod,
# P11_CORS_ORIGINS / P11_CORS_ORIGIN_REGEX). Listens on $PORT (Render sets it).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv \
    PORT=7860 P11_ENV=prod

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

# run as an unprivileged user
RUN useradd -m -u 1000 app
WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/src ./src
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
RUN uv sync --frozen --no-dev

# trained model artifacts (the run that models/latest.json points to)
COPY models /app/models

RUN chown -R app:app /app
USER app
EXPOSE 7860
CMD ["sh", "-c", "/app/.venv/bin/uvicorn p11.api.app:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
