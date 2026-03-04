import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.http import get_http_client, close_http_client
from app.core.middleware import RequestTracingMiddleware, RequestLoggingFilter
from app.routers import auth, export, trips, places
from app.routers.trips import shared_router

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    settings = get_settings()
    log_filter = RequestLoggingFilter()

    handler = logging.StreamHandler()
    handler.addFilter(log_filter)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.addHandler(handler)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    settings = get_settings()
    await get_http_client()

    from app.db.engine import close_db, init_db

    await init_db(settings)
    logger.info("Travel Companion V2 started")
    yield
    await close_db()
    await close_http_client()
    logger.info("Travel Companion V2 stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="Travel Companion AI",
        version="2.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestTracingMiddleware)

    application.include_router(auth.router)
    application.include_router(trips.router)
    application.include_router(shared_router)
    application.include_router(export.router)
    application.include_router(places.router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "healthy",
            "version": "2.0.0",
            "llm_provider": settings.llm_provider,
        }

    # Serve built frontend in production (single-container deployment)
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if (static_dir / "index.html").exists():
        application.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
