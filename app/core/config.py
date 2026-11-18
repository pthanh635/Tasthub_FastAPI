import os
import re
from functools import lru_cache
from typing import Any, Self

from dotenv import dotenv_values
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.core.constants import (
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_API_V1_PREFIX,
    DEFAULT_APP_VERSION,
    DEFAULT_JWT_ALGORITHM,
    DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS,
    ENV_FILE_NAME,
    ENV_FILE_PREFIX,
    INSECURE_PLACEHOLDER_SECRETS,
    MIN_SECRET_KEY_LENGTH,
    PLACEHOLDER_CREDENTIAL_PATTERN,
    SUPPORTED_DB_URL_PREFIXES,
    SUPPORTED_JWT_ALGORITHMS,
    SUPPORTED_REDIS_URL_PREFIXES,
    AppEnvironment,
)
from app.core.messages import ErrorMessages


def resolve_env_files(app_env: str | None = None) -> tuple[str, ...]:
    """Resolve layered .env files for the active environment.

    Order of precedence (later files override earlier ones, OS env vars win):
    1. `.env` (base local defaults)
    2. `.env.<app_env>` (environment-specific overrides, e.g. `.env.testing`)
    """
    base_values = dotenv_values(ENV_FILE_NAME)
    env_name = (
        app_env
        or os.getenv("APP_ENV")
        or base_values.get("APP_ENV")
        or AppEnvironment.DEVELOPMENT.value
    )
    env_name = str(env_name).strip().lower()
    return (ENV_FILE_NAME, f"{ENV_FILE_PREFIX}{env_name}")


def _contains_placeholder(value: str | None) -> bool:
    return bool(value and re.search(PLACEHOLDER_CREDENTIAL_PATTERN, value, re.IGNORECASE))


class Settings(BaseSettings):
    """Application configuration with multi-environment loading and fail-fast validation."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    def __init__(self, **values: Any) -> None:
        if "_env_file" not in values:
            base_values = dotenv_values(ENV_FILE_NAME)
            bootstrap_env = (
                os.getenv("APP_ENV")
                or base_values.get("APP_ENV")
                or AppEnvironment.DEVELOPMENT.value
            )
            values["_env_file"] = resolve_env_files(str(bootstrap_env))
        super().__init__(**values)

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
            raise ValueError(ErrorMessages.API_PREFIX_MUST_START_WITH_SLASH)
        return cleaned.rstrip("/") or "/"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith(SUPPORTED_DB_URL_PREFIXES):
            allowed = ", ".join(SUPPORTED_DB_URL_PREFIXES)
            raise ValueError(f"{ErrorMessages.DATABASE_URL_UNSUPPORTED_SCHEME}: {allowed}")
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
            raise ValueError(
                f"{ErrorMessages.TEST_DATABASE_URL_UNSUPPORTED_SCHEME}: {allowed}"
            )
        return cleaned

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith(SUPPORTED_REDIS_URL_PREFIXES):
            allowed = ", ".join(SUPPORTED_REDIS_URL_PREFIXES)
            raise ValueError(f"{ErrorMessages.REDIS_URL_UNSUPPORTED_SCHEME}: {allowed}")
        return cleaned

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if cleaned not in SUPPORTED_JWT_ALGORITHMS:
            allowed = ", ".join(sorted(SUPPORTED_JWT_ALGORITHMS))
            raise ValueError(f"{ErrorMessages.JWT_ALGORITHM_UNSUPPORTED}: {allowed}")
        return cleaned

    @model_validator(mode="after")
    def validate_environment_constraints(self) -> Self:
        if self.test_database_url and self.test_database_url == self.database_url:
            raise ValueError(ErrorMessages.TEST_DATABASE_URL_MUST_DIFFER)

        if self.is_production:
            if self.debug:
                raise ValueError(ErrorMessages.PRODUCTION_DEBUG_DISABLED)
            if (
                self.jwt_secret_key in INSECURE_PLACEHOLDER_SECRETS
                or _contains_placeholder(self.jwt_secret_key)
            ):
                raise ValueError(ErrorMessages.PRODUCTION_JWT_SECRET_PLACEHOLDER)
            database_password = make_url(self.database_url).password
            if _contains_placeholder(database_password):
                raise ValueError(ErrorMessages.PRODUCTION_DATABASE_PASSWORD_PLACEHOLDER)
            if not self.seed_admin_password:
                raise ValueError(ErrorMessages.PRODUCTION_SEED_ADMIN_PASSWORD_REQUIRED)
            if _contains_placeholder(self.seed_admin_password):
                raise ValueError(ErrorMessages.PRODUCTION_SEED_ADMIN_PASSWORD_PLACEHOLDER)

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file=resolve_env_files())


settings = get_settings()

