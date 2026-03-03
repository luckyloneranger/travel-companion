from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


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
        schema: type[BaseModel],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Generate structured JSON response matching schema."""

    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
