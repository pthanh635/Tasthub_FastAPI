from collections.abc import Collection
from uuid import UUID

from app.core.exceptions import (
    BadRequestError,
    PermissionDeniedError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.core.messages import ErrorMessages
from app.models.enums import ProjectStatus, UserRole, WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.repositories.task_repository import TaskRepository
from app.schemas.task import (
    ProjectTaskCreate,
    TaskCreate,
    TaskPatch,
    TaskResponse,
    TaskUpdate,
)

ALL_WORKSPACE_ROLES: frozenset[WorkspaceRole] = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.EDITOR,
        WorkspaceRole.VIEWER,
    }
)
WRITER_WORKSPACE_ROLES: frozenset[WorkspaceRole] = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.EDITOR,
    }
)
MANAGER_WORKSPACE_ROLES: frozenset[WorkspaceRole] = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
    }
)


class TaskService:
    """Business logic layer for Task management with RBAC and resource ownership."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def create(
        self,
        data: TaskCreate,
        *,
        current_user: User | None = None,
        created_by_id: UUID | None = None,
    ) -> TaskResponse:
        project = await self._repository.get_project(data.project_id)
        if project is None:
            raise ProjectNotFoundError(data.project_id)

        if project.status == ProjectStatus.ARCHIVED:
            raise BadRequestError(ErrorMessages.PROJECT_ARCHIVED)

        if current_user is not None:
            await self._authorize_workspace_access(
                project.workspace_id,
                current_user=current_user,
                allowed_roles=WRITER_WORKSPACE_ROLES,
            )
            creator_id = current_user.id
        else:
            project_owner_id = await self._repository.get_project_owner_id(
                data.project_id
            )
            if project_owner_id is None:
                raise ProjectNotFoundError(data.project_id)
            creator_id = (
                created_by_id if created_by_id is not None else project_owner_id
            )
            if created_by_id is not None and created_by_id != project_owner_id:
                if not await self._repository.user_exists(created_by_id):
                    raise UserNotFoundError(created_by_id)

        await self._validate_assignee(
            data.assignee_id,
            workspace_id=project.workspace_id,
            enforce_workspace_membership=(current_user is not None),
        )

        payload: dict[str, object] = {
            **data.model_dump(),
            "created_by_id": creator_id,
        }
        task = await self._repository.create(payload)
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
        current_user: User | None = None,
        project_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[TaskResponse]:
        if project_id is not None:
            project = await self._repository.get_project(project_id)
            if project is None:
                raise ProjectNotFoundError(project_id)
            if current_user is not None:
                await self._authorize_workspace_access(
                    project.workspace_id,
                    current_user=current_user,
                    allowed_roles=ALL_WORKSPACE_ROLES,
                )

        if current_user is not None:
            tasks = await self._repository.list_accessible_for_user(
                current_user.id,
                is_global_admin=(current_user.role == UserRole.ADMIN),
                project_id=project_id,
                offset=offset,
                limit=limit,
            )
        else:
            tasks = await self._repository.get_all(offset=offset, limit=limit)
        return [TaskResponse.model_validate(task) for task in tasks]

    async def get(
        self,
        task_id: UUID,
        *,
        current_user: User | None = None,
    ) -> TaskResponse:
        task, project = await self._get_task_and_project(task_id)
        if current_user is not None:
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
        current_user: User | None = None,
    ) -> TaskResponse:
        task, project = await self._get_task_and_project(task_id)
        if current_user is not None:
            await self._authorize_workspace_access(
                project.workspace_id,
                current_user=current_user,
                allowed_roles=WRITER_WORKSPACE_ROLES,
            )

        await self._validate_assignee(
            data.assignee_id,
            workspace_id=project.workspace_id,
            enforce_workspace_membership=(current_user is not None),
        )

        updated = await self._repository.update(task, data.model_dump())
        return TaskResponse.model_validate(updated)

    async def patch(
        self,
        task_id: UUID,
        data: TaskPatch,
        *,
        current_user: User | None = None,
    ) -> TaskResponse:
        task, project = await self._get_task_and_project(task_id)
        if current_user is not None:
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
                    enforce_workspace_membership=(current_user is not None),
                )

        if changes:
            task = await self._repository.update(task, changes)
        return TaskResponse.model_validate(task)

    async def delete(
        self,
        task_id: UUID,
        *,
        current_user: User | None = None,
    ) -> None:
        task, project = await self._get_task_and_project(task_id)
        if current_user is not None:
            await self._authorize_task_delete(
                task,
                workspace_id=project.workspace_id,
                current_user=current_user,
            )
        await self._repository.delete(task)

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
        enforce_workspace_membership: bool,
    ) -> None:
        if assignee_id is None:
            return
        if not await self._repository.user_exists(assignee_id):
            raise UserNotFoundError(assignee_id)
        if enforce_workspace_membership:
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
    ) -> WorkspaceRole | None:
        if current_user.role == UserRole.ADMIN:
            return WorkspaceRole.OWNER

        member_role = await self._repository.get_workspace_member_role(
            workspace_id,
            current_user.id,
        )
        if member_role is None or member_role not in allowed_roles:
            raise PermissionDeniedError(ErrorMessages.WORKSPACE_PERMISSION_DENIED)
        return member_role

    async def _authorize_task_delete(
        self,
        task: Task,
        *,
        workspace_id: UUID,
        current_user: User,
    ) -> None:
        if current_user.role == UserRole.ADMIN:
            return

        member_role = await self._repository.get_workspace_member_role(
            workspace_id,
            current_user.id,
        )
        if member_role is None:
            raise PermissionDeniedError(ErrorMessages.WORKSPACE_PERMISSION_DENIED)

        if member_role in MANAGER_WORKSPACE_ROLES:
            return

        if (
            member_role == WorkspaceRole.EDITOR
            and task.created_by_id == current_user.id
        ):
            return

        raise PermissionDeniedError(ErrorMessages.TASK_DELETE_FORBIDDEN)
