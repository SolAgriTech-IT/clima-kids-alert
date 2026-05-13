"""Application configuration loaded from environment variables.

Secrets and integration keys are never embedded in source code; they are read
at runtime from the process environment (Docker Compose, systemd, or a
managed secret store on VPS deployments).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg2://clima:clima_secret_change_me@localhost:5432/clima_kids",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    # When false, the API skips the Redis→WebSocket subscriber and publish_event is a no-op
    # (suitable for mutualised hosting without Redis; users refresh the dashboard manually).
    use_redis: bool = Field(default=True, alias="USE_REDIS")
    # When false, admin "run pipeline" runs the task in-process instead of Celery (.delay).
    use_celery: bool = Field(default=True, alias="USE_CELERY")
    # If set to an existing directory, FastAPI serves the Next.js static export (output: "export") at /.
    static_site_dir: str | None = Field(default=None, alias="STATIC_SITE_DIR")

    jwt_secret: str = Field(
        default="dev_jwt_secret_change_in_production_min_32_chars",
        alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    cors_origins: str = Field(default="http://localhost", alias="CORS_ORIGINS")
    rate_limit_per_minute: int = Field(default=120, alias="RATE_LIMIT_PER_MINUTE")
    # When set, SlowAPI persists counters in Redis (required for multi-replica API rate limits).
    # Example: redis://redis:6379/1 (use a DB index separate from Celery broker DB 0)
    rate_limit_storage_uri: str | None = Field(default=None, alias="RATE_LIMIT_STORAGE_URI")

    # Sentinel Hub (Copernicus) — optional OAuth client credentials
    sentinel_hub_enabled: bool = Field(default=False, alias="SENTINEL_HUB_ENABLED")
    sentinel_hub_base_url: str = Field(default="https://services.sentinel-hub.com", alias="SENTINEL_HUB_BASE_URL")
    sentinel_hub_client_id: str = Field(default="", alias="SENTINEL_HUB_CLIENT_ID")
    sentinel_hub_client_secret: str = Field(default="", alias="SENTINEL_HUB_CLIENT_SECRET")

    # Google Earth Engine — optional sidecar HTTP bridge (recommended for production GEE usage)
    gee_bridge_url: str = Field(default="", alias="GEE_BRIDGE_URL")
    gee_bridge_token: str = Field(default="", alias="GEE_BRIDGE_TOKEN")

    openweathermap_api_key: str = Field(default="", alias="OPENWEATHERMAP_API_KEY")
    openaq_api_key: str = Field(default="", alias="OPENAQ_API_KEY")
    nasa_power_enabled: bool = Field(default=True, alias="NASA_POWER_ENABLED")

    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_sms_from: str = Field(default="", alias="TWILIO_SMS_FROM")
    twilio_whatsapp_from: str = Field(default="", alias="TWILIO_WHATSAPP_FROM")

    sendgrid_api_key: str = Field(default="", alias="SENDGRID_API_KEY")
    email_from: str = Field(default="noreply@sol-agri-tech.org", alias="EMAIL_FROM")

    default_city_name: str = Field(default="Kolwezi", alias="DEFAULT_CITY_NAME")
    default_city_slug: str = Field(default="kolwezi", alias="DEFAULT_CITY_SLUG")
    default_lat: float = Field(default=-10.7147, alias="DEFAULT_LAT")
    default_lon: float = Field(default=25.4667, alias="DEFAULT_LON")

    seed_admin_email: str = Field(default="mulombodi@sol-agri-tech.org", alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str = Field(default="ChangeMeAfterFirstLogin!2026", alias="SEED_ADMIN_PASSWORD")
    # Dev only: when true, overwrites the seed admin password hash on every startup (fixes broken logins).
    seed_reset_admin_password: bool = Field(default=False, alias="SEED_RESET_ADMIN_PASSWORD")

    pipeline_interval_seconds: int = Field(default=300, alias="PIPELINE_INTERVAL_SECONDS")

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
