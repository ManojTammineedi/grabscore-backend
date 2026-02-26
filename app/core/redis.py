"""
Redis client for caching scored results and fraud velocity flags.
Gracefully degrades if Redis is unavailable.
"""

import json
import logging
from typing import Any, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_redis_client = None


def get_redis_client():
    """
    Lazy-initialize Redis client singleton.
    Returns None if Redis is disabled or unavailable.
    """
    global _redis_client

    if not settings.REDIS_ENABLED:
        return None

    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            _redis_client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis unavailable, caching disabled: {e}")
            _redis_client = None

    return _redis_client


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Cache a value with TTL (default 5 minutes). Returns True if cached."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.warning(f"Redis cache_set failed: {e}")
        return False


def cache_get(key: str) -> Optional[Any]:
    """Retrieve a cached value. Returns None if not found or Redis unavailable."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        data = client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning(f"Redis cache_get failed: {e}")
        return None
