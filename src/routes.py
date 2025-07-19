from fastapi import APIRouter
from starlette import status

from src.controllers.auth_controller import router as auth_router
from src.controllers.post_controller import router as post_router
from src.controllers.user_controller import router as user_router
from src.controllers.chat_controller import router as chat_router
from src.controllers.message_controller import router as message_router
from src.controllers.websocket_controller import router as websocket_router


router = APIRouter(
    responses={
            401: {"description": "Unauthorized"},
            500: {"description": "Internal server error"},
    }
)   

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(post_router, prefix="/posts", tags=["posts"])
router.include_router(user_router, prefix="/users", tags=["users"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(message_router, prefix="/messages", tags=["messages"])
router.include_router(websocket_router, prefix="/websocket", tags=["websocket"])
