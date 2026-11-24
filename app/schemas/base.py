from pydantic import BaseModel, ConfigDict

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
