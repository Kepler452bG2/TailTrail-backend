from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.dependencies import get_session, get_current_user
from src.models import User
from src.schemas.message import MessageCreateDTO, MessageUpdateDTO, MessageResponseDTO
from src.services.chat.message_service import MessageService


router = APIRouter(tags=["Messages"])


@router.post("/messages", response_model=MessageResponseDTO)
async def create_message(
    message_data: MessageCreateDTO,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session)
):
    """Создать новое сообщение"""
    message_service = MessageService(session)
    return await message_service.create_message(message_data, current_user.id)


@router.get("/chats/{chat_id}/messages", response_model=List[MessageResponseDTO])
async def get_chat_messages(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Получить сообщения чата"""
    message_service = MessageService(session)
    return await message_service.get_chat_messages(chat_id, current_user.id, limit, offset)


@router.put("/messages/{message_id}", response_model=MessageResponseDTO)
async def update_message(
    message_id: UUID,
    message_data: MessageUpdateDTO,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session)
):
    """Обновить сообщение"""
    message_service = MessageService(session)
    return await message_service.update_message(message_id, message_data, current_user.id)


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session)
):
    """Удалить сообщение"""
    message_service = MessageService(session)
    await message_service.delete_message(message_id, current_user.id)
    return {"message": "Message deleted successfully"}


@router.post("/chats/{chat_id}/messages/mark-read")
async def mark_messages_as_read(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session)
):
    """Отметить сообщения как прочитанные"""
    message_service = MessageService(session)
    await message_service.mark_messages_as_read(chat_id, current_user.id)
    return {"message": "Messages marked as read"} 