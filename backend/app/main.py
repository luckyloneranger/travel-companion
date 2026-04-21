import logging
import sys
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

# Some LLM providers (Gemini) occasionally output very large integers in JSON.
# Raise Python's default int-string conversion limit to avoid ValueError at parse time.
sys.set_int_max_str_digits(100000)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.http import get_http_client, close_http_client
from app.core.middleware import RequestTracingMiddleware, RequestLoggingFilter
from app.routers import auth, places, cities, journeys, admin, sharing

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
    logger.info("Regular Everyday Traveller started")
    yield
    await close_db()
    await close_http_client()
    logger.info("Regular Everyday Traveller stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="RET — Content Platform",
        version="3.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )
    application.add_middleware(RequestTracingMiddleware)

    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    application.include_router(auth.router)
    application.include_router(cities.router)
    application.include_router(journeys.router)
    application.include_router(admin.router)
    application.include_router(sharing.router)
    application.include_router(places.router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "healthy",
            "version": "3.0.0",
            "llm_provider": settings.llm_provider,
        }

    @application.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def api_not_found(path: str):
        return JSONResponse(status_code=404, content={"detail": f"API endpoint not found: /api/{path}"})

    # Serve built frontend in production (single-container deployment)
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if (static_dir / "index.html").exists():
        application.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
