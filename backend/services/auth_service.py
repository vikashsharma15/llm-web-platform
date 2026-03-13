"""

Production auth service — register, verify_otp, login, refresh, logout, get_me.

Rules:
  - Pure business logic — zero HTTP concerns
  - All limits from settings — zero magic numbers
  - All public methods return plain dict — controller never calls .model_dump()
  - Every method has: rid, structured logs, explicit error codes
  - Only one private helper: _issue_tokens() — shared by login + refresh
  - Everything else is inline — no over-extraction
"""

import logging
import secrets
import uuid
from datetime import datetime, timezone

from jose import ExpiredSignatureError, JWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.metrics import metrics
from core.token_store import TokenStore
from models.user import User, UserRole
from repositories.user_repository import UserRepository
from schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from utils.constants import ErrorCode, Messages, StatusCode
from utils.db_exception_handler import handle_integrity_error
from utils.email_handler import EmailHandler
from utils.exceptions import raise_http_error
from utils.jwt_handler import JWTHandler
from utils.password_handler import PasswordHandler

logger   = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    """
    Full production auth flow.
    Pure business logic — zero HTTP concerns.
    All public methods return plain dict.
    """

    def __init__(self, db: AsyncSession, token_store: TokenStore) -> None:
        self.db          = db
        self.repo        = UserRepository(db)
        self.token_store = token_store

    # ── Register ──────────────────────────────────────────────────────────────
    async def register(self, request: RegisterRequest, ip: str | None) -> dict:
        rid      = uuid.uuid4().hex[:12]
        email    = request.email.lower().strip()    # never mutate request object
        username = request.username.strip()

        logger.info(f"rid={rid} op=register email={email} ip={ip} started")

        # ── Duplicate check ───────────────────────────────────────────────────
        existing = await self.repo.get_by_email_or_username(email, username)
        if existing:
            if existing.email == email:
                logger.warning(f"rid={rid} op=register email_exists email={email}")
                raise_http_error(StatusCode.BAD_REQUEST, ErrorCode.EMAIL_ALREADY_EXISTS, Messages.EMAIL_ALREADY_EXISTS)
            else:
                logger.warning(f"rid={rid} op=register username_exists username={username}")
                raise_http_error(StatusCode.BAD_REQUEST, ErrorCode.USERNAME_ALREADY_EXISTS, Messages.USERNAME_ALREADY_EXISTS)

        # ── Dev bypass (EMAIL_OTP_ENABLED=false) ──────────────────────────────
        if not settings.EMAIL_OTP_ENABLED:
            logger.warning(f"rid={rid} op=register OTP disabled — creating active user directly")
            user = User(
                email=email,
                username=username,
                password=PasswordHandler.hash(request.password),
                role=UserRole.USER,
                is_active=True,
            )
            created = await self.repo.create(user)
            logger.info(f"rid={rid} op=register dev_bypass user_id={created.id}")
            return {"email": email}

        # ── Redis health ──────────────────────────────────────────────────────
        if not await self.token_store.is_healthy():
            logger.error(f"rid={rid} op=register redis_unhealthy")
            raise_http_error(StatusCode.SERVICE_UNAVAILABLE, ErrorCode.SERVICE_UNAVAILABLE, Messages.SERVICE_UNAVAILABLE)

        # ── IP rate limit (None-safe — middleware may not have set it) ────────
        if ip:
            ip_count = await self.token_store.get_ip_otp_count(ip)
            if ip_count >= settings.EMAIL_OTP_MAX_REQUESTS_PER_IP:
                logger.warning(f"rid={rid} op=register ip_rate_limited ip={ip} count={ip_count}")
                raise_http_error(StatusCode.TOO_MANY_REQUESTS, ErrorCode.RATE_LIMITED, Messages.OTP_RATE_LIMITED)

        # ── Email OTP rate limit + cooldown ───────────────────────────────────
        count, can_resend, cooldown = await self.token_store.get_otp_status(email)

        if count >= settings.EMAIL_OTP_MAX_REQUESTS:
            logger.warning(f"rid={rid} op=register email_rate_limited email={email} count={count}")
            raise_http_error(StatusCode.TOO_MANY_REQUESTS, ErrorCode.OTP_RATE_LIMITED, Messages.OTP_RATE_LIMITED)

        if not can_resend:
            logger.warning(f"rid={rid} op=register otp_cooldown email={email} cooldown={cooldown}s")
            raise_http_error(StatusCode.TOO_MANY_REQUESTS, ErrorCode.OTP_COOLDOWN, f"{Messages.OTP_COOLDOWN}. Try again in {cooldown}s")

        # ── Generate + store OTP ──────────────────────────────────────────────
        length = settings.EMAIL_OTP_LENGTH
        otp    = f"{secrets.randbelow(10 ** length):0{length}d}"

        stored = await self.token_store.store_otp(email, otp)
        if not stored:
            logger.error(f"rid={rid} op=register otp_store_failed email={email}")
            raise_http_error(StatusCode.SERVICE_UNAVAILABLE, ErrorCode.SERVICE_UNAVAILABLE, Messages.SERVICE_UNAVAILABLE)

        # Increment counters AFTER successful store
        await self.token_store.increment_otp_requests(email)
        if ip:
            await self.token_store.increment_ip_otp_count(ip)

        # ── Send email ────────────────────────────────────────────────────────
        sent = await EmailHandler.send_otp(email, otp)
        if not sent:
            # Clean up OTP — user can retry cleanly
            await self.token_store.delete_otp(email)
            logger.error(f"rid={rid} op=register email_send_failed email={email}")
            raise_http_error(StatusCode.SERVICE_UNAVAILABLE, ErrorCode.SERVICE_UNAVAILABLE, Messages.EMAIL_SERVICE_UNAVAILABLE)

        # ── Create inactive user ──────────────────────────────────────────────
        user = User(
            email=email,
            username=username,
            password=PasswordHandler.hash(request.password),
            role=UserRole.USER,
            is_active=False,
        )

        try:
            created = await self.repo.create(user)
        except Exception as exc:
            # DB failure after email sent — clean up OTP so user can retry
            await self.token_store.delete_otp(email)
            logger.error(f"rid={rid} op=register db_create_failed email={email} err={exc!r}")
            raise

        await self.token_store.set_otp_cooldown(email)

        logger.info(f"rid={rid} op=register otp_sent user_id={created.id} email={email}")
        return {"email": email}

    # ── Verify OTP ────────────────────────────────────────────────────────────
    async def verify_otp(self, email: str, otp: str) -> dict:
        rid   = uuid.uuid4().hex[:12]
        email = email.lower().strip()

        logger.info(f"rid={rid} op=verify_otp email={email} started")

        # ── Redis health ──────────────────────────────────────────────────────
        if not await self.token_store.is_healthy():
            logger.error(f"rid={rid} op=verify_otp redis_unhealthy")
            raise_http_error(StatusCode.SERVICE_UNAVAILABLE, ErrorCode.SERVICE_UNAVAILABLE, Messages.SERVICE_UNAVAILABLE)

        # ── User check ────────────────────────────────────────────────────────
        user = await self.repo.get_by_email(email)
        if not user:
            logger.warning(f"rid={rid} op=verify_otp user_not_found email={email}")
            raise_http_error(StatusCode.NOT_FOUND, ErrorCode.USER_NOT_FOUND, Messages.USER_NOT_FOUND)

        # ── Already verified (separate code from email_exists) ────────────────
        if user.is_active:
            logger.warning(f"rid={rid} op=verify_otp already_verified email={email}")
            raise_http_error(StatusCode.CONFLICT, ErrorCode.EMAIL_ALREADY_VERIFIED, Messages.EMAIL_ALREADY_VERIFIED)

        # ── OTP check ─────────────────────────────────────────────────────────
        valid = await self.token_store.verify_otp(email, otp)
        if not valid:
            logger.warning(f"rid={rid} op=verify_otp invalid_otp email={email}")
            raise_http_error(StatusCode.BAD_REQUEST, ErrorCode.INVALID_OTP, Messages.INVALID_OTP)

        # ── Activate account ──────────────────────────────────────────────────
        # Delete OTP BEFORE commit — prevents reuse if commit fails mid-flight
        await self.token_store.delete_otp(email)

        user.is_active = True
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            logger.error(f"rid={rid} op=verify_otp commit_failed email={email} err={exc!r}")
            handle_integrity_error(exc)

        logger.info(f"rid={rid} op=verify_otp verified user_id={user.id} email={email}")
        return {"email": email}

    # ── Login ─────────────────────────────────────────────────────────────────
    async def login(self, request: LoginRequest, ip: str | None) -> dict:
        rid   = uuid.uuid4().hex[:12]
        email = request.email.lower().strip()

        logger.info(f"rid={rid} op=login email={email} ip={ip} started")
        metrics.login_attempt(email)

        # ── Lock check (before any DB query — fast fail) ──────────────────────
        if await self.token_store.is_account_locked(email):
            ttl = await self.token_store.get_lock_ttl(email)
            logger.warning(f"rid={rid} op=login account_locked email={email} ttl={ttl}s")
            raise_http_error(
                StatusCode.TOO_MANY_REQUESTS,
                ErrorCode.ACCOUNT_LOCKED,
                f"{Messages.ACCOUNT_LOCKED}. {Messages.TRY_AGAIN_IN} {ttl} seconds.",
            )

        user = await self.repo.get_by_email(email)

        # ── Credential check (identical error — prevents enumeration) ─────────
        if not user or not PasswordHandler.verify(request.password, user.password):
            metrics.login_failure(email)
            attempts = await self.token_store.increment_login_attempts(email)
            logger.warning(f"rid={rid} op=login invalid_credentials email={email} attempts={attempts}")

            if attempts >= settings.LOGIN_MAX_ATTEMPTS:
                await self.token_store.lock_account(email)
                logger.warning(f"rid={rid} op=login account_locked email={email} after={attempts}_attempts")
                raise_http_error(
                    StatusCode.TOO_MANY_REQUESTS,
                    ErrorCode.ACCOUNT_LOCKED,
                    f"{Messages.ACCOUNT_LOCKED_ATTEMPTS} {settings.ACCOUNT_LOCK_SECONDS // 60} minutes.",
                )

            raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.INVALID_CREDENTIALS, Messages.INVALID_CREDENTIALS)

        # ── Active check ──────────────────────────────────────────────────────
        if not user.is_active:
            logger.warning(f"rid={rid} op=login account_not_verified email={email}")
            raise_http_error(StatusCode.FORBIDDEN, ErrorCode.ACCOUNT_DISABLED, Messages.ACCOUNT_DISABLED)

        await self.token_store.reset_login_attempts(email)

        tokens = await self._issue_tokens(user.id, user.role.value, rid)

        logger.info(f"rid={rid} op=login success user_id={user.id} email={email}")
        return tokens

    # ── Refresh ───────────────────────────────────────────────────────────────
    async def refresh(self, request: RefreshRequest) -> dict:
        rid = uuid.uuid4().hex[:12]

        # ── Decode token (401 on expired/invalid — never 500) ─────────────────
        try:
            payload = JWTHandler.verify_refresh_token(request.refresh_token)
        except ExpiredSignatureError:
            logger.warning(f"rid={rid} op=refresh token_expired")
            raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.TOKEN_EXPIRED, Messages.TOKEN_EXPIRED)
        except JWTError as exc:
            logger.warning(f"rid={rid} op=refresh token_invalid err={exc!r}")
            raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.TOKEN_INVALID, Messages.TOKEN_INVALID)

        # ── Parse sub (401 on malformed — never 500 from int() crash) ─────────
        try:
            user_id = int(payload["sub"])
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning(f"rid={rid} op=refresh malformed_sub err={exc!r}")
            raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.TOKEN_INVALID, Messages.TOKEN_INVALID)

        old_jti = payload["jti"]
        old_exp = payload["exp"]

        logger.info(f"rid={rid} op=refresh uid={user_id} started")

        # ── Reuse detection (blacklisted JTI = theft signal → revoke all) ─────
        if await self.token_store.is_blacklisted(old_jti):
            logger.warning(f"rid={rid} op=refresh token_reuse_detected uid={user_id} jti={old_jti}")
            await self.token_store.revoke_refresh_token(user_id)
            raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.TOKEN_REUSE, Messages.TOKEN_INVALID)

        # ── JTI rotation check (mismatch = possible theft → revoke all) ───────
        if not await self.token_store.is_valid_refresh_jti(user_id, old_jti):
            logger.warning(f"rid={rid} op=refresh jti_rotation_violation uid={user_id}")
            await self.token_store.revoke_refresh_token(user_id)
            raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.TOKEN_INVALID, Messages.TOKEN_INVALID)

        # ── User checks ───────────────────────────────────────────────────────
        user = await self.repo.get_by_id(user_id)
        if not user:
            logger.warning(f"rid={rid} op=refresh user_not_found uid={user_id}")
            raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.USER_NOT_FOUND, Messages.USER_NOT_FOUND)

        if not user.is_active:
            logger.warning(f"rid={rid} op=refresh account_disabled uid={user_id}")
            raise_http_error(StatusCode.FORBIDDEN, ErrorCode.ACCOUNT_DISABLED, Messages.ACCOUNT_DISABLED)

        # ── Issue new pair + blacklist old token ──────────────────────────────
        tokens = await self._issue_tokens(user.id, user.role.value, rid)

        now     = int(datetime.now(timezone.utc).timestamp())
        old_ttl = max(0, old_exp - now)
        if old_ttl > 0:
            await self.token_store.blacklist_token(old_jti, old_ttl)
            logger.debug(f"rid={rid} op=refresh old_jti_blacklisted ttl={old_ttl}s uid={user_id}")

        logger.info(f"rid={rid} op=refresh success uid={user_id}")
        return tokens

    # ── Logout ────────────────────────────────────────────────────────────────
    async def logout(self, access_token: str, user_id: int) -> None:
        rid = uuid.uuid4().hex[:12]

        jti = JWTHandler.get_jti(access_token)
        if jti:
            try:
                payload = JWTHandler.verify_token(access_token)
                now     = int(datetime.now(timezone.utc).timestamp())
                ttl     = max(0, payload["exp"] - now)
                if ttl > 0:
                    await self.token_store.blacklist_token(jti, ttl)
                    logger.debug(f"rid={rid} op=logout jti_blacklisted ttl={ttl}s uid={user_id}")
            except ExpiredSignatureError:
                # Expired token on logout is expected (mobile apps) — still revoke refresh
                logger.debug(f"rid={rid} op=logout token_already_expired uid={user_id}")
            except JWTError as exc:
                # Invalid token — still revoke refresh, log for visibility
                logger.warning(f"rid={rid} op=logout jwt_error uid={user_id} err={type(exc).__name__}")

        # Always revoke refresh regardless of access token state
        await self.token_store.revoke_refresh_token(user_id)
        logger.info(f"rid={rid} op=logout success uid={user_id}")

    # ── Get Me ────────────────────────────────────────────────────────────────
    async def get_me(self, current_user: User) -> dict:
        rid = uuid.uuid4().hex[:12]
        logger.info(f"rid={rid} op=get_me uid={current_user.id}")
        return UserResponse.model_validate(current_user).model_dump()

    # =========================================================================
    # PRIVATE HELPER
    # Only one — because login + refresh both need it.
    # Everything else is inline.
    # =========================================================================

    async def _issue_tokens(self, user_id: int, role: str, rid: str) -> dict:
        """
        Create access + refresh token pair and persist JTI in Redis.
        Raises 503 if JTI storage fails — tokens never returned without storage.
        Shared by login() and refresh() — that's the only reason this exists.
        """
        access_token  = JWTHandler.create_access_token(user_id, role)
        refresh_token = JWTHandler.create_refresh_token(user_id)

        refresh_payload = JWTHandler.verify_refresh_token(refresh_token)
        refresh_ttl     = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600

        try:
            await self.token_store.store_refresh_jti(user_id, refresh_payload["jti"], refresh_ttl)
        except Exception as exc:
            logger.error(f"rid={rid} jti_store_failed uid={user_id} err={exc!r}")
            raise_http_error(StatusCode.SERVICE_UNAVAILABLE, ErrorCode.SERVICE_UNAVAILABLE, Messages.SERVICE_UNAVAILABLE)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ).model_dump()