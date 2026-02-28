"""Centralized Azure OpenAI service for all LLM operations.

Provides high-level methods for chat completions with JSON and text responses.
All generators should use this service instead of direct OpenAI client calls.

Usage:
    from app.services.external import AzureOpenAIService
    
    service = AzureOpenAIService()
    
    # For JSON responses
    data = await service.chat_completion_json(
        system_prompt="You are a helpful assistant.",
        user_prompt="Generate a travel plan.",
    )
    
    # For text responses  
    text = await service.chat_completion(
        system_prompt="You are a helpful assistant.",
        user_prompt="Describe this place.",
    )
"""

import json
import logging
from typing import Any, Optional

from openai import AsyncAzureOpenAI

from app.core.clients import OpenAIClient
from app.config.tuning import AGENT

logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """Centralized service for Azure OpenAI operations.
    
    Provides high-level methods for chat completions with consistent
    error handling and configuration.
    
    Attributes:
        client: The shared AsyncAzureOpenAI client instance
        deployment: The Azure OpenAI deployment name
    """
    
    def __init__(self):
        """Initialize the service using the shared OpenAI client."""
        pass  # Uses OpenAIClient singleton
    
    @property
    def client(self) -> AsyncAzureOpenAI:
        """Get the shared OpenAI client."""
        return OpenAIClient.get_client()
    
    @property
    def deployment(self) -> str:
        """Get the deployment name."""
        return OpenAIClient.get_deployment()
    
    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Execute a chat completion and return text response.
        
        Args:
            system_prompt: The system prompt setting behavior
            user_prompt: The user prompt with the request
            max_tokens: Optional max tokens (defaults to AGENT.max_tokens)
            
        Returns:
            The assistant's response text
            
        Raises:
            ValueError: If response is empty
        """
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=max_tokens or AGENT.max_tokens,
        )
        
        if not response.choices:
            raise ValueError("LLM returned empty choices array")
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        return content

    async def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """Execute a chat completion and return parsed JSON response.
        
        Uses OpenAI's JSON mode for guaranteed valid JSON output.
        
        Args:
            system_prompt: The system prompt setting behavior
            user_prompt: The user prompt with the request
            max_tokens: Optional max tokens (defaults to AGENT.max_tokens)
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            ValueError: If response is empty or invalid JSON
        """
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens or AGENT.max_tokens,
        )
        
        if not response.choices:
            raise ValueError("LLM returned empty choices array")
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        return json.loads(content)
