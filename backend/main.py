import logging
from fastapi import FastAPI
import uvicorn

from core.config import get_settings
from db.database import create_tables
from routers.router_registry import register_routers
from middlewares import register_middlewares

# Logging configuration — shows all INFO logs in console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Choose Your Own Adventure API",
        description="API to generate cool stories based on user input",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redocs",
    )

    register_middlewares(app)  # CORS + all exception handlers
    register_routers(app)      # all routers
    create_tables()            # ✅ app ke andar — startup pe DB ready

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)