from collections.abc import Collection
from uuid import UUID

from app.core.exceptions import PermissionDeniedError
from app.core.messages import ErrorMessages
from app.models.enums import UserRole, WorkspaceRole
from app.models.user import User

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


def ensure_workspace_role(
    user: User,
    member_role: WorkspaceRole | None,
    allowed_roles: Collection[WorkspaceRole],
) -> None:
    """Enforce that the user has an allowed role in the workspace (global ADMIN bypasses)."""
    if user.role == UserRole.ADMIN:
        return
    if member_role is None or member_role not in allowed_roles:
        raise PermissionDeniedError(ErrorMessages.WORKSPACE_PERMISSION_DENIED)


def ensure_workspace_owner_or_admin(
    user: User,
    owner_id: UUID,
) -> None:
    """Enforce that the user is the workspace owner or a global admin."""
    if user.role != UserRole.ADMIN and owner_id != user.id:
        raise PermissionDeniedError(ErrorMessages.WORKSPACE_OWNER_REQUIRED)


def ensure_task_delete_permission(
    user: User,
    member_role: WorkspaceRole | None,
    task_created_by_id: UUID,
) -> None:
    """Enforce task deletion for admins, managers, and the task's editor creator."""
    if user.role == UserRole.ADMIN:
        return

    if member_role is None:
        raise PermissionDeniedError(ErrorMessages.WORKSPACE_PERMISSION_DENIED)

    if member_role in MANAGER_WORKSPACE_ROLES:
        return

    if member_role == WorkspaceRole.EDITOR and task_created_by_id == user.id:
        return

    raise PermissionDeniedError(ErrorMessages.TASK_DELETE_FORBIDDEN)
