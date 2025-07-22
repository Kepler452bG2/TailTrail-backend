import uuid
from typing import Annotated, Generator, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import sessionmanager, get_db_session
from src.models import User
from src.repositories.user_repository import UserRepository
from src.utils.token.auth.token_util import verify_token

DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

security = HTTPBearer()

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with sessionmanager.session() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Получить текущего пользователя из JWT токена"""
    token = credentials.credentials
    
    try:
        payload = verify_token(token)  # This already raises specific HTTPExceptions
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Convert user_id to UUID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format"
            )
        
        user_repository = UserRepository(session)
        user = await user_repository.find_by_id(user_uuid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    except HTTPException:
        # Re-raise HTTPExceptions (including JWT errors) without modification
        raise
    except Exception as e:
        # Log the actual error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


async def get_current_user_websocket(websocket: WebSocket, user_id: UUID) -> User:
    """Получить текущего пользователя для WebSocket подключения"""
    try:
        # Получаем токен из query параметров или headers
        token = websocket.query_params.get("token")
        if not token:
            # Пробуем получить из headers
            token = websocket.headers.get("Authorization")
            if token and token.startswith("Bearer "):
                token = token[7:]
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not provided"
            )
        
        payload = verify_token(token)  # This already raises specific HTTPExceptions
        token_user_id = payload.get("user_id")
        if token_user_id is None or UUID(token_user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token user mismatch"
            )
        
        async with sessionmanager.session() as session:
            user_repository = UserRepository(session)
            user = await user_repository.find_by_id(user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebSocket authentication failed"
        )


CurrentUserDep = Annotated[User, Depends(get_current_user)]