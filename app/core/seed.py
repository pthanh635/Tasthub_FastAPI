import asyncio
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.enums import ProjectStatus, UserRole, WorkspaceRole
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember

DEFAULT_SEED_WORKSPACE_NAME = "Default Workspace"
DEFAULT_SEED_PROJECT_NAME = "Default Project"


@dataclass(frozen=True)
class SeedContext:
    user_id: UUID
    workspace_id: UUID
    project_id: UUID


async def seed_initial_data(session: AsyncSession) -> SeedContext:
    """Idempotently seed a default User, Workspace, WorkspaceMember, and Project."""
    user_email = settings.seed_admin_email.strip().lower()
    user_password = settings.seed_admin_password

    user_stmt = select(User).where(User.email == user_email)
    user = (await session.scalars(user_stmt)).first()

    if user is None:
        if not user_password:
            raise RuntimeError(
                "SEED_ADMIN_PASSWORD must be configured before creating an admin"
            )

        user = User(
            email=user_email,
            hashed_password=hash_password(user_password),
            full_name="TaskHub Seed Owner",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        await session.flush()

    workspace_stmt = select(Workspace).where(
        Workspace.owner_id == user.id,
        Workspace.name == DEFAULT_SEED_WORKSPACE_NAME,
    )
    workspace = (await session.scalars(workspace_stmt)).first()
    if workspace is None:
        workspace = Workspace(
            name=DEFAULT_SEED_WORKSPACE_NAME,
            description="Seeded workspace for TaskHub",
            owner_id=user.id,
        )
        session.add(workspace)
        await session.flush()

    member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == user.id,
    )
    member = (await session.scalars(member_stmt)).first()
    if member is None:
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRole.OWNER,
        )
        session.add(member)
        await session.flush()

    project_stmt = select(Project).where(
        Project.workspace_id == workspace.id,
        Project.name == DEFAULT_SEED_PROJECT_NAME,
    )
    project = (await session.scalars(project_stmt)).first()
    if project is None:
        project = Project(
            workspace_id=workspace.id,
            name=DEFAULT_SEED_PROJECT_NAME,
            description="Seeded project for TaskHub",
            status=ProjectStatus.ACTIVE,
        )
        session.add(project)
        await session.flush()

    return SeedContext(
        user_id=user.id,
        workspace_id=workspace.id,
        project_id=project.id,
    )


async def _run_cli_seed() -> None:
    async with AsyncSessionLocal() as session:
        context = await seed_initial_data(session)
        await session.commit()
        print(
            f"Seeded successfully -> user_id={context.user_id}, "
            f"workspace_id={context.workspace_id}, project_id={context.project_id}"
        )


if __name__ == "__main__":
    asyncio.run(_run_cli_seed())
