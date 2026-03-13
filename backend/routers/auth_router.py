from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from schemas.auth import LoginRequest, OTPRequest, OTPVerifyRequest, RefreshRequest, RegisterRequest
from controllers.auth_controller import AuthController
from dependencies import get_auth_controller, require_active_user
from models.user import User
from utils.constants import StatusCode

router = APIRouter()


@router.post("/register", status_code=StatusCode.CREATED)
async def register(
    request:      RegisterRequest,
    http_request: Request,
    controller:   AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    """
    Register new account.
    Email must be unique. OTP sent to email for verification.
    """
    return await controller.register(request, http_request)


@router.post("/login", status_code=StatusCode.OK)
async def login(
    request:      LoginRequest,
    http_request: Request,
    controller:   AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    """
    Authenticate and get tokens.
    Returns access_token (60min) + refresh_token (7days) + expires_in.
    Rate limited — account locks after 5 failed attempts for 10 min.
    """
    return await controller.login(request, http_request)


@router.post("/request-otp", status_code=StatusCode.OK)
async def request_otp(
    request:    OTPRequest,
    controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    """
    Request OTP for email verification.
    Cooldown enforced — cannot resend within EMAIL_OTP_RESEND_COOLDOWN seconds.
    """
    return await controller.request_otp(request.email)


@router.post("/verify-otp", status_code=StatusCode.OK)
async def verify_otp(
    request:    OTPVerifyRequest,
    controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    """
    Submit OTP to verify email.
    Max 3 wrong attempts before OTP is invalidated.
    """
    return await controller.verify_otp(request.email, request.otp)


@router.post("/refresh", status_code=StatusCode.OK)
async def refresh(
    request:    RefreshRequest,
    controller: AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    """
    Refresh Token Rotation — new access_token + new refresh_token.
    Old refresh token immediately invalidated on use.
    Reusing old token = possible theft → all tokens revoked.
    """
    return await controller.refresh(request)


@router.post("/logout", status_code=StatusCode.OK)
async def logout(
    raw_request:  Request,
    current_user: User          = Depends(require_active_user),
    controller:   AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    """
    Logout — blacklists access token + revokes refresh token.
    Requires: Authorization: Bearer <access_token>
    """
    return await controller.logout(raw_request, current_user)


@router.get("/me", status_code=StatusCode.OK)
async def me(
    current_user: User          = Depends(require_active_user),
    controller:   AuthController = Depends(get_auth_controller),
) -> JSONResponse:
    """
    Current user profile.
    Requires: Authorization: Bearer <access_token>
    """
    return await  controller.me(current_user)