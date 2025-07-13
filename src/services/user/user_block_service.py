import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.models.user_block import UserBlock
from src.repositories.user_block_repository import UserBlockRepository
from src.repositories.user_repository import UserRepository
from src.schemas.user import (
    UserBlockResponseDTO, 
    UserBlockListResponseDTO, 
    UserBlockStatusDTO,
    UserBlockActionResponseDTO
)


class UserBlockService:
    def __init__(self, db: AsyncSession):
        self.user_block_repository = UserBlockRepository(db)
        self.user_repository = UserRepository(db)
    
    async def block_user(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> UserBlockActionResponseDTO:
        """Блокирует пользователя"""
        # Проверяем, что пользователь не блокирует сам себя
        if blocker_id == blocked_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя заблокировать самого себя"
            )
        
        # Проверяем, что заблокируемый пользователь существует
        blocked_user = await self.user_repository.find_by_id(blocked_id)
        if not blocked_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        # Проверяем, не заблокирован ли уже этот пользователь
        existing_block = await self.user_block_repository.is_blocked(blocker_id, blocked_id)
        if existing_block:
            return UserBlockActionResponseDTO(
                success=False,
                message="Пользователь уже заблокирован",
                is_blocked=True
            )
        
        # Создаем блокировку
        await self.user_block_repository.create_block(blocker_id, blocked_id)
        
        return UserBlockActionResponseDTO(
            success=True,
            message="Пользователь успешно заблокирован",
            is_blocked=True
        )
    
    async def unblock_user(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> UserBlockActionResponseDTO:
        """Разблокирует пользователя"""
        # Убираем блокировку
        success = await self.user_block_repository.remove_block(blocker_id, blocked_id)
        
        if success:
            return UserBlockActionResponseDTO(
                success=True,
                message="Пользователь успешно разблокирован",
                is_blocked=False
            )
        else:
            return UserBlockActionResponseDTO(
                success=False,
                message="Пользователь не был заблокирован",
                is_blocked=False
            )
    
    async def get_blocked_users(self, blocker_id: uuid.UUID) -> UserBlockListResponseDTO:
        """Получает список заблокированных пользователей"""
        blocked_users = await self.user_block_repository.get_blocked_users(blocker_id)
        
        blocked_users_dto = [
            UserBlockResponseDTO.from_orm(block) for block in blocked_users
        ]
        
        return UserBlockListResponseDTO(
            blocked_users=blocked_users_dto,
            total=len(blocked_users_dto)
        )
    
    async def check_block_status(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> UserBlockStatusDTO:
        """Проверяет статус блокировки пользователя"""
        block = await self.user_block_repository.is_blocked(blocker_id, blocked_id)
        
        if block:
            return UserBlockStatusDTO(
                is_blocked=True,
                blocked_at=block.created_at
            )
        else:
            return UserBlockStatusDTO(
                is_blocked=False,
                blocked_at=None
            )
    
    async def get_blocked_user_ids(self, blocker_id: uuid.UUID) -> List[uuid.UUID]:
        """Получает список ID заблокированных пользователей"""
        return await self.user_block_repository.get_blocked_user_ids(blocker_id)
    
    async def get_blocker_ids_who_blocked(self, blocked_id: uuid.UUID) -> List[uuid.UUID]:
        """Получает список ID пользователей, которые заблокировали данного пользователя"""
        return await self.user_block_repository.get_blocker_ids_who_blocked(blocked_id)
    
    async def is_user_blocked(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
        """Проверяет заблокирован ли пользователь"""
        block = await self.user_block_repository.is_blocked(blocker_id, blocked_id)
        return block is not None 