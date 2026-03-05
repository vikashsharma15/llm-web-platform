import uuid
import logging
from typing import Optional

from fastapi import Cookie, Response, BackgroundTasks, status
from fastapi.responses import JSONResponse

from schemas.story import CreateStoryRequest, StoryResponse
from schemas.job import StoryJobResponse
from services.job_service import JobService
from services.story_service import StoryService
from middlewares.response_formatter import format_response

logger = logging.getLogger(__name__)


def get_session_id(session_id: Optional[str] = Cookie(None)) -> str:
    if not session_id:
        return str(uuid.uuid4())
    return session_id


class StoryController:

    def __init__(self, job_service: JobService, story_service: StoryService):
        self.job_service = job_service
        self.story_service = story_service

    def create_story(
        self,
        request: CreateStoryRequest,
        background_tasks: BackgroundTasks,
        response: Response,
        session_id: str,
    ) -> JSONResponse:
        response.set_cookie(key="session_id", value=session_id, httponly=True)

        try:
            job = self.job_service.create_job(theme=request.theme, session_id=session_id)
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            return format_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to create story job",
            )

        background_tasks.add_task(
            self.job_service.process_story_job,
            job_id=job.job_id,
            theme=request.theme,
            session_id=session_id,
        )

        return format_response(
            status_code=status.HTTP_202_ACCEPTED,
            message="Story job created successfully",
            data=StoryJobResponse.model_validate(job).model_dump(mode="json"),
        )

    def get_complete_story(self, story_id: int) -> JSONResponse:
        try:
            story = self.story_service.get_complete_story(story_id)
            return format_response(
                status_code=status.HTTP_200_OK,
                message="Story fetched successfully",
                data=story.model_dump(mode="json"),
            )
        except ValueError as e:
            return format_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=str(e),
            )
        except Exception as e:
            logger.error(f"Error fetching story {story_id}: {e}")
            return format_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to fetch story",
            )