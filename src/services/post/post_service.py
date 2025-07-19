import uuid
import math
from typing import List, Dict, Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import aiohttp

from src.config import settings

from src.models.post import Post
from src.repositories.post_repository import PostRepository
from src.services.user.user_service import UserService
from src.schemas.post import (
    PostCreateDTO,
    PostUpdateDTO,
    PostResponseDTO,
    PostFiltersDTO,
    PostPaginationDTO,
    PostListResponseDTO,
    PostLocationDTO,
    LikeResponseDTO
)


class PostService:
    def __init__(self, db: AsyncSession):
        self.post_repository = PostRepository(db)

    async def create_post(self, post_data: PostCreateDTO, user_id: uuid.UUID) -> PostResponseDTO:
        """Create new post"""
        
        # Для координат устанавливаем значения по умолчанию, если не предоставлены
        if post_data.last_seen_location:
            last_seen_latitude = post_data.last_seen_location.latitude
            last_seen_longitude = post_data.last_seen_location.longitude
        else:
            # Координаты тоже могут быть NULL
            last_seen_latitude = None
            last_seen_longitude = None
        
        new_post = Post(
            pet_name=post_data.pet_name,
            pet_species=post_data.pet_species,
            pet_breed=post_data.pet_breed,
            age=post_data.age,
            gender=post_data.gender,
            weight=post_data.weight,
            color=post_data.color,
            description=post_data.description,
            location_name=post_data.location_name,
            contact_phone=post_data.contact_phone,
            last_seen_latitude=last_seen_latitude,
            last_seen_longitude=last_seen_longitude,
            images=post_data.images or [],
            user_id=user_id,
            status="active"
        )
        
        created_post = await self.post_repository.insert_one(new_post)
        if not created_post:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating post"
            )
        
        return await self._post_to_response_dto(created_post, user_id)

    async def get_post_by_id(self, post_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> PostResponseDTO:
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        return await self._post_to_response_dto(post, current_user_id)

    async def get_posts_with_filters(
        self,
        filters: PostFiltersDTO,
        pagination: PostPaginationDTO,
        current_user_id: Optional[uuid.UUID] = None
    ) -> PostListResponseDTO:
        posts, total_count = await self.post_repository.find_with_filters_and_pagination(
            filters, pagination, current_user_id
        )
        
        total_pages = math.ceil(total_count / pagination.per_page)
        has_next = pagination.page < total_pages
        has_prev = pagination.page > 1
        
        post_dtos = []
        for post in posts:
            post_dto = await self._post_to_response_dto(post, current_user_id)
            post_dtos.append(post_dto)
        
        return PostListResponseDTO(
            posts=post_dtos,
            total=total_count,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )

    async def update_post(
        self, 
        post_id: uuid.UUID, 
        post_data: PostUpdateDTO, 
        user_id: uuid.UUID
    ) -> PostResponseDTO:
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to edit this post"
            )
        
        if post_data.pet_name is not None:
            post.pet_name = post_data.pet_name
        if post_data.pet_species is not None:
            post.pet_species = post_data.pet_species
        if post_data.pet_breed is not None:
            post.pet_breed = post_data.pet_breed
        if post_data.age is not None:
            post.age = post_data.age
        if post_data.gender is not None:
            post.gender = post_data.gender
        if post_data.weight is not None:
            post.weight = post_data.weight
        if post_data.color is not None:
            post.color = post_data.color
        if post_data.description is not None:
            post.description = post_data.description
        if post_data.location_name is not None:
            post.location_name = post_data.location_name
        if post_data.contact_phone is not None:
            post.contact_phone = post_data.contact_phone
        if post_data.last_seen_location is not None:
            post.last_seen_latitude = post_data.last_seen_location.latitude
            post.last_seen_longitude = post_data.last_seen_location.longitude
        if post_data.images is not None:
            post.images = post_data.images
        if post_data.status is not None:
            post.status = post_data.status
        
        updated_post = await self.post_repository.update_one(post)
        if not updated_post:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating post"
            )
        
        return await self._post_to_response_dto(updated_post, user_id)

    async def delete_post(self, post_id: uuid.UUID, user_id: uuid.UUID) -> None:
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to delete this post"
            )
        
        success = await self.post_repository.delete_one(post_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting post"
            )

    async def get_user_posts(self, user_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> List[PostResponseDTO]:
        posts = await self.post_repository.find_by_user_id(user_id, current_user_id)
        post_dtos = []
        for post in posts:
            post_dto = await self._post_to_response_dto(post, current_user_id)
            post_dtos.append(post_dto)
        return post_dtos

    async def search_posts(self, search_text: str, current_user_id: Optional[uuid.UUID] = None) -> List[PostResponseDTO]:
        posts = await self.post_repository.search_by_text(search_text, current_user_id)
        post_dtos = []
        for post in posts:
            post_dto = await self._post_to_response_dto(post, current_user_id)
            post_dtos.append(post_dto)
        return post_dtos

    async def get_posts_statistics(self) -> Dict[str, Any]:
        return await self.post_repository.get_posts_statistics()

    async def change_post_status(
        self, 
        post_id: uuid.UUID, 
        new_status: str, 
        user_id: uuid.UUID
    ) -> PostResponseDTO:
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to change status of this post"
            )
        valid_statuses = ["active", "found", "closed"]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Available statuses: {', '.join(valid_statuses)}"
            )
        
        post.status = new_status
        updated_post = await self.post_repository.update_one(post)
        if not updated_post:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating post status"
            )
        
        return await self._post_to_response_dto(updated_post, user_id)

    async def update_post_images(self, post_id: int, image_urls: list[str], user_id: int) -> PostResponseDTO:
        """Update post images"""
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to edit this post"
            )
        
        post.images = image_urls
        updated_post = await self.post_repository.update_one(post)
        return await self._post_to_response_dto(updated_post, user_id)

    # Методы для работы с лайками
    async def toggle_like(self, post_id: uuid.UUID, user_id: uuid.UUID) -> LikeResponseDTO:
        """Toggle like on a post (like if not liked, unlike if liked)"""
        
        # Check if post exists
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Check if user already liked this post
        existing_like = await self.post_repository.find_like_by_user_and_post(user_id, post_id)
        
        if existing_like:
            # Unlike the post
            await self.post_repository.delete_like_by_user_and_post(user_id, post_id)
            is_liked = False
        else:
            # Like the post
            await self.post_repository.create_like(user_id, post_id)
            is_liked = True
        
        # Get updated likes count
        likes_count = await self.post_repository.count_likes_by_post(post_id)
        
        return LikeResponseDTO(
            post_id=post_id,
            user_id=user_id,
            likes_count=likes_count,
            is_liked=is_liked
        )

    async def get_like_status(self, post_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> tuple[int, bool]:
        """Get like count and whether user has liked the post"""
        likes_count = await self.post_repository.count_likes_by_post(post_id)
        is_liked = False
        
        if user_id:
            existing_like = await self.post_repository.find_like_by_user_and_post(user_id, post_id)
            is_liked = existing_like is not None
        
        return likes_count, is_liked

    async def _post_to_response_dto(self, post: Post, current_user_id: Optional[uuid.UUID] = None) -> PostResponseDTO:
        """Convert Post model to PostResponseDTO with like information"""
        
        # Get like information
        likes_count, is_liked = await self.get_like_status(post.id, current_user_id)
        
        # Create location DTO only if coordinates are present
        location_dto = None
        if post.last_seen_latitude is not None and post.last_seen_longitude is not None:
            location_dto = PostLocationDTO(
                latitude=post.last_seen_latitude,
                longitude=post.last_seen_longitude
            )
        
        return PostResponseDTO(
            id=post.id,
            pet_name=post.pet_name,
            pet_species=post.pet_species,
            pet_breed=post.pet_breed,
            age=post.age,
            gender=post.gender,
            weight=post.weight,
            color=post.color,
            description=post.description,
            location_name=post.location_name,
            contact_phone=post.contact_phone,
            last_seen_location=location_dto,
            images=post.images,
            status=post.status,
            created_at=post.created_at,
            updated_at=post.updated_at,
            user_id=post.user_id,
            likes_count=likes_count,
            is_liked=is_liked
        )

    async def send_complaint(self, post_id: uuid.UUID, complaint_text: str, user_id: uuid.UUID) -> dict:
        """Send complaint to external service"""
        # Проверяем, что пост существует
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )

        # Получаем данные пользователя
        user_service = UserService(self.post_repository.dao.db)
        user = await user_service.get_user_by_id(user_id)
        
        complaint_payload = {
            "complaint": complaint_text,
            "user_name": user.email if user.email else "Неизвестный",
            "email": user.email if user.email else "Не указан",
            "phone": user.phone if user.phone else "Не указан",
            "post_id": str(post_id)
        }
        
        # Отправляем жалобу на внешний сервер
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.COMPLAINT_SERVICE_URL,
                    json=complaint_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return {"success": True, "message": "Жалоба успешно отправлена"}
                    else:
                        return {"success": False, "message": f"Ошибка при отправке жалобы: {response.status}"}
                        
        except Exception as e:
            return {"success": False, "message": f"Ошибка соединения: {str(e)}"}