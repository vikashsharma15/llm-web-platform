from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse

from models.user import User
from schemas.story_schema import CreateStoryRequest
from services.job_service import JobService
from services.story_service import StoryService
from utils.constants import Messages, StatusCode
from utils.response_helper import success_response


class StoryController:
    """HTTP layer only — request/response, no business logic."""

    def __init__(self, job_service: JobService, story_service: StoryService) -> None:
        self.job_service   = job_service
        self.story_service = story_service

    async def create_story(
        self,
        request:          CreateStoryRequest,
        background_tasks: BackgroundTasks,
        current_user:     User,
    ) -> JSONResponse:
        data = await self.job_service.create_job(   # ← dict ab service se aayega
            theme=request.theme,
            user_id=current_user.id,
        )

        background_tasks.add_task(
            self.job_service.process_story_job,
            job_id=data["job_id"],                  # ← dict access, not data.job_id
            theme=request.theme,
            user_id=current_user.id,
        )

        return success_response(
            status_code=StatusCode.ACCEPTED,
            message=Messages.JOB_ACCEPTED,
            data=data,                              # ← plain dict, no model_validate
        )

    async def get_complete_story(self, story_id: int, current_user: User) -> JSONResponse:
        data = await self.story_service.get_complete_story(story_id, current_user.id)

        return success_response(
            status_code=StatusCode.OK,
            message=Messages.STORY_FETCHED,
            data=data,                              # ← data, not undefined `story`
        )