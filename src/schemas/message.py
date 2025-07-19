from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreateDTO(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    chat_id: UUID


class MessageUpdateDTO(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    is_read: bool = False


class MessageSenderDTO(BaseModel):
    id: UUID
    email: str
    image_url: str | None = None


class MessageResponseDTO(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    updated_at: datetime
    is_read: bool
    chat_id: UUID
    sender: MessageSenderDTO

    class Config:
        from_attributes = True


class WebSocketMessage(BaseModel):
    type: str  # "message", "typing", "user_online", "user_offline"
    data: dict 