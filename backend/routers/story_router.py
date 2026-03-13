from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from controllers.story_controller import StoryController
from dependencies import get_story_controller, require_active_user
from models.user import User
from schemas.story_schema import CreateStoryRequest
from utils.constants import StatusCode

router = APIRouter()


@router.post("/create", status_code=StatusCode.ACCEPTED)
async def create_story(                            
    request:          CreateStoryRequest,
    background_tasks: BackgroundTasks,
    current_user:     User            = Depends(require_active_user),
    controller:       StoryController = Depends(get_story_controller),
) -> JSONResponse:
    """
    Queue story generation as background job.
    Returns job_id immediately — poll /jobs/{job_id} for status.
    """
    return await controller.create_story(          
        request=request,
        background_tasks=background_tasks,
        current_user=current_user,
    )


@router.get("/{story_id}/complete", status_code=StatusCode.OK)
async def get_complete_story(                       
    story_id:     int,
    current_user: User            = Depends(require_active_user),
    controller:   StoryController = Depends(get_story_controller),
) -> JSONResponse:
    """
    Fetch complete story with all nodes.
    Only owner can access — 403 for others.
    """
    return await controller.get_complete_story(     
        story_id=story_id,
        current_user=current_user,
    )