from fastapi import APIRouter, Depends, BackgroundTasks, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.story import CreateStoryRequest
from controllers.story_controller import StoryController, get_session_id
from services.job_service import JobService
from services.story_service import StoryService


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db)


def get_story_service(db: Session = Depends(get_db)) -> StoryService:
    return StoryService(db)


router = APIRouter(prefix="/stories", tags=["Stories"])


@router.post("/create", status_code=202)
def create_story(
    request: CreateStoryRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session_id: str = Depends(get_session_id),
    job_service: JobService = Depends(get_job_service),
    story_service: StoryService = Depends(get_story_service),
) -> JSONResponse:
    controller = StoryController(job_service, story_service)
    return controller.create_story(
        request=request,
        background_tasks=background_tasks,
        response=response,
        session_id=session_id,
    )


@router.get("/{story_id}/complete", status_code=200)
def get_complete_story(
    story_id: int,
    job_service: JobService = Depends(get_job_service),
    story_service: StoryService = Depends(get_story_service),
) -> JSONResponse:
    controller = StoryController(job_service, story_service)
    return controller.get_complete_story(story_id=story_id)