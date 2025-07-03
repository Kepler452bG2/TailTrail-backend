from fastapi import APIRouter
from starlette import status

from src.controllers.auth_controller import router as auth_router

router = APIRouter()


@router.get("/health", tags=["health"])
async def health():
    return status.HTTP_200_OK


router.include_router(auth_router, prefix="/auth", tags=["auth"])
