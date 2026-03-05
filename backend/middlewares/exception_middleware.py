import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from middlewares.response_helper import error_response

logger = logging.getLogger(__name__)


async def db_exception_middleware(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Catches SQLAlchemy errors — returns 500 with DB error message."""
    logger.error(f"DB error on {request.url}: {exc}", exc_info=True)
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Database error occurred",
        data={"detail": str(exc)},
    )


async def http_exception_middleware(request: Request, exc: HTTPException) -> JSONResponse:
    """Catches HTTP exceptions (404, 403 etc) — returns proper status with message."""
    logger.warning(f"HTTP {exc.status_code} on {request.url}: {exc.detail}")
    return error_response(
        status_code=exc.status_code,
        message=exc.detail,
    )


async def global_exception_middleware(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches any unhandled exception — last line of defense.
    Shows error detail only in DEBUG mode, hides in production.
    """
    logger.error(f"Unhandled error on {request.url}: {type(exc).__name__}: {exc}", exc_info=True)

    from core.config import get_settings
    settings = get_settings()

    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Something went wrong",
        data={"detail": str(exc)} if settings.DEBUG else None,
    )