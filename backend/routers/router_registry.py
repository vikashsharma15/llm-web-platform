from fastapi import FastAPI, APIRouter

from core.config import get_settings
from utils.constants import RouterConfig

settings = get_settings()


def register_routers(app: FastAPI) -> None:
    """
    Mounts all API routers onto the FastAPI app.
    To add a new router: import it and add one line to ROUTERS list.
    Nothing else changes anywhere.
    """
    from routers.auth_router  import router as auth_router
    from routers.story_router import router as story_router
    from routers.job_router   import router as job_router


    ROUTERS = [
        (auth_router,  RouterConfig.AUTH_PREFIX,    [RouterConfig.AUTH_TAG]),
        (story_router, RouterConfig.STORIES_PREFIX, [RouterConfig.STORIES_TAG]),
        (job_router,   RouterConfig.JOBS_PREFIX,    [RouterConfig.JOBS_TAG]),
    ]

    api_router = APIRouter(prefix=settings.API_PREFIX)

    for router, prefix, tags in ROUTERS:
        api_router.include_router(router, prefix=prefix, tags=tags)

    app.include_router(api_router)