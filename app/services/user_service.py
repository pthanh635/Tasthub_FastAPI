from uuid import UUID

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    UserNotFoundError,
)
from app.core.messages import ErrorMessages
from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    AdminUserUpdate,
    ChangePasswordRequest,
    UserResponse,
    UserUpdate,
)


class UserService:
    """Business logic for user profile, password management, and admin user administration."""

    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repository
        self._refresh_token_repo = refresh_token_repository

    async def get_profile(self, current_user: User) -> UserResponse:
        return UserResponse.model_validate(current_user)

    async def update_profile(
        self,
        current_user: User,
        data: UserUpdate,
    ) -> UserResponse:
        changes = data.model_dump(exclude_unset=True)
        if changes:
            current_user = await self._user_repo.update(current_user, changes)
        return UserResponse.model_validate(current_user)

    async def change_password(
        self,
        current_user: User,
        data: ChangePasswordRequest,
    ) -> None:
        if not verify_password(data.current_password, current_user.hashed_password):
            raise BadRequestError(ErrorMessages.INCORRECT_CURRENT_PASSWORD)

        if data.current_password == data.new_password:
            raise BadRequestError(ErrorMessages.NEW_PASSWORD_SAME_AS_OLD)

        await self._user_repo.update(
            current_user,
            {"hashed_password": hash_password(data.new_password)},
        )
        await self._refresh_token_repo.revoke_all_for_user(current_user.id)

    async def list_users(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[UserResponse]:
        users = await self._user_repo.get_all(offset=offset, limit=limit)
        return [UserResponse.model_validate(u) for u in users]

    async def get_user_by_id(self, user_id: UUID) -> UserResponse:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return UserResponse.model_validate(user)

    async def admin_update_user(
        self,
        user_id: UUID,
        data: AdminUserUpdate,
        *,
        current_admin: User,
    ) -> UserResponse:
        target = await self._user_repo.get_by_id(user_id)
        if target is None:
            raise UserNotFoundError(user_id)

        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return UserResponse.model_validate(target)

        losing_admin_or_active = (
            (changes.get("role") is not None and changes["role"] != UserRole.ADMIN)
            or changes.get("is_active") is False
        )
        if target.id == current_admin.id and losing_admin_or_active:
            raise BadRequestError(ErrorMessages.CANNOT_DEACTIVATE_OR_DEMOTE_SELF)

        if (
            target.role == UserRole.ADMIN
            and target.is_active
            and losing_admin_or_active
        ):
            active_admins = await self._user_repo.count_active_admins()
            if active_admins <= 1:
                raise ConflictError(ErrorMessages.CANNOT_DELETE_LAST_ACTIVE_ADMIN)

        updated = await self._user_repo.update(target, changes)
        if changes.get("is_active") is False:
            await self._refresh_token_repo.revoke_all_for_user(updated.id)
        return UserResponse.model_validate(updated)

    async def admin_delete_user(
        self,
        user_id: UUID,
        *,
        current_admin: User,
    ) -> None:
        if user_id == current_admin.id:
            raise BadRequestError(ErrorMessages.CANNOT_DELETE_SELF)

        target = await self._user_repo.get_by_id(user_id)
        if target is None:
            raise UserNotFoundError(user_id)

        if target.role == UserRole.ADMIN and target.is_active:
            active_admins = await self._user_repo.count_active_admins()
            if active_admins <= 1:
                raise ConflictError(ErrorMessages.CANNOT_DELETE_LAST_ACTIVE_ADMIN)

        await self._user_repo.delete(target)
