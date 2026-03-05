from fastapi import APIRouter
from routers.job_router import router as job_router
from routers.story_router import router as story_router

api_router = APIRouter(prefix="/api")

api_router.include_router(job_router)
api_router.include_router(story_router)