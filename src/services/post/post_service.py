import uuid
import math
from typing import List, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.post import Post
from src.repositories.post_repository import PostRepository
from src.schemas.post import (
    PostCreateDTO,
    PostUpdateDTO,
    PostResponseDTO,
    PostFiltersDTO,
    PostPaginationDTO,
    PostListResponseDTO,
    PostLocationDTO
)


class PostService:
    def __init__(self, db: AsyncSession):
        self.post_repository = PostRepository(db)

    async def create_post(self, post_data: PostCreateDTO, user_id: uuid.UUID) -> PostResponseDTO:
        """Create new post"""
        
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
            last_seen_latitude=post_data.last_seen_location.latitude,
            last_seen_longitude=post_data.last_seen_location.longitude,
            images=post_data.images,
            user_id=user_id,
            status="active"
        )
        
        created_post = await self.post_repository.insert_one(new_post)
        if not created_post:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating post"
            )
        
        return self._post_to_response_dto(created_post)

    async def get_post_by_id(self, post_id: uuid.UUID) -> PostResponseDTO:
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        return self._post_to_response_dto(post)

    async def get_posts_with_filters(
        self,
        filters: PostFiltersDTO,
        pagination: PostPaginationDTO
    ) -> PostListResponseDTO:
        posts, total_count = await self.post_repository.find_with_filters_and_pagination(
            filters, pagination
        )
        
        total_pages = math.ceil(total_count / pagination.per_page)
        has_next = pagination.page < total_pages
        has_prev = pagination.page > 1
        
        post_dtos = [self._post_to_response_dto(post) for post in posts]
        
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
        
        return self._post_to_response_dto(updated_post)

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

    async def get_user_posts(self, user_id: uuid.UUID) -> List[PostResponseDTO]:
        posts = await self.post_repository.find_by_user_id(user_id)
        return [self._post_to_response_dto(post) for post in posts]

    async def search_posts(self, search_text: str) -> List[PostResponseDTO]:
        posts = await self.post_repository.search_by_text(search_text)
        return [self._post_to_response_dto(post) for post in posts]

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
        
        return self._post_to_response_dto(updated_post)

    async def update_post_images(self, post_id: int, image_urls: list[str], user_id: int) -> PostResponseDTO:
        """Update list of post images"""
        post = await self.get_post_by_id(post_id)
        
        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to change this post"
            )
        
        updated_post = await self.post_repository.update_post_images(post_id, image_urls)
        return self._post_to_response_dto(updated_post)

    def _post_to_response_dto(self, post: Post) -> PostResponseDTO:
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
            last_seen_location=PostLocationDTO(
                latitude=post.last_seen_latitude,
                longitude=post.last_seen_longitude
            ),
            images=post.images,
            status=post.status,
            created_at=post.created_at,
            updated_at=post.updated_at,
            user_id=post.user_id
        ) 