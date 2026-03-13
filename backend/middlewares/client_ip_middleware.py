from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request


class ClientIPMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        forwarded = request.headers.get("X-Forwarded-For")

        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else None

        request.state.client_ip = ip

        response = await call_next(request)
        return response