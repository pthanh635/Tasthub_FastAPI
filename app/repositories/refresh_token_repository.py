from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import DbSessionDep
from app.models.base import utc_now
from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository managing persistence, atomic rotation, and revocation of JWT refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RefreshToken, session)

    async def get_by_jti(
        self,
        jti: UUID,
        *,
        for_update: bool = False,
    ) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.jti == jti)
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.scalars(statement)
        return result.first()

    async def revoke_atomic(
        self,
        jti: UUID,
        *,
        expected_token_hash: str,
    ) -> RefreshToken | None:
        """Atomically mark an unrevoked, non-expired refresh token as revoked and return it."""
        now = utc_now()
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.jti == jti,
                RefreshToken.token_hash == expected_token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .values(revoked_at=now)
            .returning(RefreshToken)
        )
        result = await self._session.scalars(statement)
        token_record = result.first()
        await self._session.flush()
        return token_record

    async def revoke_all_for_user(
        self,
        user_id: UUID,
    ) -> None:
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=utc_now())
        )
        await self._session.execute(statement)
        await self._session.flush()


def get_refresh_token_repository(session: DbSessionDep) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)
