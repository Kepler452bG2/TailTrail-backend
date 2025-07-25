import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class UserSignUpDTO(BaseModel):
    email: EmailStr
    password: str
    phone: str | None = Field(None, pattern=r"^\+\d{1,15}$")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\+\d{1,15}$", v):
            raise ValueError("Invalid phone number")
        return v


class ForgotPasswordRequestDTO(BaseModel):
    email: EmailStr


class ResetPasswordVerifyDTO(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(..., min_length=8)


class UserVerificationDTO(BaseModel):
    email: EmailStr
    code: str


class ResendVerificationDTO(BaseModel):
    email: EmailStr


class UserLogInDTO(BaseModel):
    email: EmailStr
    password: str


class UserDTO(BaseModel):
    id: uuid.UUID
    email: str
    phone: str | None
    created_at: datetime
    image_url: str | None


class UserUpdateDTO(BaseModel):
    user_id: uuid.UUID
    phone: str | None = Field(default=None)
    current_password: str | None = Field(default=None)
    new_password: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_passwords(self):
        current_password = self.current_password
        new_password = self.new_password

        if current_password and not new_password:
            raise ValueError(
                "new_password is required when current_password is provided"
            )

        if new_password and not current_password:
            raise ValueError(
                "current_password is required when new_password is provided"
            )

        return self

