import uuid
from datetime import datetime
from typing import List

from sqlalchemy import UUID, DateTime, String, func, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY

from . import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    
    pet_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pet_species: Mapped[str] = mapped_column(String(50), nullable=False)
    pet_breed: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    
    last_seen_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    last_seen_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    
    images: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="posts")
    likes: Mapped[List["Like"]] = relationship("Like", back_populates="post", cascade="all, delete-orphan") 