import uuid
import logging
from typing import Optional

from fastapi import Cookie, Response, BackgroundTasks, status
from fastapi.responses import JSONResponse

from schemas.story_schema import CreateStoryRequest, StoryResponse
from schemas.job_schema import StoryJobResponse
from services.job_service import JobService
from services.story_service import StoryService
from middlewares.response_formatter import success_response

logger = logging.getLogger(__name__)


def get_session_id(session_id: Optional[str] = Cookie(None)) -> str:
    """
    Reads session_id from cookie.
    If not present, generates a new UUID as session_id.
    Used as a FastAPI dependency in the router.
    """
    if not session_id:
        return str(uuid.uuid4())
    return session_id


class StoryController:
    """
    Handles HTTP request/response logic for story-related endpoints.
    Does not contain business logic — delegates to services.
    """

    def __init__(self, job_service: JobService, story_service: StoryService):
        """
        Injects JobService and StoryService via dependency injection.
        Controller has no direct access to DB.
        """
        self.job_service = job_service
        self.story_service = story_service

    def create_story(
        self,
        request: CreateStoryRequest,
        background_tasks: BackgroundTasks,
        response: Response,
        session_id: str,
    ) -> JSONResponse:
        """
        Creates a story job and queues LLM generation in background.
        1. Sets session cookie on response.
        2. Creates a pending job via JobService.
        3. Adds story generation as a background task (non-blocking).
        4. Returns 202 Accepted with job details immediately.
        """
        # Set session cookie so frontend can track the user session
        response.set_cookie(key="session_id", value=session_id, httponly=True)

        # Create a pending job in DB — no LLM call yet
        job = self.job_service.create_job(
            theme=request.theme,
            session_id=session_id,
        )

        # Queue LLM story generation in background — request returns immediately
        background_tasks.add_task(
            self.job_service.process_story_job,
            job_id=job.job_id,
            theme=request.theme,
            session_id=session_id,
        )

        return success_response(
            status_code=status.HTTP_202_ACCEPTED,
            message="Story job accepted, processing in background",
            data=StoryJobResponse.model_validate(job).model_dump(mode="json"),
        )

    def get_complete_story(self, story_id: int) -> JSONResponse:
        """
        Fetches a complete story with all nodes by story ID.
        Delegates to StoryService — raises 404 if not found.
        """
        story = self.story_service.get_complete_story(story_id)
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Story fetched successfully",
            data=story.model_dump(mode="json"),
        )