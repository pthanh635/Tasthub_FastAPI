from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import (
    EMAIL_MAX_LENGTH,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
    USER_FULL_NAME_MAX_LENGTH,
    USER_FULL_NAME_MIN_LENGTH,
)


def validate_password_byte_length(value: str) -> str:
    """Ensure password does not exceed bcrypt's 72 UTF-8 byte limit."""
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(
            f"Password must not exceed {PASSWORD_MAX_BYTES} bytes in UTF-8 encoding"
        )
    return value


class StrippedBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class RegisterRequest(StrippedBaseModel):
    """Registration payload. Role selection by client is strictly forbidden."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH)
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_BYTES,
    )
    full_name: str = Field(
        min_length=USER_FULL_NAME_MIN_LENGTH,
        max_length=USER_FULL_NAME_MAX_LENGTH,
    )

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return validate_password_byte_length(value)


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_BYTES)

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return validate_password_byte_length(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(StrippedBaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(StrippedBaseModel):
    refresh_token: str = Field(min_length=1)
