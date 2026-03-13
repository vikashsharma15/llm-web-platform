import asyncio
import uuid
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import (
    SQLAlchemyError,
    OperationalError,    # DB connection lost / unavailable
    IntegrityError,      # unique constraint, FK violation
    DataError,           # wrong data type for column
    DBAPIError,          # low-level driver timeout / generic DB error
)

from utils.response_helper import error_response
from utils.constants import StatusCode, Messages, ErrorCode

logger = logging.getLogger(__name__)

# Module-level — lru_cache means this is effectively free after first call
from core.config import get_settings
settings = get_settings()


def _get_request_id(request: Request) -> str:
    return getattr(
        request.state,
        "request_id",
        request.headers.get("X-Request-ID", str(uuid.uuid4()))
    )

def _get_client_ip(request: Request) -> str:
    return getattr(request.state, "client_ip", "unknown")
# ─── DB Exception Handler ─────────────────────────────────────────────────────

async def db_exception_middleware(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Maps SQLAlchemy exceptions to HTTP responses.

    Mapping:
        IntegrityError   → 409 Conflict        (duplicate email, FK violation)
        OperationalError → 503 Unavailable      (DB connection lost / unreachable)
        DBAPIError       → 504 Gateway Timeout  (driver-level timeout)
        asyncio.Timeout  → 504 Gateway Timeout  (async query timeout)
        DataError        → 400 Bad Request      (value wrong type for column)
        everything else  → 500 Internal Error

    Security: raw SQL detail never reaches client — full detail in logs only.
    Observability: structured extra dict — ELK / Datadog / Grafana Loki ready.
    """
    request_id = _get_request_id(request)

    # Structured log — parseable by ELK, Datadog, Loki
    logger.error(
        "DB error",
        extra={
            "request_id":  request_id,
            "method":      request.method,
            "url":         str(request.url),        # str() — safe for all loggers
            "error_type":  type(exc).__name__,
            "error_detail": str(exc),
        },
        exc_info=True,   # full traceback in logs
    )

    if isinstance(exc, IntegrityError):
        status_code = StatusCode.CONFLICT
        message     = Messages.DB_CONFLICT
        code        = ErrorCode.DB_CONFLICT

    elif isinstance(exc, OperationalError):
        status_code = StatusCode.SERVICE_UNAVAILABLE
        message     = Messages.DB_UNAVAILABLE
        code        = ErrorCode.DB_UNAVAILABLE

    elif isinstance(exc, (DBAPIError, asyncio.TimeoutError)):
        status_code = StatusCode.GATEWAY_TIMEOUT
        message     = Messages.DB_TIMEOUT
        code        = ErrorCode.DB_TIMEOUT

    elif isinstance(exc, DataError):
        status_code = StatusCode.BAD_REQUEST
        message     = Messages.DB_DATA_ERROR
        code        = ErrorCode.DB_ERROR

    else:
        status_code = StatusCode.SERVER_ERROR
        message     = Messages.DB_ERROR
        code        = ErrorCode.DB_ERROR

    response = error_response(
        status_code=status_code,
        message=message,
        code=code,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ─── HTTP Exception Handler ───────────────────────────────────────────────────

async def http_exception_middleware(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = _get_request_id(request)

    log_extra = {
        "request_id": request_id,
        "method": request.method,
        "url": str(request.url),
        "status": exc.status_code,
        "detail": exc.detail,
    }

    if exc.status_code >= 500:
        logger.error("HTTP 5xx", extra=log_extra)
    elif exc.status_code in (403, 429):
        logger.warning(f"HTTP {exc.status_code}", extra=log_extra)
    else:
        logger.info(f"HTTP {exc.status_code}", extra=log_extra)

    code = None
    message = None
    data = None

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code")
        message = exc.detail.get("message", Messages.SERVER_ERROR)
        data = exc.detail.get("data")

    else:
        message = str(exc.detail)

    response = error_response(
        status_code=exc.status_code,
        message=message,
        code=code,
        data=data,
    )

    response.headers["X-Request-ID"] = request_id

    if exc.headers:
        for key, value in exc.headers.items():
            response.headers[key] = value

    return response

# ─── Global Catch-All Handler ─────────────────────────────────────────────────

async def global_exception_middleware(request: Request, exc: Exception) -> JSONResponse:
    """
    Last line of defense — catches anything that slipped past all other handlers.

    Production: returns generic 500, never exposes exception detail.
    Debug mode (DEBUG=True in .env): includes type + message for dev.

    Always logs full traceback — exc_info=True ensures stack trace in logs.
    """
    request_id = _get_request_id(request)

    logger.error(
        "Unhandled exception",
        extra={
            "request_id":   request_id,
            "method":       request.method,
            "url":          str(request.url),
            "error_type":   type(exc).__name__,
            "error_detail": str(exc),
        },
        exc_info=True,
    )

    data = (
        {"type": type(exc).__name__, "detail": str(exc)}
        if settings.DEBUG
        else None
    )

    response = error_response(
        status_code=StatusCode.SERVER_ERROR,
        message=Messages.SERVER_ERROR,
        code=ErrorCode.SERVER_ERROR,
        data=data,
    )
    response.headers["X-Request-ID"] = request_id
    return response