"""
utils/http_errors.py

Single reusable helper for raising structured HTTPExceptions.

Why this exists in utils/:
  - Used by any service that raises HTTP errors (AuthService, StoryService, etc.)
  - Keeps error shape consistent across the entire codebase
  - Without this, every service duplicates the same raise HTTPException(...) boilerplate

Usage:
    from utils.http_errors import raise_http_error

    raise_http_error(StatusCode.NOT_FOUND, ErrorCode.USER_NOT_FOUND, Messages.USER_NOT_FOUND)
"""

from fastapi import HTTPException

from utils.constants import ErrorCode, Messages, StatusCode


def raise_http_error(status: int, code: ErrorCode, message: str) -> None:
    """
    Raise a structured HTTPException caught by http_exception_middleware.

    All services use this — never construct HTTPException manually.
    Keeps error shape consistent: {"code": ..., "message": ...}
    """
    raise HTTPException(
        status_code=status,
        detail={"code": code, "message": message},
    )