from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional, Sequence, Any, Generic
import uuid

T = TypeVar("T")

class BaseDAO(ABC, Generic[T]):
    model: Type[T] = None
    db: Type[T] = None
    
    @abstractmethod
    async def find_by_id(self, _id: uuid.UUID) -> Optional[T]:
        raise NotImplementedError
        
    @abstractmethod
    async def find_one_or_none(self, **filter_by) -> Optional[T]:
        raise NotImplementedError
        
    @abstractmethod
    async def find_all(self, **filter_by) -> Sequence[T]:
        raise NotImplementedError
        
    @abstractmethod
    async def insert_one(self, obj: Any) -> Optional[T]:
        raise NotImplementedError
        
    @abstractmethod
    async def update_one(self, obj: Any) -> Optional[T]:
        raise NotImplementedError
        
    @abstractmethod
    async def delete_one(self, _id: uuid.UUID) -> bool:
        raise NotImplementedError
