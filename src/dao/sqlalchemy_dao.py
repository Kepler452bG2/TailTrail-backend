from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import uuid
from typing import Type, TypeVar, Optional, Sequence, Any, Generic

from src.logger import logger
from dao.base_dao import BaseDAO
from dependencies import DBSessionDep

T = TypeVar("T")

class SQLAlchemyDAO(BaseDAO, Generic[T]):
    db: DBSessionDep = DBSessionDep
    
    def __init__(self, model: Type[T]):
        self.model = model
        
    async def _execute_db_operation(self, operation):
        return await operation(self.db)
    
    async def find_by_id(self, _id: uuid.UUID) -> Optional[T]:
        async def operation(session):
            result = await session.execute(select(self.model).where(self.model.id == _id))
            return result.scalars().first()
        return await self._execute_db_operation(operation, self.db)

    async def find_one_or_none(self, **filter_by) -> Optional[T]:
        async def operation(session):
            query = select(self.model).filter_by(**filter_by)
            result = await session.execute(query)
            return result.scalar_one_or_none()
        return await self._execute_db_operation(operation, self.db)

    async def find_all(self, **filter_by) -> Sequence[T]:
        async def operation(session):
            query = select(self.model).filter_by(**filter_by)
            result = await session.execute(query)
            return result.scalars().all()
        return await self._execute_db_operation(operation, self.db)

    async def insert_one(self, obj: Any) -> Optional[T]:
        async def operation(session):
            try:
                session.add(obj)
                await session.commit()
                await session.refresh(obj)
                logger.info(f"Inserted new {self.model.__name__} with ID: {obj.id}")
                return obj
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"IntegrityError while inserting {self.model.__name__}: {e}")
                return None
        return await self._execute_db_operation(operation, self.db)
            
    async def update_one(self, obj: Any) -> Optional[T]:
        async def operation(session):
            try:
                result = await session.execute(select(self.model).where(self.model.id == obj.id))
                existing = result.scalars().first()
                if not existing:
                    logger.error(f"{self.model.__name__} with ID: {obj.id} not found for update")
                    return None

                merged_obj = await session.merge(obj)
                await session.commit()
                logger.info(f"Updated {self.model.__name__} with ID: {obj.id}")
                return merged_obj
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"IntegrityError while updating {self.model.__name__}: {e}")
                return None
        return await self._execute_db_operation(operation, self.db)
            
    async def delete_one(self, _id: uuid.UUID) -> bool:
        async def operation(session):
            try:
                result = await session.execute(select(self.model).where(self.model.id == _id))
                obj = result.scalars().first()
                if not obj:
                    logger.error(f"{self.model.__name__} with ID: {_id} not found for deletion")
                    return False
                    
                await session.delete(obj)
                await session.commit()
                logger.info(f"Deleted {self.model.__name__} with ID: {_id}")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Error while deleting {self.model.__name__}: {e}")
                return False
        return await self._execute_db_operation(operation, self.db)
