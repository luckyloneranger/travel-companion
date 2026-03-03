import json
import logging
from typing import Any

import openai
from pydantic import BaseModel

from .base import LLMService

logger = logging.getLogger(__name__)

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
        schema: type[BaseModel],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Generate structured JSON response matching schema."""
        json_system_prompt = f"{system_prompt}\n\nYou must respond with valid JSON."
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
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON from Azure OpenAI response: %s", e)
            raise
        except openai.OpenAIError as e:
            logger.error("Azure OpenAI generate_structured failed: %s", e)
            raise

    async def close(self) -> None:
        """Cleanup resources."""
        await self.client.close()
