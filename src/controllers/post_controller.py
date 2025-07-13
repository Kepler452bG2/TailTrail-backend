import uuid
from typing import List, Optional

from fastapi import APIRouter, Query, status, HTTPException, Depends, UploadFile, File, Form
from pydantic import ValidationError
from starlette.responses import JSONResponse

from src.dependencies import DBSessionDep, CurrentUserDep
from src.schemas.post import (
    Coordinates,
    PostCreateDTO,
    PostLocationDTO,
    PostUpdateDTO,
    PostResponseDTO,
    PostListResponseDTO,
    PostFiltersDTO,
    PostPaginationDTO,
    PostCreateWithFiles,
    PostUploadResponse,
    LikeResponseDTO,
    ComplaintRequestDTO,
    ComplaintResponseDTO
)
from src.services.post.post_service import PostService
from src.utils.upload.upload_service import get_upload_service
from src.utils.llm.gemini import validate_uploaded_files, validate_text_content
from src.utils.exceptions.exceptions import raise_validation_exception
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/{post_id}', status_code=200, response_model=PostResponseDTO)
async def get_post(post_id: uuid.UUID, db: DBSessionDep, current_user: CurrentUserDep = None):
    """Get post by ID"""
    try:
        post_service = PostService(db)
        return await post_service.get_post_by_id(post_id, current_user.id if current_user else None)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting post: {e}"
        )


@router.get('/', status_code=200, response_model=PostListResponseDTO)
async def get_posts(
    db: DBSessionDep,
    current_user: CurrentUserDep = None,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    
    pet_species: Optional[str] = Query(None, description="Pet species"),
    pet_breed: Optional[str] = Query(None, description="Pet breed"),
    gender: Optional[str] = Query(None, description="Pet gender"),
    age_min: Optional[int] = Query(None, ge=0, description="Minimum age"),
    age_max: Optional[int] = Query(None, le=30, description="Maximum age"),
    weight_min: Optional[float] = Query(None, ge=0.1, description="Minimum weight"),
    weight_max: Optional[float] = Query(None, le=200, description="Maximum weight"),
    color: Optional[str] = Query(None, description="Pet color"),
    location_name: Optional[str] = Query(None, description="Location name"),
    post_status: Optional[str] = Query(None, description="Post status"),
    user_id: Optional[uuid.UUID] = Query(None, description="User ID"),
    
    search_latitude: Optional[float] = Query(None, ge=-90, le=90, description="Search latitude"),
    search_longitude: Optional[float] = Query(None, ge=-180, le=180, description="Search longitude"),
    radius_km: Optional[float] = Query(None, ge=0.1, le=100, description="Search radius in km"),
):
    """Get posts with filters and pagination"""
    try:
        filters = PostFiltersDTO(
            pet_species=pet_species,
            pet_breed=pet_breed,
            gender=gender,
            age_min=age_min,
            age_max=age_max,
            weight_min=weight_min,
            weight_max=weight_max,
            color=color,
            location_name=location_name,
            status=post_status,
            user_id=user_id,
            search_latitude=search_latitude,
            search_longitude=search_longitude,
            radius_km=radius_km
        )
        
        pagination = PostPaginationDTO(
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        post_service = PostService(db)
        return await post_service.get_posts_with_filters(filters, pagination, current_user.id if current_user else None)
    except ValidationError as e:
        logger.error(f"Validation error in get_posts: {e}")
        raise_validation_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting posts: {e}"
        )


@router.post("/", 
             response_model=PostUploadResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Create lost pet post",
)
async def create_post(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    petName: Optional[str] = Form(None, 
                                 description="Pet name", 
                                 example="Ginger"),
    petSpecies: Optional[str] = Form(None, 
                                    description="Pet species", 
                                    example="Cat"),
    petBreed: Optional[str] = Form(None, 
                                  description="Pet breed", 
                                  example="British Shorthair"),
    age: Optional[int] = Form(None, 
                             description="Pet age in years", 
                             example="3"),
    gender: Optional[str] = Form(None, 
                                description="Pet gender (auto-converts: male, female)", 
                                example="male"),
    weight: Optional[float] = Form(None, 
                                description="Pet weight in kg", 
                                example="5.0"),
    color: Optional[str] = Form(None, 
                               description="Pet color", 
                               example="Orange"),
    description: Optional[str] = Form(None, 
                                     description="Detailed description of appearance and characteristics", 
                                     example="Lost orange cat. Very friendly, responds to name. Loves playing with a ball."),
    locationName: Optional[str] = Form(None, 
                                      description="Location name where last seen", 
                                      example="Central Park, New York"),
    contactPhone: Optional[str] = Form(None, 
                                      description="Contact phone (format: +country_code_number)", 
                                      example="+12345678901"),
    lat: Optional[float] = Form(None, 
                             description="Latitude of last seen location (can be obtained from Google/Yandex Maps)", 
                             example="40.7829"),
    lng: Optional[float] = Form(None, 
                             description="Longitude of last seen location (can be obtained from Google/Yandex Maps)", 
                             example="-73.9654"),
    files: Optional[List[UploadFile]] = File(None, 
                                           description="Pet photos (JPG/PNG/GIF, up to 10MB each, recommended 1-5 photos)")
):
    try:
        coordinates = None
        location_dto = None
        
        if lat is not None and lng is not None:
            coordinates = Coordinates(lat=lat, lng=lng)
            location_dto = PostLocationDTO(
                latitude=coordinates.lat,
                longitude=coordinates.lng
            )
        
        post_dto = PostCreateDTO(
            pet_name=petName if petName and petName.strip() else None,
            pet_species=petSpecies if petSpecies and petSpecies.strip() else None,
            pet_breed=petBreed if petBreed and petBreed.strip() else None,
            age=age,
            gender=gender if gender and gender.strip() else None,
            weight=weight,
            color=color if color and color.strip() else None,
            description=description if description and description.strip() else None,
            location_name=locationName if locationName and locationName.strip() else None,
            contact_phone=contactPhone if contactPhone and contactPhone.strip() else None,
            last_seen_location=location_dto,
            images=[]  
        )
        
        uploaded_files = []
        failed_uploads = []
        
        # Проверка текстового контента с помощью Gemini
        text_parts = []
        if post_dto.pet_name:
            text_parts.append(f"Имя: {post_dto.pet_name}")
        if post_dto.description:
            text_parts.append(f"Описание: {post_dto.description}")
        if post_dto.location_name:
            text_parts.append(f"Местоположение: {post_dto.location_name}")
        if post_dto.pet_species:
            text_parts.append(f"Вид: {post_dto.pet_species}")
        if post_dto.pet_breed:
            text_parts.append(f"Порода: {post_dto.pet_breed}")
        
        if text_parts:
            combined_text = "\n".join(text_parts)
            await validate_text_content(combined_text)
        
        if files and len(files) > 0 and files[0] and files[0].filename: 
            # Анализ изображений с помощью Gemini
            await validate_uploaded_files(files)
            
            upload_service = get_upload_service()
            
            for file in files:
                if file is None:
                    continue
                    
                try:
                    file_content = await file.read()
                    
                    upload_result = await upload_service.upload_file(
                        file_content=file_content,
                        filename=file.filename,
                        content_type=file.content_type,
                        folder="posts"
                    )
                    
                    if upload_result.success:
                        uploaded_files.append(upload_result.file_url)
                    else:
                        logger.error(f"Failed to upload file {file.filename}: {upload_result.error}")
                        failed_uploads.append(f"{file.filename}: {upload_result.error}")
                        
                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {e}")
                    failed_uploads.append(f"{file.filename}: {str(e)}")
        
        # Устанавливаем загруженные файлы или пустой список
        post_dto.images = uploaded_files if uploaded_files else []
        
        post_service = PostService(db)
        post = await post_service.create_post(post_dto, current_user.id)
        
        return PostUploadResponse(
            post=post,
            uploaded_files=uploaded_files,
            failed_uploads=failed_uploads
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise_validation_exception(e)
    
    except HTTPException:
        # Передаем HTTPException без изменений (включая ошибки Gemini валидации)
        raise
    
    except Exception as e:
        logger.error(f"Error creating post with files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating post with files: {e}"
        )
    


@router.patch('/{post_id}', status_code=200, response_model=PostResponseDTO)
async def update_post(
    post_id: uuid.UUID,
    post_data: PostUpdateDTO,
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    """Update post by ID"""
    try:
        # Проверка текстового контента с помощью Gemini
        text_parts = []
        if post_data.pet_name:
            text_parts.append(f"Имя: {post_data.pet_name}")
        if post_data.description:
            text_parts.append(f"Описание: {post_data.description}")
        if post_data.location_name:
            text_parts.append(f"Местоположение: {post_data.location_name}")
        if post_data.pet_species:
            text_parts.append(f"Вид: {post_data.pet_species}")
        if post_data.pet_breed:
            text_parts.append(f"Порода: {post_data.pet_breed}")
        
        if text_parts:
            combined_text = "\n".join(text_parts)
            await validate_text_content(combined_text)
        
        post_service = PostService(db)
        return await post_service.update_post(post_id, post_data, current_user.id)
    except ValidationError as e:
        logger.error(f"Validation error in update_post: {e}")
        raise_validation_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating post: {e}"
        )


@router.delete('/{post_id}', status_code=204)
async def delete_post(
    post_id: uuid.UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    """Delete post by ID"""
    try:
        post_service = PostService(db)
        await post_service.delete_post(post_id, current_user.id)
        return JSONResponse(
            content={"detail": "Post successfully deleted"},
            status_code=status.HTTP_204_NO_CONTENT
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting post: {e}"
            )


@router.get('/my/posts', status_code=200, response_model=List[PostResponseDTO])
async def get_my_posts(
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    """Get current user's posts"""
    try:
        post_service = PostService(db)
        return await post_service.get_user_posts(current_user.id, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user posts: {e}"
        )


@router.get('/search/text', status_code=200, response_model=List[PostResponseDTO])
async def search_posts(
    search_text: str = Query(..., min_length=2, description="Search text"),
    db: DBSessionDep = DBSessionDep,
    current_user: CurrentUserDep = None
):
    """Search posts by text"""
    try:
        post_service = PostService(db)
        return await post_service.search_posts(search_text, current_user.id if current_user else None)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching posts: {e}"
        )


@router.patch('/{post_id}/status', status_code=200, response_model=PostResponseDTO)
async def change_post_status(
    post_id: uuid.UUID,
    new_status: str = Query(..., pattern="^(active|found|closed)$", description="New status"),
    db: DBSessionDep = DBSessionDep,
    current_user: CurrentUserDep = CurrentUserDep
):
    """Change post status"""
    try:
        post_service = PostService(db)
        return await post_service.change_post_status(post_id, new_status, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing post status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing post status: {e}"
        )


# Новые роуты для лайков
@router.post('/{post_id}/like', status_code=200, response_model=LikeResponseDTO)
async def toggle_like(
    post_id: uuid.UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    """Toggle like on a post (like if not liked, unlike if liked)"""
    try:
        post_service = PostService(db)
        return await post_service.toggle_like(post_id, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling like: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling like: {e}"
        )


@router.get('/{post_id}/likes', status_code=200)
async def get_like_status(
    post_id: uuid.UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep = None
):
    """Get like status for a post"""
    try:
        post_service = PostService(db)
        likes_count, is_liked = await post_service.get_like_status(post_id, current_user.id if current_user else None)
        return {
            "post_id": post_id,
            "likes_count": likes_count,
            "is_liked": is_liked
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting like status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting like status: {e}"
        )
        

@router.post('/{post_id}/complaint', status_code=200, response_model=ComplaintResponseDTO)
async def create_complaint(
    post_id: uuid.UUID,
    complaint_data: ComplaintRequestDTO,
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    """Create complaint for a post"""
    try:
        # Проверка текста жалобы с помощью Gemini
        await validate_text_content(complaint_data.complaint)
        
        post_service = PostService(db)
        result = await post_service.send_complaint(post_id, complaint_data.complaint, current_user.id)
        
        return ComplaintResponseDTO(
            success=result["success"],
            message=result["message"]
        )
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating complaint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating complaint: {e}"
        )
