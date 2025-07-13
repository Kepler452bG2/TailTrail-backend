import uuid
from typing import List, Optional, Sequence
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.dao.sqlalchemy_dao import SQLAlchemyDAO
from src.models.block import Block
from src.models.user import User
from src.repositories.base_repository import BaseRepository


class BlockRepository(BaseRepository[Block]):
    model = Block
    dao_class = SQLAlchemyDAO

    async def create_block(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> Block:
        """Create a new block"""
        block = Block(
            blocker_id=blocker_id,
            blocked_id=blocked_id
        )
        return await self.dao.insert_one(block)

    async def remove_block(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
        """Remove a block"""
        query = select(self.model).where(
            and_(
                self.model.blocker_id == blocker_id,
                self.model.blocked_id == blocked_id
            )
        )
        result = await self.dao.db.execute(query)
        block = result.scalar_one_or_none()
        
        if block:
            return await self.dao.delete_one(block.id)
        return False

    async def is_blocked(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
        """Check if user is blocked"""
        query = select(self.model).where(
            and_(
                self.model.blocker_id == blocker_id,
                self.model.blocked_id == blocked_id
            )
        )
        result = await self.dao.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_blocked_users(self, blocker_id: uuid.UUID) -> Sequence[Block]:
        """Get all users blocked by a specific user"""
        query = select(self.model).options(
            selectinload(self.model.blocked)
        ).where(self.model.blocker_id == blocker_id)
        
        result = await self.dao.db.execute(query)
        return result.scalars().all()

    async def get_blocked_user_ids(self, blocker_id: uuid.UUID) -> List[uuid.UUID]:
        """Get list of blocked user IDs for a specific user"""
        query = select(self.model.blocked_id).where(self.model.blocker_id == blocker_id)
        result = await self.dao.db.execute(query)
        return list(result.scalars().all())

    async def get_users_who_blocked(self, blocked_id: uuid.UUID) -> List[uuid.UUID]:
        """Get list of users who blocked a specific user"""
        query = select(self.model.blocker_id).where(self.model.blocked_id == blocked_id)
        result = await self.dao.db.execute(query)
        return list(result.scalars().all()) 