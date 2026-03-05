import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from middlewares.response_formatter import format_response

logger = logging.getLogger(__name__)


# Pointer #6 — DB errors globally caught
async def db_exception_middleware(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(f"DB error on {request.url}: {exc}")
    return format_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Database error occurred",
    )


# Pointer #2 — Any unhandled exception globally caught
async def global_exception_middleware(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return format_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Something went wrong",
    )