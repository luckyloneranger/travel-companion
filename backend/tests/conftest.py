"""Shared fixtures for backend API tests.

Provides a fully-isolated test environment with:
- In-memory SQLite database (via StaticPool so the schema survives across connections)
- Mock LLM service (no real API calls)
- httpx.AsyncClient wired to the FastAPI app through ASGITransport
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

# ── Set environment variables BEFORE any app imports ────────────────────
os.environ.update(
    {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4-test",
        "AZURE_OPENAI_API_VERSION": "2024-02-15-preview",
        "GOOGLE_PLACES_API_KEY": "test-places-key",
        "GOOGLE_ROUTES_API_KEY": "test-routes-key",
        "APP_ENV": "test",
        "DEBUG": "false",
        "LOG_LEVEL": "WARNING",
    }
)

# Clear the cached settings so the test env vars take effect
from app.config.settings import get_settings as _real_get_settings

_real_get_settings.cache_clear()

from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.models import Base
from app.db.repository import TripRepository
from app.dependencies import (
    get_db_session,
    get_directions_service,
    get_http,
    get_journey_orchestrator,
    get_llm_service,
    get_places_service,
    get_routes_service,
    get_settings,
    get_trip_repository,
)
from app.main import create_app
from app.services.llm.base import LLMService


# ── Mock LLM Service ───────────────────────────────────────────────────


class MockLLMService(LLMService):
    """LLM service that returns canned responses for tests."""

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        return json.dumps({"message": "mock llm response"})

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        return {"message": "mock structured response"}

    async def close(self) -> None:
        pass


# ── Test Settings ──────────────────────────────────────────────────────


def _test_settings() -> Settings:
    """Return a Settings object with dummy keys and test DB URL."""
    _real_get_settings.cache_clear()
    return _real_get_settings()


# ── Database fixtures ──────────────────────────────────────────────────

_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
    future=True,
)

_test_session_factory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Create tables before each test and drop them after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


async def _override_get_trip_repository():
    async with _test_session_factory() as session:
        yield TripRepository(session)


# ── Application fixture ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def app():
    """Create a fresh FastAPI app with dependency overrides for testing."""
    application = create_app()

    # Override all dependencies that touch external services or the DB
    application.dependency_overrides[get_settings] = _test_settings
    application.dependency_overrides[get_llm_service] = lambda: MockLLMService()
    application.dependency_overrides[get_http] = lambda: AsyncMock()
    application.dependency_overrides[get_places_service] = lambda: AsyncMock()
    application.dependency_overrides[get_routes_service] = lambda: AsyncMock()
    application.dependency_overrides[get_directions_service] = lambda: AsyncMock()
    application.dependency_overrides[get_db_session] = _override_get_db_session
    application.dependency_overrides[get_trip_repository] = _override_get_trip_repository

    yield application

    application.dependency_overrides.clear()


# ── HTTP client fixture ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async test client that talks to the FastAPI app in-process."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
