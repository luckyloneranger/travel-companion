import json
import logging
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from .base import LLMService

logger = logging.getLogger(__name__)


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
        schema: type[BaseModel],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Generate structured JSON response matching schema."""
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
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON from Gemini response: %s", e)
            raise
        except Exception as e:
            logger.error("Gemini generate_structured failed: %s", e)
            raise

    async def close(self) -> None:
        """Cleanup resources."""
        pass
