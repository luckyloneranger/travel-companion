"""Tips generator for activity recommendations."""

import json
import logging
from typing import Optional

from openai import AsyncAzureOpenAI

from app.config.tuning import AGENT
from app.core.clients import OpenAIClient
from app.generators.tips.prompts import TIPS_SYSTEM_PROMPT, build_tips_prompt

logger = logging.getLogger(__name__)


class TipsGenerator:
    """Generator for activity tips using Azure OpenAI.
    
    Generates personalized, actionable tips for each activity
    in a travel itinerary.
    
    Usage:
        generator = TipsGenerator()
        tips = await generator.generate(schedule)
    """

    def __init__(self):
        """Initialize the tips generator."""
        pass  # Uses OpenAIClient singleton

    @property
    def client(self) -> AsyncAzureOpenAI:
        """Get the shared OpenAI client."""
        return OpenAIClient.get_client()

    @property
    def deployment(self) -> str:
        """Get the deployment name."""
        return OpenAIClient.get_deployment()

    async def generate(
        self,
        schedule: list[dict],
        destination: str = "",
        interests: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Generate helpful tips for each activity.

        Args:
            schedule: List of scheduled activities with times and place info.
                      Each dict should have: place_id, time_start, name, category
            destination: The city/destination name for contextual tips
            interests: User's interests for personalized tips

        Returns:
            Dictionary mapping place_id to tip text
        """
        if not schedule:
            return {}
        
        # Build prompt using the prompt module
        prompt, _ = build_tips_prompt(
            schedule,
            destination=destination,
            interests=interests,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": TIPS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=AGENT.max_tokens,
            )

            content = response.choices[0].message.content
            if not content:
                return {}
            
            data = json.loads(content)
            return data.get("tips", {})

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Tips generation failed: {e}")
            return {}
