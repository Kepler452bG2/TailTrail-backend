import uuid
from typing import List, Optional

from fastapi import APIRouter, Query, status, HTTPException, Depends, UploadFile, File, Form
from starlette.responses import JSONResponse

from src.dependencies import DBSessionDep, CurrentUserDep
from src.schemas.post import (
    PostCreateDTO,
    PostUpdateDTO,
    PostResponseDTO,
    PostListResponseDTO,
    PostFiltersDTO,
    PostPaginationDTO,
    PostCreateWithFiles,
    PostUploadResponse
)
from src.services.post.post_service import PostService
from src.utils.upload.upload_service import get_upload_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    responses={
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"}
    }
)


@router.get('/{post_id}', status_code=200, response_model=PostResponseDTO)
async def get_post(post_id: uuid.UUID, db: DBSessionDep):
    post_service = PostService(db)
    return await post_service.get_post_by_id(post_id)


@router.get('/', status_code=200, response_model=PostListResponseDTO)
async def get_posts(
    db: DBSessionDep,
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
    status: Optional[str] = Query(None, description="Post status"),
    user_id: Optional[uuid.UUID] = Query(None, description="User ID"),
    
    search_latitude: Optional[float] = Query(None, ge=-90, le=90, description="Search latitude"),
    search_longitude: Optional[float] = Query(None, ge=-180, le=180, description="Search longitude"),
    radius_km: Optional[float] = Query(None, ge=0.1, le=100, description="Search radius in km"),
):
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
        status=status,
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
    return await post_service.get_posts_with_filters(filters, pagination)


@router.post("/", 
             response_model=PostUploadResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Create lost pet post",
)
async def create_post(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    petName: str = Form(..., 
                        description="Pet name", 
                        example="Ginger"),
    petSpecies: str = Form(..., 
                          description="Pet species", 
                          example="Cat"),
    petBreed: str = Form(..., 
                        description="Pet breed", 
                        example="British Shorthair"),
    age: int = Form(..., 
                   description="Pet age in years", 
                   example=3),
    gender: str = Form(..., 
                      description="Pet gender (auto-converts: male, female)", 
                      example="male"),
    weight: float = Form(..., 
                      description="Pet weight in kg", 
                      example=5.0),
    color: str = Form(..., 
                     description="Pet color", 
                     example="Orange"),
    description: str = Form(..., 
                           description="Detailed description of appearance and characteristics (minimum 10 characters)", 
                           example="Lost orange cat. Very friendly, responds to name. Loves playing with a ball."),
    locationName: str = Form(..., 
                            description="Location name where last seen", 
                            example="Central Park, New York"),
    contactPhone: str = Form(..., 
                            description="Contact phone (format: +country_code_number)", 
                            example="+12345678901"),
    lat: float = Form(..., 
                     ge=-90, 
                     le=90, 
                     description="Latitude of last seen location (can be obtained from Google/Yandex Maps)", 
                     example=40.7829),
    lng: float = Form(..., 
                     ge=-180, 
                     le=180, 
                     description="Longitude of last seen location (can be obtained from Google/Yandex Maps)", 
                     example=-73.9654),
    files: List[UploadFile] = File(None, 
                                  description="Pet photos (JPG/PNG/GIF, up to 10MB each, recommended 1-5 photos)")
):
    try:
        # Создаем координаты из отдельных полей
        from src.schemas.post import Coordinates
        coordinates = Coordinates(lat=lat, lng=lng)
        
        # Создаем объект поста
        post_data = PostCreateWithFiles(
            petName=petName,
            petSpecies=petSpecies,
            petBreed=petBreed,
            age=age,
            gender=gender,
            weight=weight,
            color=color,
            description=description,
            locationName=locationName,
            contactPhone=contactPhone,
            lastSeenLocation=coordinates
        )
        try:
            age_number = int(''.join(filter(str.isdigit, age))) if age else 0
        except:
            age_number = 0
            
        try:
            # Пытаемся извлечь число из строки веса
            weight_str = weight.replace(',', '.').replace(' ', '')
            weight_number = float(''.join(c for c in weight_str if c.isdigit() or c == '.'))
        except:
            weight_number = 1.0
        
        # Создаем координаты для PostLocationDTO
        from src.schemas.post import PostLocationDTO
        location_dto = PostLocationDTO(
            latitude=coordinates.lat,
            longitude=coordinates.lng
        )
        
        # Создаем пост без загруженных файлов (добавим их позже)
        post_dto = PostCreateDTO(
            pet_name=post_data.petName,
            pet_species=post_data.petSpecies,
            pet_breed=post_data.petBreed,
            age=age_number,
            gender=gender,
            weight=weight_number,
            color=post_data.color,
            description=post_data.description,
            location_name=post_data.locationName,
            contact_phone=post_data.contactPhone,
            last_seen_location=location_dto,
            images=["placeholder"]  
        )
        
        uploaded_files = []
        failed_uploads = []
        
        if files and len(files) > 0 and files[0].filename: 
            upload_service = get_upload_service()
            
            for file in files:
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
        
        if uploaded_files:
            post_dto.images = uploaded_files
        else:
            post_dto.images = []
        
        post_service = PostService(db)
        post = await post_service.create_post(post_dto, current_user.id)
        
        return PostUploadResponse(
            post=post,
            uploaded_files=uploaded_files,
            failed_uploads=failed_uploads
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating post with files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating post with files"
        )


@router.patch('/{post_id}', status_code=200, response_model=PostResponseDTO)
async def update_post(
    post_id: uuid.UUID,
    post_data: PostUpdateDTO,
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    post_service = PostService(db)
    return await post_service.update_post(post_id, post_data, current_user.id)


@router.delete('/{post_id}', status_code=204)
async def delete_post(
    post_id: uuid.UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    post_service = PostService(db)
    await post_service.delete_post(post_id, current_user.id)
    return JSONResponse(
        content={"detail": "Post successfully deleted"},
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.get('/my/posts', status_code=200, response_model=List[PostResponseDTO])
async def get_my_posts(
    db: DBSessionDep,
    current_user: CurrentUserDep
):
    post_service = PostService(db)
    return await post_service.get_user_posts(current_user.id)


@router.get('/search/text', status_code=200, response_model=List[PostResponseDTO])
async def search_posts(
    search_text: str = Query(..., min_length=2, description="Search text"),
    db: DBSessionDep = DBSessionDep
):
    post_service = PostService(db)
    return await post_service.search_posts(search_text)


@router.patch('/{post_id}/status', status_code=200, response_model=PostResponseDTO)
async def change_post_status(
    post_id: uuid.UUID,
    new_status: str = Query(..., pattern="^(active|found|closed)$", description="New status"),
    db: DBSessionDep = DBSessionDep,
    current_user: CurrentUserDep = CurrentUserDep
):
    post_service = PostService(db)
    return await post_service.change_post_status(post_id, new_status, current_user.id)

