import uuid
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from utils.response_helper import error_response
from utils.constants import StatusCode, Messages, ErrorCode

logger = logging.getLogger(__name__)

# Pydantic internal prefixes — stripped from user-facing messages
_PYDANTIC_PREFIXES = (
    "Value error, ",
    "value_error: ",
    "value error: ",
    "Assertion failed, ",
)

# Location parts that are Pydantic internals — stripped from field name
_SKIP_LOC_PARTS = {"body", "query", "path", "header", "cookie"}

# Maps Pydantic error type → ErrorCode — used for frontend i18n
_PYDANTIC_TYPE_TO_CODE: dict[str, ErrorCode] = {
    "missing":                    ErrorCode.FIELD_REQUIRED,
    "string_too_short":           ErrorCode.PASSWORD_TOO_SHORT,
    "string_too_long":            ErrorCode.PASSWORD_TOO_LONG,
    "value_error.email":          ErrorCode.INVALID_EMAIL,
    "string_pattern_mismatch":    ErrorCode.FIELD_INVALID,
    "value_error":                ErrorCode.FIELD_INVALID,
    "int_parsing":                ErrorCode.FIELD_INVALID,
    "bool_parsing":               ErrorCode.FIELD_INVALID,
}


def _clean_field(loc: tuple) -> str:
    """
    Builds clean field path from Pydantic loc tuple.

    Strips location type prefix (body/query/path/header/cookie).
    Joins remaining parts with dots for nested fields.

    Examples:
        ("body", "email")            → "email"
        ("body", "address", "city")  → "address.city"
        ("query", "page")            → "page"
        ("body", 0, "name")          → "0.name"
        ()                           → "unknown"
    """
    parts = [str(p) for p in loc if str(p) not in _SKIP_LOC_PARTS]
    if parts:
        return ".".join(parts)
    # Fallback — loc had only skip parts, use last element
    return str(loc[-1]) if loc else "unknown"


def _clean_message(msg: str) -> str:
    """
    Strips Pydantic-internal prefixes from error messages.

    Examples:
        "Value error, Password too short"  → "Password too short"
        "value_error: invalid email"       → "invalid email"
        "String should have at least..."   → unchanged (already user-friendly)
    """
    for prefix in _PYDANTIC_PREFIXES:
        if msg.startswith(prefix):
            return msg[len(prefix):]
    return msg


def _get_error_code(error: dict) -> str:
    """
    Maps Pydantic error type → machine-readable ErrorCode string.
    Falls back to FIELD_INVALID for unknown types.
    Used by frontend for i18n — e.g. show "Invalid email" in user's language.
    """
    pydantic_type = error.get("type", "")
    code = _PYDANTIC_TYPE_TO_CODE.get(pydantic_type, ErrorCode.FIELD_INVALID)
    return code.value   # return plain str — JSON serializable


async def validation_exception_middleware(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handles Pydantic 422 validation errors — production grade.

    Returns FIRST error only — one actionable error at a time.
    Logs ALL errors — full context in logs for debugging.

    Response shape:
        {
            "status_code": 422,
            "message": "Validation failed",
            "data": {
                "field":   "email",
                "message": "value is not a valid email address",
                "code":    "invalid_email"      ← frontend i18n key
            }
        }

    Edge cases:
        - Empty errors list           → generic validation_failed
        - loc has only skip parts     → last loc element used
        - Nested body fields          → "address.city" dot-joined
        - No loc                      → "unknown" field
        - Pydantic prefix in message  → stripped cleanly
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    errors     = exc.errors()

    # Structured log — ELK / Datadog / Grafana Loki ready
    logger.warning(
        "Validation failed",
        extra={
            "request_id":   request_id,
            "method":       request.method,
            "url":          str(request.url),   # str() — safe for all loggers
            "error_count":  len(errors),
            "errors":       errors,             # full list in logs — only first shown to client
        },
    )

    # Guard — empty errors (rare but Pydantic can surprise)
    if not errors:
        response = error_response(
            status_code=StatusCode.UNPROCESSABLE,
            message=Messages.VALIDATION_FAILED,
            code=ErrorCode.VALIDATION_FAILED,
            data={
                "field":   "unknown",
                "message": "Validation failed",
                "code":    ErrorCode.FIELD_INVALID.value,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response

    first   = errors[0]
    field   = _clean_field(tuple(first.get("loc", ())))
    message = _clean_message(first.get("msg", "Invalid value"))
    code    = _get_error_code(first)

    response = error_response(
        status_code=StatusCode.UNPROCESSABLE,
        message=Messages.VALIDATION_FAILED,
        code=ErrorCode.VALIDATION_FAILED,
        data={
            "field":   field,
            "message": message[:200],
            "code":    code,        # machine-readable — frontend i18n key
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response