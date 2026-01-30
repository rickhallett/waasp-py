"""Application configuration with environment-based settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "waasp"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = Field(default=False)
    secret_key: str = Field(default="change-me-in-production")

    # Database
    database_url: str = Field(
        default="sqlite:///./waasp.db",
        description="Database connection string",
    )

    # Redis / Celery
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection for Celery broker",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend",
    )

    # API
    api_prefix: str = "/api/v1"
    api_token: str | None = Field(
        default=None,
        description="API token for admin endpoints",
    )

    # Security defaults
    default_trust_level: Literal["blocked", "limited", "trusted", "sovereign"] = "blocked"
    
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
