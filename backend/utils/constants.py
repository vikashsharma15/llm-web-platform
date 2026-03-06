from fastapi import status


class StatusCode:
    """HTTP status codes — use these instead of hardcoded integers."""

    # 2xx Success
    OK            = status.HTTP_200_OK
    CREATED       = status.HTTP_201_CREATED
    ACCEPTED      = status.HTTP_202_ACCEPTED

    # 4xx Client Errors
    BAD_REQUEST   = status.HTTP_400_BAD_REQUEST
    UNAUTHORIZED  = status.HTTP_401_UNAUTHORIZED
    FORBIDDEN     = status.HTTP_403_FORBIDDEN
    NOT_FOUND     = status.HTTP_404_NOT_FOUND
    UNPROCESSABLE = status.HTTP_422_UNPROCESSABLE_ENTITY

    # 5xx Server Errors
    SERVER_ERROR  = status.HTTP_500_INTERNAL_SERVER_ERROR


class RouterConfig:
    """Router prefix and tag constants — single source of truth."""

    JOBS_PREFIX    = "/jobs"
    STORIES_PREFIX = "/stories"

    JOBS_TAG    = "Jobs"
    STORIES_TAG = "Stories"


class Messages:
    """Response messages — consistent across all endpoints."""

    # ─── Job Success ───────────────────────────────────
    JOB_FETCHED  = "Job fetched successfully"
    JOB_ACCEPTED = "Story job accepted, processing in background"

    # ─── Job Errors ────────────────────────────────────
    JOB_NOT_FOUND = "Job not found"
    JOB_FAILED    = "Job processing failed"

    # ─── Story Success ─────────────────────────────────
    STORY_FETCHED = "Story fetched successfully"

    # ─── Story Errors ──────────────────────────────────
    STORY_NOT_FOUND       = "Story not found"
    STORY_NODES_NOT_FOUND = "No nodes found for this story"
    STORY_ROOT_NOT_FOUND  = "Root node not found for this story"

    # ─── DB Errors ─────────────────────────────────────
    DB_ERROR     = "Database error occurred"

    # ─── Server Errors ─────────────────────────────────
    SERVER_ERROR = "Something went wrong"

    # ─── Validation ────────────────────────────────────
    VALIDATION_FAILED = "Validation failed"