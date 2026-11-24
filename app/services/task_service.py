from app.schemas.task import TaskCreate, TaskRead


class TaskService:
    def __init__(self) -> None:
        self._tasks: dict[int, TaskRead] = {}
        self._next_id = 1

    def create(self, data: TaskCreate) -> TaskRead:
        task = TaskRead(id=self._next_id, **data.model_dump())
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def list_all(self) -> list[TaskRead]:
        return list(self._tasks.values())

    def get(self, task_id: int) -> TaskRead | None:
        return self._tasks.get(task_id)

    def replace(self, task_id: int, data: TaskCreate) -> TaskRead | None:
        if task_id not in self._tasks:
            return None
        task = TaskRead(id=task_id, **data.model_dump())
        self._tasks[task_id] = task
        return task

    def delete(self, task_id: int) -> bool:
        if task_id not in self._tasks:
            return False
        del self._tasks[task_id]
        return True


# A single instance keeps tasks available between requests within this process.
_task_service = TaskService()


def get_task_service() -> TaskService:
    return _task_service
