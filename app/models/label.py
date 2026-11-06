from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.workspace import Workspace


class TaskLabel(Base):
    __tablename__ = "task_labels"

    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tasks.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("labels.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    task: Mapped[Task] = relationship(
        "Task",
        back_populates="task_labels",
        lazy="selectin",
    )
    label: Mapped[Label] = relationship(
        "Label",
        back_populates="task_labels",
        lazy="selectin",
    )


class Label(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "labels"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_labels_workspace_name",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(32), nullable=False)

    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="labels",
        lazy="selectin",
    )
    task_labels: Mapped[list[TaskLabel]] = relationship(
        "TaskLabel",
        back_populates="label",
        lazy="selectin",
    )
    tasks: Mapped[list[Task]] = relationship(
        "Task",
        secondary="task_labels",
        back_populates="labels",
        viewonly=True,
        lazy="selectin",
    )

