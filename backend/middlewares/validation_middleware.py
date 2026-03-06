from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from utils.response_helper import error_response
from utils.constants import StatusCode, Messages


async def validation_exception_middleware(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Catches Pydantic 422 errors — returns first error as clean object.
    Single error object instead of array — cleaner for frontend consumption.
    """
    errors = exc.errors()

    # Return first error only — most relevant to the user
    first_error = errors[0]
    field = ".".join(str(loc) for loc in first_error["loc"])

    # Clean message — strip "Value error, " prefix added by Pydantic
    message = first_error["msg"].replace("Value error, ", "")

    return error_response(
        status_code=StatusCode.UNPROCESSABLE,
        message=Messages.VALIDATION_FAILED,
        data={
            "field": field,
            "message": message,
        },
    )