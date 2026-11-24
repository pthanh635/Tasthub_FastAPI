from datetime import UTC, datetime
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.constants import ENTITY_NAME_MAX_LENGTH, ENTITY_NAME_MIN_LENGTH
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.base import BaseSchema


class TaskCreate(BaseSchema):
    """Schema for creating a new Task. Status is initialized by server to TODO."""

    project_id: UUID
    title: str = Field(
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
    )
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def ensure_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class ProjectTaskCreate(BaseSchema):
    """Schema for creating a Task inside a specific project path."""

    title: str = Field(
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
    )
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def ensure_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class TaskUpdate(BaseSchema):
    """Schema for replacing all editable fields of an existing Task via PUT."""

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


class TaskPatch(BaseSchema):
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


class TaskResponse(BaseModel):
    """Schema returned in Task API responses (independent from input schemas)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: UUID | None
    created_by_id: UUID
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Paginated task response schema containing items and total count."""

    items: list[TaskResponse]
    total: int
    offset: int
    limit: int


TaskRead = TaskResponse
