from uuid import UUID

from app.core.constants import TokenType
from app.core.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
)
from app.core.messages import ErrorMessages
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserResponse


class AuthService:
    """Business logic for user registration, login, atomic token refresh, and logout."""

    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repository
        self._refresh_token_repo = refresh_token_repository

    async def register(self, data: RegisterRequest) -> UserResponse:
        normalized_email = data.email.strip().lower()
        user = await self._user_repo.create(
            {
                "email": normalized_email,
                "hashed_password": hash_password(data.password),
                "full_name": data.full_name,
                "role": UserRole.MEMBER,
                "is_active": True,
            }
        )
        await self._user_repo.commit()
        return UserResponse.model_validate(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError(ErrorMessages.INVALID_CREDENTIALS)

        if not user.is_active:
            raise PermissionDeniedError(ErrorMessages.INACTIVE_USER)

        tokens = await self._issue_token_pair(user)
        await self._refresh_token_repo.commit()
        return tokens

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        payload = decode_token(
            raw_refresh_token,
            expected_type=TokenType.REFRESH,
        )
        token_digest = hash_token(raw_refresh_token)

        revoked_record = await self._refresh_token_repo.revoke_atomic(
            payload.jti,
            expected_token_hash=token_digest,
        )
        if revoked_record is None:
            existing_record = await self._refresh_token_repo.get_by_jti(payload.jti)
            if (
                existing_record is not None
                and existing_record.revoked_at is not None
            ):
                # Reuse of revoked refresh token detected: revoke all sessions of user
                await self._refresh_token_repo.revoke_all_for_user(
                    existing_record.user_id,
                )
                await self._refresh_token_repo.commit()
            raise AuthenticationError(
                ErrorMessages.REFRESH_TOKEN_REVOKED_OR_EXPIRED
            )

        user = await self._user_repo.get_by_id(payload.sub)
        if user is None:
            raise AuthenticationError(ErrorMessages.USER_NOT_FOUND_FOR_TOKEN)
        if not user.is_active:
            raise PermissionDeniedError(ErrorMessages.INACTIVE_USER)

        tokens = await self._issue_token_pair(user)
        await self._refresh_token_repo.commit()
        return tokens

    async def logout(
        self,
        raw_refresh_token: str,
        *,
        current_user_id: UUID,
    ) -> None:
        payload = decode_token(
            raw_refresh_token,
            expected_type=TokenType.REFRESH,
        )
        if payload.sub != current_user_id:
            raise PermissionDeniedError(
                ErrorMessages.REFRESH_TOKEN_OWNERSHIP_MISMATCH
            )

        token_digest = hash_token(raw_refresh_token)
        token_record = await self._refresh_token_repo.get_by_jti(
            payload.jti,
            for_update=True,
        )
        if token_record is None or token_record.token_hash != token_digest:
            raise AuthenticationError(ErrorMessages.REFRESH_TOKEN_INVALID)

        if token_record.revoked_at is None:
            await self._refresh_token_repo.revoke_atomic(
                payload.jti,
                expected_token_hash=token_digest,
            )
            await self._refresh_token_repo.commit()

    async def _issue_token_pair(self, user: User) -> TokenResponse:
        access_token = create_access_token(
            subject=user.id,
            role=user.role.value,
        )
        refresh_token, jti, expires_at = create_refresh_token(subject=user.id)
        await self._refresh_token_repo.create(
            {
                "jti": jti,
                "user_id": user.id,
                "token_hash": hash_token(refresh_token),
                "expires_at": expires_at,
                "revoked_at": None,
            }
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
