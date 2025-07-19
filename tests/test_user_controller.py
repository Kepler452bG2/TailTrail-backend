import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient
from io import BytesIO

from src.models.user import User


class TestUserController:
    """Test cases for user controller endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test successful current user retrieval."""
        response = await async_client.get("/api/v1/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert data["first_name"] == test_user.first_name
        assert data["last_name"] == test_user.last_name
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, async_client: AsyncClient):
        """Test current user retrieval without authentication."""
        response = await async_client.get("/api/v1/users/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_current_user_success(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test successful current user update."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "+1234567899"
        }
        
        response = await async_client.patch(
            "/api/v1/users/me",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["phone"] == "+1234567899"
    
    @pytest.mark.asyncio
    async def test_update_current_user_partial(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test partial current user update."""
        update_data = {
            "first_name": "OnlyFirst"
        }
        
        response = await async_client.patch(
            "/api/v1/users/me",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "OnlyFirst"
        assert data["last_name"] == test_user.last_name  # Should remain unchanged
    
    @pytest.mark.asyncio
    async def test_update_current_user_duplicate_phone(self, async_client: AsyncClient, test_user: User, test_user_2: User, auth_headers: dict):
        """Test current user update with duplicate phone."""
        update_data = {
            "phone": test_user_2.phone
        }
        
        response = await async_client.patch(
            "/api/v1/users/me",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "phone" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_update_current_user_invalid_phone(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test current user update with invalid phone format."""
        update_data = {
            "phone": "invalid-phone"
        }
        
        response = await async_client.patch(
            "/api/v1/users/me",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_current_user_unauthorized(self, async_client: AsyncClient):
        """Test current user update without authentication."""
        update_data = {
            "first_name": "Hacker"
        }
        
        response = await async_client.patch("/api/v1/users/me", json=update_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_delete_current_user_success(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test successful current user deletion."""
        response = await async_client.delete("/api/v1/users/me", headers=auth_headers)
        
        assert response.status_code == 204
        
        # Verify user is deleted by trying to get profile
        get_response = await async_client.get("/api/v1/users/me", headers=auth_headers)
        assert get_response.status_code == 401  # Token should be invalid now
    
    @pytest.mark.asyncio
    async def test_delete_current_user_unauthorized(self, async_client: AsyncClient):
        """Test current user deletion without authentication."""
        response = await async_client.delete("/api/v1/users/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_upload_profile_image_success(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test successful profile image upload."""
        with patch('src.utils.upload.upload_service.get_upload_service') as mock_get_service, \
             patch('src.utils.llm.gemini.validate_uploaded_files') as mock_validate:
            
            # Mock upload service
            mock_service = MagicMock()
            mock_service.upload_file = AsyncMock(return_value=MagicMock(
                success=True,
                file_url="https://example.com/profile-image.jpg",
                error=None
            ))
            mock_get_service.return_value = mock_service
            
            # Mock Gemini validation (no errors)
            mock_validate.return_value = None
            
            # Create mock file
            file_content = b"fake image content"
            files = {"file": ("profile.jpg", BytesIO(file_content), "image/jpeg")}
            
            response = await async_client.post(
                "/api/v1/users/me/upload-image",
                files=files,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["image_url"] == "https://example.com/profile-image.jpg"
            assert data["message"] == "Profile image uploaded successfully"
    
    @pytest.mark.asyncio
    async def test_upload_profile_image_validation_error(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test profile image upload with validation error."""
        with patch('src.utils.llm.gemini.validate_uploaded_files') as mock_validate:
            # Mock Gemini validation error
            from fastapi import HTTPException
            mock_validate.side_effect = HTTPException(
                status_code=400,
                detail={
                    "error": "Обнаружен неподходящий контент",
                    "message": "Файл содержит неподходящий контент",
                    "sensitive_files": ["profile.jpg"]
                }
            )
            
            file_content = b"inappropriate content"
            files = {"file": ("profile.jpg", BytesIO(file_content), "image/jpeg")}
            
            response = await async_client.post(
                "/api/v1/users/me/upload-image",
                files=files,
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "error" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_profile_image_upload_failure(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test profile image upload with upload service failure."""
        with patch('src.utils.upload.upload_service.get_upload_service') as mock_get_service, \
             patch('src.utils.llm.gemini.validate_uploaded_files') as mock_validate:
            
            # Mock upload service failure
            mock_service = MagicMock()
            mock_service.upload_file = AsyncMock(return_value=MagicMock(
                success=False,
                file_url=None,
                error="Upload failed"
            ))
            mock_get_service.return_value = mock_service
            
            # Mock Gemini validation (no errors)
            mock_validate.return_value = None
            
            file_content = b"fake image content"
            files = {"file": ("profile.jpg", BytesIO(file_content), "image/jpeg")}
            
            response = await async_client.post(
                "/api/v1/users/me/upload-image",
                files=files,
                headers=auth_headers
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "upload failed" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_profile_image_no_file(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test profile image upload without file."""
        response = await async_client.post(
            "/api/v1/users/me/upload-image",
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_upload_profile_image_invalid_format(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test profile image upload with invalid file format."""
        file_content = b"fake text content"
        files = {"file": ("document.txt", BytesIO(file_content), "text/plain")}
        
        response = await async_client.post(
            "/api/v1/users/me/upload-image",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_upload_profile_image_unauthorized(self, async_client: AsyncClient):
        """Test profile image upload without authentication."""
        file_content = b"fake image content"
        files = {"file": ("profile.jpg", BytesIO(file_content), "image/jpeg")}
        
        response = await async_client.post(
            "/api/v1/users/me/upload-image",
            files=files
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, async_client: AsyncClient, test_user: User):
        """Test successful user retrieval by ID."""
        response = await async_client.get(f"/api/v1/users/{test_user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert data["first_name"] == test_user.first_name
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, async_client: AsyncClient):
        """Test user retrieval with non-existent ID."""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = await async_client.get(f"/api/v1/users/{fake_id}")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_invalid_uuid(self, async_client: AsyncClient):
        """Test user retrieval with invalid UUID format."""
        response = await async_client.get("/api/v1/users/invalid-uuid")
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_users_list_success(self, async_client: AsyncClient, test_user: User, test_user_2: User):
        """Test successful users list retrieval."""
        response = await async_client.get("/api/v1/users/")
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert len(data["users"]) >= 2
    
    @pytest.mark.asyncio
    async def test_get_users_list_with_pagination(self, async_client: AsyncClient, test_user: User, test_user_2: User):
        """Test users list retrieval with pagination."""
        response = await async_client.get("/api/v1/users/?page=1&per_page=1")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 1
        assert data["page"] == 1
        assert data["per_page"] == 1
        assert data["total"] >= 2
    
    @pytest.mark.asyncio
    async def test_get_users_list_with_search(self, async_client: AsyncClient, test_user: User):
        """Test users list retrieval with search."""
        response = await async_client.get(f"/api/v1/users/?search={test_user.first_name}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) >= 1
        found_user = next((u for u in data["users"] if u["id"] == str(test_user.id)), None)
        assert found_user is not None
    
    @pytest.mark.asyncio
    async def test_get_users_list_empty_search(self, async_client: AsyncClient):
        """Test users list retrieval with search that returns no results."""
        response = await async_client.get("/api/v1/users/?search=nonexistentuser")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 0
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_verify_phone_success(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test successful phone verification."""
        with patch('src.services.user.user_service.UserService.verify_phone_code') as mock_verify:
            mock_verify.return_value = True
            
            verify_data = {
                "phone": test_user.phone,
                "code": "123456"
            }
            
            response = await async_client.post(
                "/api/v1/users/verify-phone",
                json=verify_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "phone verified" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_verify_phone_invalid_code(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test phone verification with invalid code."""
        with patch('src.services.user.user_service.UserService.verify_phone_code') as mock_verify:
            mock_verify.return_value = False
            
            verify_data = {
                "phone": test_user.phone,
                "code": "000000"
            }
            
            response = await async_client.post(
                "/api/v1/users/verify-phone",
                json=verify_data,
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "invalid" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_verify_phone_unauthorized(self, async_client: AsyncClient):
        """Test phone verification without authentication."""
        verify_data = {
            "phone": "+1234567890",
            "code": "123456"
        }
        
        response = await async_client.post("/api/v1/users/verify-phone", json=verify_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_send_phone_verification_success(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test successful phone verification code sending."""
        with patch('src.services.user.user_service.UserService.send_phone_verification_code') as mock_send:
            mock_send.return_value = True
            
            send_data = {
                "phone": test_user.phone
            }
            
            response = await async_client.post(
                "/api/v1/users/send-phone-verification",
                json=send_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "verification code sent" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_send_phone_verification_failure(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test phone verification code sending failure."""
        with patch('src.services.user.user_service.UserService.send_phone_verification_code') as mock_send:
            mock_send.return_value = False
            
            send_data = {
                "phone": test_user.phone
            }
            
            response = await async_client.post(
                "/api/v1/users/send-phone-verification",
                json=send_data,
                headers=auth_headers
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "failed to send" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_send_phone_verification_unauthorized(self, async_client: AsyncClient):
        """Test phone verification code sending without authentication."""
        send_data = {
            "phone": "+1234567890"
        }
        
        response = await async_client.post("/api/v1/users/send-phone-verification", json=send_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_user_preferences_success(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test successful user preferences update."""
        preferences_data = {
            "language": "en",
            "timezone": "UTC",
            "email_notifications": True,
            "push_notifications": False
        }
        
        response = await async_client.patch(
            "/api/v1/users/me/preferences",
            json=preferences_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "en"
        assert data["timezone"] == "UTC"
        assert data["email_notifications"] is True
        assert data["push_notifications"] is False
    
    @pytest.mark.asyncio
    async def test_update_user_preferences_unauthorized(self, async_client: AsyncClient):
        """Test user preferences update without authentication."""
        preferences_data = {
            "language": "en"
        }
        
        response = await async_client.patch("/api/v1/users/me/preferences", json=preferences_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test successful user statistics retrieval."""
        response = await async_client.get("/api/v1/users/me/stats", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "posts_count" in data
        assert "likes_received" in data
        assert "likes_given" in data
        assert "join_date" in data
    
    @pytest.mark.asyncio
    async def test_get_user_stats_unauthorized(self, async_client: AsyncClient):
        """Test user statistics retrieval without authentication."""
        response = await async_client.get("/api/v1/users/me/stats")
        
        assert response.status_code == 401 