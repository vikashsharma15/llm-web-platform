from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from middlewares.response_formatter import format_response


# Pointer #9 — Reusable middleware
# Sirf ek baar register karo main.py mein
# Poore app mein har route pe automatically kaam karega
async def validation_exception_middleware(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return format_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation failed",
        data=errors,
    )