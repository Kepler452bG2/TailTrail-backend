import uuid
from typing import List, Optional

from fastapi import APIRouter, Query, status, HTTPException, Depends, UploadFile, File, Form
from pydantic import ValidationError
from starlette.responses import JSONResponse

from src.dependencies import CurrentUserDep, DBSessionDep, get_session, get_current_user
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User
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
from src.utils.llm.gemini import validate_uploaded_files
from src.utils.exceptions.exceptions import raise_validation_exception
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/{post_id}', status_code=200, response_model=PostResponseDTO)
async def get_post(post_id: uuid.UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Get post by ID"""
    try:
        post_service = PostService(session)
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
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
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
        
        post_service = PostService(session)
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
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
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
        
        if files and len(files) > 0 and files[0] and files[0].filename: 
            upload_service = get_upload_service()
            
            for file in files:
                if file is None:
                    continue
                    
                try:
                    # Читаем содержимое файла один раз
                    file_content = await file.read()
                    
                    # Проверяем размер файла
                    if len(file_content) == 0:
                        logger.error(f"File {file.filename} is empty")
                        failed_uploads.append(f"{file.filename}: Файл пустой")
                        continue
                    
                    logger.info(f"Processing file {file.filename} with size {len(file_content)} bytes")
                    
                    # Валидируем файл (без повторного чтения)
                    validation_error = upload_service.validate_file(file.filename, file.content_type, len(file_content))
                    if validation_error:
                        logger.error(f"Validation failed for {file.filename}: {validation_error}")
                        failed_uploads.append(f"{file.filename}: {validation_error}")
                        continue
                    
                    # Анализируем с помощью Gemini (если доступен)
                    try:
                        from src.utils.llm.gemini import image_analyzer
                        if image_analyzer:
                            # Создаем временный UploadFile для анализа
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                                temp_file.write(file_content)
                                temp_file.flush()
                                
                                # Здесь можно добавить анализ если нужно
                                logger.info(f"File {file.filename} passed content validation")
                    except Exception as e:
                        logger.warning(f"Gemini analysis failed for {file.filename}: {e}")
                        # Продолжаем загрузку даже если анализ не удался
                    
                    # Загружаем файл в S3
                    upload_result = await upload_service.upload_file(
                        file_content=file_content,
                        filename=file.filename,
                        content_type=file.content_type,
                        folder="posts"
                    )
                    
                    if upload_result.success:
                        uploaded_files.append(upload_result.file_url)
                        logger.info(f"Successfully uploaded {file.filename}")
                    else:
                        logger.error(f"Failed to upload file {file.filename}: {upload_result.error}")
                        failed_uploads.append(f"{file.filename}: {upload_result.error}")
                        
                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {e}")
                    failed_uploads.append(f"{file.filename}: {str(e)}")
        
        # Устанавливаем загруженные файлы или пустой список
        post_dto.images = uploaded_files if uploaded_files else []
        
        post_service = PostService(session)
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
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update post by ID"""
    try:
        post_service = PostService(session)
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
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete post by ID"""
    try:
        post_service = PostService(session)
        await post_service.delete_post(post_id, current_user.id)
        return None  # 204 No Content should not have a response body
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
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get current user's posts"""
    try:
        post_service = PostService(session)
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
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Search posts by text"""
    try:
        post_service = PostService(session)
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
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Change post status"""
    try:
        post_service = PostService(session)
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
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Toggle like on a post (like if not liked, unlike if liked)"""
    try:
        post_service = PostService(session)
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
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get like status for a post"""
    try:
        post_service = PostService(session)
        like_status = await post_service.get_like_status(post_id, current_user.id if current_user else None)
        return like_status
    except ValidationError as e:
        logger.error(f"Validation error in get_like_status: {e}")
        raise_validation_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting like status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting like status: {e}"
        )


@router.get('/images/check/{filename:path}', status_code=200)
async def check_image_accessibility(filename: str):
    """Проверить доступность изображения"""
    try:
        from src.utils.upload import get_upload_service
        
        upload_service = get_upload_service()
        file_url = f"{upload_service.base_url}/{filename}"
        
        is_accessible = await upload_service.check_file_accessibility(file_url)
        
        return {
            "filename": filename,
            "url": file_url,
            "accessible": is_accessible,
            "bucket": upload_service.bucket_name,
            "base_url": upload_service.base_url
        }
        
    except Exception as e:
        logger.error(f"Error checking image accessibility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking image: {e}"
        )


@router.get('/s3/status', status_code=200)
async def check_s3_status():
    """Проверить статус S3 и настройки bucket"""
    try:
        from src.utils.upload import get_upload_service
        
        upload_service = get_upload_service()
        
        # Проверяем bucket
        try:
            response = upload_service.s3_client.head_bucket(Bucket=upload_service.bucket_name)
            bucket_exists = True
        except ClientError as e:
            bucket_exists = False
            bucket_error = str(e)
        
        # Проверяем bucket policy
        try:
            policy_response = upload_service.s3_client.get_bucket_policy(Bucket=upload_service.bucket_name)
            bucket_policy = policy_response.get('Policy', 'No policy')
        except ClientError as e:
            bucket_policy = f"Error getting policy: {e}"
        
        # Проверяем public access block
        try:
            access_response = upload_service.s3_client.get_public_access_block(Bucket=upload_service.bucket_name)
            public_access = access_response.get('PublicAccessBlockConfiguration', {})
        except ClientError as e:
            public_access = f"Error getting public access: {e}"
        
        return {
            "bucket_name": upload_service.bucket_name,
            "region": upload_service.region_name,
            "base_url": upload_service.base_url,
            "bucket_exists": bucket_exists,
            "bucket_policy": bucket_policy,
            "public_access_block": public_access,
            "aws_credentials_configured": bool(upload_service.s3_client)
        }
        
    except Exception as e:
        logger.error(f"Error checking S3 status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking S3: {e}"
        )


@router.post('/test-upload', status_code=200)
async def test_file_upload(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Тестировать загрузку файла"""
    try:
        from src.utils.upload import get_upload_service
        
        upload_service = get_upload_service()
        
        # Читаем файл
        file_content = await file.read()
        
        logger.info(f"Test upload: {file.filename}, size: {len(file_content)} bytes")
        
        # Загружаем в тестовую папку
        upload_result = await upload_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type,
            folder="test"
        )
        
        return {
            "filename": file.filename,
            "original_size": len(file_content),
            "upload_result": upload_result.model_dump() if upload_result else None,
            "bucket": upload_service.bucket_name,
            "base_url": upload_service.base_url
        }
        
    except Exception as e:
        logger.error(f"Error in test upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in test upload: {e}"
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
