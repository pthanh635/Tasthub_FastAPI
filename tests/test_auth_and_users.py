import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.constants import TokenType
from app.core.exceptions import AuthenticationError
from app.core.messages import ErrorMessages
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_jwt_helpers() -> None:
    """Verify bcrypt password hashing and JWT access/refresh token encoding & validation."""
    hashed = hash_password("MyStrongPassword123!")
    assert hashed != "MyStrongPassword123!"
    assert verify_password("MyStrongPassword123!", hashed) is True
    assert verify_password("WrongPassword", hashed) is False

    user_id = uuid.uuid4()
    access = create_access_token(subject=user_id, role="MEMBER")
    decoded_access = decode_token(access, expected_type=TokenType.ACCESS)
    assert decoded_access.sub == user_id
    assert decoded_access.role == "MEMBER"

    with pytest.raises(AuthenticationError):
        decode_token(access, expected_type=TokenType.REFRESH)

    expired = create_access_token(
        subject=user_id,
        role="MEMBER",
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(AuthenticationError):
        decode_token(expired, expected_type=TokenType.ACCESS)

    refresh, jti, _exp = create_refresh_token(subject=user_id)
    decoded_refresh = decode_token(refresh, expected_type=TokenType.REFRESH)
    assert decoded_refresh.sub == user_id
    assert decoded_refresh.jti == jti


async def test_jwt_edge_cases_and_refresh_token_calling_api(
    async_client: AsyncClient,
) -> None:
    """Verify refresh token calling API -> 401 and validly signed token with garbage sub -> 401."""
    user_id = uuid.uuid4()
    refresh_token, _jti, _exp = create_refresh_token(subject=user_id)

    # Refresh token used as Bearer token on protected API must return 401 with WWW-Authenticate
    resp_refresh_as_access = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert resp_refresh_as_access.status_code == 401
    assert resp_refresh_as_access.headers.get("WWW-Authenticate") == "Bearer"

    # Valid signature but garbage 'sub' must return 401 (never 500)
    now = datetime.now(UTC)
    garbage_sub_token = jwt.encode(
        {
            "sub": "not-a-valid-uuid-at-all",
            "type": TokenType.ACCESS.value,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    resp_garbage_sub = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {garbage_sub_token}"},
    )
    assert resp_garbage_sub.status_code == 401
    assert resp_garbage_sub.headers.get("WWW-Authenticate") == "Bearer"


async def test_bcrypt_72_byte_utf8_limit_and_register_role_rejection(
    async_client: AsyncClient,
) -> None:
    """Verify >72 UTF-8 byte passwords (even <72 chars) -> 422, and client role injection -> 422."""
    # 30 Vietnamese multibyte characters = 90 UTF-8 bytes (> 72 bytes, though len == 30)
    multibyte_over_72_bytes = "ộ" * 30
    assert len(multibyte_over_72_bytes) == 30
    assert len(multibyte_over_72_bytes.encode("utf-8")) == 90

    reg_over_72 = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "utf8@example.com",
            "password": multibyte_over_72_bytes,
            "full_name": "UTF8 User",
        },
    )
    assert reg_over_72.status_code == 422

    login_over_72 = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "utf8@example.com",
            "password": multibyte_over_72_bytes,
        },
    )
    assert login_over_72.status_code == 422

    # Client attempting to choose role during register must be rejected
    reg_with_role = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "hacker@example.com",
            "password": "ValidPassword123!",
            "full_name": "Role Hacker",
            "role": "ADMIN",
        },
    )
    assert reg_with_role.status_code == 422


async def test_register_login_refresh_reuse_revokes_all_sessions_and_logout(
    async_client: AsyncClient,
) -> None:
    """Verify register, duplicate 409, login, refresh rotation, and reuse revoking all."""
    register_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "  Alice@Example.com  ",
            "password": "StrongPassword123!",
            "full_name": "  Alice Nguyen  ",
        },
    )
    assert register_resp.status_code == 201
    user_data = register_resp.json()
    assert user_data["email"] == "alice@example.com"
    assert user_data["full_name"] == "Alice Nguyen"
    assert user_data["role"] == "MEMBER"
    assert "hashed_password" not in user_data

    # Duplicate email -> 409 Conflict
    duplicate_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "AnotherPassword123!",
            "full_name": "Alice Duplicate",
        },
    )
    assert duplicate_resp.status_code == 409

    bad_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401
    assert bad_login.headers.get("WWW-Authenticate") == "Bearer"

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "StrongPassword123!"},
    )
    assert login_resp.status_code == 200
    tokens_1 = login_resp.json()
    refresh_token_1 = tokens_1["refresh_token"]

    # Rotate refresh_token_1 -> issues refresh_token_2
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert refresh_resp.status_code == 200
    tokens_2 = refresh_resp.json()
    refresh_token_2 = tokens_2["refresh_token"]
    assert refresh_token_2 != refresh_token_1

    # Reusing revoked refresh_token_1 -> 401 AND revokes all sessions of that user
    reuse_old_refresh = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert reuse_old_refresh.status_code == 401

    # Verify refresh_token_2 was also revoked due to token reuse detection!
    compromised_session_refresh = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_2},
    )
    assert compromised_session_refresh.status_code == 401

    # Fresh login and normal logout
    login_again = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "StrongPassword123!"},
    )
    tokens_3 = login_again.json()
    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens_3["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens_3['access_token']}"},
    )
    assert logout_resp.status_code == 204

    refresh_after_logout = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens_3["refresh_token"]},
    )
    assert refresh_after_logout.status_code == 401


async def test_user_profile_null_rejection_and_change_password(
    async_client: AsyncClient,
) -> None:
    """Verify GET /users/me, PATCH null rejection -> 422, and change-password flow."""
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "password": "InitialPassword123!",
            "full_name": "Bob Tran",
        },
    )
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "InitialPassword123!"},
    )
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Sending explicit null to NOT NULL field full_name must return 422 (never 500)
    null_patch = await async_client.patch(
        "/api/v1/users/me",
        json={"full_name": None},
        headers=headers,
    )
    assert null_patch.status_code == 422

    patch_resp = await async_client.patch(
        "/api/v1/users/me",
        json={"full_name": "  Bob Tran Updated  "},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["full_name"] == "Bob Tran Updated"

    change_pw = await async_client.post(
        "/api/v1/users/me/change-password",
        json={
            "current_password": "InitialPassword123!",
            "new_password": "NewSecurePassword456!",
        },
        headers=headers,
    )
    assert change_pw.status_code == 204

    # Refresh token from before password change is revoked -> 401
    revoked_refresh = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert revoked_refresh.status_code == 401

    # Login with old password after change -> 401
    old_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "InitialPassword123!"},
    )
    assert old_login.status_code == 401

    new_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "NewSecurePassword456!"},
    )
    assert new_login.status_code == 200


async def test_admin_user_management_and_protections(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify member 403 on user admin, self-delete blocked, and last admin protected."""
    # Register two members
    reg_a = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "member_a@example.com",
            "password": "MemberPass123!",
            "full_name": "Member A",
        },
    )
    member_a_id = reg_a.json()["id"]
    login_a = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "member_a@example.com", "password": "MemberPass123!"},
    )
    member_a_headers = {
        "Authorization": f"Bearer {login_a.json()['access_token']}"
    }

    reg_b = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "member_b@example.com",
            "password": "MemberPass123!",
            "full_name": "Member B",
        },
    )
    member_b_id = reg_b.json()["id"]

    # Member A trying to update or delete Member B -> 403 Forbidden
    member_patch_other = await async_client.patch(
        f"/api/v1/users/{member_b_id}",
        json={"full_name": "Hacked by A"},
        headers=member_a_headers,
    )
    assert member_patch_other.status_code == 403

    member_delete_other = await async_client.delete(
        f"/api/v1/users/{member_b_id}",
        headers=member_a_headers,
    )
    assert member_delete_other.status_code == 403

    # Seeded admin cannot delete or deactivate themselves -> 400
    admin_me = await async_client.get("/api/v1/users/me", headers=auth_headers)
    admin_id = admin_me.json()["id"]

    self_delete = await async_client.delete(
        f"/api/v1/users/{admin_id}",
        headers=auth_headers,
    )
    assert self_delete.status_code == 400

    self_deactivate = await async_client.patch(
        f"/api/v1/users/{admin_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert self_deactivate.status_code == 400

    # Admin deactivating Member A -> Member A gets 403 with "Inactive user" message
    deactivate_a = await async_client.patch(
        f"/api/v1/users/{member_a_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert deactivate_a.status_code == 200
    assert deactivate_a.json()["is_active"] is False

    inactive_me = await async_client.get(
        "/api/v1/users/me",
        headers=member_a_headers,
    )
    assert inactive_me.status_code == 403
    assert inactive_me.json()["detail"] == ErrorMessages.INACTIVE_USER

    # Admin deleting Member B -> 204 No Content
    delete_b = await async_client.delete(
        f"/api/v1/users/{member_b_id}",
        headers=auth_headers,
    )
    assert delete_b.status_code == 204
