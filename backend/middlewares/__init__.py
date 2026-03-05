from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from middlewares.request_validator import validation_exception_middleware
from middlewares.error_handler import db_exception_middleware, global_exception_middleware


# Pointer #2 #9 — Register karo sirf ek baar main.py mein
# app.register_middlewares(app) — bas itna kafi hai
def register_middlewares(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_middleware)
    app.add_exception_handler(SQLAlchemyError, db_exception_middleware)
    app.add_exception_handler(Exception, global_exception_middleware)