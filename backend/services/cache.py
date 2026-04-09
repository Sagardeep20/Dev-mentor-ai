import json
import logging
from typing import Optional, Any
from datetime import datetime, timezone

import redis.asyncio as redis
from config import REDIS_URL, REDIS_CACHE_TTL

logger = logging.getLogger("devmentor.cache")

# Global Redis connection pool
_redis_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create Redis connection."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_pool


async def close_redis():
    """Close Redis connection."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


class CacheService:
    """Redis-based caching service for DevMentor."""

    def __init__(self):
        self.ttl = REDIS_CACHE_TTL
        self.prefix = "devmentor:"

    def _key(self, category: str, key: str) -> str:
        """Build namespaced cache key."""
        return f"{self.prefix}{category}:{key}"

    async def get(self, category: str, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            redis_client = await get_redis()
            cache_key = self._key(category, key)
            value = await redis_client.get(cache_key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(self, category: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL override."""
        try:
            redis_client = await get_redis()
            cache_key = self._key(category, key)
            ttl = ttl or self.ttl
            await redis_client.setex(cache_key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def delete(self, category: str, key: str) -> bool:
        """Delete a cache entry."""
        try:
            redis_client = await get_redis()
            cache_key = self._key(category, key)
            await redis_client.delete(cache_key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    async def invalidate_pattern(self, category: str, pattern: str) -> int:
        """Delete all keys matching pattern in a category."""
        try:
            redis_client = await get_redis()
            full_pattern = self._key(category, pattern)
            keys = []
            async for key in redis_client.scan_iter(match=full_pattern):
                keys.append(key)
            if keys:
                return await redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
            return 0

    # ============ Specialized cache methods ============

    async def get_explanation(self, code_hash: str, project_id: str) -> Optional[str]:
        """Get cached code explanation."""
        cache_key = f"{project_id}:{code_hash}"
        result = await self.get("explanation", cache_key)
        return result.get("explanation") if result else None

    async def set_explanation(self, code_hash: str, project_id: str, explanation: str, language: str):
        """Cache code explanation."""
        cache_key = f"{project_id}:{code_hash}"
        await self.set("explanation", cache_key, {
            "explanation": explanation,
            "language": language,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }, ttl=self.ttl)

    async def get_llm_response(self, query_hash: str, project_path: str) -> Optional[dict]:
        """Get cached LLM response for a query (short TTL for LLM caching)."""
        cache_key = f"{project_path}:{query_hash}"
        return await self.get("llm", cache_key)

    async def set_llm_response(self, query_hash: str, project_path: str, response: dict):
        """Cache LLM response with shorter TTL (5 min for LLM responses)."""
        cache_key = f"{project_path}:{query_hash}"
        await self.set("llm", cache_key, {
            "response": response,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }, ttl=300)  # 5 minutes

    async def get_issues(self, project_id: str) -> Optional[list]:
        """Get cached issues for a project."""
        result = await self.get("issues", project_id)
        return result.get("issues") if result else None

    async def set_issues(self, project_id: str, issues: list):
        """Cache issues for a project."""
        await self.set("issues", project_id, {
            "issues": issues,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }, ttl=self.ttl)

    async def invalidate_project(self, project_id: str):
        """Invalidate all cache for a project (on re-analysis)."""
        await self.invalidate_pattern("explanation", f"{project_id}:*")
        await self.invalidate_pattern("llm", f"{project_id}*")
        await self.invalidate_pattern("issues", project_id)


# Global cache instance
cache = CacheService()