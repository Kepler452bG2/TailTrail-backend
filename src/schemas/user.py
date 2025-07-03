import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserSignUpDTO(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogInDTO(BaseModel):
    email: EmailStr
    password: str


class UserDTO(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    created_at: datetime
