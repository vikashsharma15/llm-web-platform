from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from schemas.story_schema import CreateStoryRequest
from controllers.story_controller import StoryController
from dependencies import get_story_controller
from utils.constants import StatusCode

router = APIRouter()


@router.post("/create", status_code=StatusCode.ACCEPTED)
def create_story(
    request: CreateStoryRequest,
    background_tasks: BackgroundTasks,
    controller: StoryController = Depends(get_story_controller),
) -> JSONResponse:
    """Creates a story job and queues LLM generation in background."""
    return controller.create_story(
        request=request,
        background_tasks=background_tasks,
    )


@router.get("/{story_id}/complete", status_code=StatusCode.OK)
def get_complete_story(
    story_id: int,
    controller: StoryController = Depends(get_story_controller),
) -> JSONResponse:
    """Fetches complete story with all nodes by story_id."""
    return controller.get_complete_story(story_id=story_id)