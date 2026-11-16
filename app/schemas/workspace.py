from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import ENTITY_NAME_MAX_LENGTH, ENTITY_NAME_MIN_LENGTH
from app.models.enums import WorkspaceRole
from app.schemas.base import BaseSchema


class WorkspaceCreate(BaseSchema):
    """Payload for creating a new workspace. The creator automatically becomes OWNER."""

    name: str = Field(
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
        description="Display name of the workspace.",
        examples=["Platform Engineering"],
    )
    description: str | None = Field(
        default=None,
        description="Optional summary describing the workspace purpose.",
        examples=["Core backend services and infrastructure tasks"],
    )


class WorkspaceUpdate(BaseSchema):
    """Payload for updating workspace metadata (OWNER or global ADMIN only)."""

    name: str | None = Field(
        default=None,
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
        description="Updated workspace name.",
        examples=["Core Platform Engineering"],
    )
    description: str | None = Field(
        default=None,
        description="Updated workspace description.",
        examples=["Updated workspace description"],
    )

    @model_validator(mode="after")
    def reject_explicit_null_name(self) -> Self:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class WorkspaceResponse(BaseModel):
    """Workspace representation returned in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique workspace UUID.")
    name: str = Field(description="Workspace name.")
    description: str | None = Field(description="Workspace description.")
    owner_id: UUID = Field(description="UUID of the workspace OWNER user.")
    created_at: datetime = Field(description="Workspace creation UTC timestamp.")
    updated_at: datetime = Field(description="Last workspace update UTC timestamp.")


class WorkspaceMemberCreate(BaseModel):
    """Payload for inviting a user to a workspace or updating their workspace role."""

    user_id: UUID = Field(
        description="UUID of the user to invite or update in the workspace.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    role: WorkspaceRole = Field(
        default=WorkspaceRole.VIEWER,
        description="Assigned workspace role (`ADMIN`, `EDITOR`, or `VIEWER`).",
        examples=[WorkspaceRole.EDITOR],
    )


class WorkspaceMemberResponse(BaseModel):
    """Workspace membership record returned in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique membership record UUID.")
    workspace_id: UUID = Field(description="Workspace UUID.")
    user_id: UUID = Field(description="Member user UUID.")
    role: WorkspaceRole = Field(description="Member role inside the workspace.")
    joined_at: datetime = Field(description="UTC timestamp when the user joined.")

