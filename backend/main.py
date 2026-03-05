from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import get_settings
from db.database import create_tables
from routers.api import api_router
from middlewares import register_middlewares

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Choose Your Own Adventure API",
        description="API to generate cool stories based on user input",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redocs",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pointer #2 #9 — ek line mein sab middlewares register
    register_middlewares(app)

    # Pointer #4 — sirf ek router
    app.include_router(api_router)

    create_tables()

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)