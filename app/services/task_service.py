from uuid import UUID

from app.core.exceptions import (
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate


class TaskService:
    """Business logic layer for Task management."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def create(
        self,
        data: TaskCreate,
        *,
        created_by_id: UUID | None = None,
    ) -> TaskResponse:
        project_owner_id = await self._repository.get_project_owner_id(data.project_id)
        if project_owner_id is None:
            raise ProjectNotFoundError(data.project_id)

        creator_id = created_by_id if created_by_id is not None else project_owner_id
        if created_by_id is not None and created_by_id != project_owner_id:
            if not await self._repository.user_exists(created_by_id):
                raise UserNotFoundError(created_by_id)

        if data.assignee_id is not None:
            if not await self._repository.user_exists(data.assignee_id):
                raise UserNotFoundError(data.assignee_id)

        payload: dict[str, object] = {
            **data.model_dump(),
            "created_by_id": creator_id,
        }
        task = await self._repository.create(payload)
        return TaskResponse.model_validate(task)

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[TaskResponse]:
        tasks = await self._repository.get_all(offset=offset, limit=limit)
        return [TaskResponse.model_validate(task) for task in tasks]

    async def get(self, task_id: UUID) -> TaskResponse:
        task = await self._repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return TaskResponse.model_validate(task)

    async def replace(self, task_id: UUID, data: TaskUpdate) -> TaskResponse:
        task = await self._repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        if data.assignee_id is not None:
            if not await self._repository.user_exists(data.assignee_id):
                raise UserNotFoundError(data.assignee_id)

        updated = await self._repository.update(task, data.model_dump())
        return TaskResponse.model_validate(updated)

    async def delete(self, task_id: UUID) -> None:
        task = await self._repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        await self._repository.delete(task)
