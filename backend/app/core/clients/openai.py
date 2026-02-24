"""Centralized Azure OpenAI client.

Provides a singleton pattern for the Azure OpenAI client to avoid
creating multiple client instances across the application.

Usage:
    from app.core.clients import OpenAIClient
    
    client = OpenAIClient.get_client()
    deployment = OpenAIClient.get_deployment()
    
    response = await client.chat.completions.create(
        model=deployment,
        messages=[...],
    )
"""

from typing import Optional

from openai import AsyncAzureOpenAI

from app.config import get_settings


class OpenAIClient:
    """Singleton Azure OpenAI client factory.
    
    This class provides a single shared AsyncAzureOpenAI client instance
    that can be reused across the entire application, avoiding the overhead
    of creating multiple client connections.
    """
    
    _instance: Optional[AsyncAzureOpenAI] = None
    _deployment: Optional[str] = None
    
    @classmethod
    def get_client(cls) -> AsyncAzureOpenAI:
        """Get the shared AsyncAzureOpenAI client instance.
        
        Creates the client on first call, returns cached instance thereafter.
        
        Returns:
            AsyncAzureOpenAI: The shared client instance
        """
        if cls._instance is None:
            settings = get_settings()
            cls._instance = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            cls._deployment = settings.azure_openai_deployment
        return cls._instance
    
    @classmethod
    def get_deployment(cls) -> str:
        """Get the configured deployment name.
        
        Returns:
            str: The Azure OpenAI deployment name (e.g., 'gpt-4')
        """
        if cls._deployment is None:
            cls.get_client()  # Initialize if needed
        return cls._deployment  # type: ignore
    
    @classmethod
    def reset(cls) -> None:
        """Reset the client instance.
        
        Useful for testing or when settings change.
        """
        cls._instance = None
        cls._deployment = None
