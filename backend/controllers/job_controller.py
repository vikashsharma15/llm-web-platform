import logging

from fastapi import status
from fastapi.responses import JSONResponse

from schemas.job import StoryJobResponse
from services.job_service import JobService
from middlewares.response_formatter import format_response

logger = logging.getLogger(__name__)


class JobController:

    def __init__(self, job_service: JobService):
        self.job_service = job_service

    def get_job_status(self, job_id: str) -> JSONResponse:
        try:
            job = self.job_service.get_job(job_id)
            return format_response(
                status_code=status.HTTP_200_OK,
                message="Job fetched successfully",
                data=StoryJobResponse.model_validate(job).model_dump(mode="json"),
            )
        except ValueError as e:
            return format_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=str(e),
            )
        except Exception as e:
            logger.error(f"Error fetching job {job_id}: {e}")
            return format_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to fetch job",
            )