import pytest


def test_simple_addition():
    """Simple test to check if pytest is working."""
    assert 1 + 1 == 2


def test_simple_string():
    """Simple test to check string operations."""
    assert "hello" + " world" == "hello world"


@pytest.mark.asyncio
async def test_simple_async():
    """Simple async test to check if pytest-asyncio is working."""
    async def async_function():
        return "async result"
    
    result = await async_function()
    assert result == "async result" 