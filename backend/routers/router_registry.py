from fastapi import FastAPI, APIRouter

from core.config import get_settings
from utils.constants import RouterConfig
from routers.job_router import router as job_router
from routers.story_router import router as story_router

settings = get_settings()

# Add new router here only — nothing else changes
ROUTERS = [
    (story_router, RouterConfig.STORIES_PREFIX, [RouterConfig.STORIES_TAG]),
    (job_router,   RouterConfig.JOBS_PREFIX,    [RouterConfig.JOBS_TAG])
]

# Module level — built once on app startup
api_router = APIRouter(prefix=settings.API_PREFIX)

for router, prefix, tags in ROUTERS:
    api_router.include_router(router, prefix=prefix, tags=tags)


def register_routers(app: FastAPI) -> None:
    """Mounts the pre-built api_router onto the FastAPI app."""
    app.include_router(api_router)