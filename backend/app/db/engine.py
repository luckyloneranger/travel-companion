import logging
import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import Settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _build_connect_args(database_url: str) -> dict:
    """Build connection args, enabling SSL for remote PostgreSQL hosts."""
    if "localhost" in database_url or "127.0.0.1" in database_url:
        return {}
    # Remote host — enable SSL (required by Azure, Supabase, etc.)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    return {"ssl": ssl_ctx}


def get_engine(settings: Settings):
    global _engine
    if _engine is None:
        # Strip ssl=require from URL (asyncpg handles SSL via connect_args)
        url = settings.database_url.split("?")[0]
        _engine = create_async_engine(
            url,
            echo=settings.debug,
            future=True,
            connect_args=_build_connect_args(url),
        )
    return _engine


def get_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        engine = get_engine(settings)
        _session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_session(settings: Settings):
    """Async generator that yields a DB session."""
    factory = get_session_factory(settings)
    async with factory() as session:
        yield session


async def init_db(settings: Settings):
    """Create all tables."""
    from .models import Base

    engine = get_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


async def close_db():
    """Close the engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
