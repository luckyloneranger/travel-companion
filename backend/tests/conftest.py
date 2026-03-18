"""Shared fixtures for backend API tests.

Provides a fully-isolated test environment with:
- PostgreSQL database via testcontainers (real DB per test session)
- Mock LLM service (no real API calls)
- httpx.AsyncClient wired to the FastAPI app through ASGITransport
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import Request
from testcontainers.postgres import PostgresContainer

# ── Start PostgreSQL container BEFORE any app imports ─────────────────

_pg_container = PostgresContainer("postgres:16-alpine", driver="asyncpg")
_pg_container.start()
_pg_url = _pg_container.get_connection_url()

import atexit
atexit.register(_pg_container.stop)

# ── Set environment variables BEFORE any app imports ────────────────────
os.environ.update(
    {
        "DATABASE_URL": _pg_url,
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

from app.config import Settings
from app.db.models import Base, User
from app.db.repository import TripRepository
from app.dependencies import (
    get_current_user,
    get_db_session,
    get_directions_service,
    get_http,
    get_journey_orchestrator,
    get_llm_service,
    get_places_service,
    get_routes_service,
    get_settings,
    get_trip_repository,
    require_user,
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
        max_retries: int = 2,
    ) -> BaseModel:
        """Return a default instance of the requested schema.

        Attempts to build a minimal valid instance. Falls back to an empty
        model if construction fails (tests that actually exercise
        generate_structured use their own MagicMock overrides).
        """
        try:
            return schema.model_validate({"message": "mock structured response"})
        except Exception:
            # Most schemas don't have a 'message' field. Return a stub that
            # won't crash the test app fixture (individual tests mock at a
            # higher level anyway).
            return schema.model_construct()

    async def close(self) -> None:
        pass

    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list]:
        text = await self.generate(system_prompt, user_prompt, max_tokens, temperature)
        return (text, [])

    async def generate_structured_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> tuple[BaseModel, list]:
        result = await self.generate_structured(
            system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
        )
        return (result, [])


# ── Test Settings ──────────────────────────────────────────────────────


def _test_settings() -> Settings:
    """Return a Settings object with dummy keys and test DB URL."""
    _real_get_settings.cache_clear()
    return _real_get_settings()


# ── Database fixtures ──────────────────────────────────────────────────

# Engine and session factory are created lazily per event loop to avoid
# asyncpg "attached to a different loop" errors with pytest-asyncio.
_test_engine = None
_test_session_factory = None


def _get_test_engine():
    global _test_engine
    if _test_engine is None:
        _test_engine = create_async_engine(_pg_url, echo=False, future=True)
    return _test_engine


def _get_test_session_factory():
    global _test_session_factory
    if _test_session_factory is None:
        _test_session_factory = async_sessionmaker(
            _get_test_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _test_session_factory


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Create tables before each test and drop them after."""
    global _test_engine, _test_session_factory
    # Reset engine per test to bind to the current event loop
    if _test_engine is not None:
        await _test_engine.dispose()
    _test_engine = None
    _test_session_factory = None

    engine = _get_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed the mock user so foreign key constraints are satisfied
    async with _get_test_session_factory()() as session:
        session.add(User(
            id=_MOCK_USER["sub"],
            email=_MOCK_USER["email"],
            name=_MOCK_USER["name"],
            provider="test",
        ))
        await session.commit()

    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    _test_engine = None
    _test_session_factory = None


async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _get_test_session_factory()() as session:
        yield session


async def _override_get_trip_repository():
    async with _get_test_session_factory()() as session:
        yield TripRepository(session)


# ── Mock auth ─────────────────────────────────────────────────────────

_MOCK_USER = {"sub": "test-user-id", "email": "test@example.com", "name": "Test User"}


async def _override_get_current_user(request: Request) -> dict | None:
    """Return mock user only when the test sends an X-Test-User header."""
    if request.headers.get("x-test-user"):
        return _MOCK_USER
    return None


async def _override_require_user(request: Request) -> dict:
    """Require the X-Test-User header; raise 401 otherwise (like real auth)."""
    user = await _override_get_current_user(request)
    if not user:
        from fastapi import HTTPException as _H
        raise _H(401, "Not authenticated")
    return user


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
    application.dependency_overrides[get_current_user] = _override_get_current_user
    application.dependency_overrides[require_user] = _override_require_user

    yield application

    application.dependency_overrides.clear()


# ── HTTP client fixture ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async test client that talks to the FastAPI app in-process."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
