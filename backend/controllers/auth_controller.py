from fastapi import Request
from fastapi.responses import JSONResponse

from models.user import User
from schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from services.auth_service import AuthService
from utils.constants import ErrorCode, Messages, StatusCode
from utils.exceptions import raise_http_error       
from utils.response_helper import success_response


class AuthController:
    """HTTP layer only — request/response, no business logic."""

    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    async def register(self, request: RegisterRequest, http_request: Request) -> JSONResponse:
        ip   = getattr(http_request.state, "client_ip", None)
        user = await self.auth_service.register(request, ip)

        return success_response(
            status_code=StatusCode.CREATED,
            message=Messages.USER_REGISTERED,
            data=user,
        )

    async def login(self, request: LoginRequest, http_request: Request) -> JSONResponse:
        ip         = getattr(http_request.state, "client_ip", None)
        token_data = await self.auth_service.login(request, ip)

        return success_response(
            status_code=StatusCode.OK,
            message=Messages.LOGIN_SUCCESS,
            data=token_data,
        )

    async def verify_otp(self, email: str, otp: str) -> JSONResponse:
        result = await self.auth_service.verify_otp(email, otp)

        return success_response(
            status_code=StatusCode.OK,
            message=Messages.OTP_VERIFIED,
            data=result,
        )

    async def refresh(self, request: RefreshRequest) -> JSONResponse:
        token_data = await self.auth_service.refresh(request)

        return success_response(
            status_code=StatusCode.OK,
            message=Messages.TOKEN_REFRESHED,
            data=token_data,
        )

    async def logout(self, http_request: Request, current_user: User) -> JSONResponse:
        auth_header = http_request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            raise_http_error(          # ← fix 1+2: consistent + no missing import
                StatusCode.UNAUTHORIZED,
                ErrorCode.TOKEN_INVALID,
                Messages.TOKEN_INVALID,
            )

        token = auth_header[7:]
        await self.auth_service.logout(token, current_user.id)

        return success_response(
            status_code=StatusCode.OK,
            message=Messages.LOGOUT_SUCCESS,
            data=None,
        )

    async def me(self, current_user: User) -> JSONResponse:  
        data = await self.auth_service.get_me(current_user) 

        return success_response(
            status_code=StatusCode.OK,
            message=Messages.USER_FETCHED,
            data=data,
        )