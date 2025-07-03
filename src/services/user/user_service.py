from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.repositories.user_repository import UserRepository
from src.schemas.user import UserLogInDTO, UserSignUpDTO


class UserService:
    @staticmethod
    async def create_user(user_data: UserSignUpDTO) -> str:
        existing_user = await UserRepository.find_one_or_none(email=user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use!"
            )

        new_user = await UserRepository.insert_one(user_data)
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user!",
            )

        return UserService.generate_token({"user_id": str(new_user.id)})

    @staticmethod
    async def authenticate_user(user_data: UserLogInDTO) -> str:
        user = await UserRepository.find_one_or_none(email=user_data.email)
        if not user or not user.check_password(user_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials!"
            )

        return UserService.generate_token({"user_id": str(user.id)})

    @staticmethod
    def generate_token(payload: dict) -> str:
        payload["exp"] = datetime.now(UTC) + timedelta(seconds=settings.jwt_expiration)
        return jwt.encode(payload, settings.secret_key, algorithm="HS256")

    @staticmethod
    def verify_token(token: str) -> dict:
        try:
            return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired!")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token!")
