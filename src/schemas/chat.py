from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class ChatCreateDTO(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    is_group: bool = False
    participant_ids: List[UUID] = Field(min_length=1)


class ChatUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, max_length=255)


class ChatParticipantDTO(BaseModel):
    id: UUID
    email: str
    image_url: Optional[str] = None
    is_online: bool = False
    last_seen: Optional[datetime] = None


class ChatResponseDTO(BaseModel):
    id: UUID
    name: Optional[str] = None
    is_group: bool
    created_at: datetime
    updated_at: datetime
    participants: List[ChatParticipantDTO]
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0

    class Config:
        from_attributes = True 