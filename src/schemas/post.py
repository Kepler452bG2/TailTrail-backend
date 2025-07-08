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
    pet_name: str = Field(..., min_length=1, max_length=100, description="Pet name")
    pet_species: str = Field(..., min_length=1, max_length=50, description="Pet species")
    pet_breed: str = Field(..., min_length=1, max_length=100, description="Pet breed")
    age: int = Field(..., ge=0, le=30, description="Pet age")
    gender: str = Field(..., pattern="^(male|female|unknown)$", description="Pet gender")
    weight: float = Field(..., ge=0.1, le=200, description="Pet weight in kg")
    color: str = Field(..., min_length=1, max_length=50, description="Pet color")
    description: str = Field(..., min_length=10, max_length=2000, description="Description")
    location_name: str = Field(..., min_length=1, max_length=200, description="Location name")
    contact_phone: str = Field(..., pattern=r"^\+\d{1,15}$", description="Contact phone")
    last_seen_location: PostLocationDTO = Field(..., description="Last seen location coordinates")
    images: List[str] = Field(..., min_items=1, max_items=10, description="Array of image URLs")

    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if not v:
            raise ValueError('At least one image must be uploaded')
        return v


class PostCreate(BaseModel):
    petName: str = Field(..., min_length=1, max_length=100)
    petSpecies: str = Field(..., min_length=1, max_length=50) 
    petBreed: str = Field(..., min_length=1, max_length=100)
    age: str = Field(..., min_length=1, max_length=50)
    gender: str = Field(..., min_length=1, max_length=20)
    weight: str = Field(..., min_length=1, max_length=50)
    color: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=2000)
    locationName: str = Field(..., min_length=1, max_length=200)
    contactPhone: str = Field(..., min_length=1, max_length=20)
    lastSeenLocation: Coordinates


class PostCreateWithFiles(BaseModel):
    """Schema for creating posts with file uploads - matches controller Form parameters"""
    petName: str = Field(..., min_length=1, max_length=100)
    petSpecies: str = Field(..., min_length=1, max_length=50) 
    petBreed: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=30, description="Pet age in years")
    gender: str = Field(..., min_length=1, max_length=20)
    weight: float = Field(..., ge=0.1, le=200.0, description="Pet weight in kg")
    color: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=2000)
    locationName: str = Field(..., min_length=1, max_length=200)
    contactPhone: str = Field(..., min_length=1, max_length=20)
    lastSeenLocation: Coordinates


class PostUpdateDTO(BaseModel):
    pet_name: Optional[str] = Field(None, min_length=1, max_length=100)
    pet_species: Optional[str] = Field(None, min_length=1, max_length=50)
    pet_breed: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=30)
    gender: Optional[str] = Field(None, pattern="^(male|female|unknown)$")
    weight: Optional[float] = Field(None, ge=0.1, le=200)
    color: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    location_name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_phone: Optional[str] = Field(None, pattern=r"^\+\d{1,15}$")
    last_seen_location: Optional[PostLocationDTO] = None
    images: Optional[List[str]] = Field(None, min_items=1, max_items=10)
    status: Optional[str] = Field(None, pattern="^(active|found|closed)$")


class PostResponseDTO(BaseModel):
    id: uuid.UUID
    pet_name: str
    pet_species: str
    pet_breed: str
    age: int
    gender: str
    weight: float
    color: str
    description: str
    location_name: str
    contact_phone: str
    last_seen_location: PostLocationDTO
    images: List[str]
    status: str
    created_at: datetime
    updated_at: datetime
    user_id: uuid.UUID


class PostFiltersDTO(BaseModel):
    pet_species: Optional[str] = None
    pet_breed: Optional[str] = None
    gender: Optional[str] = None
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, le=30)
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
    petName: Optional[str] = Field(None, min_length=1, max_length=100)
    petSpecies: Optional[str] = Field(None, min_length=1, max_length=50)
    petBreed: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[str] = Field(None, min_length=1, max_length=50)
    gender: Optional[str] = Field(None, min_length=1, max_length=20)
    weight: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    locationName: Optional[str] = Field(None, min_length=1, max_length=200)
    contactPhone: Optional[str] = Field(None, min_length=1, max_length=20)
    lastSeenLocation: Optional[Coordinates] = None
    status: Optional[PostStatus] = None


class PostResponse(BaseModel):
    id: int
    petName: str
    petSpecies: str
    petBreed: str
    age: str
    gender: str
    weight: str
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