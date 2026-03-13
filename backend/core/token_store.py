import logging
from redis.asyncio import Redis
from redis.exceptions import RedisError

from core.config import get_settings
from core.metrics import metrics

logger   = logging.getLogger(__name__)
settings = get_settings()

_BLACKLIST_PREFIX    = "jwt:blacklist:"
_REFRESH_PREFIX      = "jwt:refresh:"
_RATE_LIMIT_PREFIX   = "auth:rate:"
_LOCK_PREFIX         = "auth:lock:"
_OTP_PREFIX          = "auth:otp:"
_OTP_COOLDOWN_PREFIX = "auth:otp:cd:"
_OTP_RATE_PREFIX     = "auth:otp:rate:"
_OTP_IP_PREFIX       = "auth:otp:ip:"          # IP-level OTP rate limiting


class TokenStore:
    """
    Redis-backed auth state — graceful degradation when Redis is unavailable.

    Fail strategy per operation:
        FAIL SAFE  -> security ops  -> deny request  (blacklist, refresh validation)
        FAIL OPEN  -> UX ops        -> allow request (rate limit, lock check, reset)
        SKIP       -> write ops     -> silently skip (store, delete, cooldown)
    """

    def __init__(self, redis: Redis | None) -> None:
        self.redis = redis

    @property
    def _available(self) -> bool:
        return self.redis is not None

    @staticmethod
    def _to_str(value) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value) if value is not None else ""

    async def is_healthy(self) -> bool:
        if not self._available:
            return False
        try:
            await self.redis.ping()
            return True
        except RedisError:
            return False

    # ── 1. JWT Blacklist ──────────────────────────────────────────────────────

    async def blacklist_token(self, jti: str, ttl_seconds: int) -> None:
        # SKIP if Redis down — logout still proceeds, token expires naturally
        if not self._available:
            logger.warning(f"Redis down — token NOT blacklisted jti={jti}")
            return
        try:
            await self.redis.setex(f"{_BLACKLIST_PREFIX}{jti}", ttl_seconds, "1")
            metrics.token_blacklisted()
            logger.info(f"Token blacklisted jti={jti} ttl={ttl_seconds}s")
        except RedisError as e:
            logger.error(f"Blacklist write failed jti={jti}: {e}")
            raise

    async def is_blacklisted(self, jti: str) -> bool:
        # FAIL SAFE — deny if Redis errors (can't verify revocation)
        if not self._available:
            return False
        try:
            return await self.redis.exists(f"{_BLACKLIST_PREFIX}{jti}") == 1
        except RedisError as e:
            logger.error(f"Blacklist check failed jti={jti}: {e}")
            return True

    # ── 2. Refresh Token Rotation ─────────────────────────────────────────────

    async def store_refresh_jti(self, user_id: int, jti: str, ttl_seconds: int) -> None:
        # SKIP if Redis down — refresh rotation disabled in degraded mode
        if not self._available:
            logger.warning(f"Redis down — refresh jti NOT stored user={user_id}")
            return
        try:
            await self.redis.setex(f"{_REFRESH_PREFIX}{user_id}", ttl_seconds, jti)
        except RedisError as e:
            logger.error(f"Store refresh jti failed user={user_id}: {e}")
            raise

    async def is_valid_refresh_jti(self, user_id: int, jti: str) -> bool:
        # FAIL OPEN if Redis down — allow refresh in degraded mode
        if not self._available:
            return True
        try:
            stored = await self.redis.get(f"{_REFRESH_PREFIX}{user_id}")
            if stored is None:
                return False
            return self._to_str(stored) == jti
        except RedisError as e:
            logger.error(f"Refresh jti check failed user={user_id}: {e}")
            return False

    async def revoke_refresh_token(self, user_id: int) -> None:
        # SKIP if Redis down
        if not self._available:
            return
        try:
            await self.redis.delete(f"{_REFRESH_PREFIX}{user_id}")
        except RedisError as e:
            logger.error(f"Revoke refresh failed user={user_id}: {e}")

    # ── 3. Login Rate Limiting ────────────────────────────────────────────────

    async def increment_login_attempts(self, identifier: str) -> int:
        # FAIL OPEN — return 0, don't block users when Redis is down
        if not self._available:
            return 0
        try:
            key  = f"{_RATE_LIMIT_PREFIX}{identifier}"
            pipe = self.redis.pipeline()
            await pipe.incr(key)
            await pipe.expire(key, settings.LOGIN_RATE_LIMIT_WINDOW)
            results = await pipe.execute()
            count = int(self._to_str(results[0]))
            metrics.login_attempt(identifier)
            return count
        except RedisError as e:
            logger.error(f"Rate limit incr failed identifier={identifier}: {e}")
            return 0

    async def get_login_attempts(self, identifier: str) -> int:
        # FAIL OPEN — return 0
        if not self._available:
            return 0
        try:
            val = await self.redis.get(f"{_RATE_LIMIT_PREFIX}{identifier}")
            return int(self._to_str(val)) if val else 0
        except RedisError as e:
            logger.error(f"Rate limit get failed identifier={identifier}: {e}")
            return 0

    async def reset_login_attempts(self, identifier: str) -> None:
        # SKIP if Redis down — already authenticated, safe to ignore
        if not self._available:
            return
        try:
            await self.redis.delete(f"{_RATE_LIMIT_PREFIX}{identifier}")
        except RedisError as e:
            logger.error(f"Rate limit reset failed identifier={identifier}: {e}")

    # ── 4. Account Lockout ────────────────────────────────────────────────────

    async def lock_account(self, email: str) -> None:
        # SKIP if Redis down — can't lock, log warning
        if not self._available:
            logger.warning(f"Redis down — account NOT locked email={email}")
            return
        try:
            await self.redis.set(
                f"{_LOCK_PREFIX}{email}", "1",
                ex=settings.ACCOUNT_LOCK_SECONDS,
                nx=True,
            )
            metrics.account_locked(email)
            logger.warning(f"Account locked email={email} duration={settings.ACCOUNT_LOCK_SECONDS}s")
        except RedisError as e:
            logger.error(f"Account lock failed email={email}: {e}")

    async def is_account_locked(self, email: str) -> bool:
        # FAIL OPEN — don't block users when Redis is down
        if not self._available:
            return False
        try:
            return await self.redis.exists(f"{_LOCK_PREFIX}{email}") == 1
        except RedisError as e:
            logger.error(f"Lock check failed email={email}: {e}")
            return False

    async def get_lock_ttl(self, email: str) -> int:
        # FAIL OPEN — return 0
        if not self._available:
            return 0
        try:
            ttl = await self.redis.ttl(f"{_LOCK_PREFIX}{email}")
            return max(0, int(self._to_str(ttl)) if ttl else 0)
        except RedisError as e:
            logger.error(f"Lock TTL failed email={email}: {e}")
            return 0

    # ── 5. Email OTP ──────────────────────────────────────────────────────────

    async def get_otp_status(self, email: str) -> tuple[int, bool, int]:
        """
        Single pipeline call replacing 3 separate round trips.
        Returns (request_count, can_resend, cooldown_ttl).
        FAIL OPEN — returns (0, True, 0) if Redis down.
        """
        if not self._available:
            return 0, True, 0
        try:
            rate_key     = f"{_OTP_RATE_PREFIX}{email}"
            cooldown_key = f"{_OTP_COOLDOWN_PREFIX}{email}"
            pipe = self.redis.pipeline()
            await pipe.get(rate_key)
            await pipe.exists(cooldown_key)
            await pipe.ttl(cooldown_key)
            results = await pipe.execute()

            count       = int(self._to_str(results[0])) if results[0] else 0
            on_cooldown = bool(results[1])
            ttl         = max(0, int(results[2]) if results[2] and results[2] > 0 else 0)

            return count, not on_cooldown, ttl
        except RedisError as e:
            logger.error(f"OTP status check failed email={email}: {e}")
            return 0, True, 0

    async def increment_otp_requests(self, email: str) -> None:
        # SKIP if Redis down
        if not self._available:
            return
        try:
            key  = f"{_OTP_RATE_PREFIX}{email}"
            pipe = self.redis.pipeline()
            await pipe.incr(key)
            await pipe.expire(key, settings.EMAIL_OTP_RATE_WINDOW)
            await pipe.execute()
        except RedisError as e:
            logger.error(f"OTP rate increment failed email={email}: {e}")

    # ── 6. IP-level OTP Rate Limiting ─────────────────────────────────────────

    async def get_ip_otp_count(self, ip: str) -> int:
        # FAIL OPEN — return 0, don't block on Redis down
        if not self._available:
            return 0
        try:
            val = await self.redis.get(f"{_OTP_IP_PREFIX}{ip}")
            return int(self._to_str(val)) if val else 0
        except RedisError as e:
            logger.error(f"IP OTP count get failed ip={ip}: {e}")
            return 0

    async def increment_ip_otp_requests(self, ip: str) -> None:
        # SKIP if Redis down
        if not self._available:
            return
        try:
            key  = f"{_OTP_IP_PREFIX}{ip}"
            pipe = self.redis.pipeline()
            await pipe.incr(key)
            await pipe.expire(key, settings.EMAIL_OTP_RATE_WINDOW)
            await pipe.execute()
        except RedisError as e:
            logger.error(f"IP OTP increment failed ip={ip}: {e}")

    # ── 7. OTP Store / Verify / Cleanup ───────────────────────────────────────

    async def store_otp(self, email: str, otp: str) -> bool:
        """Returns True on success, False on failure."""
        if not self._available:
            return False
        try:
            ttl  = settings.EMAIL_OTP_EXPIRE_MINUTES * 60
            pipe = self.redis.pipeline()
            await pipe.setex(f"{_OTP_PREFIX}{email}:code",     ttl, otp)
            await pipe.setex(f"{_OTP_PREFIX}{email}:attempts", ttl, "0")
            await pipe.execute()
            logger.info(f"OTP stored email={email} ttl={ttl}s")
            return True
        except RedisError as e:
            logger.error(f"OTP store failed email={email}: {e}")
            return False

    async def verify_otp(self, email: str, submitted_otp: str) -> tuple[bool, str]:
        # FAIL SAFE — return expired if Redis down
        if not self._available:
            return False, "expired"
        code_key     = f"{_OTP_PREFIX}{email}:code"
        attempts_key = f"{_OTP_PREFIX}{email}:attempts"
        try:
            pipe = self.redis.pipeline()
            await pipe.get(code_key)
            await pipe.get(attempts_key)
            results      = await pipe.execute()
            stored_otp   = results[0]
            raw_attempts = results[1]
        except RedisError as e:
            logger.error(f"OTP fetch failed email={email}: {e}")
            return False, "expired"

        if stored_otp is None:
            return False, "expired"

        stored_otp = self._to_str(stored_otp)
        attempts   = int(self._to_str(raw_attempts)) if raw_attempts else 0

        if attempts >= settings.EMAIL_OTP_MAX_ATTEMPTS:
            try:
                await self.redis.delete(code_key, attempts_key)
            except RedisError:
                pass
            metrics.otp_failed("max_attempts")
            return False, "max_attempts"

        if stored_otp != submitted_otp:
            try:
                await self.redis.incr(attempts_key)
            except RedisError:
                pass
            metrics.otp_failed("invalid")
            return False, "invalid"

        try:
            await self.redis.delete(code_key, attempts_key)
        except RedisError as e:
            logger.error(f"OTP cleanup failed email={email}: {e}")

        logger.info(f"OTP verified email={email}")
        return True, "ok"

    async def can_resend_otp(self, email: str) -> bool:
        # FAIL SAFE — prevent spam if Redis down
        if not self._available:
            return False
        try:
            return await self.redis.exists(f"{_OTP_COOLDOWN_PREFIX}{email}") == 0
        except RedisError as e:
            logger.error(f"OTP cooldown check failed email={email}: {e}")
            return False

    async def set_otp_cooldown(self, email: str) -> None:
        # SKIP if Redis down
        if not self._available:
            return
        try:
            await self.redis.setex(
                f"{_OTP_COOLDOWN_PREFIX}{email}",
                settings.EMAIL_OTP_RESEND_COOLDOWN, "1",
            )
        except RedisError as e:
            logger.error(f"OTP cooldown set failed email={email}: {e}")

    async def get_otp_cooldown_ttl(self, email: str) -> int:
        # FAIL OPEN — return 0
        if not self._available:
            return 0
        try:
            ttl = await self.redis.ttl(f"{_OTP_COOLDOWN_PREFIX}{email}")
            return max(0, int(self._to_str(ttl)) if ttl else 0)
        except RedisError as e:
            logger.error(f"OTP cooldown TTL failed email={email}: {e}")
            return 0

    async def delete_otp(self, email: str) -> None:
        # SKIP if Redis down
        if not self._available:
            return
        try:
            await self.redis.delete(
                f"{_OTP_PREFIX}{email}:code",
                f"{_OTP_PREFIX}{email}:attempts",
            )
        except RedisError as e:
            logger.error(f"OTP delete failed email={email}: {e}")