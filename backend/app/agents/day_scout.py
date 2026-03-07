"""Day Scout agent — selects activities for themed days from Google Places candidates.

Given a batch of 2-3 themed days, candidate PlaceCandidates from the Google
Places API, and a list of already-used place IDs, the agent asks the LLM to
pick the best subset, cluster them into geographically coherent themed days,
and estimate visit durations.
"""

import json
import logging

from app.models.internal import AIPlan
from app.prompts import day_plan_prompts
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class DayScoutAgent:
    """Selects activities for themed days from Google Places candidates."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def plan_batch(
        self,
        candidates: list,
        batch_themes: dict[int, list],
        destination: str,
        pace: str,
        landmarks: list[dict] | None = None,
        already_used: set[str] | None = None,
        meal_time_guidance: str = "",
        travelers_description: str = "1 adult",
    ) -> AIPlan:
        """Plan activities for a batch of 2-3 themed days.

        Args:
            candidates: Pre-vetted places from Google Places API.
            batch_themes: Mapping of day number to list of assigned themes.
            destination: Name of the city being planned.
            pace: One of "relaxed", "moderate", "packed".
            landmarks: Optional top landmarks by visitor reviews.
            already_used: Place IDs already planned on other days.
            meal_time_guidance: Regional meal timing guidance string.
            travelers_description: Description of the travel group.

        Returns:
            AIPlan with selected_place_ids, day_groups, durations, and cost_estimates.
        """
        system_prompt = day_plan_prompts.load("day_scout_system")
        user_prompt = self._build_user_prompt(
            candidates, batch_themes, destination, pace,
            landmarks, already_used, meal_time_guidance, travelers_description,
        )

        logger.info(
            "[DayScout] Planning days %s in %s (%d candidates, pace=%s)",
            list(batch_themes.keys()), destination, len(candidates), pace,
        )

        plan = await self.llm.generate_structured(
            system_prompt, user_prompt, schema=AIPlan
        )
        return plan

    def _build_user_prompt(
        self, candidates, batch_themes, destination, pace,
        landmarks, already_used, meal_time_guidance, travelers_description,
    ) -> str:
        """Format the user prompt template with candidate data."""
        from app.config.planning import DAY_PLANNER_PACE_GUIDE, DINING_TYPES

        guide = DAY_PLANNER_PACE_GUIDE.get(pace, DAY_PLANNER_PACE_GUIDE["moderate"])

        attractions = []
        dining = []
        for c in candidates:
            entry = {
                "place_id": c.place_id,
                "name": c.name,
                "rating": c.rating,
                "user_ratings_total": c.user_ratings_total,
                "types": c.types[:3],
                "location": {"lat": c.location.lat, "lng": c.location.lng} if c.location else None,
            }
            if c.suggested_duration_minutes:
                entry["suggested_duration_minutes"] = c.suggested_duration_minutes
            if set(c.types) & DINING_TYPES:
                dining.append(entry)
            else:
                attractions.append(entry)

        themes_text = ""
        for day_num, themes in sorted(batch_themes.items()):
            theme_names = ", ".join(
                f"{t.theme} ({t.category})" if hasattr(t, 'category') else str(t)
                for t in themes
            )
            themes_text += f"Day {day_num}: {theme_names}\n"

        landmarks_section = ""
        if landmarks:
            lines = ["TOP LANDMARKS by visitor reviews (include at least one per batch):"]
            for lm in landmarks[:5]:
                lines.append(f"- {lm.get('name')} ({lm.get('user_ratings_total', 0):,} reviews)")
            landmarks_section = "\n".join(lines)

        used_text = ", ".join(sorted(already_used)[:20]) if already_used else "none"

        template = day_plan_prompts.load("day_scout_user")
        return template.format(
            batch_day_numbers=", ".join(str(d) for d in sorted(batch_themes.keys())),
            destination=destination,
            batch_themes=themes_text,
            pace=pace,
            activities_per_day=guide["total"],
            landmarks_section=landmarks_section,
            already_used_ids=used_text,
            attractions_json=json.dumps(attractions[:40], indent=2),
            dining_json=json.dumps(dining[:20], indent=2),
            meal_time_guidance=meal_time_guidance,
        )
