from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.constants import TokenType
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.messages import ErrorMessages
from app.core.security import decode_token
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.project_repository import (
    ProjectRepository,
    get_project_repository,
)
from app.repositories.refresh_token_repository import (
    RefreshTokenRepository,
    get_refresh_token_repository,
)
from app.repositories.task_repository import TaskRepository, get_task_repository
from app.repositories.user_repository import UserRepository, get_user_repository
from app.repositories.workspace_repository import (
    WorkspaceRepository,
    get_workspace_repository,
)
from app.services.auth_service import AuthService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="JWT Access Token (`Bearer <access_token>`)",
    auto_error=False,
)

BearerCredentialsDep = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
RefreshTokenRepositoryDep = Annotated[
    RefreshTokenRepository,
    Depends(get_refresh_token_repository),
]
WorkspaceRepositoryDep = Annotated[
    WorkspaceRepository,
    Depends(get_workspace_repository),
]
ProjectRepositoryDep = Annotated[
    ProjectRepository,
    Depends(get_project_repository),
]
TaskRepositoryDep = Annotated[TaskRepository, Depends(get_task_repository)]


def get_auth_service(
    user_repo: UserRepositoryDep,
    refresh_token_repo: RefreshTokenRepositoryDep,
) -> AuthService:
    return AuthService(user_repo, refresh_token_repo)


def get_user_service(
    user_repo: UserRepositoryDep,
    refresh_token_repo: RefreshTokenRepositoryDep,
) -> UserService:
    return UserService(user_repo, refresh_token_repo)


def get_workspace_service(
    workspace_repo: WorkspaceRepositoryDep,
    project_repo: ProjectRepositoryDep,
    user_repo: UserRepositoryDep,
) -> WorkspaceService:
    return WorkspaceService(workspace_repo, project_repo, user_repo)


def get_task_service(repository: TaskRepositoryDep) -> TaskService:
    return TaskService(repository)


async def get_current_user(
    credentials: BearerCredentialsDep,
    user_repo: UserRepositoryDep,
) -> User:
    """Authenticate request via Bearer JWT access token and return active User."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError(ErrorMessages.NOT_AUTHENTICATED)

    payload = decode_token(
        credentials.credentials,
        expected_type=TokenType.ACCESS,
    )
    user = await user_repo.get_by_id(payload.sub)
    if user is None:
        raise AuthenticationError(ErrorMessages.USER_NOT_FOUND_FOR_TOKEN)
    if not user.is_active:
        raise PermissionDeniedError(ErrorMessages.INACTIVE_USER)
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
WorkspaceServiceDep = Annotated[
    WorkspaceService,
    Depends(get_workspace_service),
]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def require_global_roles(
    *allowed_roles: UserRole,
) -> Callable[[CurrentUserDep], User]:
    """Dependency factory enforcing global UserRole RBAC."""
    allowed_set = frozenset(allowed_roles)

    def _check_role(current_user: CurrentUserDep) -> User:
        if current_user.role not in allowed_set:
            raise PermissionDeniedError(ErrorMessages.GLOBAL_ADMIN_REQUIRED)
        return current_user

    return _check_role


AdminUserDep = Annotated[User, Depends(require_global_roles(UserRole.ADMIN))]
