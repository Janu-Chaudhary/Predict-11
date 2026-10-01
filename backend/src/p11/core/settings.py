"""All configuration in one place, read from environment / .env (prefix P11_)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
DEV_CORS_REGEX = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="P11_", env_file=REPO_ROOT / ".env", extra="ignore"
    )

    env: str = "dev"
    database_url: str = "postgresql+psycopg://p11:p11@localhost:5433/p11"

    data_dir: Path = REPO_ROOT / "data"
    raw_archive_dir: Path = REPO_ROOT / "data" / "archive"  # gzipped raw source payloads
    lake_dir: Path = REPO_ROOT / "data" / "lake"  # parquet for training/backtests

    # CORS: explicit origins (P11_CORS_ORIGINS, a JSON list) plus an
    # optional regex. In dev (the default) any localhost / 127.0.0.1 port is allowed, so a
    # second Next dev server on :3001 works; in production set P11_ENV=prod and list origins.
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_origin_regex: str | None = None

    @property
    def effective_cors_origin_regex(self) -> str | None:
        if self.cors_origin_regex:
            return self.cors_origin_regex
        return DEV_CORS_REGEX if self.env == "dev" else None

    # scraping politeness
    http_min_interval_s: float = 1.0
    http_user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
