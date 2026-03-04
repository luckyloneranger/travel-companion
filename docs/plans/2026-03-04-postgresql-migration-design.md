# SQLite → PostgreSQL Migration Design

**Date:** 2026-03-04
**Status:** Approved

## Goal

Remove SQLite entirely. PostgreSQL everywhere: local dev (Docker), production (Azure), tests (testcontainers).

## Decisions

- **Local dev DB:** Docker PostgreSQL via docker-compose
- **Migrations:** Alembic with autogenerate
- **Tests:** testcontainers (real PostgreSQL per test session)
- **Approach:** Hard switch — no dual-driver support

## Dependencies

- **Remove:** `aiosqlite`
- **Add:** `asyncpg` (async PG driver), `alembic` (migrations), `testcontainers[postgres]` (test DB)

## Changes

### 1. Settings (`app/config/settings.py`)

Change `database_url` default from `sqlite+aiosqlite:///./trips.db` to `postgresql+asyncpg://postgres:postgres@localhost:5432/travelcompanion`.

### 2. Engine (`app/db/engine.py`)

No SQLite-specific code exists to remove. Works unchanged with asyncpg.

### 3. Alembic

- `alembic init --template async` inside `backend/`
- Configure `alembic/env.py` to import `Base.metadata` from `app.db.models`
- Generate initial migration: `alembic revision --autogenerate -m "initial schema"`
- Keep `create_all` in `init_db()` as safety net
- Production: run `alembic upgrade head` before app start

### 4. Local dev (`docker-compose.yml`)

PostgreSQL 16 container with volume persistence. Developers run `docker compose up -d db`.

### 5. Tests (`conftest.py`)

Replace in-memory SQLite + StaticPool with testcontainers PostgreSQL. Spins up a real PG container per test session, creates/drops tables per test.

### 6. Dockerfile

Remove aiosqlite. asyncpg installs via pip with no system deps.

### 7. SQLAlchemy Models

No changes. Current models use standard types (String, Text, Float, DateTime) — no SQLite-specific features.

## Files to modify

| File | Change |
|------|--------|
| `backend/requirements.txt` | Remove aiosqlite, add asyncpg + alembic + testcontainers |
| `backend/app/config/settings.py` | Change default DATABASE_URL |
| `backend/tests/conftest.py` | Replace SQLite with testcontainers PostgreSQL |
| `backend/alembic.ini` | New — Alembic config |
| `backend/alembic/env.py` | New — migration environment |
| `backend/alembic/versions/` | New — initial migration |
| `docker-compose.yml` | New — PostgreSQL for local dev |
| `Dockerfile` | No aiosqlite (already not needed) |
| `CLAUDE.md` | Update database references |
| `README.md` | Update setup instructions |
