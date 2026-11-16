from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import ENTITY_NAME_MAX_LENGTH, ENTITY_NAME_MIN_LENGTH
from app.models.enums import ProjectStatus
from app.schemas.base import BaseSchema


class ProjectCreate(BaseSchema):
    """Payload for creating a new project inside a workspace."""

    name: str = Field(
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
        description="Project name.",
        examples=["Q4 Backend Roadmap"],
    )
    description: str | None = Field(
        default=None,
        description="Optional project description.",
        examples=["Deliver authentication, RBAC, and Redis caching"],
    )


class ProjectUpdate(BaseSchema):
    """Payload for updating or archiving an existing project."""

    name: str | None = Field(
        default=None,
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
        description="Updated project name.",
        examples=["Q4 Backend Roadmap (Completed)"],
    )
    description: str | None = Field(
        default=None,
        description="Updated project description.",
        examples=["All Q4 milestones completed"],
    )
    status: ProjectStatus | None = Field(
        default=None,
        description=(
            "Project lifecycle status (`ACTIVE` or `ARCHIVED`). "
            "Archived projects reject new tasks."
        ),
        examples=[ProjectStatus.ARCHIVED],
    )

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for field_name in ("name", "status"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class ProjectResponse(BaseModel):
    """Project representation returned in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique project UUID.")
    workspace_id: UUID = Field(description="Parent workspace UUID.")
    name: str = Field(description="Project name.")
    description: str | None = Field(description="Project description.")
    status: ProjectStatus = Field(description="Project status (`ACTIVE` or `ARCHIVED`).")
    created_at: datetime = Field(description="Project creation UTC timestamp.")
    updated_at: datetime = Field(description="Last project update UTC timestamp.")

