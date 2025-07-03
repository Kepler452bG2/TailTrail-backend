from fastapi import APIRouter
from starlette import status
from starlette.responses import JSONResponse

from src.dependencies import DBSessionDep
from src.schemas.user import UserLogInDTO, UserSignUpDTO
from src.services.user.user_service import UserService

router = APIRouter()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: UserSignUpDTO):
    token = await UserService.create_user(user_data=request)
    return JSONResponse({"token": token}, status_code=status.HTTP_201_CREATED)


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(request: UserLogInDTO):
    token = await UserService.authenticate_user(user_data=request)
    return JSONResponse({"token": token}, status_code=status.HTTP_200_OK)
