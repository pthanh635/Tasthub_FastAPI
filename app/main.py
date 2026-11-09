from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.routers import auth, projects, tasks, users, workspaces
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import AppException


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description=(
        "Day 3: TaskHub API with JWT Authentication, Bcrypt Password Hashing, "
        "Role-Based Access Control (RBAC), and Resource Ownership"
    ),
    version="0.3.0",
    lifespan=lifespan,
)


@app.exception_handler(AppException)
async def app_exception_handler(
    _request: Request,
    exc: AppException,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
        headers=exc.headers,
    )


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
