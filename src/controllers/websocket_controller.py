import json
import logging
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import ValidationError

from src.dependencies import get_session, get_current_user_websocket
from src.models import User
from src.schemas.message import WebSocketMessage, MessageCreateDTO
from src.services.chat.message_service import MessageService
from src.services.chat.chat_service import ChatService
from src.websocket_manager import websocket_manager


router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: UUID):
    """WebSocket endpoint для чата"""
    try:
        # Получаем пользователя из базы данных
        user = await get_current_user_websocket(websocket, user_id)
        if not user:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        # Подключаем пользователя
        await websocket_manager.connect(websocket, user_id)
        
        try:
            while True:
                # Получаем сообщение от клиента
                logger.info(f"Waiting for message from user {user_id}")
                data = await websocket.receive_text()
                logger.info(f"Received raw data: {data}")
                message_data = json.loads(data)
                logger.info(f"Parsed JSON: {message_data}")
                
                # Валидируем сообщение
                try:
                    ws_message = WebSocketMessage(**message_data)
                    logger.info(f"Validated WebSocket message: {ws_message}")
                except ValidationError as e:
                    logger.error(f"Validation error: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {"message": "Invalid message format", "details": str(e)}
                    }))
                    continue
                
                # Обрабатываем сообщение
                logger.info(f"Processing WebSocket message from user {user_id}")
                await handle_websocket_message(websocket, user_id, ws_message)
                
        except WebSocketDisconnect:
            pass
        finally:
            await websocket_manager.disconnect(user_id)
            
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))


async def handle_websocket_message(websocket: WebSocket, user_id: UUID, message: WebSocketMessage):
    """Обработать WebSocket сообщение"""
    try:
        logger.info(f"Received WebSocket message: type={message.type}, data={message.data}")
        
        if message.type == "join_chat":
            logger.info("Routing to handle_join_chat")
            await handle_join_chat(user_id, message.data)
        elif message.type == "leave_chat":
            logger.info("Routing to handle_leave_chat")
            await handle_leave_chat(user_id, message.data)
        elif message.type == "send_message":
            logger.info("Routing to handle_send_message")
            await handle_send_message(websocket, user_id, message.data)
        elif message.type == "typing":
            logger.info("Routing to handle_typing")
            await handle_typing(user_id, message.data)
        elif message.type == "mark_read":
            logger.info("Routing to handle_mark_read")
            await handle_mark_read(user_id, message.data)
        else:
            logger.warning(f"Unknown message type: {message.type}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": f"Unknown message type: {message.type}"}
            }))
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"message": str(e)}
        }))


async def handle_join_chat(user_id: UUID, data: Dict[str, Any]):
    """Обработать присоединение к чату"""
    chat_id = UUID(data["chat_id"])
    await websocket_manager.join_chat(user_id, chat_id)
    
    logger.info(f"User {user_id} joined chat {chat_id}")
    logger.info(f"Chat users now: {websocket_manager.chat_users.get(chat_id, set())}")
    
    # Уведомляем других пользователей о присоединении
    await websocket_manager.broadcast_to_chat(chat_id, {
        "type": "user_joined",
        "data": {"user_id": str(user_id)}
    }, exclude_user=user_id)


async def handle_leave_chat(user_id: UUID, data: Dict[str, Any]):
    """Обработать выход из чата"""
    chat_id = UUID(data["chat_id"])
    await websocket_manager.leave_chat(user_id, chat_id)
    
    # Уведомляем других пользователей о выходе
    await websocket_manager.broadcast_to_chat(chat_id, {
        "type": "user_left",
        "data": {"user_id": str(user_id)}
    }, exclude_user=user_id)


async def handle_send_message(websocket: WebSocket, user_id: UUID, data: Dict[str, Any]):
    """Обработать отправку сообщения"""
    try:
        logger.info(f"handle_send_message called: user={user_id}, data={data}")
        # Создаем сообщение в базе данных
        from src.database import sessionmanager
        async with sessionmanager.session() as session:
            message_service = MessageService(session)
            message_data = MessageCreateDTO(
                content=data["content"],
                chat_id=UUID(data["chat_id"])
            )
            
            # Сохраняем сообщение
            logger.info(f"Creating message in DB...")
            message = await message_service.create_message(message_data, user_id)
            logger.info(f"Message created: {message.id}")
            
            # Отправляем сообщение всем участникам чата
            chat_id = UUID(data["chat_id"])
            users_in_chat = websocket_manager.chat_users.get(chat_id, set())
            logger.info(f"Broadcasting message to chat {chat_id}, users: {users_in_chat}")
            
            await websocket_manager.broadcast_to_chat(chat_id, {
                "type": "new_message",
                "data": message.model_dump(mode='json')
            })
            logger.info(f"Broadcast completed for message {message.id}")
            
    except Exception as e:
        logger.error(f"Error in handle_send_message: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"message": f"Failed to send message: {str(e)}"}
        }))


async def handle_typing(user_id: UUID, data: Dict[str, Any]):
    """Обработать статус печатания"""
    chat_id = UUID(data["chat_id"])
    is_typing = data.get("is_typing", False)
    
    await websocket_manager.handle_typing(user_id, chat_id, is_typing)


async def handle_mark_read(user_id: UUID, data: Dict[str, Any]):
    """Обработать пометку сообщений как прочитанных"""
    try:
        chat_id = UUID(data["chat_id"])
        
        from src.database import sessionmanager
        async with sessionmanager.session() as session:
            message_service = MessageService(session)
            await message_service.mark_messages_as_read(chat_id, user_id)
            
            # Уведомляем других пользователей о том, что сообщения прочитаны
            await websocket_manager.broadcast_to_chat(chat_id, {
                "type": "messages_read",
                "data": {"user_id": str(user_id)}
            }, exclude_user=user_id)
            
    except Exception as e:
        await websocket_manager.send_message_to_user(user_id, {
            "type": "error",
            "data": {"message": f"Failed to mark messages as read: {str(e)}"}
        }) 