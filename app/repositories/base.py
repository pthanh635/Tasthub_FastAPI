from collections.abc import Mapping
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic asynchronous repository for SQLAlchemy 2.x CRUD operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def get_by_id(self, entity_id: UUID) -> ModelType | None:
        return await self._session.get(self._model, entity_id)

    async def get_all(self, *, offset: int = 0, limit: int = 100) -> list[ModelType]:
        statement = select(self._model).offset(offset).limit(limit)
        result = await self._session.scalars(statement)
        return list(result.all())

    async def create(self, data: Mapping[str, object]) -> ModelType:
        instance = self._model(**data)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(
        self,
        instance: ModelType,
        data: Mapping[str, object],
    ) -> ModelType:
        for field_name, value in data.items():
            setattr(instance, field_name, value)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self._session.delete(instance)
        await self._session.flush()

