import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.config import settings
from src.database import sessionmanager
from src.routes import router as api_v1_router

# Import models to ensure they are registered with SQLAlchemy
from src.models import User, Post, Like, Chat, Message, Block

logging.basicConfig(
    stream=sys.stdout, level=logging.DEBUG if settings.DEBUG_LOGS else logging.INFO
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if sessionmanager._engine is not None:
        await sessionmanager.close()


app = FastAPI(
    lifespan=lifespan, 
    title="TailTrail API",
    # Настройки для WebSocket
    websocket_ping_interval=20.0,  # Ping каждые 20 секунд
    websocket_ping_timeout=10.0,   # Таймаут ping 10 секунд
    websocket_close_timeout=10.0   # Таймаут закрытия 10 секунд
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)

@app.get('/', tags=['root'])
def root():
    return {"ping": "pong"}

app.include_router(api_v1_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
