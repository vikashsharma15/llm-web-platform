from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_TITLE:       str  = "Choose Your Own Adventure API"
    APP_DESCRIPTION: str  = "API to generate cool stories based on user input"
    APP_VERSION:     str  = "0.1.0"
    DEBUG:           bool = False
    HOST:            str  = "localhost"
    PORT:            int  = 8000
    API_PREFIX:      str  = "/api"

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str

     # ─── SMTP ─────────────────────────────────────────────────────────────────
    SMTP_HOST:     str  = "smtp-relay.brevo.com"
    SMTP_PORT:     int  = 587
    SMTP_USER:     str  = ""   # ← SMTP_USERNAME → SMTP_USER
    SMTP_PASS:     str  = ""   # ← SMTP_PASSWORD → SMTP_PASS
    FROM_EMAIL:    str  = ""   # ← SMTP_FROM → FROM_EMAIL
    FROM_NAME:     str  = "Story Generator"  # ← add karo
    SMTP_TLS:      bool = True

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL:                   str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE:             int = 20   # max concurrent connections in pool
    REDIS_CONNECT_TIMEOUT:       int = 5    # seconds — fail fast if Redis unreachable
    REDIS_SOCKET_TIMEOUT:        int = 5    # seconds — fail fast on stalled commands
    REDIS_HEALTH_CHECK_INTERVAL: int = 30   # seconds — keepalive ping interval
    REDIS_RETRY_ATTEMPTS:        int = 3    # exponential backoff retries

    # ─── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = ""

    # ─── LLM ──────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str

    # ─── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY:              str = "change-this-in-production"
    JWT_ALGORITHM:               str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60   # 1 hour — short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS:   int = 7    # 7 days — long-lived refresh token

    # ─── Rate Limiting + Lockout ──────────────────────────────────────────────
    LOGIN_RATE_LIMIT_WINDOW: int = 60    # seconds — sliding window per identifier
    LOGIN_MAX_ATTEMPTS:      int = 5     # failures allowed before lockout
    ACCOUNT_LOCK_SECONDS:    int = 600   # 10 min hard lockout duration

    # ─── NTA Gateway — Working Hours Login Restriction ────────────────────────
    # Block logins outside defined hours — prevents off-hours attacks
    # 24h format, server timezone. Set ENFORCE=True in production .env
    LOGIN_ENFORCE_HOURS:      bool = False  # False = unrestricted (default dev)
    LOGIN_ALLOWED_HOUR_START: int  = 8      # 08:00 — earliest allowed login
    LOGIN_ALLOWED_HOUR_END:   int  = 22     # 22:00 — latest allowed login

    # ─── Email OTP — 2FA ──────────────────────────────────────────────────────
    # Requires SMTP config below. Set EMAIL_OTP_ENABLED=True after SMTP ready.
    EMAIL_OTP_ENABLED:         bool = True  # False = OTP step skipped
    EMAIL_OTP_EXPIRE_MINUTES:  int  = 10     # OTP TTL — expires after N min
    EMAIL_OTP_LENGTH:          int  = 6      # digits — 6 = 1M combinations
    EMAIL_OTP_MAX_ATTEMPTS:    int  = 3      # wrong tries before OTP invalidated
    EMAIL_OTP_RESEND_COOLDOWN: int  = 60     # seconds between resend requests
    EMAIL_OTP_MAX_REQUESTS: int = 3     # max OTP sends allowed
    EMAIL_OTP_RATE_WINDOW:  int = 600   # seconds (10 min window)
    EMAIL_OTP_MAX_REQUESTS_PER_IP: int = 10
    # ─── Metrics ──────────────────────────────────────────────────────────────
    METRICS_ENABLED: bool = True   # False = log-only mode (dev/CI)

    # ─── Properties ───────────────────────────────────────────────────────────

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parses comma-separated ALLOWED_ORIGINS into usable list."""
        if not self.ALLOWED_ORIGINS:
            return []
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def smtp_configured(self) -> bool:
        """True only when all SMTP fields are present — guards email sending."""
        return bool(
            self.SMTP_HOST
            and self.SMTP_USER
            and self.SMTP_PASS
            and self.FROM_EMAIL
        )   

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """
    Cached singleton — reads .env exactly once on startup.
    lru_cache ensures same object across entire app lifetime.
    """
    return Settings()