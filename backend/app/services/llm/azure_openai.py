import asyncio
import json
import logging
from typing import Any, TypeVar

import openai
from pydantic import BaseModel, ValidationError

from .base import LLMService
from .exceptions import LLMValidationError, LLMContentFilterError

logger = logging.getLogger(__name__)

# Transient OpenAI errors worth retrying
_TRANSIENT_ERRORS = (openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError, openai.RateLimitError)
_API_MAX_RETRIES = 2
_API_RETRY_BASE_DELAY = 2.0


def _sanitize_content(text: str) -> str:
    """Remove null characters that corrupt non-ASCII text from LLM output."""
    return text.replace("\x00", "")


def _is_content_filter_error(error: openai.OpenAIError) -> bool:
    """Check if an OpenAI error is a content filter rejection."""
    if isinstance(error, openai.BadRequestError):
        error_body = getattr(error, "body", None)
        if isinstance(error_body, dict):
            error_detail = error_body.get("error", {})
            code = error_detail.get("code", "")
            inner = error_detail.get("innererror", {})
            inner_code = inner.get("code", "") if isinstance(inner, dict) else ""
            return code == "content_filter" or inner_code == "ResponsibleAIPolicyViolation"
    return False

T = TypeVar("T", bound=BaseModel)

# Models that only support temperature=1 and max_completion_tokens (not max_tokens)
_REASONING_MODEL_PREFIXES = ("o1", "o3", "gpt-5")


class AzureOpenAILLMService(LLMService):
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str,
    ) -> None:
        self.deployment = deployment
        self.client = openai.AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self._is_reasoning = any(
            deployment.lower().startswith(p) for p in _REASONING_MODEL_PREFIXES
        )

    def _build_params(
        self, max_tokens: int, temperature: float, **extra: Any,
    ) -> dict[str, Any]:
        """Build model params, omitting temperature for reasoning models."""
        params: dict[str, Any] = {
            "max_completion_tokens": max_tokens,
            **extra,
        }
        if not self._is_reasoning:
            params["temperature"] = temperature
        return params

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""
        params = self._build_params(max_tokens, temperature)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        for attempt in range(_API_MAX_RETRIES + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.deployment, messages=messages, **params,
                )
                return _sanitize_content(response.choices[0].message.content or "")
            except _TRANSIENT_ERRORS as e:
                if attempt < _API_MAX_RETRIES:
                    delay = _API_RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning("Transient OpenAI error (attempt %d/%d), retrying in %.1fs: %s", attempt + 1, _API_MAX_RETRIES + 1, delay, e)
                    await asyncio.sleep(delay)
                    continue
                logger.error("Azure OpenAI generate failed after %d attempts: %s", _API_MAX_RETRIES + 1, e)
                raise
            except openai.OpenAIError as e:
                if _is_content_filter_error(e):
                    logger.warning("Azure content filter rejected request: %s", e)
                    raise LLMContentFilterError(e) from e
                logger.error("Azure OpenAI generate failed: %s", e)
                raise
        raise RuntimeError("Unreachable")

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
        json_system_prompt = f"{system_prompt}\n\nYou must respond with valid JSON."
        last_errors: list[str] = []
        params = self._build_params(
            max_tokens, temperature,
            response_format={"type": "json_object"},
        )
        messages = [
            {"role": "system", "content": json_system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for attempt in range(1 + max_retries):
            try:
                response = await self._call_with_retry(messages, params)
                content = _sanitize_content(response.choices[0].message.content or "{}")
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
            except openai.OpenAIError as e:
                if _is_content_filter_error(e):
                    logger.warning("Azure content filter rejected structured request: %s", e)
                    raise LLMContentFilterError(e) from e
                logger.error("Azure OpenAI generate_structured failed: %s", e)
                raise

        raise LLMValidationError(schema.__name__, last_errors, 1 + max_retries)

    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list["SearchCitation"]]:
        """Generate text with web search grounding via Responses API."""
        from .base import SearchCitation
        try:
            params: dict[str, Any] = {
                "model": self.deployment,
                "tools": [{"type": "web_search"}],
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_output_tokens": max_tokens,
            }
            if not self._is_reasoning:
                params["temperature"] = temperature

            response = await self.client.responses.create(**params)
            text = _sanitize_content(response.output_text or "")
            citations = self._extract_response_citations(response)
            return (text, citations)
        except Exception as e:
            logger.warning("Azure search grounding failed, falling back: %s", e)
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
        """Generate structured JSON with web search via Responses API."""
        from .base import SearchCitation
        json_system_prompt = f"{system_prompt}\n\nYou must respond with valid JSON."
        last_errors: list[str] = []

        for attempt in range(1 + max_retries):
            try:
                params: dict[str, Any] = {
                    "model": self.deployment,
                    "tools": [{"type": "web_search"}],
                    "input": [
                        {"role": "system", "content": json_system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "schema": schema.model_json_schema(),
                            "name": schema.__name__,
                            "strict": False,
                        }
                    },
                    "max_output_tokens": max_tokens,
                }
                if not self._is_reasoning:
                    params["temperature"] = temperature

                response = await self.client.responses.create(**params)
                content = _sanitize_content(response.output_text or "{}")
                citations = self._extract_response_citations(response)
                raw = json.loads(content)
                return (schema.model_validate(raw), citations)
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
                if isinstance(e, openai.OpenAIError) and _is_content_filter_error(e):
                    raise LLMContentFilterError(e) from e
                logger.warning("Azure search+structured failed, falling back: %s", e)
                result = await self.generate_structured(
                    system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
                )
                return (result, [])

        raise LLMValidationError(schema.__name__, last_errors, 1 + max_retries)

    @staticmethod
    def _extract_response_citations(response) -> list["SearchCitation"]:
        """Extract citations from Responses API url_citation annotations."""
        from .base import SearchCitation
        citations: list[SearchCitation] = []
        try:
            for item in getattr(response, "output", []):
                if getattr(item, "type", "") != "message":
                    continue
                for block in getattr(item, "content", []):
                    for annotation in getattr(block, "annotations", []) or []:
                        if getattr(annotation, "type", "") == "url_citation":
                            citations.append(SearchCitation(
                                url=getattr(annotation, "url", ""),
                                title=getattr(annotation, "title", ""),
                            ))
        except Exception:
            pass
        return citations

    async def _call_with_retry(self, messages: list[dict], params: dict) -> Any:
        """Call the OpenAI API with retry on transient errors."""
        for attempt in range(_API_MAX_RETRIES + 1):
            try:
                return await self.client.chat.completions.create(
                    model=self.deployment, messages=messages, **params,
                )
            except _TRANSIENT_ERRORS as e:
                if attempt < _API_MAX_RETRIES:
                    delay = _API_RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning("Transient OpenAI error (attempt %d/%d), retrying in %.1fs: %s", attempt + 1, _API_MAX_RETRIES + 1, delay, e)
                    await asyncio.sleep(delay)
                    continue
                raise
        raise RuntimeError("Unreachable")

    async def close(self) -> None:
        """Cleanup resources."""
        await self.client.close()
