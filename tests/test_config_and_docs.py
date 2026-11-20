from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings, resolve_env_files
from app.core.constants import AppEnvironment
from app.main import create_app

VALID_SECRET = "a-very-strong-and-unique-secret-key-with-at-least-32-chars"
VALID_PROD_DB = "postgresql+asyncpg://prod_user:StrongProdPass99!@db.internal:5432/taskhub_prod"
VALID_ADMIN_PASSWORD = "SafeAdminPassword938!"


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


def test_settings_bootstrap_and_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    for key in ("APP_ENV", "APP_NAME", "CACHE_TTL_SECONDS", "JWT_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        f"APP_ENV=staging\nAPP_NAME=BaseApp\nCACHE_TTL_SECONDS=30\nJWT_SECRET_KEY={VALID_SECRET}\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.staging").write_text(
        "APP_NAME=EnvironmentApp\nCACHE_TTL_SECONDS=120\n", encoding="utf-8"
    )
    (tmp_path / ".env.testing").write_text(
        "APP_NAME=TestingEnvironmentApp\nCACHE_TTL_SECONDS=90\n", encoding="utf-8"
    )

    from_env_files = Settings()
    assert from_env_files.app_env == AppEnvironment.STAGING
    assert from_env_files.app_name == "EnvironmentApp"
    assert from_env_files.cache_ttl_seconds == 120

    monkeypatch.setenv("APP_NAME", "OperatingSystemApp")
    monkeypatch.setenv("APP_ENV", "testing")
    from_os_environment = Settings()
    assert from_os_environment.app_env == AppEnvironment.TESTING
    assert from_os_environment.app_name == "OperatingSystemApp"
    assert from_os_environment.cache_ttl_seconds == 90


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
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY must not contain a placeholder"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.PRODUCTION,
            debug=False,
            jwt_secret_key="change-this-to-a-secure-random-secret-key-at-least-32-bytes",
            database_url=VALID_PROD_DB,
        )

    # 3. Default 'changeme' DB password is forbidden in production
    with pytest.raises(
        ValidationError,
        match="DATABASE_URL password must not contain a placeholder",
    ):
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
        seed_admin_password=VALID_ADMIN_PASSWORD,
    )
    assert prod.is_production is True
    assert prod.docs_enabled is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("jwt_secret_key", "A-PLACEHOLDER-secret-value-that-is-long-enough-123"),
        ("jwt_secret_key", "A-DuMmY-secret-value-that-is-long-enough-123456"),
        ("database_url", "postgresql+asyncpg://u:EXAMPLE-pass@db:5432/app"),
        ("database_url", "postgresql+asyncpg://u:dummy@db:5432/app"),
        ("seed_admin_password", "REPLACE_WITH_a_secure_password"),
        ("seed_admin_password", "changeme-admin-password"),
    ],
)
def test_production_rejects_placeholder_credentials(field: str, value: str) -> None:
    kwargs: dict[str, object] = {
        "_env_file": None,
        "app_env": AppEnvironment.PRODUCTION,
        "jwt_secret_key": VALID_SECRET,
        "database_url": VALID_PROD_DB,
        "seed_admin_password": VALID_ADMIN_PASSWORD,
    }
    kwargs[field] = value
    with pytest.raises(ValidationError) as error:
        Settings(**kwargs)
    assert value not in str(error.value)


def test_production_requires_seed_admin_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)
    with pytest.raises(ValidationError, match="SEED_ADMIN_PASSWORD is required"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.PRODUCTION,
            jwt_secret_key=VALID_SECRET,
            database_url=VALID_PROD_DB,
        )


def test_production_example_fails_startup_without_leaking_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)
    example_path = Path(__file__).parents[1] / ".env.production.example"
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=str(example_path))
    rendered_error = str(error.value)
    assert "REPLACE_WITH" not in rendered_error
    assert "STRONG_PASSWORD" not in rendered_error
    assert "JWT_SECRET_KEY must not contain a placeholder" in rendered_error


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
        seed_admin_password=VALID_ADMIN_PASSWORD,
    )
    prod_app = create_app(prod_settings)
    transport = ASGITransport(app=prod_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/docs")).status_code == 404
        assert (await client.get("/redoc")).status_code == 404
        assert (await client.get("/openapi.json")).status_code == 404
        assert (await client.get("/health")).status_code == 200
