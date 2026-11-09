from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_JWT_ALGORITHM,
    DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS,
    MIN_SECRET_KEY_LENGTH,
)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="TaskHub API", validation_alias="APP_NAME")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    database_url: str = Field(
        default="postgresql+asyncpg://localhost:5432/taskhub",
        validation_alias="DATABASE_URL",
        min_length=1,
    )
    test_database_url: str | None = Field(
        default=None,
        validation_alias="TEST_DATABASE_URL",
    )
    jwt_secret_key: str = Field(
        default="taskhub-dev-secret-key-must-be-at-least-32-bytes-long",
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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
