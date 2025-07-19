from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import joinedload

from src.dao.sqlalchemy_dao import SQLAlchemyDAO
from src.models import Message, User
from src.repositories.base_repository import BaseRepository


class MessageRepository(BaseRepository[Message]):
    model = Message
    dao_class = SQLAlchemyDAO
    
    def __init__(self, session):
        super().__init__(session)

    async def get_chat_messages(self, chat_id: UUID, limit: int = 50, offset: int = 0) -> List[Message]:
        """Получить сообщения чата"""
        query = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .options(joinedload(Message.sender))
            .order_by(desc(Message.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        messages = result.scalars().all()
        return list(reversed(messages))  # Возвращаем в хронологическом порядке

    async def get_unread_count(self, chat_id: UUID, user_id: UUID) -> int:
        """Получить количество непрочитанных сообщений"""
        query = (
            select(func.count(Message.id))
            .where(
                and_(
                    Message.chat_id == chat_id,
                    Message.sender_id != user_id,
                    Message.is_read == False
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def mark_messages_as_read(self, chat_id: UUID, user_id: UUID) -> None:
        """Отметить все сообщения в чате как прочитанные"""
        query = (
            select(Message)
            .where(
                and_(
                    Message.chat_id == chat_id,
                    Message.sender_id != user_id,
                    Message.is_read == False
                )
            )
        )
        result = await self.session.execute(query)
        messages = result.scalars().all()
        
        for message in messages:
            message.is_read = True
        
        await self.session.commit()

    async def get_last_message(self, chat_id: UUID) -> Optional[Message]:
        """Получить последнее сообщение в чате"""
        query = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .options(joinedload(Message.sender))
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() 