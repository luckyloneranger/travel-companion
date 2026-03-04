# SQLite → PostgreSQL Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace SQLite with PostgreSQL everywhere — local dev, tests, and production.

**Architecture:** Swap aiosqlite for asyncpg driver, add Alembic for schema migrations, use testcontainers for real PostgreSQL in tests, docker-compose for local dev PostgreSQL.

**Tech Stack:** asyncpg, Alembic, testcontainers[postgres], PostgreSQL 16, Docker Compose

---

### Task 1: Update dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Update requirements.txt**

Replace the Database section and add to Testing section:

```
# Database
asyncpg>=0.29.0
sqlalchemy[asyncio]>=2.0.25
alembic>=1.13.0
```

And in Testing section, add:

```
testcontainers[postgres]>=4.0.0
```

Remove the line: `aiosqlite>=0.20.0`

**Step 2: Install new dependencies**

Run: `cd backend && source venv/bin/activate && pip install -r requirements.txt`
Expected: All packages install successfully, asyncpg and alembic available

**Step 3: Verify removal**

Run: `pip show aiosqlite`
Expected: Package not found (or still installed but no longer required — that's fine)

**Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps: replace aiosqlite with asyncpg, add alembic + testcontainers"
```

---

### Task 2: Add docker-compose for local PostgreSQL

**Files:**
- Create: `docker-compose.yml` (project root)

**Step 1: Create docker-compose.yml**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: travelcompanion
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

**Step 2: Start PostgreSQL**

Run: `docker compose up -d db`
Expected: PostgreSQL container starts, healthy

**Step 3: Verify connection**

Run: `docker compose exec db psql -U postgres -d travelcompanion -c "SELECT version();"`
Expected: Shows PostgreSQL 16.x version string

**Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "infra: add docker-compose with PostgreSQL for local dev"
```

---

### Task 3: Update settings default DATABASE_URL

**Files:**
- Modify: `backend/app/config/settings.py`

**Step 1: Change the database_url default**

In `backend/app/config/settings.py`, change:

```python
database_url: str = "sqlite+aiosqlite:///./trips.db"
```

to:

```python
database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/travelcompanion"
```

**Step 2: Commit**

```bash
git add backend/app/config/settings.py
git commit -m "config: change default DATABASE_URL to PostgreSQL"
```

---

### Task 4: Set up Alembic

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (directory)

**Step 1: Initialize Alembic**

Run: `cd backend && source venv/bin/activate && alembic init -t async alembic`
Expected: Creates `alembic/` directory and `alembic.ini`

**Step 2: Configure alembic.ini**

In `backend/alembic.ini`, find the line:

```
sqlalchemy.url = driver://user:pass@localhost/dbname
```

Replace with:

```
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/travelcompanion
```

**Step 3: Configure alembic/env.py**

Replace the contents of `backend/alembic/env.py` with:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from settings (env vars), falling back to alembic.ini."""
    try:
        settings = get_settings()
        return settings.database_url
    except Exception:
        return config.get_main_option("sqlalchemy.url", "")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    engine = create_async_engine(get_url())
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 4: Generate initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial schema"`
Expected: Creates a migration file in `alembic/versions/` with create_table for users, trips, trip_shares

**Step 5: Run migration**

Run: `cd backend && alembic upgrade head`
Expected: Tables created in PostgreSQL (docker compose db must be running)

**Step 6: Verify tables exist**

Run: `docker compose exec db psql -U postgres -d travelcompanion -c "\dt"`
Expected: Shows users, trips, trip_shares, alembic_version tables

**Step 7: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add Alembic async migrations with initial schema"
```

---

### Task 5: Update tests to use testcontainers PostgreSQL

**Files:**
- Modify: `backend/tests/conftest.py`

**Step 1: Replace SQLite test database with testcontainers**

In `backend/tests/conftest.py`, replace the database-related code.

Change the env vars section — remove the `DATABASE_URL` override:

```python
os.environ.update(
    {
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
```

Remove these lines (SQLite engine + session factory):

```python
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
```

Remove the `StaticPool` import.

Add testcontainers setup at module level (after the imports):

```python
from testcontainers.postgres import PostgresContainer

# Start PostgreSQL container for test session (stays alive across all tests)
_pg_container = PostgresContainer("postgres:16-alpine", driver="asyncpg")
_pg_container.start()
_pg_url = _pg_container.get_connection_url()

# Set DATABASE_URL so app settings pick it up
os.environ["DATABASE_URL"] = _pg_url

import atexit
atexit.register(_pg_container.stop)

_test_engine = create_async_engine(_pg_url, echo=False, future=True)
_test_session_factory = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)
```

**Step 2: Run tests**

Run: `cd backend && source venv/bin/activate && pytest -x -q`
Expected: All 164 tests pass (Docker must be running for testcontainers)

**Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: replace SQLite with testcontainers PostgreSQL"
```

---

### Task 6: Clean up engine.py

**Files:**
- Modify: `backend/app/db/engine.py`

**Step 1: Remove any SQLite-specific handling**

The current `engine.py` has no SQLite-specific code, but verify there are no `check_same_thread` or `StaticPool` references. If clean, no changes needed.

**Step 2: Verify app starts**

Run: `cd backend && source venv/bin/activate && uvicorn app.main:app --port 8000` (with docker compose db running)
Expected: App starts, connects to PostgreSQL, "Database tables initialized" in logs

**Step 3: Smoke test**

Run: `curl -s http://localhost:8000/health | python3 -m json.tool`
Expected: `{"status": "healthy", ...}`

**Step 4: Commit (if any changes)**

```bash
git commit -m "refactor: clean up engine.py for PostgreSQL-only"
```

---

### Task 7: Update Dockerfile

**Files:**
- Modify: `Dockerfile`

**Step 1: Verify Dockerfile works without aiosqlite**

The Dockerfile just runs `pip install -r requirements.txt` — since aiosqlite is already removed from requirements.txt, no Dockerfile changes needed. Verify the build still works.

Run: `docker build -t travel-companion .`
Expected: Build succeeds

**Step 2: Commit (if any changes needed)**

---

### Task 8: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Step 1: Update README.md**

In the Quick Start backend section, add PostgreSQL setup before the backend commands:

```markdown
### 0. Database

```bash
docker compose up -d db    # Start PostgreSQL
```
```

Update Prerequisites to include Docker.

Remove any SQLite references. Update the database_url env var description.

**Step 2: Update CLAUDE.md**

- Change Database description from "SQLAlchemy async + aiosqlite" to "SQLAlchemy async + asyncpg (PostgreSQL)"
- Update the `DATABASE_URL` in Environment Variables section
- Add Alembic migration commands to Build & Run Commands
- Add `docker-compose.yml` to Architecture section

**Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: update README and CLAUDE.md for PostgreSQL migration"
```

---

### Task 9: Final verification

**Step 1: Run full test suite**

Run: `cd backend && source venv/bin/activate && pytest -x -q`
Expected: All 164 tests pass

**Step 2: TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: Clean (no frontend changes, but verify nothing broke)

**Step 3: Docker build**

Run: `docker build -t travel-companion .`
Expected: Build succeeds

**Step 4: End-to-end smoke test**

```bash
docker compose up -d db
cd backend && source venv/bin/activate
alembic upgrade head
uvicorn app.main:app --port 8000
# In another terminal:
curl -s http://localhost:8000/health
```

Expected: Health check returns healthy

---

## Execution Order

Tasks 1-5 are sequential (each depends on the previous).
Tasks 6-8 can be done in parallel after Task 5.
Task 9 is the final verification after everything else.
