from __future__ import annotations

from typing import Any

from app.schemas.base import ErrorResponse, InternalErrorResponse

OPENAPI_DESCRIPTION: str = (
    "**TaskHub API** is a multi-tenant Task Management REST API built with "
    "**FastAPI**, **SQLAlchemy 2.x Async ORM**, **PostgreSQL (`asyncpg`)**, "
    "**Redis**, and **Pydantic v2**.\n\n"
    "---\n\n"
    "### 🔐 Authentication & Security (`BearerAuth`)\n"
    "- Authenticate via `POST /api/v1/auth/login` to receive a short-lived "
    "**Access Token** (`type=access`) and a long-lived **Refresh Token** (`type=refresh`).\n"
    "- Click the **Authorize** button in Swagger UI and enter your `<access_token>` "
    "to authenticate protected endpoints (`Authorization: Bearer <access_token>`).\n"
    "- **Refresh Token Rotation & Reuse Detection**: `POST /api/v1/auth/refresh` "
    "atomically revokes the used refresh token and issues a new token pair. Reusing "
    "an already-revoked refresh token immediately revokes all active sessions for "
    "that user.\n\n"
    "### 🛡️ Role-Based Access Control (RBAC) & Ownership\n"
    "- **Global Roles (`UserRole`)**:\n"
    "  - `ADMIN`: Full platform administration (`/api/v1/users`) and global access.\n"
    "  - `MEMBER`: Standard user role scoped to workspaces they own or join.\n"
    "- **Workspace Roles (`WorkspaceRole`)**:\n"
    "  - `OWNER`: Full control over the workspace, including updating and deleting it.\n"
    "  - `ADMIN`: Can invite/remove members, create/update projects, and manage tasks.\n"
    "  - `EDITOR`: Can create/update projects and tasks, and delete tasks they created.\n"
    "  - `VIEWER`: Read-only access to workspace projects and tasks.\n\n"
    "### ⚡ Redis Caching & Request Tracing Headers\n"
    "Every HTTP response includes diagnostic headers:\n"
    "- `X-Request-ID`: Sanitized correlation UUID for end-to-end request tracing.\n"
    "- `X-Process-Time-Ms`: Request execution duration in milliseconds.\n"
    "- `X-Cache`: Cache status (`HIT`, `MISS`, or `BYPASS`). Write operations "
    "increment the cache version to invalidate stale entries."
)

OPENAPI_TAGS: list[dict[str, Any]] = [
    {
        "name": "Health",
        "description": "Service liveness and readiness probes.",
    },
    {
        "name": "Authentication",
        "description": (
            "User registration, credential login, atomic JWT refresh token rotation, "
            "and session logout revocation."
        ),
    },
    {
        "name": "Users",
        "description": (
            "Authenticated user self-service profile endpoints (`/me`) and global "
            "`ADMIN` user management endpoints."
        ),
    },
    {
        "name": "Workspaces",
        "description": (
            "Multi-tenant workspace lifecycle, member invitation, workspace RBAC "
            "role assignment, and workspace-scoped project creation."
        ),
    },
    {
        "name": "Projects",
        "description": (
            "Project inspection, metadata updates, project archiving (`ACTIVE` / `ARCHIVED`), "
            "and project-scoped task listing/creation."
        ),
    },
    {
        "name": "Tasks",
        "description": (
            "Task CRUD operations, status workflows (`TODO`, `IN_PROGRESS`, `IN_REVIEW`, `DONE`), "
            "priority management (`LOW`, `MEDIUM`, `HIGH`, `URGENT`), and pagination."
        ),
    },
]

OPENAPI_CONTACT: dict[str, str] = {
    "name": "TaskHub API Engineering",
    "email": "engineering@taskhub.dev",
}

OPENAPI_LICENSE: dict[str, str] = {
    "name": "MIT License",
    "url": "https://opensource.org/licenses/MIT",
}

SWAGGER_UI_PARAMETERS: dict[str, Any] = {
    "persistAuthorization": True,
    "displayRequestDuration": True,
    "filter": True,
}

GLOBAL_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    500: {
        "model": InternalErrorResponse,
        "description": "Unhandled internal server error with correlation request_id.",
    },
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Build standardized OpenAPI error response specifications for the given HTTP status codes."""
    catalog: dict[int, dict[str, Any]] = {
        400: {
            "model": ErrorResponse,
            "description": "Bad Request — business rule violation or invalid state transition.",
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized — missing, invalid, expired, or revoked JWT token.",
        },
        403: {
            "model": ErrorResponse,
            "description": (
                "Forbidden — inactive account or insufficient role/ownership permissions."
            ),
        },
        404: {
            "model": ErrorResponse,
            "description": "Not Found — requested resource does not exist.",
        },
        409: {
            "model": ErrorResponse,
            "description": (
                "Conflict — duplicate unique resource or database integrity constraint."
            ),
        },
    }
    return {code: catalog[code] for code in status_codes if code in catalog}

