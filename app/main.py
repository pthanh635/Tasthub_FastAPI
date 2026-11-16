from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.v1.routers import auth, projects, tasks, users, workspaces
from app.core.cache import RedisCache
from app.core.config import Settings, settings
from app.core.database import engine
from app.core.exceptions import AppException
from app.core.middleware import RedisCacheMiddleware, RequestContextMiddleware
from app.core.openapi import (
    GLOBAL_ERROR_RESPONSES,
    OPENAPI_CONTACT,
    OPENAPI_DESCRIPTION,
    OPENAPI_LICENSE,
    OPENAPI_TAGS,
    SWAGGER_UI_PARAMETERS,
)
from app.schemas.base import HealthCheckResponse

cache = RedisCache(settings.redis_url, ttl_seconds=settings.cache_ttl_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    await cache.connect()
    _app.state.cache = cache
    yield
    await cache.close()
    await engine.dispose()


def create_app(app_settings: Settings = settings) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    docs_url = "/docs" if app_settings.docs_enabled else None
    redoc_url = "/redoc" if app_settings.docs_enabled else None
    openapi_url = "/openapi.json" if app_settings.docs_enabled else None

    application = FastAPI(
        title=app_settings.app_name,
        description=OPENAPI_DESCRIPTION,
        version=app_settings.app_version,
        openapi_tags=OPENAPI_TAGS,
        contact=OPENAPI_CONTACT,
        license_info=OPENAPI_LICENSE,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
        responses=GLOBAL_ERROR_RESPONSES,
        lifespan=lifespan,
    )

    application.add_middleware(RedisCacheMiddleware, cache=cache)
    application.add_middleware(RequestContextMiddleware)

    @application.exception_handler(AppException)
    async def app_exception_handler(
        _request: Request,
        exc: AppException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
            headers=exc.headers,
        )

    @application.exception_handler(IntegrityError)
    async def integrity_error_handler(
        _request: Request,
        _exc: IntegrityError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Database integrity conflict occurred"},
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        _exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @application.get(
        "/health",
        tags=["Health"],
        response_model=HealthCheckResponse,
        summary="Service liveness check",
        description="Verify that the TaskHub API process is up and responding to HTTP requests.",
        response_description="Service health status indicator.",
    )
    async def health() -> HealthCheckResponse:
        return HealthCheckResponse(status="ok")

    prefix = app_settings.api_v1_prefix
    application.include_router(auth.router, prefix=prefix)
    application.include_router(users.router, prefix=prefix)
    application.include_router(workspaces.router, prefix=prefix)
    application.include_router(projects.router, prefix=prefix)
    application.include_router(tasks.router, prefix=prefix)

    return application


app = create_app(settings)

