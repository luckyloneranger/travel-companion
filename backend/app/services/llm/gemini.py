import json
import logging
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from .base import LLMService
from .exceptions import LLMValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiLLMService(LLMService):
    """Google Gemini LLM service using the google-genai SDK."""

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = genai.Client(api_key=api_key)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )
            return response.text or ""
        except Exception as e:
            logger.error("Gemini generate failed: %s", e)
            raise

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> T:
        """Generate structured JSON response matching schema.

        Validates the response against the Pydantic schema and retries
        on validation or JSON parsing errors up to max_retries times.

        Raises:
            LLMValidationError: If validation fails after all retries.
        """
        last_errors: list[str] = []

        for attempt in range(1 + max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_json_schema=schema.model_json_schema(),
                    ),
                )
                content = response.text or "{}"
                raw = json.loads(content)
                return schema.model_validate(raw)
            except ValidationError as e:
                last_errors = [str(err) for err in e.errors()]
                logger.warning(
                    "Schema validation failed (attempt %d/%d): %s",
                    attempt + 1, 1 + max_retries, e,
                )
                continue
            except json.JSONDecodeError as e:
                last_errors = [str(e)]
                logger.warning(
                    "JSON parse failed (attempt %d/%d): %s",
                    attempt + 1, 1 + max_retries, e,
                )
                continue
            except Exception as e:
                logger.error("Gemini generate_structured failed: %s", e)
                raise

        raise LLMValidationError(schema.__name__, last_errors, 1 + max_retries)

    async def close(self) -> None:
        """Cleanup resources."""
        pass
