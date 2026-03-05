from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from middlewares.response_formatter import error_response


async def validation_exception_middleware(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Catches Pydantic validation errors (422) — formats into clean field-level error list.
    Overrides FastAPI's default validation error format.
    """
    # Extract field name and message from each validation error
    errors = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation failed",
        data=errors,
    )