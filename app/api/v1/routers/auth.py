from fastapi import APIRouter, Response, status

from app.api.v1.dependencies import AuthServiceDep, CurrentUserDep
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
)
async def logout(
    data: LogoutRequest,
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> Response:
    await service.logout(data.refresh_token, current_user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

