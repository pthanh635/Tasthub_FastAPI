import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings
from app.core.constants import PASSWORD_MAX_BYTES, TokenType
from app.core.exceptions import AuthenticationError
from app.core.messages import ErrorMessages

TOKEN_TYPE_ACCESS = TokenType.ACCESS
TOKEN_TYPE_REFRESH = TokenType.REFRESH


@dataclass(frozen=True)
class TokenPayload:
    sub: UUID
    jti: UUID
    token_type: TokenType
    expires_at: datetime
    role: str | None = None


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt (enforcing <= 72 UTF-8 bytes)."""
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > PASSWORD_MAX_BYTES:
        raise ValueError(f"Password cannot exceed {PASSWORD_MAX_BYTES} UTF-8 bytes")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > PASSWORD_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(
            password_bytes,
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False


def hash_token(raw_token: str) -> str:
    """Return a SHA-256 hex digest of a token for safe database storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(
    *,
    subject: UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, object] = {
        "sub": str(subject),
        "role": role,
        "type": TokenType.ACCESS.value,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    *,
    subject: UUID,
    jti: UUID | None = None,
    expires_delta: timedelta | None = None,
) -> tuple[str, UUID, datetime]:
    """Create a signed JWT refresh token and return (token, jti, expires_at)."""
    now = datetime.now(UTC)
    token_jti = jti if jti is not None else uuid.uuid4()
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(days=settings.refresh_token_expire_days)
    )
    payload: dict[str, object] = {
        "sub": str(subject),
        "type": TokenType.REFRESH.value,
        "jti": str(token_jti),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    encoded = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded, token_jti, expire


def decode_token(token: str, *, expected_type: TokenType) -> TokenPayload:
    """Decode and validate a JWT token, ensuring its type matches expected_type."""
    try:
        raw_payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise AuthenticationError(ErrorMessages.INVALID_OR_EXPIRED_TOKEN) from exc

    if not isinstance(raw_payload, dict):
        raise AuthenticationError(ErrorMessages.MALFORMED_TOKEN_PAYLOAD)

    raw_type = raw_payload.get("type")
    if not isinstance(raw_type, str) or raw_type != expected_type.value:
        raise AuthenticationError(ErrorMessages.INVALID_TOKEN_TYPE)

    try:
        raw_sub = raw_payload["sub"]
        raw_jti = raw_payload["jti"]
        raw_exp = raw_payload["exp"]
        if (
            not isinstance(raw_sub, str)
            or not isinstance(raw_jti, str)
            or not isinstance(raw_exp, int | float)
        ):
            raise ValueError("Invalid claim types")
        subject_uuid = UUID(raw_sub)
        jti_uuid = UUID(raw_jti)
        expires_at = datetime.fromtimestamp(raw_exp, tz=UTC)
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise AuthenticationError(ErrorMessages.MALFORMED_TOKEN_PAYLOAD) from exc

    role_val = raw_payload.get("role")
    role_str = role_val if isinstance(role_val, str) else None

    return TokenPayload(
        sub=subject_uuid,
        jti=jti_uuid,
        token_type=expected_type,
        expires_at=expires_at,
        role=role_str,
    )
