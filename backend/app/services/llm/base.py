from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class SearchCitation(BaseModel):
    """Normalized citation from any provider's web search."""
    url: str
    title: str
    cited_text: str = ""


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

    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list[SearchCitation]]:
        """Generate text with web search grounding.

        Default: falls back to generate() with empty citations.
        Providers override this to use native search tools.
        """
        text = await self.generate(system_prompt, user_prompt, max_tokens, temperature)
        return (text, [])

    async def generate_structured_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> tuple[T, list[SearchCitation]]:
        """Generate structured output with web search grounding.

        Default: falls back to generate_structured() with empty citations.
        Providers override this to use native search tools.
        """
        result = await self.generate_structured(
            system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
        )
        return (result, [])

    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
