import uuid
import logging

from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse

from schemas.story_schema import CreateStoryRequest
from schemas.job_schema import StoryJobResponse
from services.job_service import JobService
from services.story_service import StoryService
from utils.response_helper import success_response
from utils.constants import StatusCode, Messages

logger = logging.getLogger(__name__)


class StoryController:
    """Handles HTTP request/response logic for story-related endpoints."""

    def __init__(self, job_service: JobService, story_service: StoryService):
        """Injects JobService and StoryService via dependency injection."""
        self.job_service = job_service
        self.story_service = story_service

    def create_story(
        self,
        request: CreateStoryRequest,
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        """
        Creates a story job and queues LLM generation in background.
        Returns 202 immediately — client polls job status for completion.
        session_id generated server-side — never exposed to client.
        """
        # Server generates session_id — user never sees or manages this
        session_id = str(uuid.uuid4())

        job = self.job_service.create_job(
            theme=request.theme,
            session_id=session_id,
        )

        # Queue LLM story generation — request returns immediately
        background_tasks.add_task(
            self.job_service.process_story_job,
            job_id=job.job_id,
            theme=request.theme,
            session_id=session_id,
        )

        return success_response(
            status_code=StatusCode.ACCEPTED,
            message=Messages.JOB_ACCEPTED,
            data=StoryJobResponse.model_validate(job).model_dump(mode="json"),
        )

    def get_complete_story(self, story_id: int) -> JSONResponse:
        """Fetches a complete story with all nodes by story ID."""
        story = self.story_service.get_complete_story(story_id)
        return success_response(
            status_code=StatusCode.OK,
            message=Messages.STORY_FETCHED,
            data=story.model_dump(mode="json"),
        )