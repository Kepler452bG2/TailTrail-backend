import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from starlette.responses import JSONResponse

from src.dependencies import get_session
from src.schemas.user import UserLogInDTO, UserSignUpDTO
from src.services.user.user_service import UserService
from src.utils.exceptions import raise_validation_exception
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: UserSignUpDTO, session: AsyncSession = Depends(get_session)) -> dict:
    """Register a new user"""
    try:
        user_service = UserService(session=session)
        await user_service.create_user(user_data=request)
        return {"detail": "User created successfully!"}
    except ValidationError as e:
        logger.error(f"Validation error during signup: {e}")
        raise_validation_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during signup: {e}"
        )


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(request: UserLogInDTO, session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Authenticate user and return JWT token"""
    try:
        user_service = UserService(session=session)
        token = await user_service.authenticate_user(user_data=request)
        return JSONResponse({"token": token}, status_code=status.HTTP_200_OK)
    except ValidationError as e:
        logger.error(f"Validation error during login: {e}")
        raise_validation_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {e}"
        )