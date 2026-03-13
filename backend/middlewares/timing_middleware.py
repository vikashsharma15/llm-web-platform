import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths to skip — no timing noise for health/metrics endpoints
_SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Request timing + access log middleware.

    Logs every request with:
        - method, path, status, duration_ms
        - request_id (from header or generated)
        - Adds X-Request-ID + X-Response-Time headers to every response

    Log format (structured — ELK/Datadog/Loki parseable):
        INFO  "POST /api/auth/login 200 84ms request_id=xxxx"
        extra: {method, path, status, duration_ms, request_id}

    Timing threshold warnings:
        > 1000ms → warning  (slow endpoint, investigate)
        > 3000ms → error    (severely slow, likely a problem)

    Skips paths in _SKIP_PATHS — no noise for health checks / metrics scrapes.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip timing for health/metrics endpoints
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start      = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        status      = response.status_code

        log_extra = {
            "request_id":   request_id,
            "method":       request.method,
            "path":         request.url.path,
            "status":       status,
            "duration_ms":  duration_ms,
        }

        # Log level based on duration — surface slow endpoints automatically
        msg = f"{request.method} {request.url.path} {status} {duration_ms}ms"

        if duration_ms > 3000:
            logger.error(f"SLOW REQUEST {msg}", extra=log_extra)
        elif duration_ms > 1000:
            logger.warning(f"SLOW REQUEST {msg}", extra=log_extra)
        elif status >= 500:
            logger.error(msg, extra=log_extra)
        elif status >= 400:
            logger.warning(msg, extra=log_extra)
        else:
            logger.info(msg, extra=log_extra)

        # Inject correlation headers into every response
        response.headers["X-Request-ID"]    = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response