import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    post_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("posts.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="likes")
    post: Mapped["Post"] = relationship("Post", back_populates="likes")

    # Ensure unique constraint for user-post pair
    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='_user_post_like_uc'),
    ) 