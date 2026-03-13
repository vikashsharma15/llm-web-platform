from typing import Any
from fastapi.responses import JSONResponse


def success_response(
    status_code: int,
    message: str,
    data: Any = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data":    data,      # None is fine, frontend handles it
        },
    )


def error_response(
    status_code: int,
    message: str,
    code: Any = None,
    data: Any = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "success": False,
        "message": message,
    }
    if code is not None:
        content["code"] = code.value if hasattr(code, "value") else str(code)
    if data is not None:
        content["data"] = data

    return JSONResponse(status_code=status_code, content=content)