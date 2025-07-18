from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models to ensure they are registered
from .user import User
from .post import Post
from .like import Like
from .block import Block
