from fastapi.responses import JSONResponse


def success_response(status_code: int, message: str, data=None) -> JSONResponse:
    """Standard success response — used by controllers only."""
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "message": message,
            "data": data,
        },
    )


def error_response(status_code: int, message: str, data=None) -> JSONResponse:
    """Standard error response — used by middlewares only."""
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "message": message,
            "data": data,
        },
    )