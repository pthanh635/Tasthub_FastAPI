from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import PASSWORD_MAX_BYTES


def validate_password_byte_length(value: str) -> str:
    """Ensure password does not exceed bcrypt's 72 UTF-8 byte limit."""
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(
            f"Password must not exceed {PASSWORD_MAX_BYTES} bytes in UTF-8 encoding"
        )
    return value


class BaseSchema(BaseModel):
    """Base Pydantic model automatically stripping leading and trailing whitespaces."""

    model_config = ConfigDict(str_strip_whitespace=True)


class ErrorResponse(BaseModel):
    """Standard API error response schema returned for 4xx client errors."""

    detail: str = Field(
        description="Human-readable explanation of the error.",
        examples=["Invalid or expired authentication credentials"],
    )


class InternalErrorResponse(BaseModel):
    """Error response schema returned for unhandled 500 server errors with correlation ID."""

    detail: str = Field(
        default="Internal server error",
        description="Generic error message hiding internal implementation details.",
        examples=["Internal server error"],
    )
    request_id: str | None = Field(
        default=None,
        description="Request correlation ID matching the X-Request-ID response header.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class HealthCheckResponse(BaseModel):
    """Liveness health check payload."""

    status: str = Field(
        default="ok",
        description="Service operational status.",
        examples=["ok"],
    )

