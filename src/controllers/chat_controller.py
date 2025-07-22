from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.dependencies import get_session, get_current_user
from src.models import User
from src.schemas.chat import ChatCreateDTO, ChatUpdateDTO, ChatResponseDTO
from src.services.chat.chat_service import ChatService


router = APIRouter(tags=["Chat"])


@router.post("/chats", response_model=ChatResponseDTO)
async def create_chat(
    chat_data: ChatCreateDTO,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session)
):
    """Создать новый чат"""
    chat_service = ChatService(session)
    return await chat_service.create_chat(chat_data, current_user.id)


@router.get("/chats", response_model=List[ChatResponseDTO])
async def get_user_chats(
    current_user: User = Depends(get_current_user),
    session=Depends(get_session)
):
    """Получить все чаты пользователя"""
    chat_service = ChatService(session)
    return await chat_service.get_user_chats(current_user.id)


@router.get("/chats/{chat_id}", response_model=ChatResponseDTO)
async def get_chat_by_id(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session)
):
    """Получить чат по ID"""
    chat_service = ChatService(session)
    return await chat_service.get_chat_by_id(chat_id, current_user.id)


@router.put("/chats/{chat_id}", response_model=ChatResponseDTO)
async def update_chat(
    chat_id: UUID,
    chat_data: ChatUpdateDTO,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session)
):
    """Обновить чат"""
    chat_service = ChatService(session)
    return await chat_service.update_chat(chat_id, chat_data, current_user.id)


@router.delete("/chats/{chat_id}")
async def delete_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session)
):
    """Удалить чат"""
    chat_service = ChatService(session)
    await chat_service.delete_chat(chat_id, current_user.id)
    return {"message": "Chat deleted successfully"} 