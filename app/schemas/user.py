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
from app.models.enums import UserRole
from app.schemas.base import BaseSchema, validate_password_byte_length


class UserResponse(BaseModel):
    """Public user profile representation (excludes hashed_password)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseSchema):
    """Schema for updating the current user's profile via PATCH /users/me."""

    full_name: str | None = Field(
        default=None,
        min_length=USER_FULL_NAME_MIN_LENGTH,
        max_length=USER_FULL_NAME_MAX_LENGTH,
    )

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        if "full_name" in self.model_fields_set and self.full_name is None:
            raise ValueError("full_name cannot be null")
        return self


class AdminUserUpdate(BaseSchema):
    """Schema for global ADMIN updating a user's profile, role, or active status."""

    full_name: str | None = Field(
        default=None,
        min_length=USER_FULL_NAME_MIN_LENGTH,
        max_length=USER_FULL_NAME_MAX_LENGTH,
    )
    role: UserRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for field_name in ("full_name", "role", "is_active"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class ChangePasswordRequest(BaseModel):
    """Schema for changing the current user's password. Whitespaces are strictly preserved."""

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_BYTES)
    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_BYTES,
    )

    @field_validator("current_password", "new_password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return validate_password_byte_length(value)
