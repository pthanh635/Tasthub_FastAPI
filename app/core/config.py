import os
from functools import lru_cache
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_API_V1_PREFIX,
    DEFAULT_APP_VERSION,
    DEFAULT_JWT_ALGORITHM,
    DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS,
    INSECURE_PLACEHOLDER_SECRETS,
    MIN_SECRET_KEY_LENGTH,
    SUPPORTED_DB_URL_PREFIXES,
    SUPPORTED_JWT_ALGORITHMS,
    SUPPORTED_REDIS_URL_PREFIXES,
    AppEnvironment,
)


def resolve_env_files(app_env: str | None = None) -> tuple[str, ...]:
    """Resolve layered .env files for the active environment.

    Order of precedence (later files override earlier ones, OS env vars win):
    1. `.env` (base local defaults)
    2. `.env.<app_env>` (environment-specific overrides, e.g. `.env.testing`)
    """
    env_name = (app_env or os.getenv("APP_ENV") or AppEnvironment.DEVELOPMENT.value).strip().lower()
    return (".env", f".env.{env_name}")


class Settings(BaseSettings):
    """Application configuration with multi-environment loading and fail-fast validation."""

    model_config = SettingsConfigDict(
        env_file=resolve_env_files(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )

    app_env: AppEnvironment = Field(
        default=AppEnvironment.DEVELOPMENT,
        validation_alias="APP_ENV",
    )
    app_name: str = Field(
        default="TaskHub API",
        validation_alias="APP_NAME",
        min_length=1,
    )
    app_version: str = Field(
        default=DEFAULT_APP_VERSION,
        validation_alias="APP_VERSION",
        min_length=1,
    )
    api_v1_prefix: str = Field(
        default=DEFAULT_API_V1_PREFIX,
        validation_alias="API_V1_PREFIX",
        min_length=1,
    )
    debug: bool = Field(
        default=False,
        validation_alias="DEBUG",
    )
    docs_enabled: bool = Field(
        default=True,
        validation_alias="DOCS_ENABLED",
    )
    database_url: str = Field(
        default="postgresql+asyncpg://localhost:5432/taskhub",
        validation_alias="DATABASE_URL",
        min_length=1,
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
        min_length=1,
    )
    cache_ttl_seconds: int = Field(
        default=30,
        validation_alias="CACHE_TTL_SECONDS",
        ge=0,
    )
    test_database_url: str | None = Field(
        default=None,
        validation_alias="TEST_DATABASE_URL",
    )
    jwt_secret_key: str = Field(
        validation_alias="JWT_SECRET_KEY",
        min_length=MIN_SECRET_KEY_LENGTH,
    )
    jwt_algorithm: str = Field(
        default=DEFAULT_JWT_ALGORITHM,
        validation_alias="JWT_ALGORITHM",
        min_length=1,
    )
    access_token_expire_minutes: int = Field(
        default=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
        gt=0,
    )
    refresh_token_expire_days: int = Field(
        default=DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS,
        validation_alias="REFRESH_TOKEN_EXPIRE_DAYS",
        gt=0,
    )
    seed_admin_email: str = Field(
        default="owner@taskhub.dev",
        validation_alias="SEED_ADMIN_EMAIL",
    )
    seed_admin_password: str | None = Field(
        default=None,
        validation_alias="SEED_ADMIN_PASSWORD",
        min_length=12,
    )

    @property
    def is_development(self) -> bool:
        return self.app_env == AppEnvironment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.app_env == AppEnvironment.TESTING

    @property
    def is_staging(self) -> bool:
        return self.app_env == AppEnvironment.STAGING

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnvironment.PRODUCTION

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/'")
        return cleaned.rstrip("/") or "/"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith(SUPPORTED_DB_URL_PREFIXES):
            allowed = ", ".join(SUPPORTED_DB_URL_PREFIXES)
            raise ValueError(f"DATABASE_URL must start with one of: {allowed}")
        return cleaned

    @field_validator("test_database_url")
    @classmethod
    def validate_test_database_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not cleaned.startswith(SUPPORTED_DB_URL_PREFIXES):
            allowed = ", ".join(SUPPORTED_DB_URL_PREFIXES)
            raise ValueError(f"TEST_DATABASE_URL must start with one of: {allowed}")
        return cleaned

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith(SUPPORTED_REDIS_URL_PREFIXES):
            allowed = ", ".join(SUPPORTED_REDIS_URL_PREFIXES)
            raise ValueError(f"REDIS_URL must start with one of: {allowed}")
        return cleaned

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if cleaned not in SUPPORTED_JWT_ALGORITHMS:
            allowed = ", ".join(sorted(SUPPORTED_JWT_ALGORITHMS))
            raise ValueError(f"JWT_ALGORITHM must be one of: {allowed}")
        return cleaned

    @model_validator(mode="after")
    def validate_environment_constraints(self) -> Self:
        if self.test_database_url and self.test_database_url == self.database_url:
            raise ValueError(
                "TEST_DATABASE_URL must not point to the same database as DATABASE_URL"
            )

        if self.is_production:
            if self.debug:
                raise ValueError("DEBUG must be False when APP_ENV is 'production'")
            if self.jwt_secret_key in INSECURE_PLACEHOLDER_SECRETS:
                raise ValueError(
                    "JWT_SECRET_KEY must not use an example placeholder value in production"
                )
            if ":changeme@" in self.database_url:
                raise ValueError(
                    "DATABASE_URL must not use default 'changeme' credentials in production"
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file=resolve_env_files())


settings = get_settings()

