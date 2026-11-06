from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
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


class TaskCreate(TaskBase):
    """Schema for creating a new Task.

    `created_by_id` is intentionally excluded from client input in Day 2 to prevent
    identity spoofing before JWT Authentication (Day 3) is introduced; the service
    layer resolves `created_by_id` from the seeded project/workspace owner or test fixture.
    """

    project_id: UUID


class TaskUpdate(TaskBase):
    """Schema for replacing all editable fields of an existing Task via PUT."""


class TaskResponse(TaskBase):
    """Schema returned in Task API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime


TaskRead = TaskResponse
