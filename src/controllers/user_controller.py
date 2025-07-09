import uuid
from dependencies import CurrentUserDep, DBSessionDep
from typing import List

from fastapi import APIRouter
from schemas.post import PostResponseDTO
from services.post.post_service import PostService


router = APIRouter()

@router.get('/{user_id}/posts', status_code=200, response_model=List[PostResponseDTO])
async def get_user_posts(
    db: DBSessionDep,
    user_id: uuid.UUID
):
    post_service = PostService(db)
    return await post_service.get_user_posts(user_id=user_id)


