import json
import logging
from typing import Any

import openai
from pydantic import BaseModel

from .base import LLMService

logger = logging.getLogger(__name__)


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

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
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
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": json_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
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
