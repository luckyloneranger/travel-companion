import logging
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from .base import LLMService
from .exceptions import LLMValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


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
            return response.content[0].text.replace("\x00", "")
        except anthropic.APIError as e:
            logger.error("Anthropic generate failed: %s", e)
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
        on validation errors or missing tool_use blocks up to max_retries times.

        Raises:
            LLMValidationError: If validation fails after all retries.
        """
        tool_definition = {
            "name": "submit",
            "description": "Submit structured response",
            "input_schema": schema.model_json_schema(),
        }
        last_errors: list[str] = []

        for attempt in range(1 + max_retries):
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

                # Find tool_use block
                raw = None
                for block in response.content:
                    if block.type == "tool_use":
                        raw = block.input
                        break

                if raw is None:
                    last_errors = ["No tool_use block found in response"]
                    logger.warning(
                        "No tool_use block (attempt %d/%d)",
                        attempt + 1, 1 + max_retries,
                    )
                    continue

                return schema.model_validate(raw)
            except ValidationError as e:
                last_errors = [str(err) for err in e.errors()]
                logger.warning(
                    "Schema validation failed (attempt %d/%d): %s",
                    attempt + 1, 1 + max_retries, e,
                )
                continue
            except anthropic.APIError as e:
                logger.error("Anthropic generate_structured failed: %s", e)
                raise

        raise LLMValidationError(schema.__name__, last_errors, 1 + max_retries)

    async def close(self) -> None:
        """Cleanup resources."""
        await self.client.close()
