from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.constants import (
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
    USER_FULL_NAME_MAX_LENGTH,
    USER_FULL_NAME_MIN_LENGTH,
)
from app.core.messages import ErrorMessages
from app.models.enums import UserRole
from app.schemas.base import BaseSchema, validate_password_byte_length


class UserResponse(BaseModel):
    """Public user profile representation (excludes hashed_password)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        description="Unique user UUID.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    email: EmailStr = Field(
        description="Normalized lowercase user email address.",
        examples=["developer@taskhub.dev"],
    )
    full_name: str = Field(
        description="User display name.",
        examples=["Nguyen Van A"],
    )
    role: UserRole = Field(
        description="Global platform role (`ADMIN` or `MEMBER`).",
        examples=[UserRole.MEMBER],
    )
    is_active: bool = Field(
        description="Whether the user account is active and allowed to authenticate.",
        examples=[True],
    )
    created_at: datetime = Field(description="Account creation UTC timestamp.")
    updated_at: datetime = Field(description="Last profile modification UTC timestamp.")


class UserUpdate(BaseSchema):
    """Schema for updating the current user's profile via PATCH /users/me."""

    full_name: str | None = Field(
        default=None,
        min_length=USER_FULL_NAME_MIN_LENGTH,
        max_length=USER_FULL_NAME_MAX_LENGTH,
        description="Updated display name for the current user.",
        examples=["Nguyen Van B"],
    )

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        if "full_name" in self.model_fields_set and self.full_name is None:
            raise ValueError(
                ErrorMessages.FIELD_CANNOT_BE_NULL.format(field_name="full_name")
            )
        return self


class AdminUserUpdate(BaseSchema):
    """Schema for global ADMIN updating a user's profile, role, or active status."""

    full_name: str | None = Field(
        default=None,
        min_length=USER_FULL_NAME_MIN_LENGTH,
        max_length=USER_FULL_NAME_MAX_LENGTH,
        description="Updated user display name.",
        examples=["Nguyen Van B"],
    )
    role: UserRole | None = Field(
        default=None,
        description="Updated global platform role (`ADMIN` or `MEMBER`).",
        examples=[UserRole.ADMIN],
    )
    is_active: bool | None = Field(
        default=None,
        description=(
            "Account activation flag. Setting to `false` revokes all active refresh tokens."
        ),
        examples=[True],
    )

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for field_name in ("full_name", "role", "is_active"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(ErrorMessages.FIELD_CANNOT_BE_NULL.format(field_name=field_name))
        return self


class ChangePasswordRequest(BaseModel):
    """Schema for changing the current user's password. Whitespaces are strictly preserved."""

    current_password: str = Field(
        min_length=1,
        max_length=PASSWORD_MAX_BYTES,
        description="Current account password for verification.",
        examples=["OldStrongPass123!"],
    )
    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_BYTES,
        description="New password (8 to 72 UTF-8 bytes, must differ from current_password).",
        examples=["NewStrongPass456!"],
    )

    @field_validator("current_password", "new_password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return validate_password_byte_length(value)

