import json
import hashlib
from typing import Optional, Any
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

class InMemoryCache:
    """Fallback in-memory cache when Redis server is unavailable."""
    def __init__(self):
        self._store = {}

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._store

class RedisClient:
    def __init__(self):
        self._client = None
        self._fallback = InMemoryCache()
        self._is_connected = False

    async def init(self):
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2.0
            )
            await self._client.ping()
            self._is_connected = True
            logger.info("Successfully connected to Redis server.")
        except Exception as e:
            logger.warning(f"Redis server unavailable ({e}). Using in-memory fallback cache.")
            self._is_connected = False

    async def get(self, key: str) -> Optional[str]:
        if self._is_connected and self._client:
            try:
                return await self._client.get(key)
            except Exception:
                pass
        return await self._fallback.get(key)

    async def set(self, key: str, value: str, expire: int = 3600) -> None:
        if self._is_connected and self._client:
            try:
                await self._client.set(key, value, ex=expire)
                return
            except Exception:
                pass
        await self._fallback.set(key, value, ex=expire)

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(self, key: str, value: Any, expire: int = 3600) -> None:
        await self.set(key, json.dumps(value), expire=expire)

    @staticmethod
    def generate_cache_key(prefix: str, query: str, user_roles: list[str], department: str, model_version: str = "v1") -> str:
        """Cache key MUST account for user permissions & query to avoid security leaks!"""
        roles_str = ",".join(sorted(user_roles))
        raw_key = f"{prefix}:{query.strip().lower()}:{roles_str}:{department}:{model_version}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

redis_client = RedisClient()
