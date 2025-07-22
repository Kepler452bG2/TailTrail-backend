# Руководство по WebSocket в TailTrail

## 🚀 Основная фича

**Теперь тебе НЕ НУЖНО подключаться к каждому чату отдельно!**

При подключении к WebSocket ты автоматически подписываешься на **ВСЕ свои чаты** и получаешь уведомления из всех сразу.

## 📡 Подключение

```
ws://localhost:8000/websocket/ws/{user_id}
```

## 🔄 Что происходит автоматически при подключении:

1. ✅ Подключение к WebSocket
2. 🔍 Поиск всех твоих чатов в БД
3. 🔗 Автоматическая подписка на все чаты
4. 📬 Ты сразу получаешь уведомления из ВСЕХ чатов

## 📨 Входящие события (что ты получаешь):

### Сообщения
- `new_message` - новое сообщение в любом из твоих чатов
- `messages_read` - кто-то прочитал сообщения

### Активность пользователей  
- `user_typing` - кто-то печатает
- `user_stopped_typing` - перестал печатать
- `user_joined` - присоединился к чату
- `user_left` - покинул чат

### Системные
- `global_notification` - глобальные уведомления
- `my_chats` - список твоих чатов
- `chat_status` - статус всех чатов
- `error` - ошибки

## 📤 Исходящие команды (что ты отправляешь):

### Управление чатами
```json
{
    "type": "get_my_chats",
    "data": {}
}
```

```json
{
    "type": "get_chat_status", 
    "data": {}
}
```

### Отправка сообщений
```json
{
    "type": "send_message",
    "data": {
        "chat_id": "uuid-чата",
        "content": "текст сообщения"
    }
}
```

### Статус "печатает"
```json
{
    "type": "typing",
    "data": {
        "chat_id": "uuid-чата",
        "is_typing": true
    }
}
```

### Пометка как прочитанное
```json
{
    "type": "mark_read",
    "data": {
        "chat_id": "uuid-чата"
    }
}
```

### Управление подключениями (если нужно)
```json
{
    "type": "join_chat",
    "data": {
        "chat_id": "uuid-чата"
    }
}
```

```json
{
    "type": "leave_chat",
    "data": {
        "chat_id": "uuid-чата"
    }
}
```

## 🎯 Как отслеживать сообщения в реальном времени

### JavaScript пример:
```javascript
const ws = new WebSocket(`ws://localhost:8000/websocket/ws/${userId}`);

// Получение всех уведомлений
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'new_message':
            // Новое сообщение из ЛЮБОГО чата
            console.log(`📨 Сообщение в чате ${message.data.chat_id}`);
            console.log(`От: ${message.data.sender.email}`);
            console.log(`Текст: ${message.data.content}`);
            showNotification(message.data);
            break;
            
        case 'user_typing':
            showTypingIndicator(message.data.user_id);
            break;
            
        case 'my_chats':
            // Список всех твоих чатов с количеством непрочитанных
            message.data.chats.forEach(chat => {
                updateChatUI(chat);
            });
            break;
    }
};

// При подключении автоматически получаем список чатов
ws.onopen = function() {
    console.log('🚀 Подключен! Автоматически подписан на все чаты');
    
    // Получаем актуальный список чатов
    setTimeout(() => {
        ws.send(JSON.stringify({
            type: 'get_my_chats',
            data: {}
        }));
    }, 1000);
};
```

## 🧪 Тестирование

Запусти тестовый клиент:

```bash
python websocket_test_client.py
```

Измени `user_id` в файле на реальный ID.

## 🛠 Продвинутые возможности

### Системные уведомления из кода:

```python
from src.websocket_manager import websocket_manager

# Уведомить всех участников чата
await websocket_manager.notify_chat_participants(
    chat_id=chat_id,
    notification={
        "type": "system_message",
        "message": "Администратор добавил нового участника"
    }
)

# Глобальное уведомление пользователю
await websocket_manager.send_global_notification(
    user_id=user_id,
    notification={
        "type": "account_warning",
        "message": "Ваш аккаунт будет заблокирован"
    }
)
```

### Проверка онлайн статуса:

```python
# Кто сейчас онлайн
online_users = websocket_manager.get_online_users()

# Конкретный пользователь онлайн?
is_online = websocket_manager.is_user_online(user_id)

# Список чатов пользователя
user_chats = websocket_manager.get_user_chats_list(user_id)
```

## 💡 Преимущества новой системы:

✅ **Один WebSocket = все чаты**  
✅ **Мгновенные уведомления из всех чатов**  
✅ **Автоматическая подписка**  
✅ **Отслеживание статуса "печатает" везде**  
✅ **Глобальные системные уведомления**  
✅ **Статистика онлайн пользователей**

## 🔥 Что изменилось:

**Раньше:**
- Подключаешься к WebSocket
- Вручную подписываешься на каждый чат: `join_chat`
- Получаешь уведомления только из подключенных чатов

**Сейчас:**  
- Подключаешься к WebSocket
- 🎉 **АВТОМАТИЧЕСКИ** подписываешься на ВСЕ чаты
- Получаешь уведомления из ВСЕХ чатов сразу! 