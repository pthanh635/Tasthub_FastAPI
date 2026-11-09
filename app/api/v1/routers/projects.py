from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.v1.dependencies import (
    CurrentUserDep,
    TaskServiceDep,
    WorkspaceServiceDep,
)
from app.schemas.project import ProjectResponse, ProjectUpdate
from app.schemas.task import ProjectTaskCreate, TaskResponse

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project by UUID",
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
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List tasks in a project",
)
async def list_project_tasks(
    project_id: UUID,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[TaskResponse]:
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

