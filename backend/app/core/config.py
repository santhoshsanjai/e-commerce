from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Only for local development and tests; refused in every deployed environment.
LOCAL_DEV_JWT_SECRET = "local-dev-only-jwt-secret-do-not-deploy"  # noqa: S105


class Settings(BaseSettings):
    """Application settings, read from environment variables (and `.env` in development)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "test", "dev", "staging", "production"] = "local"
    app_name: str = "E-Commerce API"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ecommerce"

    jwt_secret: str = Field(default=LOCAL_DEV_JWT_SECRET, min_length=32)
    jwt_issuer: str = "ecommerce-api"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14

    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:4200", "http://localhost:4300"]

    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    @model_validator(mode="after")
    def _require_real_secret_when_deployed(self) -> "Settings":
        if self.environment not in ("local", "test") and self.jwt_secret == LOCAL_DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set for deployed environments")
        if self.is_production and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
