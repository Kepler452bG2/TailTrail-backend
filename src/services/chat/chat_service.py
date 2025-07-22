from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Chat, User, Message
from src.repositories.chat_repository import ChatRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.user_repository import UserRepository
from src.schemas.chat import ChatCreateDTO, ChatUpdateDTO, ChatResponseDTO, ChatParticipantDTO
from src.schemas.message import MessageResponseDTO, MessageSenderDTO
from src.utils.exceptions import HTTPException


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.chat_repository = ChatRepository(session)
        self.message_repository = MessageRepository(session)
        self.user_repository = UserRepository(session)

    async def create_chat(self, chat_data: ChatCreateDTO, creator_id: UUID) -> ChatResponseDTO:
        """Создать новый чат"""
        # Проверяем, есть ли все участники
        participants = []
        for participant_id in chat_data.participant_ids:
            user = await self.user_repository.find_by_id(participant_id)
            if not user:
                raise HTTPException(status_code=404, detail=f"User {participant_id} not found")
            participants.append(user)

        # Добавляем создателя, если его нет в списке
        if creator_id not in chat_data.participant_ids:
            creator = await self.user_repository.find_by_id(creator_id)
            if creator:
                participants.append(creator)

        # Для приватных чатов проверяем, не существует ли уже такой чат
        if not chat_data.is_group and len(participants) == 2:
            existing_chat = await self.chat_repository.get_chat_by_participants(
                [p.id for p in participants]
            )
            if existing_chat:
                return await self._convert_to_response_dto(existing_chat, creator_id)

        # Создаем чат
        chat = Chat(
            name=chat_data.name,
            is_group=chat_data.is_group,
            participants=participants
        )
        
        created_chat = await self.chat_repository.insert_one(chat)
        if not created_chat:
            raise HTTPException(status_code=500, detail="Failed to create chat")
        
        return await self._convert_to_response_dto(created_chat, creator_id)

    async def get_user_chats(self, user_id: UUID) -> List[ChatResponseDTO]:
        """Получить все чаты пользователя"""
        chats = await self.chat_repository.get_user_chats(user_id)
        result = []
        for chat in chats:
            result.append(await self._convert_to_response_dto(chat, user_id))
        return result

    async def get_chat_by_id(self, chat_id: UUID, user_id: UUID) -> Optional[ChatResponseDTO]:
        """Получить чат по ID"""
        # Проверяем, является ли пользователь участником чата
        if not await self.chat_repository.is_user_participant(chat_id, user_id):
            raise HTTPException(status_code=403, detail="You are not a participant of this chat")
        
        chat = await self.chat_repository.find_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        return await self._convert_to_response_dto(chat, user_id)

    async def update_chat(self, chat_id: UUID, chat_data: ChatUpdateDTO, user_id: UUID) -> ChatResponseDTO:
        """Обновить чат"""
        # Проверяем, является ли пользователь участником чата
        if not await self.chat_repository.is_user_participant(chat_id, user_id):
            raise HTTPException(status_code=403, detail="You are not a participant of this chat")
        
        chat = await self.chat_repository.find_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        if chat_data.name is not None:
            chat.name = chat_data.name
        
        await self.chat_repository.update_one(chat)
        return await self._convert_to_response_dto(chat, user_id)

    async def delete_chat(self, chat_id: UUID, user_id: UUID) -> None:
        """Удалить чат"""
        # Проверяем, является ли пользователь участником чата
        if not await self.chat_repository.is_user_participant(chat_id, user_id):
            raise HTTPException(status_code=403, detail="You are not a participant of this chat")
        
        chat = await self.chat_repository.find_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        await self.chat_repository.delete_one(chat.id)

    async def _convert_to_response_dto(self, chat: Chat, user_id: UUID) -> ChatResponseDTO:
        """Конвертировать чат в DTO"""
        # Загружаем чат с participants чтобы избежать lazy loading  
        chat_with_participants = await self.chat_repository.get_chat_with_participants(chat.id)
        if not chat_with_participants:
            chat_with_participants = chat
            
        # Получаем участников
        participants = []
        for participant in chat_with_participants.participants:
            participants.append(ChatParticipantDTO(
                id=participant.id,
                email=participant.email,
                image_url=participant.image_url,
                is_online=participant.is_online,
                last_seen=participant.last_seen
            ))

        # Получаем последнее сообщение
        last_message = await self.message_repository.get_last_message(chat.id)
        last_message_content = None
        last_message_time = None
        if last_message:
            last_message_content = last_message.content
            last_message_time = last_message.created_at

        # Получаем количество непрочитанных сообщений
        unread_count = await self.message_repository.get_unread_count(chat.id, user_id)

        return ChatResponseDTO(
            id=chat.id,
            name=chat.name,
            is_group=chat.is_group,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            participants=participants,
            last_message=last_message_content,
            last_message_time=last_message_time,
            unread_count=unread_count
        ) 