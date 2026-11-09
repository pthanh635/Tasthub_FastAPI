from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class WorkspaceRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class ProjectStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DONE = "DONE"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"
