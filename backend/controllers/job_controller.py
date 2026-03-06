from fastapi.responses import JSONResponse

from schemas.job_schema import StoryJobResponse
from services.job_service import JobService
from utils.response_helper import success_response
from utils.constants import StatusCode, Messages


class JobController:
    """Handles HTTP request/response logic for job-related endpoints."""

    def __init__(self, job_service: JobService):
        """Injects JobService via dependency injection."""
        self.job_service = job_service

    def get_job_status(self, job_id: str) -> JSONResponse:
        """Fetches current status of a story generation job by job_id."""
        job = self.job_service.get_job(job_id)
        return success_response(
            status_code=StatusCode.OK,
            message=Messages.JOB_FETCHED,
            data=StoryJobResponse.model_validate(job).model_dump(mode="json"),
        )