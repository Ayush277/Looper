"""Typed application settings, loaded from environment (.env in dev).

Fail-fast: invalid or missing required values abort startup with a clear error.
Secrets live ONLY here (env), never in the database (NFR-6).
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    loopjob_env: Literal["dev", "prod"] = "dev"
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./loopjob.db"
    redis_url: str = "redis://localhost:6379/0"

    # Optional secrets — features degrade gracefully when unset
    openai_api_key: str = ""
    resend_api_key: str = ""
    jsearch_api_key: str = ""
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    # CORS — the frontend origin
    frontend_origin: str = "http://localhost:3000"

    @property
    def is_dev(self) -> bool:
        return self.loopjob_env == "dev"

    def model_post_init(self, __context: object) -> None:
        # Managed Postgres (Railway/Neon/Render) hands out postgresql:// with
        # libpq-style params — normalize for the asyncpg driver.
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        url = url.replace("sslmode=", "ssl=").replace("&channel_binding=require", "")
        url = url.replace("?channel_binding=require&", "?").rstrip("?")
        self.database_url = url


@lru_cache
def get_settings() -> Settings:
    return Settings()
