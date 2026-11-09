from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.v1.dependencies import (
    CurrentUserDep,
    TaskServiceDep,
    get_task_service,
)
from app.schemas.task import TaskCreate, TaskPatch, TaskResponse, TaskUpdate

__all__ = ["get_task_service", "router"]

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task (requires OWNER/ADMIN/EDITOR in workspace)",
)
async def create_task(
    data: TaskCreate,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskResponse:
    return await service.create(data, current_user=current_user)


@router.get(
    "",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List tasks accessible to current user with pagination",
)
async def list_tasks(
    current_user: CurrentUserDep,
    service: TaskServiceDep,
    project_id: Annotated[
        UUID | None,
        Query(description="Optional project UUID filter"),
    ] = None,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of records to skip"),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Max records to return"),
    ] = 100,
) -> list[TaskResponse]:
    return await service.list_all(
        current_user=current_user,
        project_id=project_id,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a task by UUID",
)
async def get_task(
    task_id: UUID,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskResponse:
    return await service.get(task_id, current_user=current_user)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update all editable fields of a task (OWNER/ADMIN/EDITOR)",
)
async def replace_task(
    task_id: UUID,
    data: TaskUpdate,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskResponse:
    return await service.replace(task_id, data, current_user=current_user)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update a task (OWNER/ADMIN/EDITOR)",
)
async def patch_task(
    task_id: UUID,
    data: TaskPatch,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskResponse:
    return await service.patch(task_id, data, current_user=current_user)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task by UUID (creator, workspace OWNER/ADMIN, or global ADMIN)",
)
async def delete_task(
    task_id: UUID,
    current_user: CurrentUserDep,
    service: TaskServiceDep,
) -> Response:
    await service.delete(task_id, current_user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
