import uuid
from datetime import datetime

import bcrypt
from sqlalchemy import UUID, DateTime, String, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from . import Base
from src.schemas.user import UserSignUpDTO


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    username: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    _hashed_password: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    @hybrid_property
    def hashed_password(self) -> str:
        raise AttributeError("Error getting hashed password!")

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.checkpw(raw_password.encode(), self._hashed_password.encode())

    @staticmethod
    def create_user(user_data: UserSignUpDTO) -> "User":
        return User(
            username=user_data.username,
            email=user_data.email,
            _hashed_password=bcrypt.hashpw(
                user_data.password.encode(), bcrypt.gensalt()
            ).decode(),
        )
