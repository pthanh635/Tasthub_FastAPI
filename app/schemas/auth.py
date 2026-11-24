from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import (
    EMAIL_MAX_LENGTH,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
    USER_FULL_NAME_MAX_LENGTH,
    USER_FULL_NAME_MIN_LENGTH,
)
from app.schemas.base import BaseSchema, validate_password_byte_length


class RegisterRequest(BaseModel):
    """Registration payload. Password whitespaces are preserved; email & full_name are stripped."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH)
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_BYTES,
    )
    full_name: str = Field(
        min_length=USER_FULL_NAME_MIN_LENGTH,
        max_length=USER_FULL_NAME_MAX_LENGTH,
    )

    @field_validator("email", "full_name")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return validate_password_byte_length(value)


class LoginRequest(BaseModel):
    """Login payload. Password whitespaces are strictly preserved."""

    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_BYTES)

    @field_validator("email")
    @classmethod
    def strip_email(cls, value: str) -> str:
        return value.strip()

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return validate_password_byte_length(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseSchema):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseSchema):
    refresh_token: str = Field(min_length=1)
