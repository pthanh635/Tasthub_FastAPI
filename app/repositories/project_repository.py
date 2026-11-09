from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository encapsulating Project queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Project]:
        statement = (
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return list(result.all())


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_project_repository(session: DbSessionDep) -> ProjectRepository:
    return ProjectRepository(session)

