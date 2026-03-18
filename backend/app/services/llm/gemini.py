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
            return (response.text or "").replace("\x00", "")
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
                content = (response.text or "{}").replace("\x00", "")
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

    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list["SearchCitation"]]:
        """Generate text with Google Search grounding."""
        from .base import SearchCitation
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
            text = (response.text or "").replace("\x00", "")
            citations = self._extract_citations(response)
            return (text, citations)
        except Exception as e:
            logger.warning("Gemini search grounding failed, falling back: %s", e)
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
    ) -> tuple[T, list["SearchCitation"]]:
        """Generate structured JSON with Google Search grounding."""
        from .base import SearchCitation
        last_errors: list[str] = []
        all_citations: list[SearchCitation] = []

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
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                )
                content = (response.text or "{}").replace("\x00", "")
                all_citations = self._extract_citations(response)
                raw = json.loads(content)
                return (schema.model_validate(raw), all_citations)
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
                logger.warning("Gemini search+structured failed, falling back: %s", e)
                result = await self.generate_structured(
                    system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
                )
                return (result, [])

        raise LLMValidationError(schema.__name__, last_errors, 1 + max_retries)

    @staticmethod
    def _extract_citations(response) -> list["SearchCitation"]:
        """Extract SearchCitation list from Gemini grounding metadata."""
        from .base import SearchCitation
        citations: list[SearchCitation] = []
        try:
            candidates = getattr(response, "candidates", None)
            if not candidates:
                return []
            metadata = getattr(candidates[0], "grounding_metadata", None)
            if not metadata:
                return []
            chunks = getattr(metadata, "grounding_chunks", None) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if web:
                    citations.append(SearchCitation(
                        url=getattr(web, "uri", ""),
                        title=getattr(web, "title", ""),
                    ))
        except Exception:
            pass
        return citations

    async def close(self) -> None:
        """Cleanup resources."""
        pass
