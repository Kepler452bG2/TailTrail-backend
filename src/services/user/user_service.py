from uuid import UUID
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User

from src.utils.token.auth.token_util import generate_token

from src.repositories.user_repository import UserRepository
from src.schemas.user import (
    UserLogInDTO,
    UserSignUpDTO,
    UserUpdateDTO,
)


class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repository = UserRepository(db)

    async def create_user(self, user_data: UserSignUpDTO) -> None:
        existing_user = await self.user_repository.find_one_or_none(
            email=user_data.email
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use!"
            )

        new_user = User.create_user(user_data)
        created_user = await self.user_repository.insert_one(new_user)
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user!",
            )


    async def authenticate_user(self, user_data: UserLogInDTO) -> str:
        user = await self.user_repository.find_one_or_none(email=user_data.email)
        if not user or not user.check_password(user_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials!"
            )

        token_payload = {"user_id": str(user.id)}
        return generate_token(token_payload)

    async def get_user_by_id(self, user_id: UUID) -> User:
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
            )
        return user
    



    async def update_user(
        self, user_data: UserUpdateDTO, profile_image_url: str | None = None
    ) -> None:
        user = await self.user_repository.find_one_or_none(id=user_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
            )

        if user_data.phone is not None:
            user.phone = user_data.phone

        if profile_image_url:
            user.image_url = profile_image_url

        if user_data.new_password:
            if not user_data.current_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="current_password is required to set a new password",
                )
            if not user.check_password(user_data.current_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid current password",
                )
            user.set_password(user_data.new_password)

        await self.user_repository.update_one(user)


    async def delete_user_by_id(self, user_id: UUID) -> None:
        user = await self.user_repository.find_one_or_none(id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
            )

        await self.user_repository.delete_one(user_id)

    async def delete_profile_image(self, user_id: UUID) -> None:
        user = await self.user_repository.find_one_or_none(id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found!"
            )

        user.image_url = ""
        await self.user_repository.update_one(user)