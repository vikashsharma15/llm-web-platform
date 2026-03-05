from fastapi import Depends
from sqlalchemy.orm import Session

from db.database import get_db
from services.job_service import JobService
from services.story_service import StoryService
from controllers.job_controller import JobController
from controllers.story_controller import StoryController


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    """Injects DB session into JobService."""
    return JobService(db)


def get_story_service(db: Session = Depends(get_db)) -> StoryService:
    """Injects DB session into StoryService."""
    return StoryService(db)


def get_job_controller(
    job_service: JobService = Depends(get_job_service),
) -> JobController:
    """Injects JobService into JobController."""
    return JobController(job_service)


def get_story_controller(
    job_service: JobService = Depends(get_job_service),
    story_service: StoryService = Depends(get_story_service),
) -> StoryController:
    """Injects JobService and StoryService into StoryController."""
    return StoryController(job_service, story_service)