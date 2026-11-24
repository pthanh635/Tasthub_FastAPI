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
PLACEHOLDER_CREDENTIAL_PATTERN: str = r"replace_with|changeme|example|placeholder|dummy"
ENV_FILE_NAME: str = ".env"
ENV_FILE_PREFIX: str = ".env."
REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS: float = 1.0
REDIS_SOCKET_TIMEOUT_SECONDS: float = 1.0
REDIS_RECONNECT_INITIAL_DELAY_SECONDS: float = 1.0
REDIS_RECONNECT_MAX_DELAY_SECONDS: float = 30.0
REDIS_CACHE_VERSION_KEY: str = "taskhub:cache:version"
REDIS_CACHE_KEY_PREFIX: str = "taskhub:cache:"
HEALTH_PATH: str = "/health"
AUTH_PATH_PREFIX: str = "/api/v1/auth"
REQUEST_ID_HEADER: str = "X-Request-ID"
REQUEST_PROCESS_TIME_HEADER: str = "X-Process-Time-Ms"
CACHE_STATUS_HEADER: str = "X-Cache"
AUTHORIZATION_HEADER: str = "Authorization"
JSON_MEDIA_TYPE: str = "application/json"
HTTP_OK_STATUS: int = 200
HTTP_ERROR_STATUS_THRESHOLD: int = 400
REQUEST_ID_MAX_LENGTH: int = 64
CACHEABLE_METHODS: frozenset[str] = frozenset({"GET", "HEAD"})
DEFAULT_CACHE_PUBLIC_PATHS: tuple[str, ...] = (
    "/api/v1/workspaces",
    "/api/v1/projects",
    "/api/v1/tasks",
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


class CacheStatus(StrEnum):
    HIT = "HIT"
    MISS = "MISS"
    BYPASS = "BYPASS"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Logging & Background Task Queue Constants
DEFAULT_LOG_LEVEL: LogLevel = LogLevel.INFO
CONSOLE_LOG_FORMAT: str = "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s"
UVICORN_LOGGERS: tuple[str, ...] = ("uvicorn", "uvicorn.error", "uvicorn.access")
DEFAULT_TASK_QUEUE_SHUTDOWN_TIMEOUT_SECONDS: float = 5.0


