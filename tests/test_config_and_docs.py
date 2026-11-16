from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings, resolve_env_files
from app.core.constants import AppEnvironment
from app.main import create_app

VALID_SECRET = "a-very-strong-and-unique-secret-key-with-at-least-32-chars"
VALID_PROD_DB = "postgresql+asyncpg://prod_user:StrongProdPass99!@db.internal:5432/taskhub_prod"


def test_resolve_env_files_by_environment() -> None:
    assert resolve_env_files("development") == (".env", ".env.development")
    assert resolve_env_files("testing") == (".env", ".env.testing")
    assert resolve_env_files("PRODUCTION") == (".env", ".env.production")


def test_settings_environment_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    dev = Settings(
        _env_file=None,
        app_env=AppEnvironment.DEVELOPMENT,
        jwt_secret_key=VALID_SECRET,
    )
    assert dev.app_env == AppEnvironment.DEVELOPMENT
    assert dev.is_development is True
    assert dev.is_production is False

    test_cfg = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        jwt_secret_key=VALID_SECRET,
    )
    assert test_cfg.is_testing is True

    staging_cfg = Settings(
        _env_file=None,
        app_env=AppEnvironment.STAGING,
        jwt_secret_key=VALID_SECRET,
    )
    assert staging_cfg.is_staging is True


def test_settings_multi_environment_file_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("CACHE_TTL_SECONDS", raising=False)

    base_env = tmp_path / ".env"
    base_env.write_text(
        f"APP_NAME=BaseApp\nCACHE_TTL_SECONDS=30\nJWT_SECRET_KEY={VALID_SECRET}\n",
        encoding="utf-8",
    )
    staging_env = tmp_path / ".env.staging"
    staging_env.write_text(
        "APP_ENV=staging\nAPP_NAME=StagingApp\nCACHE_TTL_SECONDS=120\n",
        encoding="utf-8",
    )

    cfg = Settings(
        _env_file=(str(base_env), str(staging_env)),
        jwt_secret_key=VALID_SECRET,
    )
    assert cfg.app_env == AppEnvironment.STAGING
    assert cfg.app_name == "StagingApp"
    assert cfg.cache_ttl_seconds == 120
    assert cfg.jwt_secret_key == VALID_SECRET


def test_settings_fail_fast_invalid_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret_key="too-short")


def test_settings_fail_fast_invalid_database_url_scheme() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL must start with one of"):
        Settings(
            _env_file=None,
            jwt_secret_key=VALID_SECRET,
            database_url="mysql://localhost:3306/taskhub",
        )


def test_settings_fail_fast_test_db_matches_primary_db() -> None:
    same_url = "postgresql+asyncpg://postgres:pass@localhost:5432/taskhub"
    with pytest.raises(
        ValidationError,
        match="TEST_DATABASE_URL must not point to the same database as DATABASE_URL",
    ):
        Settings(
            _env_file=None,
            jwt_secret_key=VALID_SECRET,
            database_url=same_url,
            test_database_url=same_url,
        )


def test_settings_fail_fast_invalid_redis_url_and_jwt_algorithm() -> None:
    with pytest.raises(ValidationError, match="REDIS_URL must start with one of"):
        Settings(
            _env_file=None,
            jwt_secret_key=VALID_SECRET,
            redis_url="http://localhost:6379/0",
        )

    with pytest.raises(ValidationError, match="JWT_ALGORITHM must be one of"):
        Settings(
            _env_file=None,
            jwt_secret_key=VALID_SECRET,
            jwt_algorithm="none",
        )

    with pytest.raises(ValidationError, match="API_V1_PREFIX must start with '/'"):
        Settings(
            _env_file=None,
            jwt_secret_key=VALID_SECRET,
            api_v1_prefix="api/v1",
        )


def test_settings_production_fail_fast_validation() -> None:
    # 1. DEBUG=True is forbidden in production
    with pytest.raises(ValidationError, match="DEBUG must be False"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.PRODUCTION,
            debug=True,
            jwt_secret_key=VALID_SECRET,
            database_url=VALID_PROD_DB,
        )

    # 2. Placeholder JWT_SECRET_KEY is forbidden in production
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY must not use an example"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.PRODUCTION,
            debug=False,
            jwt_secret_key="change-this-to-a-secure-random-secret-key-at-least-32-bytes",
            database_url=VALID_PROD_DB,
        )

    # 3. Default 'changeme' DB password is forbidden in production
    with pytest.raises(ValidationError, match="DATABASE_URL must not use default 'changeme'"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.PRODUCTION,
            debug=False,
            jwt_secret_key=VALID_SECRET,
            database_url="postgresql+asyncpg://postgres:changeme@db.internal:5432/taskhub",
        )

    # 4. Valid production config succeeds
    prod = Settings(
        _env_file=None,
        app_env=AppEnvironment.PRODUCTION,
        debug=False,
        docs_enabled=False,
        jwt_secret_key=VALID_SECRET,
        database_url=VALID_PROD_DB,
    )
    assert prod.is_production is True
    assert prod.docs_enabled is False


async def test_swagger_ui_redoc_and_openapi_documentation(
    async_client: AsyncClient,
) -> None:
    swagger_resp = await async_client.get("/docs")
    assert swagger_resp.status_code == 200
    assert "Swagger UI" in swagger_resp.text
    assert "persistAuthorization" in swagger_resp.text

    redoc_resp = await async_client.get("/redoc")
    assert redoc_resp.status_code == 200
    assert "ReDoc" in redoc_resp.text

    openapi_resp = await async_client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()

    # Metadata verification
    assert schema["info"]["title"] == "TaskHub API"
    assert "BearerAuth" in schema["info"]["description"]
    assert "contact" in schema["info"]
    assert "license" in schema["info"]

    # Tags verification
    tag_names = {tag["name"] for tag in schema["tags"]}
    assert {
        "Health",
        "Authentication",
        "Users",
        "Workspaces",
        "Projects",
        "Tasks",
    }.issubset(tag_names)

    # Security scheme & ErrorResponse schema verification
    assert "BearerAuth" in schema["components"]["securitySchemes"]
    assert "ErrorResponse" in schema["components"]["schemas"]
    assert "InternalErrorResponse" in schema["components"]["schemas"]

    # Endpoint error response documentation verification
    login_responses = schema["paths"]["/api/v1/auth/login"]["post"]["responses"]
    assert "401" in login_responses
    assert "403" in login_responses
    assert "500" in login_responses

    workspace_responses = schema["paths"]["/api/v1/workspaces/{workspace_id}"]["delete"][
        "responses"
    ]
    assert "401" in workspace_responses
    assert "403" in workspace_responses
    assert "404" in workspace_responses


async def test_docs_disabled_in_production_mode() -> None:
    prod_settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.PRODUCTION,
        debug=False,
        docs_enabled=False,
        jwt_secret_key=VALID_SECRET,
        database_url=VALID_PROD_DB,
    )
    prod_app = create_app(prod_settings)
    transport = ASGITransport(app=prod_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/docs")).status_code == 404
        assert (await client.get("/redoc")).status_code == 404
        assert (await client.get("/openapi.json")).status_code == 404
        assert (await client.get("/health")).status_code == 200
