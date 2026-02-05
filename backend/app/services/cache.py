"""
Cache service using Redis for storing conversion results and task data
"""

import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching conversion results and frequently accessed data"""
    
    def __init__(self):
        self.redis = redis_client
        self.default_ttl = 86400  # 24 hours in seconds
    
    def hash_compose(self, content: str) -> str:
        """
        Generate SHA-256 hash of Docker Compose content
        
        Args:
            content: Docker Compose YAML content
            
        Returns:
            SHA-256 hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_cached_conversion(self, compose_hash: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached conversion result if available
        
        Args:
            compose_hash: SHA-256 hash of Docker Compose content
            
        Returns:
            List of Kubernetes manifests if cached, None otherwise
        """
        try:
            cache_key = f"conversion:{compose_hash}"
            cached_data = self.redis.get(cache_key)
            
            if cached_data:
                logger.info(f"Cache hit for conversion: {compose_hash}")
                return json.loads(cached_data)
            else:
                logger.info(f"Cache miss for conversion: {compose_hash}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve cached conversion: {e}")
            return None
    
    def cache_conversion(
        self, 
        compose_hash: str, 
        manifests: List[Dict[str, Any]], 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store conversion result in cache
        
        Args:
            compose_hash: SHA-256 hash of Docker Compose content
            manifests: List of generated Kubernetes manifests
            ttl: Time to live in seconds (default: 24 hours)
            
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            cache_key = f"conversion:{compose_hash}"
            cache_data = {
                "manifests": manifests,
                "cached_at": datetime.utcnow().isoformat(),
                "hash": compose_hash
            }
            
            ttl = ttl or self.default_ttl
            success = self.redis.set(
                cache_key, 
                json.dumps(cache_data, default=str), 
                ex=ttl
            )
            
            if success:
                logger.info(f"Cached conversion result: {compose_hash} (TTL: {ttl}s)")
            else:
                logger.error(f"Failed to cache conversion result: {compose_hash}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache conversion: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status from cache
        
        Args:
            task_id: Celery task ID
            
        Returns:
            Task status dictionary if found, None otherwise
        """
        try:
            cache_key = f"task:{task_id}"
            cached_data = self.redis.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve task status: {e}")
            return None
    
    def set_task_status(
        self, 
        task_id: str, 
        status: Dict[str, Any], 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store task status in cache
        
        Args:
            task_id: Celery task ID
            status: Task status dictionary
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            cache_key = f"task:{task_id}"
            ttl = ttl or 3600  # 1 hour default for task status
            
            success = self.redis.set(
                cache_key,
                json.dumps(status, default=str),
                ex=ttl
            )
            
            if success:
                logger.debug(f"Stored task status: {task_id}")
            else:
                logger.error(f"Failed to store task status: {task_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to store task status: {e}")
            return False
    
    def store_websocket_connection(self, deployment_id: str, connection_id: str, ttl: Optional[int] = None) -> bool:
        """
        Store WebSocket connection mapping
        
        Args:
            deployment_id: Deployment identifier
            connection_id: WebSocket connection identifier
            ttl: Time to live in seconds (default: 2 hours)
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            cache_key = f"ws:{deployment_id}"
            ttl = ttl or 7200  # 2 hours default
            
            success = self.redis.set(cache_key, connection_id, ex=ttl)
            
            if success:
                logger.debug(f"Stored WebSocket connection: {deployment_id} -> {connection_id}")
            else:
                logger.error(f"Failed to store WebSocket connection: {deployment_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to store WebSocket connection: {e}")
            return False
    
    def get_websocket_connection(self, deployment_id: str) -> Optional[str]:
        """
        Get WebSocket connection ID for deployment
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Connection ID if found, None otherwise
        """
        try:
            cache_key = f"ws:{deployment_id}"
            return self.redis.get(cache_key)
            
        except Exception as e:
            logger.error(f"Failed to retrieve WebSocket connection: {e}")
            return None
    
    def remove_websocket_connection(self, deployment_id: str) -> bool:
        """
        Remove WebSocket connection mapping
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            True if removed successfully, False otherwise
        """
        try:
            cache_key = f"ws:{deployment_id}"
            return self.redis.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Failed to remove WebSocket connection: {e}")
            return False
    
    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy
        
        Returns:
            True if Redis is accessible, False otherwise
        """
        return self.redis.ping()
    
    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries matching pattern
        
        Args:
            pattern: Redis key pattern (default: clear all)
            
        Returns:
            Number of keys deleted
        """
        try:
            if pattern:
                keys = self.redis.client.keys(pattern)
            else:
                keys = self.redis.client.keys("*")
            
            if keys:
                deleted = self.redis.client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0


# Global cache service instance
cache_service = CacheService()