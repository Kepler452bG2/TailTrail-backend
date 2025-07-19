import uuid
from datetime import datetime
from pydantic import BaseModel


class BlockCreateDTO(BaseModel):
    blocked_id: uuid.UUID


class BlockResponseDTO(BaseModel):
    id: uuid.UUID
    blocker_id: uuid.UUID
    blocked_id: uuid.UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class BlockedUserDTO(BaseModel):
    id: uuid.UUID
    email: str
    phone: str | None = None
    image_url: str | None = None
    blocked_at: datetime
    
    class Config:
        from_attributes = True


class BlockListResponseDTO(BaseModel):
    blocked_users: list[BlockedUserDTO]
    total: int 