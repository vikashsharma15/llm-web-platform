from fastapi import FastAPI, APIRouter
from routers.job_router import router as job_router
from routers.story_router import router as story_router

# To add a new router, just add an entry here — nothing else changes
ROUTERS = [
    {"router": story_router, "prefix": "/stories", "tags": ["Stories"]},
    {"router": job_router,   "prefix": "/jobs",    "tags": ["Jobs"]},
]

# Module-level router — created once, not on every request
api_router = APIRouter(prefix="/api")

for route in ROUTERS:
    api_router.include_router(
        route["router"],
        prefix=route["prefix"],
        tags=route["tags"],
    )


def register_routers(app: FastAPI) -> None:
    """Registers all API routers onto the FastAPI app."""
    app.include_router(api_router)