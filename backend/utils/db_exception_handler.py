from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from utils.constants import ErrorCode, Messages, StatusCode


def handle_integrity_error(e: Exception) -> None:
    """
    Converts SQLAlchemy IntegrityError into proper HTTPException.
    Call this in any service that does DB writes.
    """
    if not isinstance(e, IntegrityError):
        raise HTTPException(
            status_code=StatusCode.INTERNAL_SERVER_ERROR,
            detail={"code": ErrorCode.REGISTRATION_FAILED, "message": Messages.REGISTRATION_FAILED},
        )

    constraint = getattr(e.orig, "constraint_name", None) or str(e.orig).lower()

    if "uq_users_email" in constraint:
        raise HTTPException(
            status_code=StatusCode.BAD_REQUEST,
            detail={"code": ErrorCode.EMAIL_ALREADY_EXISTS, "message": Messages.EMAIL_ALREADY_EXISTS},
        )
    if "uq_users_username" in constraint:
        raise HTTPException(
            status_code=StatusCode.BAD_REQUEST,
            detail={"code": ErrorCode.USERNAME_ALREADY_EXISTS, "message": Messages.USERNAME_ALREADY_EXISTS},
        )

    raise HTTPException(
        status_code=StatusCode.INTERNAL_SERVER_ERROR,
        detail={"code": ErrorCode.REGISTRATION_FAILED, "message": Messages.REGISTRATION_FAILED},
    )