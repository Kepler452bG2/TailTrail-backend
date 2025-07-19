import json
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
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Валидируем сообщение
                try:
                    ws_message = WebSocketMessage(**message_data)
                except ValidationError as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {"message": "Invalid message format", "details": str(e)}
                    }))
                    continue
                
                # Обрабатываем сообщение
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
        if message.type == "join_chat":
            await handle_join_chat(user_id, message.data)
        elif message.type == "leave_chat":
            await handle_leave_chat(user_id, message.data)
        elif message.type == "send_message":
            await handle_send_message(websocket, user_id, message.data)
        elif message.type == "typing":
            await handle_typing(user_id, message.data)
        elif message.type == "mark_read":
            await handle_mark_read(user_id, message.data)
        else:
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
        # Создаем сообщение в базе данных
        from src.database import sessionmanager
        async with sessionmanager.session() as session:
            message_service = MessageService(session)
            message_data = MessageCreateDTO(
                content=data["content"],
                chat_id=UUID(data["chat_id"])
            )
            
            # Сохраняем сообщение
            message = await message_service.create_message(message_data, user_id)
            
            # Отправляем сообщение всем участникам чата
            await websocket_manager.broadcast_to_chat(UUID(data["chat_id"]), {
                "type": "new_message",
                "data": message.model_dump()
            })
            
    except Exception as e:
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