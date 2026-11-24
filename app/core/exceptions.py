from uuid import UUID

from app.core.constants import WWW_AUTHENTICATE_HEADERS
from app.core.messages import ErrorMessages


class AppException(Exception):  # noqa: N818
    """Base application exception handled globally by FastAPI."""

    status_code: int = 400
    headers: dict[str, str] | None = None

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if headers is not None:
            self.headers = headers
        super().__init__(message)


DomainError = AppException


class AuthenticationError(AppException):
    """Raised when credentials or authentication tokens are missing, invalid, or expired."""

    status_code = 401
    headers = WWW_AUTHENTICATE_HEADERS

    def __init__(
        self,
        message: str = ErrorMessages.INVALID_OR_EXPIRED_TOKEN,
    ) -> None:
        super().__init__(message, status_code=401, headers=WWW_AUTHENTICATE_HEADERS)


class PermissionDeniedError(AppException):
    """Raised when an authenticated user lacks permission or is inactive."""

    status_code = 403

    def __init__(self, message: str = ErrorMessages.PERMISSION_DENIED) -> None:
        super().__init__(message, status_code=403)


class ConflictError(AppException):
    """Raised when an operation conflicts with existing state (e.g., duplicate email)."""

    status_code = 409

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409)


class BadRequestError(AppException):
    """Raised when a business rule validation fails."""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class EntityNotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    status_code = 404

    def __init__(self, entity_name: str, entity_id: UUID | str) -> None:
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(
            f"{entity_name} with id '{entity_id}' was not found",
            status_code=404,
        )


class TaskNotFoundError(EntityNotFoundError):
    """Raised when a Task does not exist."""

    def __init__(self, task_id: UUID) -> None:
        super().__init__("Task", task_id)


class ProjectNotFoundError(EntityNotFoundError):
    """Raised when a referenced Project does not exist."""

    def __init__(self, project_id: UUID) -> None:
        super().__init__("Project", project_id)


class WorkspaceNotFoundError(EntityNotFoundError):
    """Raised when a referenced Workspace does not exist."""

    def __init__(self, workspace_id: UUID) -> None:
        super().__init__("Workspace", workspace_id)


class UserNotFoundError(EntityNotFoundError):
    """Raised when a referenced User does not exist."""

    def __init__(self, user_id: UUID | str) -> None:
        super().__init__("User", user_id)
