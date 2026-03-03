from fastapi import Depends

from app.config import Settings
from app.config.settings import get_settings as _get_settings
from app.db.engine import get_session as _get_db_session
from app.db.repository import TripRepository


def get_settings() -> Settings:
    return _get_settings()


async def get_db_session(settings: Settings = Depends(_get_settings)):
    async for session in _get_db_session(settings):
        yield session


async def get_trip_repository(session=Depends(get_db_session)):
    yield TripRepository(session)
