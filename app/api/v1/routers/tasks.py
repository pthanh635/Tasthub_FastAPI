from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.exceptions import EntityNotFoundError
from app.repositories.task_repository import TaskRepository, get_task_repository
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

TaskRepositoryDep = Annotated[TaskRepository, Depends(get_task_repository)]


def get_task_service(repository: TaskRepositoryDep) -> TaskService:
    return TaskService(repository)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
async def create_task(data: TaskCreate, service: TaskServiceDep) -> TaskResponse:
    try:
        return await service.create(data)
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List tasks with pagination",
)
async def list_tasks(
    service: TaskServiceDep,
    offset: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Max records to return")
    ] = 100,
) -> list[TaskResponse]:
    return await service.list_all(offset=offset, limit=limit)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a task by UUID",
)
async def get_task(task_id: UUID, service: TaskServiceDep) -> TaskResponse:
    try:
        return await service.get(task_id)
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update all editable fields of a task",
)
async def replace_task(
    task_id: UUID,
    data: TaskUpdate,
    service: TaskServiceDep,
) -> TaskResponse:
    try:
        return await service.replace(task_id, data)
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task by UUID",
)
async def delete_task(task_id: UUID, service: TaskServiceDep) -> Response:
    try:
        await service.delete(task_id)
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
