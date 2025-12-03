# backend/app/core/redis_.py
import redis.asyncio as redis
from app.core.config import settings
from typing import Optional

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            encoding="utf-8"
        )

    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None