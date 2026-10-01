"""All configuration in one place, read from environment / .env (prefix P11_)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="P11_", env_file=REPO_ROOT / ".env", extra="ignore"
    )

    env: str = "dev"
    database_url: str = "postgresql+psycopg://p11:p11@localhost:5433/p11"

    data_dir: Path = REPO_ROOT / "data"
    raw_archive_dir: Path = REPO_ROOT / "data" / "archive"  # gzipped raw source payloads
    lake_dir: Path = REPO_ROOT / "data" / "lake"  # parquet for training/backtests

    # scraping politeness
    http_min_interval_s: float = 1.0
    http_user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
