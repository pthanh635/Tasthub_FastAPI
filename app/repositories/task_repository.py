from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Repository encapsulating database queries for Task entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Task, session)

    async def get_all(self, *, offset: int = 0, limit: int = 100) -> list[Task]:
        statement = (
            select(Task)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return list(result.all())

    async def get_project_owner_id(self, project_id: UUID) -> UUID | None:
        """Return the workspace owner_id for the project, or None if project is not found."""
        statement = (
            select(Workspace.owner_id)
            .join(Project, Project.workspace_id == Workspace.id)
            .where(Project.id == project_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def user_exists(self, user_id: UUID) -> bool:
        """Check whether a User with the given UUID exists."""
        statement = select(User.id).where(User.id == user_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_task_repository(session: DbSessionDep) -> TaskRepository:
    return TaskRepository(session)
