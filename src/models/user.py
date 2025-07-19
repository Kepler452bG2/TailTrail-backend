import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import bcrypt
from sqlalchemy import UUID, DateTime, String, func, Boolean
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base
from src.schemas.user import UserSignUpDTO

if TYPE_CHECKING:
    from .chat import Chat, chat_participants
    from .message import Message


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    _hashed_password: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user")
    likes: Mapped[list["Like"]] = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    chats: Mapped[list["Chat"]] = relationship(
        "Chat", secondary="chat_participants", back_populates="participants"
    )
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="sender")

    @hybrid_property
    def hashed_password(self) -> str:
        raise AttributeError("Error getting hashed password!")

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.checkpw(raw_password.encode(), self._hashed_password.encode())

    def set_password(self, raw_password: str) -> None:
        """Set new password for user"""
        self._hashed_password = bcrypt.hashpw(
            raw_password.encode(), bcrypt.gensalt()
        ).decode()

    @staticmethod
    def create_user(user_data: UserSignUpDTO) -> "User":
        return User(
            email=user_data.email,
            phone=user_data.phone,
            _hashed_password=bcrypt.hashpw(
                user_data.password.encode(), bcrypt.gensalt()
            ).decode(),
        )
