from fastapi import APIRouter
from starlette import status

from src.controllers.auth_controller import router as auth_router
from src.controllers.post_controller import router as post_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(post_router, prefix="/posts", tags=["posts"])
