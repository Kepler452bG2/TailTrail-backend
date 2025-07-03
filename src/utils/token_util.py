from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException

from src.config import settings


def generate_token(payload: dict) -> str:
    payload["exp"] = datetime.now(UTC) + timedelta(seconds=settings.JWT_EXPIRATION)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired!")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token!")