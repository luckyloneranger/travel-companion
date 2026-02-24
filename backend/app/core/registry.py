"""Service registry for dependency injection.

Provides a central registry for shared service instances, enabling
consistent access to services throughout the application without
manual lifecycle management.

Usage:
    from app.core import registry
    
    # Get services (lazy initialization)
    places = registry.get_places()
    routes = registry.get_routes()
    
    # On app shutdown
    await registry.close_all()
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.external.google_places import GooglePlacesService
    from app.services.external.google_routes import GoogleRoutesService


class ServiceRegistry:
    """Central registry for shared service instances.
    
    Provides lazy initialization and lifecycle management for
    services that should be shared across the application.
    
    This pattern removes the need for _owns_* tracking in individual
    classes and centralizes resource cleanup.
    """
    
    _places: Optional["GooglePlacesService"] = None
    _routes: Optional["GoogleRoutesService"] = None
    
    @classmethod
    def get_places(cls) -> "GooglePlacesService":
        """Get the shared Google Places service.
        
        Creates the service on first call.
        
        Returns:
            GooglePlacesService: The shared Places service instance
        """
        if cls._places is None:
            from app.services.external.google_places import GooglePlacesService
            cls._places = GooglePlacesService()
        return cls._places
    
    @classmethod
    def get_routes(cls) -> "GoogleRoutesService":
        """Get the shared Google Routes service.
        
        Creates the service on first call.
        
        Returns:
            GoogleRoutesService: The shared Routes service instance
        """
        if cls._routes is None:
            from app.services.external.google_routes import GoogleRoutesService
            cls._routes = GoogleRoutesService()
        return cls._routes
    
    @classmethod
    async def close_all(cls) -> None:
        """Close all services and release resources.
        
        Should be called on application shutdown.
        """
        from app.core.clients.http import HTTPClientPool
        
        # Close HTTP clients (services use these)
        await HTTPClientPool.close_all()
        
        # Clear service references
        cls._places = None
        cls._routes = None
    
    @classmethod
    def reset(cls) -> None:
        """Reset all service references without closing.
        
        Useful for testing.
        """
        cls._places = None
        cls._routes = None


# Convenience alias for cleaner imports
services = ServiceRegistry
