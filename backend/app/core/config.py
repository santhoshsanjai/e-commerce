from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# Only for local development and tests; refused in every deployed environment.
LOCAL_DEV_JWT_SECRET = "local-dev-only-jwt-secret-do-not-deploy"  # noqa: S105
LOCAL_DEV_MFA_KEY = "bG9jYWwtZGV2LW9ubHktbWZhLWtleS1ub3QtcmVhbCE="


class Settings(BaseSettings):
    """Application settings, read from environment variables (and `.env` in development)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "test", "dev", "staging", "production"] = "local"
    app_name: str = "E-Commerce API"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ecommerce"
    # On AWS the connection comes in parts instead (the password from the RDS-managed secret, so it
    # can rotate). When DB_HOST is set, these build database_url.
    db_host: str | None = None
    db_port: int = 5432
    db_name: str = "ecommerce"
    db_user: str | None = None
    db_password: str | None = None
    db_sslmode: str = "require"

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
    max_video_bytes: int = 100 * 1024 * 1024

    default_currency: str = "INR"
    # Flat delivery charge in minor units (decision 8 default: free delivery).
    shipping_fee_minor: int = 0

    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    # Failed sign-ins allowed from one address (across all accounts) in the same window.
    login_ip_rate_limit_attempts: int = 30

    # Outgoing email (see app.infrastructure.email).
    email_backend: Literal["console", "smtp", "ses"] = "console"
    email_from: str = "Shop <no-reply@example.com>"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_starttls: bool = False
    smtp_username: str | None = None
    smtp_password: str | None = None
    ses_region: str | None = None
    # Where links in emails point (password reset).
    buyer_site_url: str = "http://localhost:4200"
    admin_site_url: str = "http://localhost:4300"
    password_reset_ttl_minutes: int = 30

    # Two-step sign-in for staff. The key (a Fernet key) encrypts authenticator secrets in the
    # database. Make one with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    staff_mfa_required: bool = True
    mfa_encryption_key: str = LOCAL_DEV_MFA_KEY
    mfa_issuer: str = "Shop Admin"

    @model_validator(mode="after")
    def _build_database_url(self) -> "Settings":
        if self.db_host:
            self.database_url = URL.create(
                "postgresql+psycopg",
                username=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                query={"sslmode": self.db_sslmode},
            ).render_as_string(hide_password=False)
        return self

    @model_validator(mode="after")
    def _require_real_secret_when_deployed(self) -> "Settings":
        if self.environment not in ("local", "test") and self.jwt_secret == LOCAL_DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set for deployed environments")
        if (
            self.environment not in ("local", "test")
            and LOCAL_DEV_MFA_KEY in self.mfa_encryption_key
        ):
            raise ValueError("MFA_ENCRYPTION_KEY must be set for deployed environments")
        if self.environment not in ("local", "test") and self.s3_access_key == "local":
            raise ValueError("S3_ACCESS_KEY must be empty (use the IAM role) when deployed")
        if self.is_production and not self.staff_mfa_required:
            raise ValueError("STAFF_MFA_REQUIRED must be true in production")
        if self.is_production and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production")
        if self.is_production and self.email_backend == "console":
            raise ValueError("EMAIL_BACKEND must be smtp or ses in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
