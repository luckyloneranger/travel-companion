from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMService(ABC):
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> T:
        """Generate structured response validated against schema.

        Args:
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt for the LLM.
            schema: Pydantic model class to validate against.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature.
            max_retries: Number of retry attempts on validation failure.

        Returns:
            Validated Pydantic model instance.

        Raises:
            LLMValidationError: If validation fails after all retries.
        """

    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
