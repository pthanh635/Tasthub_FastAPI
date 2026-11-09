from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import ENTITY_NAME_MAX_LENGTH, ENTITY_NAME_MIN_LENGTH
from app.models.enums import WorkspaceRole
from app.schemas.auth import StrippedBaseModel


class WorkspaceCreate(StrippedBaseModel):
    name: str = Field(
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
    )
    description: str | None = None


class WorkspaceUpdate(StrippedBaseModel):
    name: str | None = Field(
        default=None,
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
    )
    description: str | None = None

    @model_validator(mode="after")
    def reject_explicit_null_name(self) -> Self:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class WorkspaceMemberCreate(BaseModel):
    user_id: UUID
    role: WorkspaceRole = WorkspaceRole.VIEWER


class WorkspaceMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    joined_at: datetime
