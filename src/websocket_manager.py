import json
import logging
from typing import Dict, List, Set
from uuid import UUID
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from src.models import User
from src.schemas.message import WebSocketMessage, MessageCreateDTO, MessageResponseDTO
from src.services.chat.message_service import MessageService
from src.services.user.user_service import UserService


class WebSocketManager:
    def __init__(self):
        # Словарь для хранения активных подключений: user_id -> WebSocket
        self.active_connections: Dict[UUID, WebSocket] = {}
        # Словарь для хранения пользователей по чатам: chat_id -> Set[user_id]
        self.chat_users: Dict[UUID, Set[UUID]] = {}
        # Словарь для хранения статуса "печатает": chat_id -> Set[user_id]
        self.typing_users: Dict[UUID, Set[UUID]] = {}
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """Подключить пользователя к веб-сокету"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
        # Обновляем статус пользователя на онлайн
        await self._update_user_online_status(user_id, True)

    async def disconnect(self, user_id: UUID):
        """Отключить пользователя от веб-сокета"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Убираем пользователя из всех чатов
        for chat_id in list(self.chat_users.keys()):
            if user_id in self.chat_users[chat_id]:
                self.chat_users[chat_id].discard(user_id)
                if not self.chat_users[chat_id]:
                    del self.chat_users[chat_id]
        
        # Убираем пользователя из статуса "печатает"
        for chat_id in list(self.typing_users.keys()):
            if user_id in self.typing_users[chat_id]:
                self.typing_users[chat_id].discard(user_id)
                if not self.typing_users[chat_id]:
                    del self.typing_users[chat_id]
                else:
                    # Уведомляем других пользователей что пользователь перестал печатать
                    await self._broadcast_to_chat(chat_id, {
                        "type": "user_stopped_typing",
                        "data": {"user_id": str(user_id)}
                    }, exclude_user=user_id)
        
        # Обновляем статус пользователя на оффлайн
        await self._update_user_online_status(user_id, False)

    async def join_chat(self, user_id: UUID, chat_id: UUID):
        """Добавить пользователя в чат"""
        if chat_id not in self.chat_users:
            self.chat_users[chat_id] = set()
        self.chat_users[chat_id].add(user_id)
        self.logger.info(f"WebSocketManager: User {user_id} added to chat {chat_id}")

    async def leave_chat(self, user_id: UUID, chat_id: UUID):
        """Убрать пользователя из чата"""
        if chat_id in self.chat_users and user_id in self.chat_users[chat_id]:
            self.chat_users[chat_id].discard(user_id)
            if not self.chat_users[chat_id]:
                del self.chat_users[chat_id]

    async def send_message_to_user(self, user_id: UUID, message: dict):
        """Отправить сообщение конкретному пользователю"""
        if user_id in self.active_connections:
            try:
                self.logger.info(f"Sending WebSocket message to user {user_id}: {message}")
                await self.active_connections[user_id].send_text(json.dumps(message, ensure_ascii=False))
                self.logger.info(f"Successfully sent message to user {user_id}")
            except Exception as e:
                self.logger.error(f"Failed to send message to user {user_id}: {e}")
                # Если не удалось отправить, удаляем подключение
                await self.disconnect(user_id)
        else:
            self.logger.warning(f"User {user_id} not in active connections, cannot send message")

    async def broadcast_to_chat(self, chat_id: UUID, message: dict, exclude_user: UUID = None):
        """Отправить сообщение всем пользователям в чате"""
        await self._broadcast_to_chat(chat_id, message, exclude_user)

    async def _broadcast_to_chat(self, chat_id: UUID, message: dict, exclude_user: UUID = None):
        """Внутренний метод для отправки сообщений в чат"""
        if chat_id not in self.chat_users:
            return
        
        # Создаем копию множества чтобы избежать ошибки "Set changed size during iteration"
        users_copy = set(self.chat_users[chat_id])
        self.logger.info(f"WebSocketManager: Broadcasting to {len(users_copy)} users in chat {chat_id}")
        for user_id in users_copy:
            if exclude_user and user_id == exclude_user:
                self.logger.info(f"Skipping excluded user {user_id}")
                continue
            self.logger.info(f"Sending message to user {user_id}")
            await self.send_message_to_user(user_id, message)

    async def handle_typing(self, user_id: UUID, chat_id: UUID, is_typing: bool):
        """Обработать статус "печатает" """
        if is_typing:
            if chat_id not in self.typing_users:
                self.typing_users[chat_id] = set()
            self.typing_users[chat_id].add(user_id)
            
            # Уведомляем других пользователей
            await self._broadcast_to_chat(chat_id, {
                "type": "user_typing",
                "data": {"user_id": str(user_id)}
            }, exclude_user=user_id)
        else:
            if chat_id in self.typing_users and user_id in self.typing_users[chat_id]:
                self.typing_users[chat_id].discard(user_id)
                if not self.typing_users[chat_id]:
                    del self.typing_users[chat_id]
                
                # Уведомляем других пользователей
                await self._broadcast_to_chat(chat_id, {
                    "type": "user_stopped_typing",
                    "data": {"user_id": str(user_id)}
                }, exclude_user=user_id)

    async def _update_user_online_status(self, user_id: UUID, is_online: bool):
        """Обновить статус пользователя онлайн/оффлайн"""
        from src.database import sessionmanager
        from src.services.user.user_service import UserService
        
        async with sessionmanager.session() as session:
            user_service = UserService(session)
            await user_service.update_online_status(user_id, is_online)

    def get_online_users(self) -> List[UUID]:
        """Получить список онлайн пользователей"""
        return list(self.active_connections.keys())

    def is_user_online(self, user_id: UUID) -> bool:
        """Проверить, онлайн ли пользователь"""
        return user_id in self.active_connections


# Глобальный экземпляр менеджера
websocket_manager = WebSocketManager() 