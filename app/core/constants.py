from enum import StrEnum

# Password & Security Constants
PASSWORD_MIN_LENGTH: int = 8
PASSWORD_MAX_BYTES: int = 72
MIN_SECRET_KEY_LENGTH: int = 32
DEFAULT_JWT_ALGORITHM: str = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
TOKEN_HASH_LENGTH: int = 64
AUTH_HEADER_SCHEME: str = "Bearer"
WWW_AUTHENTICATE_HEADERS: dict[str, str] = {"WWW-Authenticate": AUTH_HEADER_SCHEME}

# Field Length Constants (matching DB column definitions)
EMAIL_MAX_LENGTH: int = 255
USER_FULL_NAME_MIN_LENGTH: int = 1
USER_FULL_NAME_MAX_LENGTH: int = 255
ENTITY_NAME_MIN_LENGTH: int = 1
ENTITY_NAME_MAX_LENGTH: int = 255

# Pagination Constants
DEFAULT_PAGE_OFFSET: int = 0
DEFAULT_PAGE_LIMIT: int = 100
MAX_PAGE_LIMIT: int = 100


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"
