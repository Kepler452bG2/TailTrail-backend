import uuid
from typing import List, Optional, Dict, Any, Tuple
from collections.abc import Sequence
from datetime import datetime
from fastapi import HTTPException, status

from sqlalchemy import select, and_, or_, func, desc, asc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.dao.sqlalchemy_dao import SQLAlchemyDAO
from src.models.post import Post
from src.models.like import Like
from src.repositories.base_repository import BaseRepository
from src.schemas.post import PostFiltersDTO, PostPaginationDTO, PostStatus


class PostRepository(BaseRepository[Post]):
    model = Post
    dao_class = SQLAlchemyDAO

    async def find_with_filters_and_pagination(
        self,
        filters: PostFiltersDTO,
        pagination: PostPaginationDTO
    ) -> Tuple[Sequence[Post], int]:
        query = select(self.model)
        
        # Применяем фильтры
        conditions = []
        
        if filters.pet_species:
            conditions.append(self.model.pet_species.ilike(f"%{filters.pet_species}%"))
            
        if filters.pet_breed:
            conditions.append(self.model.pet_breed.ilike(f"%{filters.pet_breed}%"))
            
        if filters.gender:
            conditions.append(self.model.gender == filters.gender)
            
        if filters.age_min is not None:
            conditions.append(self.model.age >= filters.age_min)
            
        if filters.age_max is not None:
            conditions.append(self.model.age <= filters.age_max)
            
        if filters.weight_min is not None:
            conditions.append(self.model.weight >= filters.weight_min)
            
        if filters.weight_max is not None:
            conditions.append(self.model.weight <= filters.weight_max)
            
        if filters.color:
            conditions.append(self.model.color.ilike(f"%{filters.color}%"))
            
        if filters.location_name:
            conditions.append(self.model.location_name.ilike(f"%{filters.location_name}%"))
            
        if filters.status:
            conditions.append(self.model.status == filters.status)
            
        if filters.user_id:
            conditions.append(self.model.user_id == filters.user_id)
            
        if (filters.search_latitude is not None and 
            filters.search_longitude is not None and 
            filters.radius_km is not None):
            
            degree_radius = filters.radius_km / 111.0
            
            lat_condition = and_(
                self.model.last_seen_latitude >= filters.search_latitude - degree_radius,
                self.model.last_seen_latitude <= filters.search_latitude + degree_radius
            )
            
            lng_condition = and_(
                self.model.last_seen_longitude >= filters.search_longitude - degree_radius,
                self.model.last_seen_longitude <= filters.search_longitude + degree_radius
            )
            
            conditions.append(and_(lat_condition, lng_condition))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        count_query = select(func.count(self.model.id)).where(query.whereclause) if query.whereclause is not None else select(func.count(self.model.id))
        count_result = await self.dao.db.execute(count_query)
        total_count = count_result.scalar()
        
        if hasattr(self.model, pagination.sort_by):
            sort_column = getattr(self.model, pagination.sort_by)
            if pagination.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(self.model.created_at))
        
        offset = (pagination.page - 1) * pagination.per_page
        query = query.offset(offset).limit(pagination.per_page)
        
        result = await self.dao.db.execute(query)
        posts = result.scalars().all()
        
        return posts, total_count

    async def find_by_user_id(self, user_id: uuid.UUID) -> Sequence[Post]:
        return await self.dao.find_all(user_id=user_id)

    async def find_active_posts(self) -> Sequence[Post]:
        return await self.dao.find_all(status="active")

    async def search_by_text(self, search_text: str) -> Sequence[Post]:
        query = select(self.model).where(
            or_(
                self.model.pet_name.ilike(f"%{search_text}%"),
                self.model.description.ilike(f"%{search_text}%"),
                self.model.pet_breed.ilike(f"%{search_text}%"),
                self.model.location_name.ilike(f"%{search_text}%")
            )
        )
        
        result = await self.dao.db.execute(query)
        return result.scalars().all()

    async def get_posts_statistics(self) -> Dict[str, Any]:
        status_query = select(
            self.model.status,
            func.count(self.model.id).label('count')
        ).group_by(self.model.status)
        
        status_result = await self.dao.db.execute(status_query)
        status_stats = {row.status: row.count for row in status_result.fetchall()}
        
        species_query = select(
            self.model.pet_species,
            func.count(self.model.id).label('count')
        ).group_by(self.model.pet_species)
        
        species_result = await self.dao.db.execute(species_query)
        species_stats = {row.pet_species: row.count for row in species_result.fetchall()}
        
        total_query = select(func.count(self.model.id))
        total_result = await self.dao.db.execute(total_query)
        total_count = total_result.scalar()
        
        return {
            "total_posts": total_count,
            "by_status": status_stats,
            "by_species": species_stats
        }

    async def update_post_status(self, post_id: int, new_status: PostStatus) -> Post:
        """Update post status"""
        async with self.db.session() as session:
            result = await session.execute(
                select(Post).where(Post.id == post_id)
            )
            post = result.scalar_one_or_none()
            
            if not post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Post not found"
                )
            
            post.status = new_status
            post.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(post)
            return post

    async def update_post_images(self, post_id: int, image_urls: list[str]) -> Post:
        async with self.db.session() as session:
            result = await session.execute(
                select(Post).where(Post.id == post_id)
            )
            post = result.scalar_one_or_none()
            
            if not post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Post not found"
                )
            
            post.images = image_urls
            post.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(post)
            return post

    # Методы для работы с лайками
    async def find_like_by_user_and_post(self, user_id: uuid.UUID, post_id: uuid.UUID) -> Optional[Like]:
        """Find like by user and post"""
        query = select(Like).where(
            Like.user_id == user_id,
            Like.post_id == post_id
        )
        result = await self.dao.db.execute(query)
        return result.scalar_one_or_none()

    async def count_likes_by_post(self, post_id: uuid.UUID) -> int:
        """Count likes for a specific post"""
        query = select(func.count(Like.id)).where(Like.post_id == post_id)
        result = await self.dao.db.execute(query)
        return result.scalar() or 0

    async def delete_like_by_user_and_post(self, user_id: uuid.UUID, post_id: uuid.UUID) -> bool:
        """Delete like by user and post"""
        query = delete(Like).where(
            Like.user_id == user_id,
            Like.post_id == post_id
        )
        result = await self.dao.db.execute(query)
        await self.dao.db.commit()
        return result.rowcount > 0

    async def create_like(self, user_id: uuid.UUID, post_id: uuid.UUID) -> Like:
        """Create a new like"""
        new_like = Like(
            user_id=user_id,
            post_id=post_id
        )
        
        self.dao.db.add(new_like)
        await self.dao.db.commit()
        await self.dao.db.refresh(new_like)
        return new_like 