"""Core infrastructure for shared clients and services.

This module provides centralized:
- API clients (OpenAI, HTTP)
- Service registry for dependency injection

Usage:
    from app.core import OpenAIClient, HTTPClientPool, registry
    
    # Get shared OpenAI client
    client = OpenAIClient.get_client()
    deployment = OpenAIClient.get_deployment()
    
    # Get shared services
    places = registry.get_places()
    routes = registry.get_routes()
"""

from app.core.clients import OpenAIClient, HTTPClientPool
from app.core.registry import ServiceRegistry

# Backward compatibility alias
services = ServiceRegistry
registry = ServiceRegistry

__all__ = [
    "OpenAIClient",
    "HTTPClientPool",
    "ServiceRegistry",
    "services",  # Deprecated alias
    "registry",
]
