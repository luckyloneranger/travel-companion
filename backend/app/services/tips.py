"""Tip generation service for travel activities.

Produces practical, insider tips for each activity in a day plan
using an LLM with local-knowledge prompts.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.prompts.loader import tips_prompts
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


def _format_schedule(activities: list[dict[str, Any]]) -> str:
    """Format a list of activity dicts into a readable schedule string."""
    lines: list[str] = []
    for act in activities:
        place = act.get("place", {})
        name = place.get("name", act.get("name", "Unknown"))
        place_id = place.get("place_id", act.get("place_id", ""))
        time_start = act.get("time_start", "")
        time_end = act.get("time_end", "")
        category = place.get("category", "")
        notes = act.get("notes", "")

        line = f"- [{time_start}-{time_end}] {name}"
        if category:
            line += f" ({category})"
        if notes:
            line += f" — {notes}"
        if place_id:
            line += f"  [ID: {place_id}]"
        lines.append(line)

    return "\n".join(lines) if lines else "No activities."


class TipsService:
    """Generate travel tips for activities."""

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    async def generate_tips(
        self,
        activities: list[dict[str, Any]],
        destination: str,
        interests: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate tips for a list of activities.

        Args:
            activities: List of activity dicts, each containing at least
                ``place`` (with ``name`` and ``place_id``), ``time_start``,
                and ``time_end``.
            destination: The city or destination name.
            interests: Optional list of traveler interests for
                personalised tips.

        Returns:
            Dict with a ``tips`` key mapping place_id to tip string.
        """
        system_prompt = tips_prompts.load("tips_system")
        user_template = tips_prompts.load("tips_user")

        schedule_text = _format_schedule(activities)
        interests_text = ", ".join(interests) if interests else "general sightseeing"

        # Grab a sample place_id for the template's example placeholder.
        example_id = ""
        for act in activities:
            pid = act.get("place", {}).get("place_id", act.get("place_id", ""))
            if pid:
                example_id = pid
                break

        user_prompt = user_template.format(
            destination=destination,
            interests=interests_text,
            schedule=schedule_text,
            example_id=example_id,
        )

        logger.info(
            "Generating tips for %d activities in %s",
            len(activities),
            destination,
        )

        from app.config.planning import should_use_search_grounding
        if should_use_search_grounding("selective"):
            raw_text, _citations = await self.llm.generate_with_search(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4000,
                temperature=0.7,
            )
        else:
            raw_text = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4000,
                temperature=0.7,
            )

        # Parse the JSON response from the LLM.
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            # Attempt to extract JSON from markdown-fenced output.
            stripped = raw_text.strip()
            if stripped.startswith("```"):
                # Remove opening fence (possibly ```json)
                first_newline = stripped.index("\n")
                stripped = stripped[first_newline + 1 :]
                if stripped.endswith("```"):
                    stripped = stripped[: -3].strip()
                try:
                    result = json.loads(stripped)
                except json.JSONDecodeError:
                    logger.error("Failed to parse tips JSON: %s", raw_text[:200])
                    return {"tips": {}}
            else:
                logger.error("Failed to parse tips JSON: %s", raw_text[:200])
                return {"tips": {}}

        # Ensure the result has the expected shape.
        if isinstance(result, dict) and "tips" in result:
            return result

        # If the LLM returned a flat dict of id->tip, wrap it.
        if isinstance(result, dict):
            return {"tips": result}

        return {"tips": {}}
