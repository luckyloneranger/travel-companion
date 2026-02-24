"""Shared HTTP client pool for external APIs.

Provides managed httpx.AsyncClient instances for Google APIs,
ensuring proper resource management and connection pooling.

Usage:
    from app.core.clients import HTTPClientPool
    
    # Get clients for API calls
    places_client = HTTPClientPool.get_places_client()
    routes_client = HTTPClientPool.get_routes_client()
    
    # On app shutdown
    await HTTPClientPool.close_all()
"""

import asyncio
from typing import Optional

import httpx


class HTTPClientPool:
    """Manages shared HTTP clients for Google APIs.
    
    Provides connection pooling and lifecycle management for HTTP clients
    used by Google Places and Routes services.
    
    Handles event loop changes (e.g., between tests) by tracking the loop
    and recreating clients when the loop changes.
    """
    
    _places_client: Optional[httpx.AsyncClient] = None
    _routes_client: Optional[httpx.AsyncClient] = None
    _event_loop_id: Optional[int] = None
    
    # Default timeout for API calls
    DEFAULT_TIMEOUT = 30.0
    
    @classmethod
    def _check_event_loop(cls) -> bool:
        """Check if event loop changed and reset clients if so.
        
        Returns:
            bool: True if clients were reset due to loop change
        """
        try:
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
        except RuntimeError:
            # No running loop - can't check
            return False
        
        if cls._event_loop_id is not None and cls._event_loop_id != current_loop_id:
            # Event loop changed - reset clients without trying to close
            # (closing would fail on the old loop)
            cls._places_client = None
            cls._routes_client = None
            cls._event_loop_id = current_loop_id
            return True
        
        cls._event_loop_id = current_loop_id
        return False
    
    @classmethod
    def get_places_client(cls) -> httpx.AsyncClient:
        """Get the HTTP client for Google Places API.
        
        Creates a new client if none exists, if existing one is closed,
        or if the event loop has changed.
        
        Returns:
            httpx.AsyncClient: The shared Places API client
        """
        cls._check_event_loop()
        if cls._places_client is None or cls._places_client.is_closed:
            cls._places_client = httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT)
        return cls._places_client
    
    @classmethod
    def get_routes_client(cls) -> httpx.AsyncClient:
        """Get the HTTP client for Google Routes API.
        
        Creates a new client if none exists, if existing one is closed,
        or if the event loop has changed.
        
        Returns:
            httpx.AsyncClient: The shared Routes API client
        """
        cls._check_event_loop()
        if cls._routes_client is None or cls._routes_client.is_closed:
            cls._routes_client = httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT)
        return cls._routes_client
    
    @classmethod
    async def close_all(cls) -> None:
        """Close all HTTP clients.
        
        Should be called on application shutdown to properly release resources.
        """
        if cls._places_client and not cls._places_client.is_closed:
            await cls._places_client.aclose()
            cls._places_client = None
        if cls._routes_client and not cls._routes_client.is_closed:
            await cls._routes_client.aclose()
            cls._routes_client = None
        cls._event_loop_id = None
    
    @classmethod
    def reset(cls) -> None:
        """Reset client references without closing.
        
        Useful for testing. Use close_all() in production.
        """
        cls._places_client = None
        cls._routes_client = None
        cls._event_loop_id = None
