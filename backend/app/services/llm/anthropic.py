import logging
from typing import Any

import anthropic
from pydantic import BaseModel

from .base import LLMService

logger = logging.getLogger(__name__)


class AnthropicLLMService(LLMService):
    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error("Anthropic generate failed: %s", e)
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
        tool_definition = {
            "name": "submit",
            "description": "Submit structured response",
            "input_schema": schema.model_json_schema(),
        }
        try:
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                tools=[tool_definition],
                tool_choice={"type": "tool", "name": "submit"},
            )
            for block in response.content:
                if block.type == "tool_use":
                    return block.input
            logger.warning("No tool_use block found in Anthropic response")
            return {}
        except anthropic.APIError as e:
            logger.error("Anthropic generate_structured failed: %s", e)
            raise

    async def close(self) -> None:
        """Cleanup resources."""
        await self.client.close()
