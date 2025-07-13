import uuid
from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import DBSessionDep, CurrentUserDep
from src.services.block_service import BlockService
from src.schemas.block import (
    BlockCreateDTO,
    BlockResponseDTO,
    BlockListResponseDTO
)

from src.logger import logger

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=BlockResponseDTO)
async def block_user(
    block_data: BlockCreateDTO,
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    """Block a user"""
    try:
        block_service = BlockService(db)
        return await block_service.block_user(current_user.id, block_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error blocking user: {e}"
        )


@router.delete("/{blocked_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(
    blocked_id: uuid.UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    """Unblock a user"""
    try:
        block_service = BlockService(db)
        await block_service.unblock_user(current_user.id, blocked_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error unblocking user: {e}"
        )


@router.get("/", status_code=status.HTTP_200_OK, response_model=BlockListResponseDTO)
async def get_blocked_users(
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    """Get list of blocked users"""
    try:
        block_service = BlockService(db)
        return await block_service.get_blocked_users(current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting blocked users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting blocked users: {e}"
        )


@router.get("/{user_id}/is-blocked", status_code=status.HTTP_200_OK)
async def check_if_user_blocked(
    user_id: uuid.UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    """Check if user is blocked"""
    try:
        block_service = BlockService(db)
        is_blocked = await block_service.is_user_blocked(current_user.id, user_id)
        return {"is_blocked": is_blocked}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking if user is blocked: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking if user is blocked: {e}"
        ) 