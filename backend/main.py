import logging
import logging.config
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.config import get_settings
from core.redis_client import init_redis, close_redis
from db.database import create_tables
from routers.router_registry import register_routers
from middlewares import register_middlewares

settings = get_settings()


# ─── Logging Setup ────────────────────────────────────────────────────────────
# Must run before any logger.getLogger() call
# JSON-style format — ELK / Datadog / Loki parseable
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# Silence noisy third-party loggers in production
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(
    logging.DEBUG if settings.DEBUG else logging.WARNING   # uvicorn access log only in DEBUG
)

logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup + shutdown — replaces deprecated @app.on_event.
    Order matters:
        Startup:  DB tables → Redis → ready
        Shutdown: Redis close → done
    """
    # ── Startup ──
    logger.info(f"Starting {settings.APP_TITLE} v{settings.APP_VERSION}")

    # 1. DB tables — idempotent, safe to call every startup
    await create_tables()
    logger.info("Database tables ready")

    # 2. Redis — MUST be before any request is served
    await init_redis()

    logger.info(
        f"Application ready  host={settings.HOST} "
        f"port={settings.PORT} debug={settings.DEBUG}"
    )

    yield   # ← app serves requests here

    # ── Shutdown ──
    await close_redis()
    logger.info("Application shutdown complete")


# ─── App Factory ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Creates and configures FastAPI app.
    All config driven from .env — nothing hardcoded here.

    Docs:
        DEBUG=True  → /docs + /redocs available
        DEBUG=False → docs disabled in production (security best practice)
    """
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs"    if settings.DEBUG else None,
        redoc_url="/redocs" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    register_middlewares(app)
    register_routers(app)

    return app


app = create_app()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,           # reload only in DEBUG — never in production
        log_level="debug" if settings.DEBUG else "info",
    )