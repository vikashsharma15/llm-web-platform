import logging
import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry
from redis.exceptions import ConnectionError, RedisError

from core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

# Module-level singleton — one connection pool for entire app lifetime
_redis_client: Redis | None = None


def get_redis() -> Redis | None:
    """
    Returns Redis singleton or None if unavailable.
    Callers must always handle None — never assume Redis is up.

    Usage:
        redis = get_redis()
        if redis is None:
            # fallback logic here
    """
    return _redis_client


def is_redis_available() -> bool:
    """
    Quick boolean check before any Redis operation.

    Usage:
        if is_redis_available():
            await cache_something()
    """
    return _redis_client is not None


async def init_redis() -> None:
    """
    Attempts to create Redis connection pool on app startup.
    Called exactly once in main.py lifespan — never per-request.

    Hybrid behavior:
        - Redis UP   → connects, logs success, full features enabled
        - Redis DOWN → logs warning, app starts in degraded mode (no crash)

    Production config rationale:
        decode_responses=True        → always returns str, never raw bytes
        max_connections              → pool size from settings, not hardcoded
        socket_connect_timeout       → fail fast if Redis is unreachable
        socket_timeout               → fail fast on stalled/hanging commands
        health_check_interval        → proactively detects stale connections
        retry + ExponentialBackoff   → handles transient Redis blips gracefully
    """
    global _redis_client

    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,                           # str always — no .decode() anywhere

            # Connection pool
            max_connections=settings.REDIS_POOL_SIZE,

            # Timeouts — never let a request hang waiting for Redis
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,

            # Keepalive — detect dead connections before they fail a live request
            health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,

            # Retry with exponential backoff — 0.5s → 1s → 2s → cap at 10s
            retry=Retry(
                ExponentialBackoff(cap=10, base=0.5),
                retries=settings.REDIS_RETRY_ATTEMPTS,
            ),
            retry_on_timeout=True,
        )

        # Verify Redis is actually alive before accepting traffic
        await client.ping()

        _redis_client = client
        logger.info(
            f"Redis connected ✅  pool_size={settings.REDIS_POOL_SIZE} "
            f"url={settings.REDIS_URL}"
        )

    except (ConnectionError, RedisError, OSError) as e:
        _redis_client = None
        logger.warning(
            "Redis unavailable — app running in degraded mode "
            "(caching and rate-limiting disabled). "
            f"Reason: {e}"
        )
        # ❌ No raise — app continues without Redis


async def close_redis() -> None:
    """
    Closes Redis connection pool on app shutdown.
    Called in main.py lifespan cleanup — guaranteed to run even if Redis was never up.
    """
    global _redis_client

    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed ✅")


async def safe_get(key: str) -> str | None:
    """
    Safe Redis GET — returns None on any failure instead of raising.

    Args:
        key: Redis key to fetch

    Returns:
        Cached value as str, or None if Redis is down / key missing
    """
    redis = get_redis()
    if redis is None:
        return None

    try:
        return await redis.get(key)
    except RedisError as e:
        logger.warning(f"Redis GET failed for key='{key}': {e}")
        return None


async def safe_set(key: str, value: str, ex: int | None = None) -> bool:
    """
    Safe Redis SET — returns False on any failure instead of raising.

    Args:
        key:   Redis key
        value: String value to store
        ex:    Expiry in seconds (optional)

    Returns:
        True if stored successfully, False if Redis is down or write failed
    """
    redis = get_redis()
    if redis is None:
        return False

    try:
        await redis.set(key, value, ex=ex)
        return True
    except RedisError as e:
        logger.warning(f"Redis SET failed for key='{key}': {e}")
        return False


async def safe_delete(key: str) -> bool:
    """
    Safe Redis DELETE — returns False on any failure instead of raising.

    Args:
        key: Redis key to delete

    Returns:
        True if deleted, False if Redis is down or delete failed
    """
    redis = get_redis()
    if redis is None:
        return False

    try:
        await redis.delete(key)
        return True
    except RedisError as e:
        logger.warning(f"Redis DELETE failed for key='{key}': {e}")
        return False


async def safe_incr(key: str, ex: int | None = None) -> int | None:
    """
    Safe Redis INCR — used for rate limiting counters.
    Sets expiry on first increment so keys don't live forever.

    Args:
        key: Redis key to increment
        ex:  Expiry in seconds (set only on first increment)

    Returns:
        New counter value as int, or None if Redis is down
    """
    redis = get_redis()
    if redis is None:
        return None

    try:
        count = await redis.incr(key)
        if count == 1 and ex:
            # First increment — set expiry window
            await redis.expire(key, ex)
        return count
    except RedisError as e:
        logger.warning(f"Redis INCR failed for key='{key}': {e}")
        return None