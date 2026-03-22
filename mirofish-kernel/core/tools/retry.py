"""
Smart Retry — Exponential Backoff with Jitter

Enhanced from MiroFish's retry utility.
"""

import time
import random
import functools
import logging
from dataclasses import dataclass, field
from typing import Callable, Type, Tuple, Optional, Any

logger = logging.getLogger("mirofish.retry")


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    base_delay: float = 1.0       # Base delay in seconds
    max_delay: float = 60.0       # Maximum delay cap
    exponential_base: float = 2.0
    jitter: bool = True           # Add random jitter
    retry_on: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay


def smart_retry(
    config: Optional[RetryConfig] = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for smart retry with exponential backoff.
    
    Usage:
        @smart_retry(max_retries=3)
        def call_api():
            ...
        
        @smart_retry(config=RetryConfig(max_retries=5, base_delay=2.0))
        def call_api():
            ...
    """
    if config is None:
        config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            retry_on=retry_on,
        )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.retry_on as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{config.max_retries} for "
                            f"{func.__name__}: {e}. Waiting {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_retries} retries exhausted for "
                            f"{func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_call(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    config: Optional[RetryConfig] = None,
) -> Any:
    """
    Functional retry (non-decorator).
    
    Usage:
        result = retry_call(api.fetch, args=(url,), config=RetryConfig(max_retries=5))
    """
    if kwargs is None:
        kwargs = {}
    if config is None:
        config = RetryConfig()
    
    @smart_retry(config=config)
    def _call():
        return func(*args, **kwargs)
    
    return _call()
