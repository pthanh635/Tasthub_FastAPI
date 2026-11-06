from uuid import UUID


class DomainError(Exception):
    """Base exception for domain and business rule errors."""


class EntityNotFoundError(DomainError):
    """Raised when a requested resource does not exist."""

    def __init__(self, entity_name: str, entity_id: UUID | str) -> None:
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"{entity_name} with id '{entity_id}' was not found")


class TaskNotFoundError(EntityNotFoundError):
    """Raised when a Task does not exist."""

    def __init__(self, task_id: UUID) -> None:
        super().__init__("Task", task_id)


class ProjectNotFoundError(EntityNotFoundError):
    """Raised when a referenced Project does not exist."""

    def __init__(self, project_id: UUID) -> None:
        super().__init__("Project", project_id)


class UserNotFoundError(EntityNotFoundError):
    """Raised when a referenced User (e.g., assignee or creator) does not exist."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__("User", user_id)

