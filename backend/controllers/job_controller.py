from fastapi.responses import JSONResponse

from models.user import User
from services.job_service import JobService
from utils.constants import Messages, StatusCode
from utils.response_helper import success_response


class JobController:
    """HTTP layer only — request/response, no business logic."""

    def __init__(self, job_service: JobService) -> None:
        self.job_service = job_service

    async def get_job_status(self, job_id: str, current_user: User) -> JSONResponse:
        data = await self.job_service.get_job(job_id, current_user.id)

        return success_response(
            status_code=StatusCode.OK,
            message=Messages.JOB_FETCHED,
            data=data,             
        )