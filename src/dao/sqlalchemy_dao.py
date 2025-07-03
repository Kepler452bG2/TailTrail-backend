import uuid
from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.dao.base_dao import BaseDAO
from src.logger import logger

T = TypeVar("T")


class SQLAlchemyDAO(BaseDAO, Generic[T]):
    def __init__(self, model: type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def find_by_id(self, _id: uuid.UUID) -> T | None:
        result = await self.db.execute(select(self.model).where(self.model.id == _id))
        return result.scalars().first()

    async def find_one_or_none(self, **filter_by) -> T | None:
        query = select(self.model).filter_by(**filter_by)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_all(self, **filter_by) -> Sequence[T]:
        query = select(self.model).filter_by(**filter_by)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def insert_one(self, obj: T) -> T | None:
        try:
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Inserted new {self.model.__name__} with ID: {obj.id}")
            return obj
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"IntegrityError while inserting {self.model.__name__}: {e}")
            return None

    async def update_one(self, obj: T) -> T | None:
        try:
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated {self.model.__name__} with ID: {obj.id}")
            return obj
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"IntegrityError while updating {self.model.__name__}: {e}")
            return None

    async def delete_one(self, _id: uuid.UUID) -> bool:
        try:
            obj = await self.db.get(self.model, _id)
            if not obj:
                logger.error(f"{self.model.__name__} with ID: {_id} not found")
                return False

            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted {self.model.__name__} with ID: {_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            return False