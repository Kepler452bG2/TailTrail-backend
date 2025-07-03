import uuid
from typing import Type, TypeVar, Optional, Sequence, Any, Generic

from dao.base_dao import BaseDAO
from src.logger import logger

from abc import ABC, abstractmethod

T = TypeVar("T")

class BaseRepository(ABC, Generic[T]):
    model: Type[T] = None
    dao_class = BaseDAO
    
    def __init__(self):
        self.dao = self.dao_class(self.model)
    
    async def find_by_id(self, _id: uuid.UUID) -> Optional[T]:
        return await self.dao.find_by_id(_id)

    async def find_one_or_none(self, **filter_by) -> Optional[T]:
        return await self.dao.find_one_or_none()

    async def find_all(self, db, **filter_by) -> Sequence[T]:
        return await self.dao.find_all(db, **filter_by)

    async def insert_one(self, obj: Any) -> Optional[T]:
        return await self.dao.insert_one(obj)
        
    async def update_one(self, obj: Any) -> Optional[T]:
        return await self.dao.update_one(obj)
        
    async def delete_one(self, _id: uuid.UUID) -> bool:
        return await self.dao.delete_one(_id)