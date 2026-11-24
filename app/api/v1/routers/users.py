from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.v1.dependencies import AdminUserDep, CurrentUserDep, UserServiceDep
from app.core.constants import (
    DEFAULT_PAGE_LIMIT,
    DEFAULT_PAGE_OFFSET,
    MAX_PAGE_LIMIT,
)
from app.core.openapi import error_responses
from app.schemas.user import (
    AdminUserUpdate,
    ChangePasswordRequest,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    description="Return the profile of the currently authenticated user.",
    responses=error_responses(401, 403),
)
async def get_my_profile(
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserResponse:
    return await service.get_profile(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current authenticated user profile",
    description="Update editable profile fields (`full_name`) of the currently authenticated user.",
    responses=error_responses(401, 403),
)
async def update_my_profile(
    data: UserUpdate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserResponse:
    return await service.update_profile(current_user, data)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change current user password and revoke active refresh tokens",
    description=(
        "Verify `current_password`, hash and store `new_password`, and revoke all active "
        "refresh tokens for the user."
    ),
    responses=error_responses(400, 401, 403),
)
async def change_my_password(
    data: ChangePasswordRequest,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> Response:
    await service.change_password(current_user, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List all users (global ADMIN only)",
    description="Paginated list of all registered user accounts. Requires global `ADMIN` role.",
    responses=error_responses(401, 403),
)
async def list_users(
    _admin: AdminUserDep,
    service: UserServiceDep,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of user records to skip"),
    ] = DEFAULT_PAGE_OFFSET,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_LIMIT, description="Maximum number of users to return"),
    ] = DEFAULT_PAGE_LIMIT,
) -> list[UserResponse]:
    return await service.list_users(offset=offset, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID (global ADMIN only)",
    description="Retrieve any user profile by UUID. Requires global `ADMIN` role.",
    responses=error_responses(401, 403, 404),
)
async def get_user(
    user_id: UUID,
    _admin: AdminUserDep,
    service: UserServiceDep,
) -> UserResponse:
    return await service.get_user_by_id(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user role, status, or name (global ADMIN only)",
    description=(
        "Administer a user's `full_name`, global `role`, or `is_active` flag. "
        "Guards against self-demotion/deactivation and removing the last active global admin."
    ),
    responses=error_responses(400, 401, 403, 404, 409),
)
async def admin_update_user(
    user_id: UUID,
    data: AdminUserUpdate,
    current_admin: AdminUserDep,
    service: UserServiceDep,
) -> UserResponse:
    return await service.admin_update_user(
        user_id,
        data,
        current_admin=current_admin,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user account (global ADMIN only; prevents self-delete & last admin delete)",
    description=(
        "Permanently delete a user account. Prevents self-deletion, deleting the last active "
        "admin, or deleting a user who still owns workspaces (409 Conflict)."
    ),
    responses=error_responses(400, 401, 403, 404, 409),
)
async def admin_delete_user(
    user_id: UUID,
    current_admin: AdminUserDep,
    service: UserServiceDep,
) -> Response:
    await service.admin_delete_user(user_id, current_admin=current_admin)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

