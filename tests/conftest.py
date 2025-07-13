import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.app import app
from src.database import Base, get_db_session
from src.models.user import User
from src.models.post import Post
from src.models.like import Like
from src.dependencies import get_current_user
from src.utils.token.auth.token_util import generate_token


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override the get_db dependency."""
    def _override_get_db():
        return db_session
    return _override_get_db


@pytest.fixture
def client(override_get_db):
    """Create a test client."""
    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_get_db):
    """Create an async test client."""
    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_here",
        first_name="Test",
        last_name="User",
        phone="+1234567890",
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_2(db_session: AsyncSession) -> User:
    """Create a second test user."""
    user = User(
        email="test2@example.com",
        hashed_password="hashed_password_here",
        first_name="Test2",
        last_name="User2",
        phone="+1234567891",
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authorization headers for test user."""
    access_token = generate_token(data={"user_id": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def auth_headers_2(test_user_2: User) -> dict:
    """Create authorization headers for second test user."""
    access_token = generate_token(data={"user_id": str(test_user_2.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def test_post(db_session: AsyncSession, test_user: User) -> Post:
    """Create a test post."""
    post = Post(
        pet_name="Fluffy",
        pet_species="Cat",
        pet_breed="Persian",
        age=3,
        gender="female",
        weight=4.5,
        color="White",
        description="Lost white cat, very friendly",
        location_name="Central Park",
        contact_phone="+1234567890",
        user_id=test_user.id,
        images=["https://example.com/image1.jpg"],
        status="active"
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.fixture
async def test_post_2(db_session: AsyncSession, test_user_2: User) -> Post:
    """Create a second test post."""
    post = Post(
        pet_name="Buddy",
        pet_species="Dog",
        pet_breed="Golden Retriever",
        age=2,
        gender="male",
        weight=25.0,
        color="Golden",
        description="Lost golden retriever, loves to play",
        location_name="City Park",
        contact_phone="+1234567891",
        user_id=test_user_2.id,
        images=["https://example.com/image2.jpg"],
        status="active"
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.fixture
def mock_upload_service():
    """Mock upload service."""
    mock_service = MagicMock()
    mock_service.upload_file = AsyncMock(return_value=MagicMock(
        success=True,
        file_url="https://example.com/test-image.jpg",
        error=None
    ))
    return mock_service


@pytest.fixture
def mock_gemini_validator():
    """Mock Gemini validator."""
    mock_validator = AsyncMock()
    mock_validator.return_value = None  # No validation errors
    return mock_validator


@pytest.fixture
def override_current_user(test_user: User):
    """Override current user dependency."""
    def _override_current_user():
        return test_user
    return _override_current_user


@pytest.fixture
def authenticated_client(client, override_current_user):
    """Create authenticated client."""
    app.dependency_overrides[get_current_user] = override_current_user
    yield client
    app.dependency_overrides.clear() 