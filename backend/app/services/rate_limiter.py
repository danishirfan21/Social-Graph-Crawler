"""
Rate limiting service using Redis.
"""

import time
import logging
from typing import Optional
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter using Redis.
    Allows burst traffic while enforcing average rate.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        self.redis_url = redis_url or settings.REDIS_URL
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis: Optional[Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Rate limiter connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect rate limiter to Redis: {e}")
            self.redis = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    async def is_allowed(
        self,
        identifier: str,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None
    ) -> bool:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            identifier: Unique identifier (IP, user ID, API key, etc.)
            max_requests: Override max requests
            window_seconds: Override time window
        
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        if not self.redis:
            # If Redis is unavailable, allow request (fail open)
            logger.warning("Redis unavailable, allowing request")
            return True
        
        max_req = max_requests or self.max_requests
        window = window_seconds or self.window_seconds
        
        key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        window_start = current_time - window
        
        try:
            # Use Redis sorted set to track requests in time window
            pipe = self.redis.pipeline()
            
            # Remove old requests outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window + 1)
            
            results = await pipe.execute()
            
            # results[1] is the count before adding current request
            request_count = results[1]
            
            return request_count < max_req
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True  # Fail open
    
    async def get_remaining(
        self,
        identifier: str,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None
    ) -> int:
        """
        Get remaining requests in current window.
        
        Args:
            identifier: Unique identifier
            max_requests: Override max requests
            window_seconds: Override time window
        
        Returns:
            Number of remaining requests
        """
        if not self.redis:
            return 0
        
        max_req = max_requests or self.max_requests
        window = window_seconds or self.window_seconds
        
        key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        window_start = current_time - window
        
        try:
            # Count requests in current window
            await self.redis.zremrangebyscore(key, 0, window_start)
            count = await self.redis.zcard(key)
            
            return max(0, max_req - count)
            
        except Exception as e:
            logger.error(f"Get remaining error: {e}")
            return 0
    
    async def reset(self, identifier: str):
        """Reset rate limit for an identifier."""
        if not self.redis:
            return
        
        key = f"rate_limit:{identifier}"
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Reset rate limit error: {e}")


# Global rate limiter instance
rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW
)


async def get_rate_limiter() -> RateLimiter:
    """Dependency for FastAPI routes."""
    return rate_limiter
