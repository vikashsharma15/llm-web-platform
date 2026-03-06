from fastapi import APIRouter, Depends, BackgroundTasks, Response
from fastapi.responses import JSONResponse

from schemas.story_schema import CreateStoryRequest
from controllers.story_controller import StoryController, get_session_id
from dependencies import get_story_controller
from utils.constants import StatusCode

router = APIRouter()


@router.post("/create", status_code=StatusCode.ACCEPTED)
def create_story(
    request: CreateStoryRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session_id: str = Depends(get_session_id),
    controller: StoryController = Depends(get_story_controller),
) -> JSONResponse:
    """Creates a story job and queues LLM generation in background."""
    return controller.create_story(
        request=request,
        background_tasks=background_tasks,
        response=response,
        session_id=session_id,
    )


@router.get("/{story_id}/complete", status_code=StatusCode.OK)
def get_complete_story(
    story_id: int,
    controller: StoryController = Depends(get_story_controller),
) -> JSONResponse:
    """Fetches complete story with all nodes by story_id."""
    return controller.get_complete_story(story_id=story_id)