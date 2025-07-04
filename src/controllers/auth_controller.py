from fastapi import APIRouter
from starlette import status
from starlette.responses import JSONResponse

from src.dependencies import DBSessionDep
from src.schemas.user import UserLogInDTO, UserSignUpDTO
from src.services.user.user_service import UserService

router = APIRouter()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: UserSignUpDTO, db: DBSessionDep) -> dict:
    user_service = UserService(db=db)
    await user_service.create_user(user_data=request)
    return {"detail": "User created successfully!"}


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(request: UserLogInDTO, db: DBSessionDep) -> JSONResponse:
    user_service = UserService(db=db)
    token = await user_service.authenticate_user(user_data=request)
    return JSONResponse({"token": token}, status_code=status.HTTP_200_OK)