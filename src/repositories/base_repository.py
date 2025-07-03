import uuid
from abc import ABC
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from src.dao.base_dao import BaseDAO

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    model: type[T] = None
    dao_class = BaseDAO

    def __init__(self, db: AsyncSession):
        self.dao = self.dao_class(self.model, db)

    async def find_by_id(self, _id: uuid.UUID) -> T | None:
        return await self.dao.find_by_id(_id)

    async def find_one_or_none(self, **filter_by) -> T | None:
        return await self.dao.find_one_or_none(**filter_by)

    async def find_all(self, **filter_by) -> Sequence[T]:
        return await self.dao.find_all(**filter_by)

    async def insert_one(self, obj: Any) -> T | None:
        return await self.dao.insert_one(obj)

    async def update_one(self, obj: Any) -> T | None:
        return await self.dao.update_one(obj)

    async def delete_one(self, _id: uuid.UUID) -> bool:
        return await self.dao.delete_one(_id)