from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.refresh_token import RefreshToken
    from app.models.task import Task
    from app.models.workspace import Workspace, WorkspaceMember


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"),
        default=UserRole.MEMBER,
        server_default=UserRole.MEMBER.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    owned_workspaces: Mapped[list[Workspace]] = relationship(
        "Workspace",
        back_populates="owner",
        passive_deletes=True,
    )
    workspace_memberships: Mapped[list[WorkspaceMember]] = relationship(
        "WorkspaceMember",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    assigned_tasks: Mapped[list[Task]] = relationship(
        "Task",
        back_populates="assignee",
        foreign_keys="Task.assignee_id",
        passive_deletes=True,
    )
    created_tasks: Mapped[list[Task]] = relationship(
        "Task",
        back_populates="created_by",
        foreign_keys="Task.created_by_id",
        passive_deletes=True,
    )
    comments: Mapped[list[Comment]] = relationship(
        "Comment",
        back_populates="author",
        passive_deletes=True,
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
