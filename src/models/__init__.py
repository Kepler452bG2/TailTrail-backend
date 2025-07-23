from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models to ensure they are registered
from .user import User
from .post import Post
from .like import Like
from .chat import Chat
from .message import Message
from .block import Block

