import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.config import get_settings
from db.database import create_tables
from routers.router_registry import register_routers
from middlewares import register_middlewares

# Must be configured before any logger is used
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once on startup and shutdown — replaces deprecated on_event."""
    create_tables()
    logger.info("Application started successfully")
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Creates and configures FastAPI app — all config driven from .env."""
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,   # docs only in DEBUG mode
        redoc_url="/redocs" if settings.DEBUG else None, # redoc only in DEBUG mode
        lifespan=lifespan,
    )

    register_middlewares(app)
    register_routers(app)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,  # reload only in DEBUG mode
    )