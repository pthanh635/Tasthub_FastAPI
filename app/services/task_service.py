from collections.abc import Collection
from uuid import UUID

from app.core.constants import DEFAULT_PAGE_LIMIT
from app.core.exceptions import (
    BadRequestError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.core.messages import ErrorMessages
from app.core.policies import (
    ALL_WORKSPACE_ROLES,
    WRITER_WORKSPACE_ROLES,
    ensure_task_delete_permission,
    ensure_workspace_role,
)
from app.models.enums import ProjectStatus, TaskStatus, UserRole, WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.repositories.task_repository import TaskRepository
from app.schemas.task import (
    ProjectTaskCreate,
    TaskCreate,
    TaskListResponse,
    TaskPatch,
    TaskResponse,
    TaskUpdate,
)


class TaskService:
    """Business logic layer for Task management with RBAC and resource ownership."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def create(
        self,
        data: TaskCreate,
        *,
        current_user: User,
    ) -> TaskResponse:
        project = await self._repository.get_project(data.project_id)
        if project is None:
            raise ProjectNotFoundError(data.project_id)

        if project.status == ProjectStatus.ARCHIVED:
            raise BadRequestError(ErrorMessages.PROJECT_ARCHIVED)

        await self._authorize_workspace_access(
            project.workspace_id,
            current_user=current_user,
            allowed_roles=WRITER_WORKSPACE_ROLES,
        )

        await self._validate_assignee(
            data.assignee_id,
            workspace_id=project.workspace_id,
        )

        payload: dict[str, object] = {
            **data.model_dump(),
            "status": TaskStatus.TODO,
            "created_by_id": current_user.id,
        }
        task = await self._repository.create(payload)
        await self._repository.commit()
        return TaskResponse.model_validate(task)

    async def create_in_project(
        self,
        project_id: UUID,
        data: ProjectTaskCreate,
        *,
        current_user: User,
    ) -> TaskResponse:
        full_create = TaskCreate(project_id=project_id, **data.model_dump())
        return await self.create(full_create, current_user=current_user)

    async def list_all(
        self,
        *,
        current_user: User,
        project_id: UUID | None = None,
        offset: int = 0,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> TaskListResponse:
        if project_id is not None:
            project = await self._repository.get_project(project_id)
            if project is None:
                raise ProjectNotFoundError(project_id)
            await self._authorize_workspace_access(
                project.workspace_id,
                current_user=current_user,
                allowed_roles=ALL_WORKSPACE_ROLES,
            )

        tasks, total = await self._repository.list_accessible_for_user(
            current_user.id,
            is_global_admin=(current_user.role == UserRole.ADMIN),
            project_id=project_id,
            offset=offset,
            limit=limit,
        )
        return TaskListResponse(
            items=[TaskResponse.model_validate(task) for task in tasks],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def get(
        self,
        task_id: UUID,
        *,
        current_user: User,
    ) -> TaskResponse:
        task, project = await self._get_task_and_project(task_id)
        await self._authorize_workspace_access(
            project.workspace_id,
            current_user=current_user,
            allowed_roles=ALL_WORKSPACE_ROLES,
        )
        return TaskResponse.model_validate(task)

    async def replace(
        self,
        task_id: UUID,
        data: TaskUpdate,
        *,
        current_user: User,
    ) -> TaskResponse:
        task, project = await self._get_task_and_project(task_id)
        await self._authorize_workspace_access(
            project.workspace_id,
            current_user=current_user,
            allowed_roles=WRITER_WORKSPACE_ROLES,
        )

        await self._validate_assignee(
            data.assignee_id,
            workspace_id=project.workspace_id,
        )

        updated = await self._repository.update(task, data.model_dump())
        await self._repository.commit()
        return TaskResponse.model_validate(updated)

    async def patch(
        self,
        task_id: UUID,
        data: TaskPatch,
        *,
        current_user: User,
    ) -> TaskResponse:
        task, project = await self._get_task_and_project(task_id)
        await self._authorize_workspace_access(
            project.workspace_id,
            current_user=current_user,
            allowed_roles=WRITER_WORKSPACE_ROLES,
        )

        changes = data.model_dump(exclude_unset=True)
        if "assignee_id" in changes:
            assignee_val = changes["assignee_id"]
            if isinstance(assignee_val, UUID) or assignee_val is None:
                await self._validate_assignee(
                    assignee_val,
                    workspace_id=project.workspace_id,
                )

        if changes:
            task = await self._repository.update(task, changes)
            await self._repository.commit()
        return TaskResponse.model_validate(task)

    async def delete(
        self,
        task_id: UUID,
        *,
        current_user: User,
    ) -> None:
        task, project = await self._get_task_and_project(task_id)
        member_role = await self._repository.get_workspace_member_role(
            project.workspace_id,
            current_user.id,
        )
        ensure_task_delete_permission(
            current_user,
            member_role,
            task.created_by_id,
        )
        await self._repository.delete(task)
        await self._repository.commit()

    async def _get_task_and_project(self, task_id: UUID) -> tuple[Task, Project]:
        task = await self._repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        project = await self._repository.get_project(task.project_id)
        if project is None:
            raise ProjectNotFoundError(task.project_id)
        return task, project

    async def _validate_assignee(
        self,
        assignee_id: UUID | None,
        *,
        workspace_id: UUID,
    ) -> None:
        if assignee_id is None:
            return
        if not await self._repository.user_exists(assignee_id):
            raise UserNotFoundError(assignee_id)
        role = await self._repository.get_workspace_member_role(
            workspace_id,
            assignee_id,
        )
        if role is None:
            raise BadRequestError(ErrorMessages.ASSIGNEE_NOT_IN_WORKSPACE)

    async def _authorize_workspace_access(
        self,
        workspace_id: UUID,
        *,
        current_user: User,
        allowed_roles: Collection[WorkspaceRole],
    ) -> None:
        member_role = await self._repository.get_workspace_member_role(
            workspace_id,
            current_user.id,
        )
        ensure_workspace_role(current_user, member_role, allowed_roles)
