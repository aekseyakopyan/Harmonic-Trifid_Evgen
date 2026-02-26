import pytest
import asyncio
from core.utils.retry_handler import api_retry, async_api_retry

# Test synchronous retry decorator
@api_retry(ValueError, max_attempts=3, min_wait=0.1, max_wait=0.2)
def failing_func():
    failing_func.attempts += 1
    raise ValueError("Test error")

failing_func.attempts = 0

def test_sync_retry():
    with pytest.raises(ValueError):
        failing_func()
    assert failing_func.attempts == 3

# Test asynchronous helper
async def async_failing_func():
    async_failing_func.attempts += 1
    raise RuntimeError("Async test error")

async_failing_func.attempts = 0

@pytest.mark.asyncio
async def test_async_retry():
    with pytest.raises(RuntimeError):
        await async_api_retry(async_failing_func, exceptions=RuntimeError, max_attempts=2)
    assert async_failing_func.attempts == 2
