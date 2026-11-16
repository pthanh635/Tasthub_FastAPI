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

    email: EmailStr = Field(
        max_length=EMAIL_MAX_LENGTH,
        description="Unique user email address (normalized to lowercase).",
        examples=["developer@taskhub.dev"],
    )
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_BYTES,
        description="Account password (8 to 72 UTF-8 bytes).",
        examples=["StrongPass123!"],
    )
    full_name: str = Field(
        min_length=USER_FULL_NAME_MIN_LENGTH,
        max_length=USER_FULL_NAME_MAX_LENGTH,
        description="Display name of the user.",
        examples=["Nguyen Van A"],
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

    email: EmailStr = Field(
        max_length=EMAIL_MAX_LENGTH,
        description="Registered user email address.",
        examples=["developer@taskhub.dev"],
    )
    password: str = Field(
        min_length=1,
        max_length=PASSWORD_MAX_BYTES,
        description="Account password.",
        examples=["StrongPass123!"],
    )

    @field_validator("email")
    @classmethod
    def strip_email(cls, value: str) -> str:
        return value.strip()

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return validate_password_byte_length(value)


class TokenResponse(BaseModel):
    """JWT access and refresh token pair issued upon login or token rotation."""

    access_token: str = Field(
        description="Short-lived JWT access token (`type=access`) used in Authorization header.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        description="Long-lived single-use JWT refresh token (`type=refresh`) for token rotation.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="OAuth2 token scheme.",
        examples=["bearer"],
    )


class RefreshTokenRequest(BaseSchema):
    """Payload for rotating an active refresh token into a new JWT pair."""

    refresh_token: str = Field(
        min_length=1,
        description="Active JWT refresh token (`type=refresh`) to rotate.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )


class LogoutRequest(BaseSchema):
    """Payload for revoking a refresh token during logout."""

    refresh_token: str = Field(
        min_length=1,
        description="Refresh token owned by the authenticated user to revoke.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )

