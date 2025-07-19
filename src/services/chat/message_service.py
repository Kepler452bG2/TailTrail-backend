from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Message, User
from src.repositories.message_repository import MessageRepository
from src.repositories.chat_repository import ChatRepository
from src.repositories.user_repository import UserRepository
from src.schemas.message import MessageCreateDTO, MessageUpdateDTO, MessageResponseDTO, MessageSenderDTO
from src.utils.exceptions import HTTPException


class MessageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.message_repository = MessageRepository(session)
        self.chat_repository = ChatRepository(session)
        self.user_repository = UserRepository(session)

    async def create_message(self, message_data: MessageCreateDTO, sender_id: UUID) -> MessageResponseDTO:
        """Создать новое сообщение"""
        # Проверяем, существует ли чат
        chat = await self.chat_repository.find_by_id(message_data.chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # Проверяем, является ли пользователь участником чата
        if not await self.chat_repository.is_user_participant(chat.id, sender_id):
            raise HTTPException(status_code=403, detail="You are not a participant of this chat")

        # Создаем сообщение
        message = Message(
            content=message_data.content,
            chat_id=message_data.chat_id,
            sender_id=sender_id
        )

        created_message = await self.message_repository.insert_one(message)
        if not created_message:
            raise HTTPException(status_code=500, detail="Failed to create message")

        # Load the sender separately to avoid lazy loading issues
        sender = await self.user_repository.find_by_id(sender_id)
        if not sender:
            raise HTTPException(status_code=404, detail="Sender not found")
        
        # Manually set the sender to avoid lazy loading
        created_message.sender = sender
        
        return self._to_response_dto(created_message)

    async def get_chat_messages(self, chat_id: UUID, user_id: UUID, limit: int = 50, offset: int = 0) -> List[MessageResponseDTO]:
        """Получить сообщения чата"""
        # Проверяем, является ли пользователь участником чата
        if not await self.chat_repository.is_user_participant(chat_id, user_id):
            raise HTTPException(status_code=403, detail="You are not a participant of this chat")

        messages = await self.message_repository.get_chat_messages(chat_id, limit, offset)
        return [self._to_response_dto(msg) for msg in messages]

    async def update_message(self, message_id: UUID, message_data: MessageUpdateDTO, user_id: UUID) -> MessageResponseDTO:
        """Обновить сообщение"""
        message = await self.message_repository.find_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        if message.sender_id != user_id:
            raise HTTPException(status_code=403, detail="You can only update your own messages")

        message.content = message_data.content
        updated_message = await self.message_repository.update_one(message)
        return self._to_response_dto(updated_message)

    async def delete_message(self, message_id: UUID, user_id: UUID) -> None:
        """Удалить сообщение"""
        message = await self.message_repository.find_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        if message.sender_id != user_id:
            raise HTTPException(status_code=403, detail="You can only delete your own messages")

        await self.message_repository.delete_one(message_id)

    async def mark_messages_as_read(self, chat_id: UUID, user_id: UUID) -> None:
        """Отметить сообщения как прочитанные"""
        # Проверяем, является ли пользователь участником чата
        if not await self.chat_repository.is_user_participant(chat_id, user_id):
            raise HTTPException(status_code=403, detail="You are not a participant of this chat")
        
        await self.message_repository.mark_messages_as_read(chat_id, user_id)

    def _to_response_dto(self, message: Message) -> MessageResponseDTO:
        """Конвертировать сообщение в DTO"""
        # Получаем отправителя
        sender = message.sender
        sender_dto = MessageSenderDTO(
            id=sender.id,
            email=sender.email,
            image_url=sender.image_url
        )

        return MessageResponseDTO(
            id=message.id,
            content=message.content,
            created_at=message.created_at,
            updated_at=message.updated_at,
            is_read=message.is_read,
            chat_id=message.chat_id,
            sender=sender_dto
        ) 