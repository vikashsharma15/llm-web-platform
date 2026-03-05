from fastapi.responses import JSONResponse


# Pointer #5 — Single source of truth for ALL responses
# Success ho ya error — poore app mein ek hi format
# Isko import karo jahan bhi response banana ho
def format_response(status_code: int, message: str, data=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "message": message,
            "data": data,
        },
    )