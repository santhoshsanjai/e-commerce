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

    # S3-compatible object storage. Empty s3_endpoint_url = AWS S3 (credentials from the IAM role);
    # locally it points at the SeaweedFS S3 gateway from docker-compose.
    s3_endpoint_url: str | None = "http://localhost:8333"
    s3_region: str = "us-east-1"
    s3_access_key: str | None = "local"
    s3_secret_key: str | None = "local"  # noqa: S105 - local-only default
    media_bucket: str = "product-media"
    # Private bucket for courier exports and uploaded courier files. Never public.
    private_bucket: str = "private-files"
    # Public base URL that serves the media bucket (CDN in production).
    media_public_base_url: str = "http://localhost:8333/product-media"
    max_image_bytes: int = 10 * 1024 * 1024

    default_currency: str = "INR"
    # Flat delivery charge in minor units (decision 8 default: free delivery).
    shipping_fee_minor: int = 0

    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    # Failed sign-ins allowed from one address (across all accounts) in the same window.
    login_ip_rate_limit_attempts: int = 30

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
