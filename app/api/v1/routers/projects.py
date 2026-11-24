from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.v1.dependencies import (
    CurrentUserDep,
    TaskServiceDep,
    WorkspaceServiceDep,
)
from app.core.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.core.openapi import error_responses
from app.schemas.project import ProjectResponse, ProjectUpdate
from app.schemas.task import (
    ProjectTaskCreate,
    TaskListResponse,
    TaskResponse,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project by UUID",
    description="Retrieve project details by UUID. Requires membership in the parent workspace.",
    responses=error_responses(401, 403, 404),
)
async def get_project(
    project_id: UUID,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> ProjectResponse:
    return await service.get_project(project_id, current_user=current_user)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update or archive project (OWNER/ADMIN/EDITOR only)",
    description=(
        "Update project metadata (`name`, `description`) or transition its lifecycle `status` "
        "(`ACTIVE` / `ARCHIVED`). Requires `OWNER`, `ADMIN`, or `EDITOR` role in the workspace."
    ),
    responses=error_responses(401, 403, 404),
)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> ProjectResponse:
    return await service.update_project(
        project_id,
        data,
        current_user=current_user,
    )


@router.get(
    "/{project_id}/tasks",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List tasks in a project",
    description=(
        "Paginated list of tasks within the specified project. "
        "Cached via Redis when available."
    ),
    responses=error_responses(401, 403, 404),
)
async def list_project_tasks(
    project_id: UUID,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
    offset: Annotated[int, Query(ge=0, description="Number of tasks to skip")] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_LIMIT, description="Maximum tasks to return"),
    ] = DEFAULT_PAGE_LIMIT,
) -> TaskListResponse:
    return await service.list_all(
        current_user=current_user,
        project_id=project_id,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task in a project (OWNER/ADMIN/EDITOR only)",
    description=(
        "Create a new task inside an `ACTIVE` project. Rejects creation if the "
        "project is `ARCHIVED` or if `assignee_id` is not a workspace member."
    ),
    responses=error_responses(400, 401, 403, 404),
)
async def create_project_task(
    project_id: UUID,
    data: ProjectTaskCreate,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskResponse:
    return await service.create_in_project(
        project_id,
        data,
        current_user=current_user,
    )

