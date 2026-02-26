import logging
import asyncio
from typing import Callable, Any, Type, Union, Tuple
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

def api_retry(
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]],
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0
):
    """
    Standardize retry decorator for API calls using exponential backoff.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )

async def async_api_retry(
    coro_func: Callable[..., Any],
    *args,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    max_attempts: int = 3,
    **kwargs
) -> Any:
    """
    Helper for retrying async calls without decorators if needed.
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            return await coro_func(*args, **kwargs)
        except exceptions as e:
            attempt += 1
            if attempt >= max_attempts:
                logger.error(f"Max attempts reached for {coro_func.__name__}: {e}")
                raise
            wait_time = min(10, (2 ** attempt))
            logger.warning(f"Retry {attempt}/{max_attempts} for {coro_func.__name__} after {wait_time}s due to {e}")
            await asyncio.sleep(wait_time)
