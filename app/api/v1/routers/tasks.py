from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.schemas.task import TaskCreate, TaskRead
from app.services.task_service import TaskService, get_task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, service: TaskServiceDep) -> TaskRead:
    return service.create(data)


@router.get("", response_model=list[TaskRead])
def list_tasks(service: TaskServiceDep) -> list[TaskRead]:
    return service.list_all()


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, service: TaskServiceDep) -> TaskRead:
    task = service.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskRead)
def replace_task(task_id: int, data: TaskCreate, service: TaskServiceDep) -> TaskRead:
    task = service.replace(task_id, data)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, service: TaskServiceDep) -> Response:
    if not service.delete(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
