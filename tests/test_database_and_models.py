import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import get_db_session
from app.core.seed import SeedContext, seed_initial_data
from app.models import (
    Comment,
    Label,
    Project,
    Task,
    TaskLabel,
    TaskPriority,
    TaskStatus,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)


async def test_database_connection_and_session(db_session: AsyncSession) -> None:
    """Verify async database connection and session query execution."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


async def test_get_db_session_commits_and_rolls_back(
    db_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify services own commits and the session rolls back on request errors."""
    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    monkeypatch.setattr("app.core.database.AsyncSessionLocal", factory)

    gen = get_db_session()
    session = await anext(gen)
    user = User(
        email="session-commit@taskhub.local",
        hashed_password="hash",
        full_name="Commit User",
    )
    session.add(user)
    with pytest.raises(StopAsyncIteration):
        await anext(gen)

    async with factory() as verify_session:
        saved = (
            await verify_session.scalars(
                select(User).where(User.email == "session-commit@taskhub.local")
            )
        ).first()
        assert saved is None

    gen_rollback = get_db_session()
    session_rb = await anext(gen_rollback)
    session_rb.add(
        User(
            email="session-rollback@taskhub.local",
            hashed_password="hash",
            full_name="Rollback User",
        )
    )
    await session_rb.flush()
    with pytest.raises(RuntimeError, match="simulated failure"):
        await gen_rollback.athrow(RuntimeError("simulated failure"))

    async with factory() as verify_session:
        rolled_back = (
            await verify_session.scalars(
                select(User).where(User.email == "session-rollback@taskhub.local")
            )
        ).first()
        assert rolled_back is None


async def test_unique_constraints(
    db_session: AsyncSession,
    seed_context: SeedContext,
) -> None:
    """Verify unique constraints on users, workspace_members, and labels."""
    duplicate_user = User(
        email="owner@taskhub.dev",
        hashed_password="hash",
        full_name="Duplicate Email User",
    )
    db_session.add(duplicate_user)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    duplicate_member = WorkspaceMember(
        workspace_id=seed_context.workspace_id,
        user_id=seed_context.user_id,
        role=WorkspaceRole.ADMIN,
    )
    db_session.add(duplicate_member)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    label_1 = Label(
        workspace_id=seed_context.workspace_id,
        name="Backend",
        color="#FF0000",
    )
    db_session.add(label_1)
    await db_session.flush()

    label_2 = Label(
        workspace_id=seed_context.workspace_id,
        name="Backend",
        color="#00FF00",
    )
    db_session.add(label_2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_foreign_key_constraints_and_relationships(
    db_session: AsyncSession,
    seed_context: SeedContext,
) -> None:
    """Verify foreign keys, relationships, and dependent-row cascades."""
    invalid_task = Task(
        project_id=uuid.uuid4(),
        title="Orphan task",
        created_by_id=seed_context.user_id,
    )
    db_session.add(invalid_task)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    task = Task(
        project_id=seed_context.project_id,
        title="Design schema",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        created_by_id=seed_context.user_id,
        assignee_id=seed_context.user_id,
    )
    label = Label(
        workspace_id=seed_context.workspace_id,
        name="Database",
        color="#3366FF",
    )
    db_session.add_all([task, label])
    await db_session.flush()

    task_label = TaskLabel(task_id=task.id, label_id=label.id)
    comment = Comment(
        task_id=task.id,
        author_id=seed_context.user_id,
        content="Schema looks solid!",
    )
    db_session.add_all([task_label, comment])
    await db_session.commit()

    await db_session.refresh(task, attribute_names=["comments", "labels"])
    assert len(task.comments) == 1
    assert task.comments[0].content == "Schema looks solid!"
    assert len(task.labels) == 1
    assert task.labels[0].name == "Database"

    project = await db_session.get(Project, seed_context.project_id)
    assert project is not None
    await db_session.delete(project)
    await db_session.flush()
    await db_session.commit()
    remaining_task = await db_session.scalars(
        select(Task).where(Task.id == task.id)
    )
    assert remaining_task.first() is None
    assert await db_session.get(Label, label.id) is not None


async def test_seed_initial_data_is_idempotent(db_session: AsyncSession) -> None:
    """Verify seed_initial_data is idempotent and does not duplicate records."""
    first = await seed_initial_data(db_session)
    second = await seed_initial_data(db_session)
    assert first == second

    workspaces = (await db_session.scalars(select(Workspace))).all()
    assert len(workspaces) == 1
