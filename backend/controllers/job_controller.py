from fastapi import status
from fastapi.responses import JSONResponse

from schemas.job_schema import StoryJobResponse
from services.job_service import JobService
from middlewares.response_formatter import success_response


class JobController:
    """
    Handles HTTP request/response logic for job-related endpoints.
    Does not contain business logic — delegates to JobService.
    """

    def __init__(self, job_service: JobService):
        """
        Injects JobService via dependency injection.
        Controller has no direct access to DB.
        """
        self.job_service = job_service

    def get_job_status(self, job_id: str) -> JSONResponse:
        """
        Fetches the current status of a story generation job by job_id.
        Returns job details including status, story_id, and error if any.
        Raises 404 via JobService if job not found.
        """
        job = self.job_service.get_job(job_id)
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Job fetched successfully",
            data=StoryJobResponse.model_validate(job).model_dump(mode="json"),
        )