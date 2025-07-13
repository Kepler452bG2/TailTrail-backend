import uuid
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.block import Block
from src.repositories.block_repository import BlockRepository
from src.repositories.user_repository import UserRepository
from src.schemas.block import (
    BlockCreateDTO,
    BlockResponseDTO,
    BlockedUserDTO,
    BlockListResponseDTO
)


class BlockService:
    def __init__(self, db: AsyncSession):
        self.block_repository = BlockRepository(db)
        self.user_repository = UserRepository(db)

    async def block_user(self, blocker_id: uuid.UUID, block_data: BlockCreateDTO) -> BlockResponseDTO:
        """Block a user"""
        # Check if user exists
        blocked_user = await self.user_repository.find_by_id(block_data.blocked_id)
        if not blocked_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is trying to block themselves
        if blocker_id == block_data.blocked_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block yourself"
            )
        
        # Check if user is already blocked
        is_already_blocked = await self.block_repository.is_blocked(blocker_id, block_data.blocked_id)
        if is_already_blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already blocked"
            )
        
        # Create block
        block = await self.block_repository.create_block(blocker_id, block_data.blocked_id)
        
        return BlockResponseDTO(
            id=block.id,
            blocker_id=block.blocker_id,
            blocked_id=block.blocked_id,
            created_at=block.created_at
        )

    async def unblock_user(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> None:
        """Unblock a user"""
        # Check if user exists
        blocked_user = await self.user_repository.find_by_id(blocked_id)
        if not blocked_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is blocked
        is_blocked = await self.block_repository.is_blocked(blocker_id, blocked_id)
        if not is_blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not blocked"
            )
        
        # Remove block
        success = await self.block_repository.remove_block(blocker_id, blocked_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to unblock user"
            )

    async def get_blocked_users(self, blocker_id: uuid.UUID) -> BlockListResponseDTO:
        """Get list of blocked users"""
        blocks = await self.block_repository.get_blocked_users(blocker_id)
        
        blocked_users = []
        for block in blocks:
            blocked_user_dto = BlockedUserDTO(
                id=block.blocked.id,
                email=block.blocked.email,
                phone=block.blocked.phone,
                image_url=block.blocked.image_url,
                blocked_at=block.created_at
            )
            blocked_users.append(blocked_user_dto)
        
        return BlockListResponseDTO(
            blocked_users=blocked_users,
            total=len(blocked_users)
        )

    async def is_user_blocked(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
        """Check if user is blocked"""
        return await self.block_repository.is_blocked(blocker_id, blocked_id)

    async def get_blocked_user_ids(self, blocker_id: uuid.UUID) -> List[uuid.UUID]:
        """Get list of blocked user IDs"""
        return await self.block_repository.get_blocked_user_ids(blocker_id) 