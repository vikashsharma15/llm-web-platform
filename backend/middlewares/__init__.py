from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from middlewares.exception_middleware import (
    db_exception_middleware,
    http_exception_middleware,
    global_exception_middleware,
)
from middlewares.validation_middleware import validation_exception_middleware
from middlewares.timing_middleware import RequestTimingMiddleware


def register_middlewares(app: FastAPI) -> None:
    """
    Registers all middleware + exception handlers.
    Called once in create_app() — order is significant.

    Middleware stack (Starlette processes bottom-up on request):
        1. RequestTimingMiddleware   ← outermost — times full request including handlers
        2. CORSMiddleware            ← handles preflight OPTIONS before routing

    Exception handlers (FastAPI processes most-specific first):
        RequestValidationError → 422 with field + message + error code
        HTTPException          → 4xx/5xx with request_id
        SQLAlchemyError        → mapped DB error (409/503/504/400/500)
        Exception              → catch-all 500

    Why lazy settings inside function:
        Avoids module-level get_settings() — safer for testing and import order.
    """
    from core.config import get_settings
    settings = get_settings()

    # Timing — outermost, measures full request lifecycle
    app.add_middleware(RequestTimingMiddleware)

    # CORS — before routing, handles OPTIONS preflight
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],  # frontend readable
    )

    # Exception handlers — specific before generic
    app.add_exception_handler(RequestValidationError, validation_exception_middleware)
    app.add_exception_handler(HTTPException,          http_exception_middleware)
    app.add_exception_handler(SQLAlchemyError,        db_exception_middleware)
    app.add_exception_handler(Exception,              global_exception_middleware)