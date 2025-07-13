import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from fastapi import status

from src.models.user import User


class TestAuthController:
    """Test cases for authentication controller endpoints."""
    
    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "first_name": "New",
            "last_name": "User",
            "phone": "+1234567892"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert "password" not in data
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user: User):
        """Test registration with duplicate email."""
        user_data = {
            "email": test_user.email,
            "password": "securepassword123",
            "first_name": "Duplicate",
            "last_name": "User",
            "phone": "+1234567893"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "email" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_duplicate_phone(self, async_client: AsyncClient, test_user: User):
        """Test registration with duplicate phone."""
        user_data = {
            "email": "different@example.com",
            "password": "securepassword123",
            "first_name": "Different",
            "last_name": "User",
            "phone": test_user.phone
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "phone" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email format."""
        user_data = {
            "email": "invalid-email",
            "password": "securepassword123",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567894"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password."""
        user_data = {
            "email": "test@example.com",
            "password": "123",  # Too short
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567895"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_missing_fields(self, async_client: AsyncClient):
        """Test registration with missing required fields."""
        user_data = {
            "email": "test@example.com"
            # Missing password, first_name, last_name, phone
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login."""
        with patch('src.services.user.user_service.UserService.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            login_data = {
                "email": test_user.email,
                "password": "correct_password"
            }
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["email"] == test_user.email
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient, test_user: User):
        """Test login with wrong password."""
        with patch('src.services.user.user_service.UserService.verify_password') as mock_verify:
            mock_verify.return_value = False
            
            login_data = {
                "email": test_user.email,
                "password": "wrong_password"
            }
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 401
            data = response.json()
            assert "credentials" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_user_not_found(self, async_client: AsyncClient):
        """Test login with non-existent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "any_password"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "credentials" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_unverified_user(self, async_client: AsyncClient, db_session):
        """Test login with unverified user."""
        # Create unverified user
        unverified_user = User(
            email="unverified@example.com",
            hashed_password="hashed_password",
            first_name="Unverified",
            last_name="User",
            phone="+1234567896",
            is_verified=False
        )
        db_session.add(unverified_user)
        await db_session.commit()
        
        with patch('src.services.user.user_service.UserService.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            login_data = {
                "email": "unverified@example.com",
                "password": "correct_password"
            }
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 403
            data = response.json()
            assert "verified" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client: AsyncClient, test_user: User):
        """Test successful token refresh."""
        with patch('src.utils.token.auth.token_util.verify_refresh_token') as mock_verify:
            mock_verify.return_value = str(test_user.id)
            
            refresh_data = {
                "refresh_token": "valid_refresh_token"
            }
            
            response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test token refresh with invalid token."""
        with patch('src.utils.token.auth.token_util.verify_refresh_token') as mock_verify:
            mock_verify.return_value = None
            
            refresh_data = {
                "refresh_token": "invalid_refresh_token"
            }
            
            response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
            
            assert response.status_code == 401
            data = response.json()
            assert "token" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(self, async_client: AsyncClient):
        """Test token refresh with valid token but non-existent user."""
        with patch('src.utils.token.auth.token_util.verify_refresh_token') as mock_verify:
            mock_verify.return_value = str("00000000-0000-0000-0000-000000000000")
            
            refresh_data = {
                "refresh_token": "valid_token_but_no_user"
            }
            
            response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
            
            assert response.status_code == 401
            data = response.json()
            assert "token" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_verify_email_success(self, async_client: AsyncClient, db_session):
        """Test successful email verification."""
        # Create unverified user
        unverified_user = User(
            email="toverify@example.com",
            hashed_password="hashed_password",
            first_name="To",
            last_name="Verify",
            phone="+1234567897",
            is_verified=False
        )
        db_session.add(unverified_user)
        await db_session.commit()
        await db_session.refresh(unverified_user)
        
        with patch('src.utils.token.auth.token_util.verify_email_token') as mock_verify:
            mock_verify.return_value = str(unverified_user.id)
            
            verify_data = {
                "token": "valid_verification_token"
            }
            
            response = await async_client.post("/api/v1/auth/verify-email", json=verify_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Email verified successfully"
            
            # Check user is now verified
            await db_session.refresh(unverified_user)
            assert unverified_user.is_verified is True
    
    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, async_client: AsyncClient):
        """Test email verification with invalid token."""
        with patch('src.utils.token.auth.token_util.verify_email_token') as mock_verify:
            mock_verify.return_value = None
            
            verify_data = {
                "token": "invalid_verification_token"
            }
            
            response = await async_client.post("/api/v1/auth/verify-email", json=verify_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "token" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_verify_email_user_not_found(self, async_client: AsyncClient):
        """Test email verification with valid token but non-existent user."""
        with patch('src.utils.token.auth.token_util.verify_email_token') as mock_verify:
            mock_verify.return_value = str("00000000-0000-0000-0000-000000000000")
            
            verify_data = {
                "token": "valid_token_but_no_user"
            }
            
            response = await async_client.post("/api/v1/auth/verify-email", json=verify_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "token" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_verify_email_already_verified(self, async_client: AsyncClient, test_user: User):
        """Test email verification for already verified user."""
        with patch('src.utils.token.auth.token_util.verify_email_token') as mock_verify:
            mock_verify.return_value = str(test_user.id)
            
            verify_data = {
                "token": "valid_verification_token"
            }
            
            response = await async_client.post("/api/v1/auth/verify-email", json=verify_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "already verified" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_forgot_password_success(self, async_client: AsyncClient, test_user: User):
        """Test successful forgot password request."""
        with patch('src.services.user.user_service.UserService.send_password_reset_email') as mock_send:
            mock_send.return_value = True
            
            forgot_data = {
                "email": test_user.email
            }
            
            response = await async_client.post("/api/v1/auth/forgot-password", json=forgot_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "reset instructions" in data["message"].lower()
            mock_send.assert_called_once_with(test_user.email)
    
    @pytest.mark.asyncio
    async def test_forgot_password_user_not_found(self, async_client: AsyncClient):
        """Test forgot password with non-existent user."""
        forgot_data = {
            "email": "nonexistent@example.com"
        }
        
        response = await async_client.post("/api/v1/auth/forgot-password", json=forgot_data)
        
        # Should return 200 for security reasons (don't reveal user existence)
        assert response.status_code == 200
        data = response.json()
        assert "reset instructions" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_reset_password_success(self, async_client: AsyncClient, test_user: User):
        """Test successful password reset."""
        with patch('src.utils.token.auth.token_util.verify_reset_token') as mock_verify:
            mock_verify.return_value = str(test_user.id)
            
            reset_data = {
                "token": "valid_reset_token",
                "new_password": "newSecurePassword123"
            }
            
            response = await async_client.post("/api/v1/auth/reset-password", json=reset_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "password has been reset" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, async_client: AsyncClient):
        """Test password reset with invalid token."""
        with patch('src.utils.token.auth.token_util.verify_reset_token') as mock_verify:
            mock_verify.return_value = None
            
            reset_data = {
                "token": "invalid_reset_token",
                "new_password": "newSecurePassword123"
            }
            
            response = await async_client.post("/api/v1/auth/reset-password", json=reset_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "token" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_reset_password_weak_password(self, async_client: AsyncClient, test_user: User):
        """Test password reset with weak password."""
        with patch('src.utils.token.auth.token_util.verify_reset_token') as mock_verify:
            mock_verify.return_value = str(test_user.id)
            
            reset_data = {
                "token": "valid_reset_token",
                "new_password": "123"  # Too weak
            }
            
            response = await async_client.post("/api/v1/auth/reset-password", json=reset_data)
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test successful password change."""
        with patch('src.services.user.user_service.UserService.verify_password') as mock_verify, \
             patch('src.services.user.user_service.UserService.update_password') as mock_update:
            
            mock_verify.return_value = True
            mock_update.return_value = True
            
            change_data = {
                "current_password": "current_password",
                "new_password": "newSecurePassword123"
            }
            
            response = await async_client.post(
                "/api/v1/auth/change-password",
                json=change_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "password has been changed" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, async_client: AsyncClient, test_user: User, auth_headers: dict):
        """Test password change with wrong current password."""
        with patch('src.services.user.user_service.UserService.verify_password') as mock_verify:
            mock_verify.return_value = False
            
            change_data = {
                "current_password": "wrong_password",
                "new_password": "newSecurePassword123"
            }
            
            response = await async_client.post(
                "/api/v1/auth/change-password",
                json=change_data,
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "current password" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_change_password_unauthorized(self, async_client: AsyncClient):
        """Test password change without authentication."""
        change_data = {
            "current_password": "current_password",
            "new_password": "newSecurePassword123"
        }
        
        response = await async_client.post("/api/v1/auth/change-password", json=change_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful logout."""
        response = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "logged out" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_logout_unauthorized(self, async_client: AsyncClient):
        """Test logout without authentication."""
        response = await async_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401 