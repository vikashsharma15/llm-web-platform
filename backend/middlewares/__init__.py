from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from core.config import get_settings
from middlewares.validation_middleware import validation_exception_middleware
from middlewares.exception_middleware import (
    db_exception_middleware,
    http_exception_middleware,
    global_exception_middleware,
)

settings = get_settings()


def register_middlewares(app: FastAPI) -> None:
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_middleware)
    app.add_exception_handler(HTTPException, http_exception_middleware)
    app.add_exception_handler(SQLAlchemyError, db_exception_middleware)
    app.add_exception_handler(Exception, global_exception_middleware)