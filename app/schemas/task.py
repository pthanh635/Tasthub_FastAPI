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
from app.core.messages import ErrorMessages
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.base import BaseSchema


class TaskCreate(BaseSchema):
    """Schema for creating a new Task. Status is initialized by server to TODO."""

    project_id: UUID = Field(
        description="UUID of the active project this task belongs to.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    title: str = Field(
        min_length=ENTITY_NAME_MIN_LENGTH,
        max_length=ENTITY_NAME_MAX_LENGTH,
        description="Concise summary of the task.",
        examples=["Implement multi-environment Pydantic Settings"],
    )
    description: str | None = Field(
        default=None,
        description="Detailed markdown description or acceptance criteria.",
        examples=["Add fail-fast validation for production and test environments"],
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task priority level (`LOW`, `MEDIUM`, `HIGH`, `URGENT`).",
        examples=[TaskPriority.HIGH],
    )
    assignee_id: UUID | None = Field(
        default=None,
        description="Optional UUID of a workspace member assigned to this task.",
    )
    due_date: datetime | None = Field(
        default=None,
        description="Optional target completion timestamp (UTC).",
    )

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
        description="Concise summary of the task.",
        examples=["Document OpenAPI error responses"],
    )
    description: str | None = Field(
        default=None,
        description="Detailed description of the task.",
        examples=["Attach ErrorResponse models to all router endpoints"],
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task priority level (`LOW`, `MEDIUM`, `HIGH`, `URGENT`).",
        examples=[TaskPriority.MEDIUM],
    )
    assignee_id: UUID | None = Field(
        default=None,
        description="Optional UUID of a workspace member assigned to this task.",
    )
    due_date: datetime | None = Field(
        default=None,
        description="Optional target completion timestamp (UTC).",
    )

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
        description="Updated task title.",
        examples=["Implement multi-environment Pydantic Settings (Reviewed)"],
    )
    description: str | None = Field(
        default=None,
        description="Updated task description.",
    )
    status: TaskStatus = Field(
        default=TaskStatus.TODO,
        description="Task workflow status (`TODO`, `IN_PROGRESS`, `IN_REVIEW`, `DONE`).",
        examples=[TaskStatus.IN_PROGRESS],
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task priority level (`LOW`, `MEDIUM`, `HIGH`, `URGENT`).",
        examples=[TaskPriority.HIGH],
    )
    assignee_id: UUID | None = Field(
        default=None,
        description="UUID of the assigned workspace member (or `null` to unassign).",
    )
    due_date: datetime | None = Field(
        default=None,
        description="Target completion timestamp (UTC).",
    )

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
        description="Updated task title (cannot be null if provided).",
    )
    description: str | None = Field(
        default=None,
        description="Updated task description (can be null to clear).",
    )
    status: TaskStatus | None = Field(
        default=None,
        description="Updated workflow status (`TODO`, `IN_PROGRESS`, `IN_REVIEW`, `DONE`).",
    )
    priority: TaskPriority | None = Field(
        default=None,
        description="Updated priority (`LOW`, `MEDIUM`, `HIGH`, `URGENT`).",
    )
    assignee_id: UUID | None = Field(
        default=None,
        description="Updated assignee user UUID (or `null` to unassign).",
    )
    due_date: datetime | None = Field(
        default=None,
        description="Updated due date timestamp (or `null` to clear).",
    )

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
                raise ValueError(ErrorMessages.FIELD_CANNOT_BE_NULL.format(field_name=field_name))
        return self


class TaskResponse(BaseModel):
    """Schema returned in Task API responses (independent from input schemas)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique task UUID.")
    project_id: UUID = Field(description="Parent project UUID.")
    title: str = Field(description="Task title.")
    description: str | None = Field(description="Task description.")
    status: TaskStatus = Field(description="Current workflow status.")
    priority: TaskPriority = Field(description="Task priority level.")
    assignee_id: UUID | None = Field(description="Assigned workspace member UUID.")
    created_by_id: UUID = Field(description="UUID of the user who created the task.")
    due_date: datetime | None = Field(description="Target completion UTC timestamp.")
    created_at: datetime = Field(description="Task creation UTC timestamp.")
    updated_at: datetime = Field(description="Last task update UTC timestamp.")


class TaskListResponse(BaseModel):
    """Paginated task response schema containing items and total count."""

    items: list[TaskResponse] = Field(description="List of tasks for the current page.")
    total: int = Field(description="Total number of matching tasks.")
    offset: int = Field(description="Current pagination offset.")
    limit: int = Field(description="Maximum items returned per page.")



TaskRead = TaskResponse
