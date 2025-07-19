import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, status
from httpx import AsyncClient
from io import BytesIO

from src.models.post import Post
from src.models.user import User
from src.schemas.post import PostCreateDTO


class TestPostController:
    """Test cases for post controller endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_post_success(self, async_client: AsyncClient, test_post: Post):
        """Test successful post retrieval."""
        response = await async_client.get(f"/api/v1/posts/{test_post.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_post.id)
        assert data["pet_name"] == "Fluffy"
        assert data["pet_species"] == "Cat"
        assert data["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_get_post_not_found(self, async_client: AsyncClient):
        """Test post not found error."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/posts/{fake_id}")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_posts_with_pagination(self, async_client: AsyncClient, test_post: Post, test_post_2: Post):
        """Test posts retrieval with pagination."""
        response = await async_client.get("/api/v1/posts/?page=1&per_page=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert len(data["posts"]) >= 2
    
    @pytest.mark.asyncio
    async def test_get_posts_with_filters(self, async_client: AsyncClient, test_post: Post):
        """Test posts retrieval with filters."""
        response = await async_client.get("/api/v1/posts/?pet_species=Cat&status=active")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["posts"]) >= 1
        assert data["posts"][0]["pet_species"] == "Cat"
    
    @pytest.mark.asyncio
    async def test_get_posts_with_location_filter(self, async_client: AsyncClient, test_post: Post):
        """Test posts retrieval with location filter."""
        response = await async_client.get(
            "/api/v1/posts/?search_latitude=40.7829&search_longitude=-73.9654&radius_km=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data
    
    @pytest.mark.asyncio
    async def test_create_post_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful post creation."""
        post_data = {
            "petName": "Max",
            "petSpecies": "Dog",
            "petBreed": "Labrador",
            "age": 2,
            "gender": "male",
            "weight": 30.0,
            "color": "Brown",
            "description": "Lost brown labrador",
            "locationName": "Downtown",
            "contactPhone": "+1234567890",
            "lat": 40.7829,
            "lng": -73.9654
        }
        
        response = await async_client.post(
            "/api/v1/posts/",
            data=post_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["post"]["pet_name"] == "Max"
        assert data["post"]["pet_species"] == "Dog"
        assert data["uploaded_files"] == []
        assert data["failed_uploads"] == []
    
    @pytest.mark.asyncio
    async def test_create_post_with_files(self, async_client: AsyncClient, auth_headers: dict):
        """Test post creation with file uploads."""
        with patch('src.utils.upload.upload_service.get_upload_service') as mock_get_service, \
             patch('src.utils.llm.gemini.validate_uploaded_files') as mock_validate:
            
            # Mock upload service
            mock_service = MagicMock()
            mock_service.upload_file = AsyncMock(return_value=MagicMock(
                success=True,
                file_url="https://example.com/test-image.jpg",
                error=None
            ))
            mock_get_service.return_value = mock_service
            
            # Mock Gemini validation (no errors)
            mock_validate.return_value = None
            
            post_data = {
                "petName": "Luna",
                "petSpecies": "Cat",
                "description": "Lost black cat"
            }
            
            # Create mock file
            file_content = b"fake image content"
            files = {"files": ("test.jpg", BytesIO(file_content), "image/jpeg")}
            
            response = await async_client.post(
                "/api/v1/posts/",
                data=post_data,
                files=files,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["post"]["pet_name"] == "Luna"
            assert len(data["uploaded_files"]) == 1
            assert data["uploaded_files"][0] == "https://example.com/test-image.jpg"
            mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_post_gemini_validation_error(self, async_client: AsyncClient, auth_headers: dict):
        """Test post creation with Gemini validation error."""
        with patch('src.utils.llm.gemini.validate_uploaded_files') as mock_validate:
            # Mock Gemini validation error
            mock_validate.side_effect = HTTPException(
                status_code=400,
                detail={
                    "error": "Обнаружен неподходящий контент",
                    "message": "Файлы содержат неподходящий контент: test.jpg",
                    "sensitive_files": ["test.jpg"]
                }
            )
            
            post_data = {"petName": "Test", "description": "Test post"}
            files = {"files": ("test.jpg", BytesIO(b"fake content"), "image/jpeg")}
            
            response = await async_client.post(
                "/api/v1/posts/",
                data=post_data,
                files=files,
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "error" in data["detail"]
            assert "sensitive_files" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_create_post_unauthorized(self, async_client: AsyncClient):
        """Test post creation without authentication."""
        post_data = {"petName": "Test", "description": "Test post"}
        
        response = await async_client.post("/api/v1/posts/", data=post_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_post_success(self, async_client: AsyncClient, test_post: Post, auth_headers: dict):
        """Test successful post update."""
        update_data = {
            "pet_name": "Updated Fluffy",
            "description": "Updated description",
            "status": "found"
        }
        
        response = await async_client.patch(
            f"/api/v1/posts/{test_post.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["pet_name"] == "Updated Fluffy"
        assert data["description"] == "Updated description"
        assert data["status"] == "found"
    
    @pytest.mark.asyncio
    async def test_update_post_not_found(self, async_client: AsyncClient, auth_headers: dict):
        """Test post update with non-existent post."""
        fake_id = str(uuid.uuid4())
        update_data = {"pet_name": "Updated"}
        
        response = await async_client.patch(
            f"/api/v1/posts/{fake_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_post_unauthorized(self, async_client: AsyncClient, test_post: Post, auth_headers_2: dict):
        """Test post update by non-owner."""
        update_data = {"pet_name": "Hacked"}
        
        response = await async_client.patch(
            f"/api/v1/posts/{test_post.id}",
            json=update_data,
            headers=auth_headers_2
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_delete_post_success(self, async_client: AsyncClient, test_post: Post, auth_headers: dict):
        """Test successful post deletion."""
        response = await async_client.delete(
            f"/api/v1/posts/{test_post.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify post is deleted
        get_response = await async_client.get(f"/api/v1/posts/{test_post.id}")
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_post_unauthorized(self, async_client: AsyncClient, test_post: Post, auth_headers_2: dict):
        """Test post deletion by non-owner."""
        response = await async_client.delete(
            f"/api/v1/posts/{test_post.id}",
            headers=auth_headers_2
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_my_posts(self, async_client: AsyncClient, test_post: Post, auth_headers: dict):
        """Test getting current user's posts."""
        response = await async_client.get(
            "/api/v1/posts/my/posts",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["id"] == str(test_post.id)
    
    @pytest.mark.asyncio
    async def test_search_posts(self, async_client: AsyncClient, test_post: Post):
        """Test text search in posts."""
        response = await async_client.get("/api/v1/posts/search/text?search_text=Fluffy")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("Fluffy" in str(post.values()) for post in data)
    
    @pytest.mark.asyncio
    async def test_search_posts_min_length(self, async_client: AsyncClient):
        """Test search with insufficient text length."""
        response = await async_client.get("/api/v1/posts/search/text?search_text=a")
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_change_post_status(self, async_client: AsyncClient, test_post: Post, auth_headers: dict):
        """Test changing post status."""
        response = await async_client.patch(
            f"/api/v1/posts/{test_post.id}/status?new_status=found",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "found"
    
    @pytest.mark.asyncio
    async def test_change_post_status_invalid(self, async_client: AsyncClient, test_post: Post, auth_headers: dict):
        """Test changing post status to invalid value."""
        response = await async_client.patch(
            f"/api/v1/posts/{test_post.id}/status?new_status=invalid",
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_toggle_like_post(self, async_client: AsyncClient, test_post: Post, auth_headers: dict):
        """Test toggling like on a post."""
        # First like
        response = await async_client.post(
            f"/api/v1/posts/{test_post.id}/like",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_liked"] is True
        assert data["likes_count"] == 1
        
        # Unlike
        response = await async_client.post(
            f"/api/v1/posts/{test_post.id}/like",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_liked"] is False
        assert data["likes_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_like_status(self, async_client: AsyncClient, test_post: Post, auth_headers: dict):
        """Test getting like status for a post."""
        response = await async_client.get(
            f"/api/v1/posts/{test_post.id}/likes",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "likes_count" in data
        assert "is_liked" in data
        assert data["post_id"] == str(test_post.id)
    
    @pytest.mark.asyncio
    async def test_get_like_status_unauthenticated(self, async_client: AsyncClient, test_post: Post):
        """Test getting like status without authentication."""
        response = await async_client.get(f"/api/v1/posts/{test_post.id}/likes")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_liked"] is False
    
    @pytest.mark.asyncio
    async def test_create_post_validation_error(self, async_client: AsyncClient, auth_headers: dict):
        """Test post creation with validation errors."""
        post_data = {
            "age": -1,  # Invalid age
            "weight": -5.0,  # Invalid weight
        }
        
        response = await async_client.post(
            "/api/v1/posts/",
            data=post_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_post_with_coordinates(self, async_client: AsyncClient, auth_headers: dict):
        """Test post creation with GPS coordinates."""
        post_data = {
            "petName": "GPS Cat",
            "petSpecies": "Cat",
            "lat": 40.7829,
            "lng": -73.9654,
            "locationName": "Central Park"
        }
        
        response = await async_client.post(
            "/api/v1/posts/",
            data=post_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["post"]["location_name"] == "Central Park"
    
    @pytest.mark.asyncio
    async def test_get_posts_sorting(self, async_client: AsyncClient, test_post: Post, test_post_2: Post):
        """Test posts retrieval with sorting."""
        response = await async_client.get("/api/v1/posts/?sort_by=created_at&sort_order=desc")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["posts"]) >= 2
        
        # Check if sorted by creation date (newest first)
        posts = data["posts"]
        if len(posts) >= 2:
            first_post_date = posts[0]["created_at"]
            second_post_date = posts[1]["created_at"]
            assert first_post_date >= second_post_date
    
    @pytest.mark.asyncio
    async def test_get_posts_age_filter(self, async_client: AsyncClient, test_post: Post):
        """Test posts retrieval with age filter."""
        response = await async_client.get("/api/v1/posts/?age_min=2&age_max=5")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if all returned posts have age within range
        for post in data["posts"]:
            if post["age"] is not None:
                assert 2 <= post["age"] <= 5
    
    @pytest.mark.asyncio
    async def test_get_posts_weight_filter(self, async_client: AsyncClient, test_post: Post):
        """Test posts retrieval with weight filter."""
        response = await async_client.get("/api/v1/posts/?weight_min=1.0&weight_max=10.0")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if all returned posts have weight within range
        for post in data["posts"]:
            if post["weight"] is not None:
                assert 1.0 <= post["weight"] <= 10.0 