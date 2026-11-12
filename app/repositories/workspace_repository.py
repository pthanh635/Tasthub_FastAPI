from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_LIMIT
from app.core.database import DbSessionDep
from app.core.exceptions import ConflictError
from app.core.messages import ErrorMessages
from app.models.enums import WorkspaceRole
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    """Repository encapsulating Workspace and WorkspaceMember queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Workspace, session)

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        is_global_admin: bool = False,
        offset: int = 0,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[Workspace]:
        if is_global_admin:
            statement = (
                select(Workspace)
                .order_by(Workspace.created_at.desc(), Workspace.id.desc())
                .offset(offset)
                .limit(limit)
            )
        else:
            statement = (
                select(Workspace)
                .join(
                    WorkspaceMember,
                    WorkspaceMember.workspace_id == Workspace.id,
                )
                .where(WorkspaceMember.user_id == user_id)
                .order_by(Workspace.created_at.desc(), Workspace.id.desc())
                .offset(offset)
                .limit(limit)
            )
        result = await self._session.scalars(statement)
        return list(result.all())

    async def delete(self, instance: Workspace) -> None:
        try:
            await super().delete(instance)
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConflictError(
                ErrorMessages.CANNOT_DELETE_WORKSPACE_WITH_RESOURCES
            ) from exc

    async def get_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await self._session.scalars(statement)
        return result.first()

    async def list_members(self, workspace_id: UUID) -> list[WorkspaceMember]:
        statement = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.joined_at.asc(), WorkspaceMember.id.asc())
        )
        result = await self._session.scalars(statement)
        return list(result.all())

    async def add_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self._session.add(member)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConflictError(
                ErrorMessages.WORKSPACE_MEMBER_ALREADY_EXISTS
            ) from exc
        await self._session.refresh(member)
        return member

    async def update_member_role(
        self,
        member: WorkspaceMember,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        member.role = role
        await self._session.flush()
        await self._session.refresh(member)
        return member

    async def remove_member(self, member: WorkspaceMember) -> None:
        await self._session.delete(member)
        await self._session.flush()


def get_workspace_repository(session: DbSessionDep) -> WorkspaceRepository:
    return WorkspaceRepository(session)
