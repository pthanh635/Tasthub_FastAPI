from collections.abc import Mapping

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import DbSessionDep
from app.core.exceptions import ConflictError
from app.core.messages import ErrorMessages
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository encapsulating database queries for User entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def create(self, data: Mapping[str, object]) -> User:
        try:
            return await super().create(data)
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConflictError(ErrorMessages.EMAIL_ALREADY_REGISTERED) from exc

    async def delete(self, instance: User) -> None:
        try:
            await super().delete(instance)
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConflictError(
                ErrorMessages.CANNOT_DELETE_USER_WITH_RESOURCES
            ) from exc

    async def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        statement = select(User).where(func.lower(User.email) == normalized)
        result = await self._session.scalars(statement)
        return result.first()

    async def count_active_admins(self) -> int:
        statement = (
            select(User.id)
            .where(
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
            )
            .with_for_update()
        )
        result = await self._session.scalars(statement)
        return len(result.all())


def get_user_repository(session: DbSessionDep) -> UserRepository:
    return UserRepository(session)
