from collections.abc import Collection
from uuid import UUID

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    PermissionDeniedError,
    ProjectNotFoundError,
    UserNotFoundError,
    WorkspaceNotFoundError,
)
from app.core.messages import ErrorMessages
from app.models.enums import ProjectStatus, UserRole, WorkspaceRole
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)

ALL_WORKSPACE_ROLES: frozenset[WorkspaceRole] = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.EDITOR,
        WorkspaceRole.VIEWER,
    }
)
MANAGER_WORKSPACE_ROLES: frozenset[WorkspaceRole] = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
    }
)
WRITER_WORKSPACE_ROLES: frozenset[WorkspaceRole] = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.EDITOR,
    }
)


class WorkspaceService:
    """Business logic for Workspaces, Memberships, Projects, and RBAC enforcement."""

    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        project_repository: ProjectRepository,
        user_repository: UserRepository,
    ) -> None:
        self._workspace_repo = workspace_repository
        self._project_repo = project_repository
        self._user_repo = user_repository

    async def create_workspace(
        self,
        data: WorkspaceCreate,
        *,
        current_user: User,
    ) -> WorkspaceResponse:
        workspace = await self._workspace_repo.create(
            {
                "name": data.name,
                "description": data.description,
                "owner_id": current_user.id,
            }
        )
        await self._workspace_repo.add_member(
            workspace_id=workspace.id,
            user_id=current_user.id,
            role=WorkspaceRole.OWNER,
        )
        return WorkspaceResponse.model_validate(workspace)

    async def list_workspaces(
        self,
        *,
        current_user: User,
        offset: int = 0,
        limit: int = 100,
    ) -> list[WorkspaceResponse]:
        workspaces = await self._workspace_repo.list_for_user(
            current_user.id,
            is_global_admin=(current_user.role == UserRole.ADMIN),
            offset=offset,
            limit=limit,
        )
        return [WorkspaceResponse.model_validate(ws) for ws in workspaces]

    async def get_workspace(
        self,
        workspace_id: UUID,
        *,
        current_user: User,
    ) -> WorkspaceResponse:
        workspace = await self._get_workspace_and_authorize(
            workspace_id,
            current_user=current_user,
            allowed_roles=ALL_WORKSPACE_ROLES,
        )
        return WorkspaceResponse.model_validate(workspace)

    async def update_workspace(
        self,
        workspace_id: UUID,
        data: WorkspaceUpdate,
        *,
        current_user: User,
    ) -> WorkspaceResponse:
        workspace = await self._get_workspace_or_raise(workspace_id)
        self._require_workspace_owner_or_global_admin(workspace, current_user)

        changes = data.model_dump(exclude_unset=True)
        if changes:
            workspace = await self._workspace_repo.update(workspace, changes)
        return WorkspaceResponse.model_validate(workspace)

    async def delete_workspace(
        self,
        workspace_id: UUID,
        *,
        current_user: User,
    ) -> None:
        workspace = await self._get_workspace_or_raise(workspace_id)
        self._require_workspace_owner_or_global_admin(workspace, current_user)
        await self._workspace_repo.delete(workspace)

    async def add_or_update_member(
        self,
        workspace_id: UUID,
        data: WorkspaceMemberCreate,
        *,
        current_user: User,
    ) -> WorkspaceMemberResponse:
        workspace = await self._get_workspace_and_authorize(
            workspace_id,
            current_user=current_user,
            allowed_roles=MANAGER_WORKSPACE_ROLES,
        )
        if data.role == WorkspaceRole.OWNER and data.user_id != workspace.owner_id:
            raise BadRequestError(ErrorMessages.CANNOT_ASSIGN_OWNER_ROLE)

        target_user = await self._user_repo.get_by_id(data.user_id)
        if target_user is None:
            raise UserNotFoundError(data.user_id)

        existing = await self._workspace_repo.get_member(workspace_id, data.user_id)
        if existing is not None:
            if (
                existing.user_id == workspace.owner_id
                and data.role != WorkspaceRole.OWNER
            ):
                raise ConflictError(ErrorMessages.CANNOT_DOWNGRADE_WORKSPACE_OWNER)
            updated = await self._workspace_repo.update_member_role(
                existing,
                data.role,
            )
            return WorkspaceMemberResponse.model_validate(updated)

        member = await self._workspace_repo.add_member(
            workspace_id=workspace_id,
            user_id=data.user_id,
            role=data.role,
        )
        return WorkspaceMemberResponse.model_validate(member)

    async def list_members(
        self,
        workspace_id: UUID,
        *,
        current_user: User,
    ) -> list[WorkspaceMemberResponse]:
        await self._get_workspace_and_authorize(
            workspace_id,
            current_user=current_user,
            allowed_roles=ALL_WORKSPACE_ROLES,
        )
        members = await self._workspace_repo.list_members(workspace_id)
        return [WorkspaceMemberResponse.model_validate(m) for m in members]

    async def remove_member(
        self,
        workspace_id: UUID,
        target_user_id: UUID,
        *,
        current_user: User,
    ) -> None:
        workspace = await self._get_workspace_and_authorize(
            workspace_id,
            current_user=current_user,
            allowed_roles=MANAGER_WORKSPACE_ROLES,
        )
        if target_user_id == workspace.owner_id:
            raise ConflictError(ErrorMessages.CANNOT_REMOVE_WORKSPACE_OWNER)

        member = await self._workspace_repo.get_member(workspace_id, target_user_id)
        if member is None:
            raise UserNotFoundError(target_user_id)

        await self._workspace_repo.remove_member(member)

    async def create_project(
        self,
        workspace_id: UUID,
        data: ProjectCreate,
        *,
        current_user: User,
    ) -> ProjectResponse:
        await self._get_workspace_and_authorize(
            workspace_id,
            current_user=current_user,
            allowed_roles=WRITER_WORKSPACE_ROLES,
        )
        project = await self._project_repo.create(
            {
                "workspace_id": workspace_id,
                "name": data.name,
                "description": data.description,
                "status": ProjectStatus.ACTIVE,
            }
        )
        return ProjectResponse.model_validate(project)

    async def list_projects(
        self,
        workspace_id: UUID,
        *,
        current_user: User,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ProjectResponse]:
        await self._get_workspace_and_authorize(
            workspace_id,
            current_user=current_user,
            allowed_roles=ALL_WORKSPACE_ROLES,
        )
        projects = await self._project_repo.list_by_workspace(
            workspace_id,
            offset=offset,
            limit=limit,
        )
        return [ProjectResponse.model_validate(p) for p in projects]

    async def get_project(
        self,
        project_id: UUID,
        *,
        current_user: User,
    ) -> ProjectResponse:
        project = await self._get_project_or_raise(project_id)
        await self._get_workspace_and_authorize(
            project.workspace_id,
            current_user=current_user,
            allowed_roles=ALL_WORKSPACE_ROLES,
        )
        return ProjectResponse.model_validate(project)

    async def update_project(
        self,
        project_id: UUID,
        data: ProjectUpdate,
        *,
        current_user: User,
    ) -> ProjectResponse:
        project = await self._get_project_or_raise(project_id)
        await self._get_workspace_and_authorize(
            project.workspace_id,
            current_user=current_user,
            allowed_roles=WRITER_WORKSPACE_ROLES,
        )
        changes = data.model_dump(exclude_unset=True)
        if changes:
            project = await self._project_repo.update(project, changes)
        return ProjectResponse.model_validate(project)

    async def _get_workspace_or_raise(self, workspace_id: UUID) -> Workspace:
        workspace = await self._workspace_repo.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        return workspace

    async def _get_project_or_raise(self, project_id: UUID) -> Project:
        project = await self._project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project

    async def _get_workspace_and_authorize(
        self,
        workspace_id: UUID,
        *,
        current_user: User,
        allowed_roles: Collection[WorkspaceRole],
    ) -> Workspace:
        workspace = await self._get_workspace_or_raise(workspace_id)
        if current_user.role == UserRole.ADMIN:
            return workspace

        member = await self._workspace_repo.get_member(workspace_id, current_user.id)
        if member is None or member.role not in allowed_roles:
            raise PermissionDeniedError(ErrorMessages.WORKSPACE_PERMISSION_DENIED)
        return workspace

    @staticmethod
    def _require_workspace_owner_or_global_admin(
        workspace: Workspace,
        current_user: User,
    ) -> None:
        if (
            current_user.role != UserRole.ADMIN
            and workspace.owner_id != current_user.id
        ):
            raise PermissionDeniedError(ErrorMessages.WORKSPACE_OWNER_REQUIRED)
