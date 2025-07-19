import pytest
import asyncio
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.refresh = MagicMock()
    mock_session.close = MagicMock()
    return mock_session


@pytest.fixture
def test_client():
    """Create a test client without database dependencies."""
    from src.app import app
    
    # Mock all database dependencies
    app.dependency_overrides = {}
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear() 