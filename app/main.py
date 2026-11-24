from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers import tasks
from app.core.config import settings
from app.core.database import engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description=(
        "Day 2: FastAPI layered architecture with SQLAlchemy 2.x Async ORM, "
        "PostgreSQL, Alembic & Repository Pattern"
    ),
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tasks.router, prefix="/api/v1")
