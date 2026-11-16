from enum import StrEnum

# Application & Environment Constants
DEFAULT_APP_VERSION: str = "0.5.0"
DEFAULT_API_V1_PREFIX: str = "/api/v1"


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


# Password & Security Constants
PASSWORD_MIN_LENGTH: int = 8
PASSWORD_MAX_BYTES: int = 72
MIN_SECRET_KEY_LENGTH: int = 32
DEFAULT_JWT_ALGORITHM: str = "HS256"
SUPPORTED_JWT_ALGORITHMS: frozenset[str] = frozenset({"HS256", "HS384", "HS512"})
SUPPORTED_DB_URL_PREFIXES: tuple[str, ...] = (
    "postgresql+asyncpg://",
    "sqlite+aiosqlite://",
)
SUPPORTED_REDIS_URL_PREFIXES: tuple[str, ...] = (
    "redis://",
    "rediss://",
)
INSECURE_PLACEHOLDER_SECRETS: frozenset[str] = frozenset(
    {
        "change-this-to-a-secure-random-secret-key-at-least-32-bytes",
        "taskhub-dev-secret-key-must-be-at-least-32-bytes-long",
        "changeme-secret-key-must-be-at-least-32-characters-long",
    }
)
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

