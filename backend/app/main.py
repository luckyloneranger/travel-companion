"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.middleware import RequestTracingMiddleware, RequestLoggingFilter
from app.routers import itinerary_router, journey_router

# Configure logging with request ID support
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(request_id)s] %(levelname)s %(name)s: %(message)s",
)
# Add filter to root logger to include request_id
for handler in logging.root.handlers:
    handler.addFilter(RequestLoggingFilter())

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()
    logger.info(f"Starting Travel Companion API (env: {settings.app_env})")

    # Startup: Initialize any connections/resources here
    yield

    # Shutdown: Clean up shared resources
    from app.core import services
    await services.close_all()
    logger.info("Shutting down Travel Companion API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Travel Companion API",
        description="AI-powered travel itinerary generator using Azure OpenAI and Google APIs",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request tracing middleware
    app.add_middleware(RequestTracingMiddleware)

    # Include routers
    app.include_router(itinerary_router, prefix="/api", tags=["Itinerary"])
    app.include_router(journey_router, tags=["Journey"])

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
