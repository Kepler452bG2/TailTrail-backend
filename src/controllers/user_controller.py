import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, status, HTTPException, UploadFile, File, Form
from pydantic import ValidationError
from starlette.responses import JSONResponse

from src.dependencies import get_session, get_current_user
from src.schemas.post import PostResponseDTO
from src.schemas.user import UserDTO, UserUpdateDTO
from src.services.post.post_service import PostService
from src.services.user.user_service import UserService
from src.utils.upload.upload_service import get_upload_service
from src.utils.exceptions import raise_validation_exception
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/profile', status_code=200, response_model=UserDTO)
async def get_current_user_profile(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    try:
        user_service = UserService(session)
        user = await user_service.get_user_by_id(current_user.id)
        
        return UserDTO(
            id=user.id,
            email=user.email,
            phone=user.phone,
            created_at=user.created_at,
            image_url=user.image_url
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user profile: {e}"
        )


@router.patch('/profile', status_code=200, response_model=UserDTO)
async def update_user_profile(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    phone: Optional[str] = Form(None, description="Phone number"),
    current_password: Optional[str] = Form(None, description="Current password"),
    new_password: Optional[str] = Form(None, description="New password"),
    profile_image: Optional[UploadFile] = File(None, description="Profile image")
):
    """Update user profile with optional image upload"""
    try:
        user_service = UserService(session)
        profile_image_url = None
        
        if profile_image and profile_image.filename:
            upload_service = get_upload_service()
            
            try:
                file_content = await profile_image.read()
                
                upload_result = await upload_service.upload_file(
                    file_content=file_content,
                    filename=profile_image.filename,
                    content_type=profile_image.content_type,
                    folder="users/profiles"
                )
                
                if upload_result.success:
                    profile_image_url = upload_result.file_url
                else:
                    logger.error(f"Failed to upload profile image: {upload_result.error}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to upload profile image: {upload_result.error}"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing profile image: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error processing profile image: {e}"
                )
        
        # Update user data
        user_update_data = UserUpdateDTO(
            user_id=current_user.id,
            phone=phone if phone and phone.strip() else None,
            current_password=current_password,
            new_password=new_password
        )
        
        await user_service.update_user(user_update_data, profile_image_url)
        
        # Return updated user profile
        updated_user = await user_service.get_user_by_id(current_user.id)
        return UserDTO(
            id=updated_user.id,
            email=updated_user.email,
            phone=updated_user.phone,
            created_at=updated_user.created_at,
            image_url=updated_user.image_url
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise_validation_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user profile: {e}"
        )


@router.delete('/profile/image', status_code=200)
async def delete_profile_image(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    try:
        user_service = UserService(session)
        await user_service.delete_profile_image(current_user.id)
        
        return JSONResponse(
            content={"detail": "Profile image deleted successfully"},
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting profile image: {e}"
        )


@router.get('/{user_id}/posts', status_code=200, response_model=List[PostResponseDTO])
async def get_user_posts(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    try:
        post_service = PostService(session)
        return await post_service.get_user_posts(
            user_id=user_id, 
            current_user_id=current_user.id if current_user else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user posts: {e}"
        )


@router.get('/{user_id}', status_code=200, response_model=UserDTO)
async def get_user_by_id(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        user_service = UserService(session)
        user = await user_service.get_user_by_id(user_id)
        
        return UserDTO(
            id=user.id,
            email=user.email,
            phone=user.phone,
            created_at=user.created_at,
            image_url=user.image_url
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user by ID: {e}"
        )


