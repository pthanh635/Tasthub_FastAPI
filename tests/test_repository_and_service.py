import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.core.seed import SeedContext
from app.models import TaskPriority, TaskStatus, User
from app.repositories.base import BaseRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task_service import TaskService


async def test_base_repository_crud(db_session: AsyncSession) -> None:
    """Verify generic BaseRepository[User] get_by_id, get_all, create, update, and delete."""
    user_repo = BaseRepository(User, db_session)

    created = await user_repo.create(
        {
            "email": "repo-user@taskhub.local",
            "hashed_password": "hashed-password",
            "full_name": "Repo User",
            "is_active": True,
        }
    )
    assert created.id is not None
    assert created.email == "repo-user@taskhub.local"

    fetched = await user_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.full_name == "Repo User"

    all_users = await user_repo.get_all(offset=0, limit=10)
    assert len(all_users) == 1

    updated = await user_repo.update(created, {"full_name": "Updated Repo User"})
    assert updated.full_name == "Updated Repo User"

    await user_repo.delete(updated)
    assert await user_repo.get_by_id(created.id) is None


async def test_task_repository_queries(
    db_session: AsyncSession,
    seed_context: SeedContext,
) -> None:
    """Verify TaskRepository specialized lookup methods and ordering."""
    repo = TaskRepository(db_session)

    owner_id = await repo.get_project_owner_id(seed_context.project_id)
    assert owner_id == seed_context.user_id
    assert await repo.get_project_owner_id(uuid.uuid4()) is None

    assert await repo.user_exists(seed_context.user_id) is True
    assert await repo.user_exists(uuid.uuid4()) is False


async def test_task_service_crud_and_domain_errors(
    db_session: AsyncSession,
    seed_context: SeedContext,
) -> None:
    """Verify TaskService business logic, foreign key validation, and domain exceptions."""
    repo = TaskRepository(db_session)
    service = TaskService(repo)
    current_user = await db_session.get(User, seed_context.user_id)
    assert current_user is not None

    due = datetime(2026, 12, 31, 12, 0, tzinfo=UTC)
    created = await service.create(
        TaskCreate(
            project_id=seed_context.project_id,
            title="Implement TaskService",
            description="Async service layer",
            priority=TaskPriority.HIGH,
            assignee_id=seed_context.user_id,
            due_date=due,
        ),
        current_user=current_user,
    )
    assert created.project_id == seed_context.project_id
    assert created.created_by_id == seed_context.user_id
    assert created.assignee_id == seed_context.user_id
    assert created.priority == TaskPriority.HIGH

    fetched = await service.get(created.id, current_user=current_user)
    assert fetched.id == created.id

    tasks = await service.list_all(
        current_user=current_user,
        offset=0,
        limit=10,
    )
    assert len(tasks.items) == 1
    assert tasks.total == 1

    updated = await service.replace(
        created.id,
        TaskUpdate(
            title="Completed TaskService",
            description="All tests green",
            status=TaskStatus.DONE,
            priority=TaskPriority.URGENT,
            assignee_id=None,
            due_date=None,
        ),
        current_user=current_user,
    )
    assert updated.title == "Completed TaskService"
    assert updated.status == TaskStatus.DONE
    assert updated.priority == TaskPriority.URGENT
    assert updated.assignee_id is None

    await service.delete(created.id, current_user=current_user)

    with pytest.raises(TaskNotFoundError):
        await service.get(created.id, current_user=current_user)

    with pytest.raises(TaskNotFoundError):
        await service.replace(
            created.id,
            TaskUpdate(title="Missing"),
            current_user=current_user,
        )

    with pytest.raises(TaskNotFoundError):
        await service.delete(created.id, current_user=current_user)

    with pytest.raises(ProjectNotFoundError):
        await service.create(
            TaskCreate(project_id=uuid.uuid4(), title="Invalid Project"),
            current_user=current_user,
        )

    with pytest.raises(UserNotFoundError):
        await service.create(
            TaskCreate(
                project_id=seed_context.project_id,
                title="Invalid Assignee",
                assignee_id=uuid.uuid4(),
            ),
            current_user=current_user,
        )
