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
        # Словарь для хранения чатов пользователя: user_id -> Set[chat_id]
        self.user_chats: Dict[UUID, Set[UUID]] = {}
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """Подключить пользователя к веб-сокету"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
        # Автоматически подписываем пользователя на все его чаты
        await self._subscribe_user_to_all_chats(user_id)
        
        # Обновляем статус пользователя на онлайн
        await self._update_user_online_status(user_id, True)

    async def _subscribe_user_to_all_chats(self, user_id: UUID):
        """Автоматически подписать пользователя на все его чаты"""
        try:
            from src.database import sessionmanager
            from src.services.chat.chat_service import ChatService
            
            async with sessionmanager.session() as session:
                try:
                    chat_service = ChatService(session)
                    user_chats = await chat_service.get_user_chats(user_id)
                    
                    # Сохраняем список чатов пользователя
                    self.user_chats[user_id] = set()
                    
                    for chat in user_chats:
                        chat_id = chat.id
                        # Добавляем пользователя в чат
                        await self.join_chat(user_id, chat_id)
                        # Сохраняем в список чатов пользователя
                        self.user_chats[user_id].add(chat_id)
                        
                    self.logger.info(f"User {user_id} automatically subscribed to {len(user_chats)} chats")
                    
                except Exception as e:
                    self.logger.error(f"Database error while getting chats for user {user_id}: {e}")
                    # Создаем пустой набор чатов чтобы избежать ошибок
                    self.user_chats[user_id] = set()
                    
        except Exception as e:
            self.logger.error(f"Failed to subscribe user {user_id} to all chats: {e}")
            # Создаем пустой набор чатов чтобы избежать ошибок
            self.user_chats[user_id] = set()

    async def disconnect(self, user_id: UUID):
        """Отключить пользователя от веб-сокета"""
        try:
            if user_id in self.active_connections:
                # Закрываем WebSocket соединение если оно еще открыто
                try:
                    websocket = self.active_connections[user_id]
                    if not websocket.client_state.disconnected:
                        await websocket.close(code=1000, reason="User disconnected")
                except Exception as e:
                    self.logger.error(f"Error closing websocket for user {user_id}: {e}")
                finally:
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
                        try:
                            await self._broadcast_to_chat(chat_id, {
                                "type": "user_stopped_typing",
                                "data": {"user_id": str(user_id)}
                            }, exclude_user=user_id)
                        except Exception as e:
                            self.logger.error(f"Error broadcasting typing status for user {user_id}: {e}")
            
            # Убираем список чатов пользователя
            if user_id in self.user_chats:
                del self.user_chats[user_id]
            
            # Обновляем статус пользователя на оффлайн
            try:
                await self._update_user_online_status(user_id, False)
            except Exception as e:
                self.logger.error(f"Error updating online status for user {user_id}: {e}")
                
        except Exception as e:
            self.logger.error(f"Error in disconnect for user {user_id}: {e}")

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
                websocket = self.active_connections[user_id]
                # Проверяем что соединение еще активно
                if websocket.client_state.disconnected:
                    self.logger.warning(f"WebSocket for user {user_id} is disconnected, removing from active connections")
                    del self.active_connections[user_id]
                    return
                
                self.logger.info(f"Sending WebSocket message to user {user_id}: {message}")
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
                self.logger.info(f"Successfully sent message to user {user_id}")
            except Exception as e:
                self.logger.error(f"Failed to send message to user {user_id}: {e}")
                # Если не удалось отправить, удаляем подключение без рекурсивного вызова
                if user_id in self.active_connections:
                    del self.active_connections[user_id]
                # Убираем из чатов
                for chat_id in list(self.chat_users.keys()):
                    if user_id in self.chat_users[chat_id]:
                        self.chat_users[chat_id].discard(user_id)
                        if not self.chat_users[chat_id]:
                            del self.chat_users[chat_id]
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

    async def send_global_notification(self, user_id: UUID, notification: dict):
        """Отправить глобальное уведомление пользователю"""
        if user_id in self.active_connections:
            try:
                message = {
                    "type": "global_notification",
                    "data": notification
                }
                self.logger.info(f"Sending global notification to user {user_id}: {message}")
                await self.active_connections[user_id].send_text(json.dumps(message, ensure_ascii=False))
                self.logger.info(f"Successfully sent global notification to user {user_id}")
            except Exception as e:
                self.logger.error(f"Failed to send global notification to user {user_id}: {e}")
                # Если не удалось отправить, удаляем подключение
                await self.disconnect(user_id)
        else:
            self.logger.warning(f"User {user_id} not in active connections, cannot send global notification")

    def get_online_users(self) -> List[UUID]:
        """Получить список онлайн пользователей"""
        return list(self.active_connections.keys())

    def is_user_online(self, user_id: UUID) -> bool:
        """Проверить, онлайн ли пользователь"""
        return user_id in self.active_connections

    def get_user_chats_list(self, user_id: UUID) -> Set[UUID]:
        """Получить список чатов пользователя"""
        return self.user_chats.get(user_id, set())

    def get_connection_stats(self) -> dict:
        """Получить статистику подключений для мониторинга"""
        return {
            "total_connections": len(self.active_connections),
            "total_chats": len(self.chat_users),
            "total_typing_users": sum(len(users) for users in self.typing_users.values()),
            "active_connections": list(str(uid) for uid in self.active_connections.keys()),
            "chat_distribution": {str(chat_id): len(users) for chat_id, users in self.chat_users.items()}
        }

    def cleanup_dead_connections(self):
        """Очистить мертвые соединения"""
        dead_connections = []
        for user_id, websocket in self.active_connections.items():
            try:
                if websocket.client_state.disconnected:
                    dead_connections.append(user_id)
            except Exception:
                dead_connections.append(user_id)
        
        for user_id in dead_connections:
            self.logger.warning(f"Removing dead connection for user {user_id}")
            if user_id in self.active_connections:
                del self.active_connections[user_id]

    async def notify_chat_participants(self, chat_id: UUID, notification: dict, exclude_user: UUID = None):
        """Отправить уведомление всем участникам чата (для системных уведомлений)"""
        try:
            from src.database import sessionmanager
            from src.repositories.chat_repository import ChatRepository
            
            async with sessionmanager.session() as session:
                chat_repo = ChatRepository(session)
                chat = await chat_repo.get_chat_with_participants(chat_id)
                
                if not chat:
                    self.logger.warning(f"Chat {chat_id} not found for notification")
                    return
                
                # Отправляем уведомление всем участникам чата
                for participant in chat.participants:
                    if exclude_user and participant.id == exclude_user:
                        continue
                    
                    if participant.id in self.active_connections:
                        await self.send_global_notification(participant.id, {
                            "type": "chat_notification", 
                            "chat_id": str(chat_id),
                            "notification": notification
                        })
                        
                self.logger.info(f"Sent notification to {len(chat.participants)} participants of chat {chat_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to notify chat participants {chat_id}: {e}")

    async def notify_all_user_chats(self, user_id: UUID, notification: dict):
        """Отправить уведомление во все чаты пользователя"""
        user_chats = self.get_user_chats_list(user_id)
        
        for chat_id in user_chats:
            await self.notify_chat_participants(chat_id, notification, exclude_user=user_id)


# Глобальный экземпляр менеджера
websocket_manager = WebSocketManager() 