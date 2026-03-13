from fastapi import status
from enum import Enum


class StatusCode:
    OK                  = status.HTTP_200_OK
    CREATED             = status.HTTP_201_CREATED
    ACCEPTED            = status.HTTP_202_ACCEPTED
    BAD_REQUEST         = status.HTTP_400_BAD_REQUEST
    UNAUTHORIZED        = status.HTTP_401_UNAUTHORIZED
    FORBIDDEN           = status.HTTP_403_FORBIDDEN
    NOT_FOUND           = status.HTTP_404_NOT_FOUND
    CONFLICT            = status.HTTP_409_CONFLICT
    UNPROCESSABLE       = status.HTTP_422_UNPROCESSABLE_ENTITY
    TOO_MANY_REQUESTS   = status.HTTP_429_TOO_MANY_REQUESTS
    SERVER_ERROR        = status.HTTP_500_INTERNAL_SERVER_ERROR
    SERVICE_UNAVAILABLE = status.HTTP_503_SERVICE_UNAVAILABLE
    GATEWAY_TIMEOUT     = status.HTTP_504_GATEWAY_TIMEOUT


class RouterConfig:
    AUTH_PREFIX    = "/auth"
    JOBS_PREFIX    = "/jobs"
    STORIES_PREFIX = "/stories"
    AUTH_TAG       = "Auth"
    JOBS_TAG       = "Jobs"
    STORIES_TAG    = "Stories"


class ErrorCode(str, Enum):
    """
    Machine-readable error codes — frontend i18n + client-side handling.
    str + Enum → serializes as plain string in JSON automatically.

    Usage: raise HTTPException(detail={"code": ErrorCode.INVALID_EMAIL, ...})
    Frontend: if (error.code === 'invalid_email') show translated message
    """
    # ─── Auth ─────────────────────────────────────────────────────────────────
    INVALID_CREDENTIALS     = "invalid_credentials"
    EMAIL_ALREADY_EXISTS    = "email_already_exists"
    USERNAME_ALREADY_EXISTS = "username_already_exists"
    ACCOUNT_DISABLED        = "account_disabled"
    ACCOUNT_LOCKED          = "account_locked"
    TOKEN_INVALID           = "token_invalid"
    TOKEN_EXPIRED           = "token_expired"
    TOKEN_BLACKLISTED       = "token_blacklisted"
    UNAUTHORIZED            = "unauthorized"
    FORBIDDEN               = "forbidden"
    ADMIN_REQUIRED          = "admin_required"
    USER_NOT_FOUND          = "user_not_found"

    # ─── OTP ──────────────────────────────────────────────────────────────────
    OTP_INVALID             = "otp_invalid"
    OTP_EXPIRED             = "otp_expired"
    OTP_MAX_ATTEMPTS        = "otp_max_attempts"
    OTP_COOLDOWN            = "otp_cooldown"
    OTP_REQUIRED            = "otp_required"
    OTP_RATE_LIMITED        = "otp_rate_limited"

    # ─── Validation ───────────────────────────────────────────────────────────
    INVALID_EMAIL           = "invalid_email"
    PASSWORD_TOO_SHORT      = "password_too_short"
    PASSWORD_TOO_LONG       = "password_too_long"
    PASSWORD_TOO_WEAK       = "password_too_weak"
    FIELD_REQUIRED          = "field_required"
    FIELD_INVALID           = "field_invalid"
    INVALID_THEME           = "invalid_theme"

    # ─── Resources ────────────────────────────────────────────────────────────
    NOT_FOUND               = "not_found"
    CONFLICT                = "conflict"

    # ─── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMITED            = "rate_limited"

    # ─── Jobs / Stories ───────────────────────────────────────────────────────
    JOB_NOT_FOUND           = "job_not_found"
    JOB_FAILED              = "job_failed"
    STORY_NOT_FOUND         = "story_not_found"

    # ─── Infrastructure ───────────────────────────────────────────────────────
    DB_ERROR                = "db_error"
    DB_CONFLICT             = "db_conflict"
    DB_UNAVAILABLE          = "db_unavailable"
    DB_TIMEOUT              = "db_timeout"
    SERVER_ERROR            = "server_error"
    SERVICE_UNAVAILABLE     = "service_unavailable" 
    VALIDATION_FAILED       = "validation_failed"


class Messages:
    # ─── Auth ─────────────────────────────────────────────────────────────────
    USER_REGISTERED         = "User registered successfully"
    LOGIN_SUCCESS           = "Login successful"
    TOKEN_REFRESHED         = "Token refreshed successfully"
    LOGOUT_SUCCESS          = "Logged out successfully"
    USER_FETCHED            = "User fetched successfully"
    EMAIL_ALREADY_EXISTS    = "Email already registered"
    EMAIL_ALREADY_VERIFIED  = "Email verified successfully"
    USERNAME_ALREADY_EXISTS = "Username already taken"
    INVALID_CREDENTIALS     = "Invalid email or password"
    ACCOUNT_DISABLED        = "Account is disabled"
    ADMIN_REQUIRED          = "Admin access required"
    USER_NOT_FOUND          = "User not found"

    # ─── OTP ──────────────────────────────────────────────────────────────────
    OTP_SENT                = "OTP sent to your email"
    OTP_VERIFIED            = "OTP verified successfully"
    OTP_INVALID             = "Invalid OTP"
    OTP_EXPIRED             = "OTP has expired. Please request a new one"
    OTP_MAX_ATTEMPTS        = "Too many wrong attempts. Please request a new OTP"
    OTP_COOLDOWN            = "Please wait before requesting another OTP"
    OTP_REQUIRED            = "OTP verification required"
    OTP_RATE_LIMITED        = "Too many OTP requests. Please try again later"

    # ─── Jobs ─────────────────────────────────────────────────────────────────
    JOB_FETCHED             = "Job fetched successfully"
    JOB_ACCEPTED            = "Story job accepted, processing in background"
    JOB_NOT_FOUND           = "Job not found"
    JOB_FAILED              = "Job processing failed"

    # ─── Stories ──────────────────────────────────────────────────────────────
    STORY_FETCHED           = "Story fetched successfully"
    STORY_NOT_FOUND         = "Story not found"
    STORY_NODES_NOT_FOUND   = "No nodes found for this story"
    STORY_ROOT_NOT_FOUND    = "Root node not found for this story"

    # ─── DB errors ────────────────────────────────────────────────────────────
    DB_ERROR                = "Database error occurred"
    DB_CONFLICT             = "Resource already exists or constraint violated"
    DB_UNAVAILABLE          = "Database is temporarily unavailable"
    DB_TIMEOUT              = "Database request timed out"
    DB_DATA_ERROR           = "Invalid data format"

    # ─── Generic ──────────────────────────────────────────────────────────────
    SERVER_ERROR            = "Something went wrong"
    SERVICE_UNAVAILABLE = "Service temporarily unavailable"
    EMAIL_SERVICE_UNAVAILABLE = "Email service is temporarily unavailable"
    VALIDATION_FAILED       = "Validation failed"