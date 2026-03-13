import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError, jwt

from core.config import get_settings
from utils.constants import StatusCode

logger = logging.getLogger(__name__)
settings = get_settings()


class JWTHandler:
    """
    Production-grade JWT handler.

    Two-token strategy:
        access_token  → short-lived (15-60 min) — every API call
        refresh_token → long-lived (7 days) — only to get new access token

    Standard claims (RFC 7519):
        sub  → user_id (subject)
        role → RBAC role
        type → "access" | "refresh" — prevents token type misuse
        iss  → issuer — prevents token from another API being accepted
        aud  → audience — prevents token reuse across services
        iat  → issued at (unix timestamp)
        exp  → expiry (unix timestamp)
        jti  → unique token ID — enables revocation + audit logging
    """

    ALGORITHM = "HS256"
    ISSUER    = "choose-your-adventure-api"   # iss claim
    AUDIENCE  = "choose-your-adventure-client" # aud claim

    # ─── Access Token ─────────────────────────────────────────────────────────

    @classmethod
    def create_access_token(cls, user_id: int, role: str) -> str:
        """
        Creates short-lived access token.
        Expires: ACCESS_TOKEN_EXPIRE_MINUTES from .env (default 60 min).

        Improvement #1 — int(timestamp()) instead of datetime object
        Improvement #2 — iss + aud claims
        Improvement #5 — jti unique token ID per token
        """
        now    = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub":  str(user_id),                  # RFC 7519 — must be string
            "role": role,
            "type": "access",                       # guard — prevent refresh token misuse
            "iss":  cls.ISSUER,                     # issuer
            "aud":  cls.AUDIENCE,                   # audience
            "iat":  int(now.timestamp()),            # unix int — better compatibility
            "exp":  int(expire.timestamp()),         # unix int — better compatibility
            "jti":  str(uuid.uuid4()),              # unique ID — revocation + audit
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=cls.ALGORITHM)

    # ─── Refresh Token ────────────────────────────────────────────────────────

    @classmethod
    def create_refresh_token(cls, user_id: int) -> str:
        """
        Creates long-lived refresh token.
        Expires: REFRESH_TOKEN_EXPIRE_DAYS from .env (default 7 days).
        No role — role fetched fresh from DB when new access token is created.

        Improvement #5 — jti for rotation tracking
        """
        now    = datetime.now(timezone.utc)
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub":  str(user_id),
            "type": "refresh",                      # guard — prevent access token misuse
            "iss":  cls.ISSUER,
            "aud":  cls.AUDIENCE,
            "iat":  int(now.timestamp()),
            "exp":  int(expire.timestamp()),
            "jti":  str(uuid.uuid4()),              # unique ID per refresh token
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=cls.ALGORITHM)

    # ─── Verify ───────────────────────────────────────────────────────────────

    @classmethod
    def verify_token(cls, token: str, expected_type: str = "access") -> dict:
        """
        Verifies JWT — signature, expiry, type, issuer, audience.

        Edge cases:
            1. Empty/missing token       → 401
            2. Expired token             → 401
            3. Wrong token type          → 401 (refresh used as access)
            4. Wrong issuer/audience     → 401 (token from another service)
            5. Tampered signature        → 401
            6. Missing sub claim         → 401
            7. sub not a valid int       → 401

        Security: same generic message for ALL failures — never leak reason.
        Improvement #6 — Bearer prefix stripped here if present
        """
        # Improvement #6 — handle "Bearer <token>" if passed directly
        token = cls._extract_token(token)

        if not token:
            raise HTTPException(
                status_code=StatusCode.UNAUTHORIZED,
                detail="Token is invalid or expired",
            )

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[cls.ALGORITHM],
                audience=cls.AUDIENCE,      # Improvement #2 — aud validation
            )

            # Guard — issuer check (Improvement #2)
            if payload.get("iss") != cls.ISSUER:
                logger.warning(f"JWT issuer mismatch: {payload.get('iss')}")
                raise HTTPException(
                    status_code=StatusCode.UNAUTHORIZED,
                    detail="Token is invalid or expired",
                )

            # Guard — token type mismatch (e.g. refresh token on protected route)
            if payload.get("type") != expected_type:
                logger.warning(
                    f"JWT type mismatch — expected={expected_type} "
                    f"got={payload.get('type')}"
                )
                raise HTTPException(
                    status_code=StatusCode.UNAUTHORIZED,
                    detail="Token is invalid or expired",
                )

            # Guard — sub missing
            sub = payload.get("sub")
            if not sub:
                raise HTTPException(
                    status_code=StatusCode.UNAUTHORIZED,
                    detail="Token is invalid or expired",
                )

            # Guard — sub must be valid int (user_id)
            try:
                int(sub)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=StatusCode.UNAUTHORIZED,
                    detail="Token is invalid or expired",
                )

            return payload

        except ExpiredSignatureError:
            logger.info("JWT expired — client should use refresh token")
            raise HTTPException(
                status_code=StatusCode.UNAUTHORIZED,
                detail="Token is invalid or expired",
            )

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=StatusCode.UNAUTHORIZED,
                detail="Token is invalid or expired",
            )

    @classmethod
    def verify_refresh_token(cls, token: str) -> dict:
        """Verifies token as refresh type — used in /auth/refresh endpoint."""
        return cls.verify_token(token, expected_type="refresh")

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @classmethod
    def _extract_token(cls, token: str) -> str:
        """
        Improvement #6 — strips 'Bearer ' prefix if present.
        FastAPI's HTTPBearer already strips it, but this is a safety net
        in case token is passed directly (e.g. tests, mobile clients).
        """
        if not token or not token.strip():
            return ""
        token = token.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        return token

    @classmethod
    def get_jti(cls, token: str) -> str | None:
        """
        Improvement #5 — extracts jti from token WITHOUT verification.
        Used for blacklisting on logout (future Redis integration).

        WARNING: decode without verification — only for blacklist lookup.
        """
        try:
            # options={"verify_signature": False} — intentional, jti only
            unverified = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[cls.ALGORITHM],
                options={"verify_signature": False, "verify_exp": False},
                audience=cls.AUDIENCE,
            )
            return unverified.get("jti")
        except Exception:
            return None