from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload, joinedload

from src.dao.sqlalchemy_dao import SQLAlchemyDAO
from src.models import Chat, Message, User
from src.repositories.base_repository import BaseRepository


class ChatRepository(BaseRepository[Chat]):
    model = Chat
    dao_class = SQLAlchemyDAO
    
    def __init__(self, session):
        super().__init__(session)

    async def get_user_chats(self, user_id: UUID) -> List[Chat]:
        """Получить все чаты пользователя с последним сообщением"""
        query = (
            select(Chat)
            .join(Chat.participants)
            .where(User.id == user_id)
            .options(
                selectinload(Chat.participants),
                selectinload(Chat.messages).options(
                    joinedload(Message.sender)
                )
            )
            .order_by(Chat.updated_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_chat_by_participants(self, participant_ids: List[UUID]) -> Optional[Chat]:
        """Найти чат по участникам (для приватных чатов)"""
        if len(participant_ids) == 2:
            # Для приватных чатов
            query = (
                select(Chat)
                .join(Chat.participants)
                .where(Chat.is_group == False)
                .group_by(Chat.id)
                .having(func.count(User.id) == 2)
                .options(selectinload(Chat.participants))
            )
            result = await self.session.execute(query)
            chats = result.scalars().all()
            
            for chat in chats:
                chat_participant_ids = {p.id for p in chat.participants}
                if chat_participant_ids == set(participant_ids):
                    return chat
        return None

    async def get_chat_with_messages(self, chat_id: UUID, limit: int = 50, offset: int = 0) -> Optional[Chat]:
        """Получить чат с сообщениями"""
        query = (
            select(Chat)
            .where(Chat.id == chat_id)
            .options(
                selectinload(Chat.participants),
                selectinload(Chat.messages)
                .options(joinedload(Message.sender))
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def is_user_participant(self, chat_id: UUID, user_id: UUID) -> bool:
        """Проверить, является ли пользователь участником чата"""
        query = (
            select(Chat)
            .join(Chat.participants)
            .where(and_(Chat.id == chat_id, User.id == user_id))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None 