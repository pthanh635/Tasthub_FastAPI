from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import create_access_token
from app.core.seed import SeedContext, seed_initial_data
from app.main import app
from app.models import Base, UserRole


def get_test_database_url() -> str:
    """Resolve dedicated PostgreSQL test database URL and prevent touching dev/prod DB."""
    dev_url = make_url(settings.database_url)
    if settings.test_database_url:
        test_url = make_url(settings.test_database_url)
        if test_url.password == "changeme" and dev_url.password != "changeme":
            test_url = test_url.set(
                username=dev_url.username,
                password=dev_url.password,
                host=dev_url.host,
                port=dev_url.port,
            )
    else:
        test_url = dev_url.set(database=f"{dev_url.database}_test")

    if test_url.database == dev_url.database:
        raise RuntimeError(
            "Refusing to run destructive tests on the development/production database."
        )
    return test_url.render_as_string(hide_password=False)


@pytest.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an isolated async PostgreSQL test engine for each test function."""
    engine = create_async_engine(
        get_test_database_url(),
        poolclass=NullPool,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
async def session_factory(
    db_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def seed_context(db_session: AsyncSession) -> SeedContext:
    context = await seed_initial_data(db_session)
    await db_session.commit()
    return context


@pytest.fixture
def auth_headers(seed_context: SeedContext) -> dict[str, str]:
    """Return Bearer Authorization headers for the seeded owner user."""
    token = create_access_token(
        subject=seed_context.user_id,
        role=UserRole.ADMIN.value,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def async_client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()
