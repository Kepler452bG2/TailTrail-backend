from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dao.sqlalchemy_dao import SQLAlchemyDAO
from src.models.user import User
from src.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User
    dao_class = SQLAlchemyDAO

    async def get_online_users(self) -> List[User]:
        """Получить список онлайн пользователей"""
        query = select(User).where(User.is_online == True)
        result = await self.session.execute(query)
        return result.scalars().all()