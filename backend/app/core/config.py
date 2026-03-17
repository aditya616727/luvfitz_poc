"""
Application configuration – loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Postgres ──
    postgres_user: str = "outfit_user"
    postgres_password: str = "outfit_secret_pw"
    postgres_db: str = "outfit_builder"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str = "postgresql://outfit_user:outfit_secret_pw@localhost:5432/outfit_builder"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── Celery ──
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── App ──
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # ── Scraping ──
    scrape_concurrency: int = 3
    scrape_delay_seconds: float = 2.0
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
