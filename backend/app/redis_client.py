"""
Redis client configuration and connection management
"""

import redis
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with connection management"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance with lazy initialization"""
        if self._client is None:
            self._client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            logger.info(f"Redis client initialized with URL: {settings.redis_url}")
        return self._client
    
    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed for key {key}: {e}")
            return None
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiration"""
        try:
            return self.client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS failed for key {key}: {e}")
            return False
    
    def close(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Redis connection closed")


# Global Redis client instance
redis_client = RedisClient()