from fastapi import APIRouter, Response, status

from app.api.v1.dependencies import AuthServiceDep, CurrentUserDep
from app.core.openapi import error_responses
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Create a new `MEMBER` account with a unique email and bcrypt-hashed password. "
        "Role selection by the client is prohibited."
    ),
    response_description="Created user profile (excluding password hash).",
    responses=error_responses(409),
)
async def register(
    data: RegisterRequest,
    service: AuthServiceDep,
) -> UserResponse:
    return await service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT access + refresh tokens",
    description=(
        "Verify email and password credentials, ensure account is active, "
        "and return a signed JWT access token (`type=access`) and refresh token (`type=refresh`)."
    ),
    response_description="Issued JWT access and refresh token pair.",
    responses=error_responses(401, 403),
)
async def login(
    data: LoginRequest,
    service: AuthServiceDep,
) -> TokenResponse:
    return await service.login(data.email, data.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue a new JWT token pair",
    description=(
        "Atomically consume an active refresh token and issue a new access + refresh token pair. "
        "If a previously revoked refresh token is presented (token reuse attack), all active "
        "refresh tokens for the user are immediately revoked."
    ),
    response_description="Rotated JWT access and refresh token pair.",
    responses=error_responses(401, 403),
)
async def refresh_tokens(
    data: RefreshTokenRequest,
    service: AuthServiceDep,
) -> TokenResponse:
    return await service.refresh(data.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token to log out",
    description="Revoke a refresh token belonging to the currently authenticated user.",
    responses=error_responses(401, 403),
)
async def logout(
    data: LogoutRequest,
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> Response:
    await service.logout(data.refresh_token, current_user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


