import time
from dataclasses import dataclass
from fnmatch import fnmatch

from app.core.config import get_settings
from loguru import logger
from redis.asyncio import Redis


@dataclass
class _LocalEntry:
    expires_at: float
    value: str


_redis: Redis | None = None
_local_cache: dict[str, _LocalEntry] = {}


def _client() -> Redis | None:
    global _redis
    settings = get_settings()
    if not settings.redis_url:
        return None
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_report_cache(key: str) -> str | None:
    client = _client()
    if client is not None:
        try:
            return await client.get(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis report cache unavailable: {}", exc)
            return None

    entry = _local_cache.get(key)
    if entry is None:
        return None
    if entry.expires_at <= time.monotonic():
        _local_cache.pop(key, None)
        return None
    return entry.value


async def set_report_cache(key: str, value: str, ttl: int = 30) -> None:
    client = _client()
    if client is not None:
        try:
            await client.setex(key, ttl, value)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis report cache unavailable: {}", exc)

    _local_cache[key] = _LocalEntry(time.monotonic() + ttl, value)


async def invalidate_report_cache() -> None:
    pattern = "reports:v1:*"
    client = _client()
    if client is not None:
        try:
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis report cache invalidation failed: {}", exc)

    for key in list(_local_cache):
        if fnmatch(key, pattern):
            _local_cache.pop(key, None)


async def close_report_cache() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
