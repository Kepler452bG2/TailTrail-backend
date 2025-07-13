import uuid
from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user_block import UserBlock
from src.repositories.base_repository import BaseRepository
from src.dao.sqlalchemy_dao import SQLAlchemyDAO


class UserBlockRepository(BaseRepository[UserBlock]):
    model = UserBlock
    dao_class = SQLAlchemyDAO
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
    
    async def create_block(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> UserBlock:
        """Создает блокировку пользователя"""
        user_block = UserBlock(
            blocker_id=blocker_id,
            blocked_id=blocked_id
        )
        return await self.insert_one(user_block)
    
    async def remove_block(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
        """Убирает блокировку пользователя"""
        query = select(UserBlock).where(
            and_(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id
            )
        )
        result = await self.dao.db.execute(query)
        user_block = result.scalars().first()
        
        if user_block:
            await self.dao.db.delete(user_block)
            await self.dao.db.commit()
            return True
        return False
    
    async def is_blocked(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> Optional[UserBlock]:
        """Проверяет заблокирован ли пользователь"""
        query = select(UserBlock).where(
            and_(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id
            )
        )
        result = await self.dao.db.execute(query)
        return result.scalars().first()
    
    async def get_blocked_users(self, blocker_id: uuid.UUID) -> List[UserBlock]:
        """Получает список заблокированных пользователей"""
        query = select(UserBlock).where(UserBlock.blocker_id == blocker_id)
        result = await self.dao.db.execute(query)
        return result.scalars().all()
    
    async def get_blocked_user_ids(self, blocker_id: uuid.UUID) -> List[uuid.UUID]:
        """Получает список ID заблокированных пользователей"""
        query = select(UserBlock.blocked_id).where(UserBlock.blocker_id == blocker_id)
        result = await self.dao.db.execute(query)
        return result.scalars().all()
    
    async def get_users_who_blocked(self, blocked_id: uuid.UUID) -> List[UserBlock]:
        """Получает список пользователей, которые заблокировали данного пользователя"""
        query = select(UserBlock).where(UserBlock.blocked_id == blocked_id)
        result = await self.dao.db.execute(query)
        return result.scalars().all()
    
    async def get_blocker_ids_who_blocked(self, blocked_id: uuid.UUID) -> List[uuid.UUID]:
        """Получает список ID пользователей, которые заблокировали данного пользователя"""
        query = select(UserBlock.blocker_id).where(UserBlock.blocked_id == blocked_id)
        result = await self.dao.db.execute(query)
        return result.scalars().all()
    
    async def count_blocked_users(self, blocker_id: uuid.UUID) -> int:
        """Подсчитывает количество заблокированных пользователей"""
        query = select(func.count(UserBlock.id)).where(UserBlock.blocker_id == blocker_id)
        result = await self.dao.db.execute(query)
        return result.scalar() or 0 