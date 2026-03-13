import logging
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.redis_client import get_redis
from core.token_store import TokenStore
from db.database import get_db
from models.user import User, UserRole

from repositories.user_repository import UserRepository
from services.job_service import JobService
from services.story_service import StoryService

from services.auth_service import AuthService
from controllers.job_controller import JobController
from controllers.story_controller import StoryController
from controllers.auth_controller import AuthController

from utils.jwt_handler import JWTHandler
from utils.constants import StatusCode, Messages, ErrorCode
from utils.exceptions import raise_http_error  # ← replaces manual HTTPException

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


# ─── Token Store Dependency ───────────────────────────────────────────────────

def get_token_store() -> TokenStore:
    return TokenStore(get_redis())


# ─── Core Auth Dependency ─────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
    token_store: TokenStore = Depends(get_token_store),
) -> User:
    if not credentials:
        raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.UNAUTHORIZED, "Authorization header missing")

    token   = credentials.credentials
    payload = JWTHandler.verify_token(token, expected_type="access")
    jti     = payload.get("jti")
    user_id = int(payload["sub"])

    if jti and await token_store.is_blacklisted(jti):
        raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.UNAUTHORIZED, Messages.OTP_INVALID)

    user = await UserRepository(db).get_by_id(user_id) 
    if not user:
        raise_http_error(StatusCode.UNAUTHORIZED, ErrorCode.USER_NOT_FOUND, Messages.USER_NOT_FOUND)

    if not user.is_active:
        raise_http_error(StatusCode.FORBIDDEN, ErrorCode.FORBIDDEN, Messages.ACCOUNT_DISABLED)

    return user


# ─── Role Guards ──────────────────────────────────────────────────────────────

async def require_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise_http_error(StatusCode.FORBIDDEN, ErrorCode.FORBIDDEN, Messages.ADMIN_REQUIRED)
    return current_user


# ─── Service Factories ────────────────────────────────────────────────────────

def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db)


def get_story_service(db: Session = Depends(get_db)) -> StoryService:
    return StoryService(db)


def get_auth_service(
    db: Session = Depends(get_db),
    token_store: TokenStore = Depends(get_token_store),
) -> AuthService:
    return AuthService(db, token_store)


# ─── Controller Factories ─────────────────────────────────────────────────────

def get_job_controller(
    job_service: JobService = Depends(get_job_service),
) -> JobController:
    return JobController(job_service)


def get_story_controller(
    job_service: JobService     = Depends(get_job_service),
    story_service: StoryService = Depends(get_story_service),
) -> StoryController:
    return StoryController(job_service, story_service)


def get_auth_controller(
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthController:
    return AuthController(auth_service)