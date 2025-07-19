import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, String, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base

if TYPE_CHECKING:
    from .user import User


class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    
    # Пользователь, который блокирует
    blocker_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    
    # Пользователь, которого блокируют
    blocked_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    
    # Relationships
    blocker: Mapped["User"] = relationship("User", foreign_keys=[blocker_id], back_populates="blocks_made")
    blocked: Mapped["User"] = relationship("User", foreign_keys=[blocked_id], back_populates="blocks_received")
    
    # Ограничение на уникальность пары blocker_id, blocked_id
    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='unique_block_pair'),
    ) 