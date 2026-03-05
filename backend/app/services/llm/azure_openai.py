import json
import logging
from typing import Any, TypeVar

import openai
from pydantic import BaseModel, ValidationError

from .base import LLMService
from .exceptions import LLMValidationError

logger = logging.getLogger(__name__)

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
        try:
            params = self._build_params(max_tokens, temperature)
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **params,
            )
            return response.choices[0].message.content or ""
        except openai.OpenAIError as e:
            logger.error("Azure OpenAI generate failed: %s", e)
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
        json_system_prompt = f"{system_prompt}\n\nYou must respond with valid JSON."
        last_errors: list[str] = []

        for attempt in range(1 + max_retries):
            try:
                params = self._build_params(
                    max_tokens, temperature,
                    response_format={"type": "json_object"},
                )
                response = await self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": json_system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    **params,
                )
                content = response.choices[0].message.content or "{}"
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
                logger.error("Azure OpenAI generate_structured failed: %s", e)
                raise

        raise LLMValidationError(schema.__name__, last_errors, 1 + max_retries)

    async def close(self) -> None:
        """Cleanup resources."""
        await self.client.close()
