import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base


class UserBlock(Base):
    __tablename__ = "user_blocks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    blocked_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Уникальное ограничение - один пользователь может заблокировать другого только один раз
    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='unique_user_block'),
    )
    
    def __repr__(self):
        return f"<UserBlock(blocker_id={self.blocker_id}, blocked_id={self.blocked_id})>" 