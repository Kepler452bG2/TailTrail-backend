import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.utils.token.auth.token_util import verify_token

DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

security = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: DBSessionDep
) -> User:
    
    # Проверяем токен
    payload = verify_token(credentials.credentials)
    user_id = payload.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user_repository = UserRepository(db)
    user = await user_repository.find_by_id(uuid.UUID(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
