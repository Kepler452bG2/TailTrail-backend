import uuid
from datetime import datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator, validator


class PostLocationDTO(BaseModel):
    """DTO for location coordinates"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")


class PostStatus(str, Enum):
    ACTIVE = "active"
    FOUND = "found"
    CLOSED = "closed"


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class PostCreateDTO(BaseModel):
    """DTO for creating a post"""
    pet_name: Optional[str] = Field(None, description="Pet name")
    pet_species: Optional[str] = Field(None, description="Pet species")
    pet_breed: Optional[str] = Field(None, description="Pet breed")
    age: Optional[int] = Field(None, description="Pet age")
    gender: Optional[str] = Field(None, description="Pet gender")
    weight: Optional[float] = Field(None, description="Pet weight in kg")
    color: Optional[str] = Field(None, description="Pet color")
    description: Optional[str] = Field(None, description="Description")
    location_name: Optional[str] = Field(None, description="Location name")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    last_seen_location: Optional[PostLocationDTO] = Field(None, description="Last seen location coordinates")
    images: Optional[List[str]] = Field(None, description="Array of image URLs")

    @field_validator('weight')
    @classmethod
    def validate_weight(cls, v):
        if v is not None:
            # Если это строка и она равна 'string' или пустая - возвращаем None
            if isinstance(v, str) and (v.strip().lower() == 'string' or not v.strip()):
                return None
            # Если это число и оно меньше 0 - возвращаем None
            if isinstance(v, (int, float)) and v < 0:
                return None
        return v

    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        if v is not None:
            # Если это строка и она равна 'string' или пустая - возвращаем None
            if isinstance(v, str) and (v.strip().lower() == 'string' or not v.strip()):
                return None
            # Если это число и оно меньше 0 - возвращаем None
            if isinstance(v, (int, float)) and v < 0:
                return None
        return v

    @field_validator('contact_phone')
    @classmethod
    def validate_contact_phone(cls, v):
        if v is not None and v.strip() and v.strip().lower() != 'string' and not v.startswith('+'):
            raise ValueError('Contact phone must start with +')
        return v if v and v.strip() and v.strip().lower() != 'string' else None

    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        if v is not None and v.strip() and v.strip().lower() != 'string' and v not in ['male', 'female', 'unknown']:
            raise ValueError('Gender must be male, female, or unknown')
        return v if v and v.strip() and v.strip().lower() != 'string' else None

    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        # Разрешаем пустые списки - они будут сохранены как пустой список в БД
        if v is not None and len(v) == 0:
            return []
        return v


class PostCreate(BaseModel):
    petName: Optional[str] = Field(None)
    petSpecies: Optional[str] = Field(None) 
    petBreed: Optional[str] = Field(None)
    age: Optional[int] = Field(None)
    gender: Optional[str] = Field(None)
    weight: Optional[float] = Field(None)
    color: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    locationName: Optional[str] = Field(None)
    contactPhone: Optional[str] = Field(None)
    lastSeenLocation: Optional[Coordinates] = None


class PostCreateWithFiles(BaseModel):
    """Schema for creating posts with file uploads - matches controller Form parameters"""
    petName: Optional[str] = Field(None)
    petSpecies: Optional[str] = Field(None) 
    petBreed: Optional[str] = Field(None)
    age: Optional[int] = Field(None, description="Pet age in years")
    gender: Optional[str] = Field(None)
    weight: Optional[float] = Field(None, description="Pet weight in kg")
    color: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    locationName: Optional[str] = Field(None)
    contactPhone: Optional[str] = Field(None)
    lastSeenLocation: Optional[Coordinates] = None


class PostUpdateDTO(BaseModel):
    pet_name: Optional[str] = Field(None)
    pet_species: Optional[str] = Field(None)
    pet_breed: Optional[str] = Field(None)
    age: Optional[int] = Field(None)
    gender: Optional[str] = Field(None, description="Pet gender")
    weight: Optional[float] = Field(None)
    color: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    location_name: Optional[str] = Field(None)
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    last_seen_location: Optional[PostLocationDTO] = None
    images: Optional[List[str]] = Field(None)
    status: Optional[str] = Field(None, pattern="^(active|found|closed)$")

    @field_validator('contact_phone')
    @classmethod
    def validate_contact_phone(cls, v):
        if v is not None and v.strip() and v.strip().lower() != 'string' and not v.startswith('+'):
            raise ValueError('Contact phone must start with +')
        return v if v and v.strip() and v.strip().lower() != 'string' else None

    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        if v is not None and v.strip() and v.strip().lower() != 'string' and v not in ['male', 'female', 'unknown']:
            raise ValueError('Gender must be male, female, or unknown')
        return v if v and v.strip() and v.strip().lower() != 'string' else None

    @field_validator('weight')
    @classmethod
    def validate_weight(cls, v):
        if v is not None:
            # Если это строка и она равна 'string' или пустая - возвращаем None
            if isinstance(v, str) and (v.strip().lower() == 'string' or not v.strip()):
                return None
            # Если это число и оно меньше 0 - возвращаем None
            if isinstance(v, (int, float)) and v < 0:
                return None
        return v

    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        if v is not None:
            # Если это строка и она равна 'string' или пустая - возвращаем None
            if isinstance(v, str) and (v.strip().lower() == 'string' or not v.strip()):
                return None
            # Если это число и оно меньше 0 - возвращаем None
            if isinstance(v, (int, float)) and v < 0:
                return None
        return v


class PostResponseDTO(BaseModel):
    id: uuid.UUID
    pet_name: Optional[str] = None
    pet_species: Optional[str] = None
    pet_breed: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    color: Optional[str] = None
    description: Optional[str] = None
    location_name: Optional[str] = None
    contact_phone: Optional[str] = None
    last_seen_location: Optional[PostLocationDTO] = None
    images: Optional[List[str]] = None
    status: str
    created_at: datetime
    updated_at: datetime
    user_id: uuid.UUID
    likes_count: int = Field(default=0, description="Number of likes")
    is_liked: bool = Field(default=False, description="Whether current user liked this post")


class LikeResponseDTO(BaseModel):
    """DTO for like response"""
    post_id: uuid.UUID
    user_id: uuid.UUID
    likes_count: int
    is_liked: bool


class PostFiltersDTO(BaseModel):
    pet_species: Optional[str] = None
    pet_breed: Optional[str] = None
    gender: Optional[str] = None
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None)
    weight_min: Optional[float] = Field(None, ge=0.1)
    weight_max: Optional[float] = Field(None, le=200)
    color: Optional[str] = None
    location_name: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|found|closed)$")
    user_id: Optional[uuid.UUID] = None
    
    # For radius search
    search_latitude: Optional[float] = Field(None, ge=-90, le=90)
    search_longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[float] = Field(None, ge=0.1, le=100)


class PostPaginationDTO(BaseModel):
    """DTO for pagination"""
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(10, ge=1, le=100, description="Items per page")
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class PostListResponseDTO(BaseModel):
    """DTO for response with post list"""
    posts: List[PostResponseDTO]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PostUpdate(BaseModel):
    petName: Optional[str] = Field(None, max_length=100)
    petSpecies: Optional[str] = Field(None, max_length=50)
    petBreed: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None)
    gender: Optional[str] = Field(None, max_length=20)
    weight: Optional[float] = Field(None)
    color: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    locationName: Optional[str] = Field(None, max_length=200)
    contactPhone: Optional[str] = Field(None, max_length=20)
    lastSeenLocation: Optional[Coordinates] = None
    status: Optional[PostStatus] = None


class PostResponse(BaseModel):
    id: int
    petName: str
    petSpecies: str
    petBreed: str
    age: int
    gender: str
    weight: float
    color: str
    description: str
    locationName: str
    contactPhone: str
    lastSeenLocation: Coordinates
    images: List[str]
    status: PostStatus
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostUploadResponse(BaseModel):
    post: PostResponseDTO = Field(..., description="Created post with all data")
    uploaded_files: List[str] = Field(..., description="URLs of successfully uploaded photos")
    failed_uploads: List[str] = Field(..., description="List of file upload errors (if any)")
    
    class Config:
        schema_extra = {
            "example": {
                    "post": {
                        "id": 1,
                        "petName": "Ginger",
                        "petSpecies": "Cat",
                        "petBreed": "British Shorthair",
                        "age": 3,
                        "gender": "male",
                        "weight": 5.0,
                        "color": "Orange",
                        "description": "Lost orange cat, very friendly...",
                        "locationName": "Central Park, New York",
                        "contactPhone": "+12345678901",
                        "lastSeenLocation": {"lat": 40.7829, "lng": -73.9654},
                        "images": ["https://s3.amazonaws.com/bucket/image1.jpg"],
                        "status": "active",
                        "user_id": 1,
                        "created_at": "2025-01-08T20:00:00Z",
                        "updated_at": "2025-01-08T20:00:00Z"
                    },
                    "uploaded_files": [
                        "https://tail-trail-bucket.s3.us-east-1.amazonaws.com/posts/photo1.jpg"
                    ],
                    "failed_uploads": []
                }
        }


class PostFilters(BaseModel):
    petSpecies: Optional[str] = None
    petBreed: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[PostStatus] = PostStatus.ACTIVE
    locationName: Optional[str] = None
    search: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    radius: Optional[float] = Field(None, gt=0, le=1000)

    @validator('radius')
    def validate_radius_with_coordinates(cls, v, values):
        if v is not None:
            if 'lat' not in values or 'lng' not in values or values['lat'] is None or values['lng'] is None:
                raise ValueError('lat and lng are required when using radius')
        return v


class PostListFilters(PostFilters):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    sort_by: Optional[str] = Field("created_at", pattern="^(created_at|updated_at|petName)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")


class PostsResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PostStatistics(BaseModel):
    total_posts: int
    active_posts: int
    found_posts: int
    closed_posts: int
    posts_by_species: dict


class PostListResponseDTO(BaseModel):
    """DTO for response with post list"""
    posts: List[PostResponseDTO]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool 