from datetime import UTC, datetime
from typing import Self
from uuid import UUID

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.constants import ENTITY_NAME_MAX_LENGTH, ENTITY_NAME_MIN_LENGTH
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.auth import StrippedBaseModel


class TaskBase(StrippedBaseModel):
    title: str = Field(
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
    )
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def ensure_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class ProjectTaskCreate(TaskBase):
    """Schema for creating a new Task inside a specific project (/projects/{id}/tasks)."""


class TaskCreate(TaskBase):
    """Schema for creating a new Task via /tasks."""

    project_id: UUID


class TaskUpdate(TaskBase):
    """Schema for replacing all editable fields of an existing Task via PUT."""


class TaskPatch(StrippedBaseModel):
    """Schema for partially updating a Task via PATCH."""

    title: str | None = Field(
        default=None,
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
    )
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: UUID | None = None
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def ensure_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for field_name in ("title", "status", "priority"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class TaskResponse(TaskBase):
    """Schema returned in Task API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime


TaskRead = TaskResponse
