"""Day planner agent — uses LLM to select places and group them into themed days.

Given a set of discovered PlaceCandidates from the Google Places API, the agent
asks the LLM to pick the best subset, cluster them into geographically coherent
themed days, and estimate visit durations.
"""

import json
import logging

from app.models.internal import AIPlan, DayGroup, PlaceCandidate
from app.prompts import day_plan_prompts
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

# Pace → stops-per-day guidance (attractions, dining, total)
_PACE_GUIDE: dict[str, dict[str, int]] = {
    "relaxed": {"total": 5, "attractions": 3, "dining": 2},
    "moderate": {"total": 7, "attractions": 5, "dining": 2},
    "packed": {"total": 9, "attractions": 7, "dining": 2},
}

# Dining-related type identifiers (mirrors scheduler._MEAL_TYPES)
_DINING_TYPES: set[str] = {"restaurant", "cafe", "bakery", "bar", "food", "dining"}


def _is_dining(candidate: PlaceCandidate) -> bool:
    """Check whether a candidate is a dining place."""
    return bool(set(candidate.types) & _DINING_TYPES)


class DayPlannerAgent:
    """Uses LLM to select places and group them into themed days."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def plan_days(
        self,
        candidates: list[PlaceCandidate],
        city_name: str,
        num_days: int,
        interests: list[str],
        pace: str,
    ) -> AIPlan:
        """Given discovered place candidates, select and group into themed days.

        Args:
            candidates: Pre-vetted places from Google Places API.
            city_name: Name of the city being planned.
            num_days: Number of days to plan for this city.
            interests: User's stated interests (e.g. ["art", "food"]).
            pace: One of "relaxed", "moderate", "packed".

        Returns:
            AIPlan with selected_place_ids, day_groups (theme + place_ids),
            and durations (place_id -> minutes).
        """
        system_prompt = day_plan_prompts.load("planning_system")
        user_prompt = self._build_user_prompt(
            candidates, city_name, num_days, interests, pace
        )

        logger.info(
            "[DayPlanner] Planning %d day(s) in %s (%d candidates, pace=%s)",
            num_days,
            city_name,
            len(candidates),
            pace,
        )

        data = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=AIPlan,
            max_tokens=8000,
            temperature=0.7,
        )

        plan = self._parse_plan(data, num_days)

        # Deduplicate place_ids within and across days
        plan = self._deduplicate_plan(plan, candidates)

        # Validate: check for orphan IDs (LLM-generated IDs not in candidates)
        valid_ids = {c.place_id for c in candidates}
        orphan_ids = [
            pid for pid in plan.selected_place_ids if pid not in valid_ids
        ]
        if orphan_ids:
            logger.warning(
                "[DayPlanner] %d orphan place_ids not in candidates: %s",
                len(orphan_ids),
                orphan_ids[:5],
            )

        # Validate dining presence per day
        dining_ids = {
            c.place_id for c in candidates if _is_dining(c)
        }
        for i, group in enumerate(plan.day_groups):
            day_dining = [pid for pid in group.place_ids if pid in dining_ids]
            if len(day_dining) == 0:
                logger.warning(
                    "[DayPlanner] Day %d (%s) has NO dining places — "
                    "LLM ignored meal requirement",
                    i + 1,
                    group.theme,
                )

        logger.info(
            "[DayPlanner] LLM selected %d places across %d day groups",
            len(plan.selected_place_ids),
            len(plan.day_groups),
        )

        return plan

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _deduplicate_plan(
        self,
        plan: AIPlan,
        candidates: list[PlaceCandidate],
    ) -> AIPlan:
        """Remove duplicate place_ids within and across days.

        Within a day, exact duplicates are collapsed. Across days,
        non-dining places are only kept on their first occurrence.
        Dining places may repeat across days (e.g. a hotel breakfast spot).
        """
        dining_ids = {c.place_id for c in candidates if _is_dining(c)}
        seen_across_days: set[str] = set()
        total_removed = 0

        for group in plan.day_groups:
            # 1. Remove within-day duplicates (preserve first occurrence)
            seen_in_day: set[str] = set()
            deduped: list[str] = []
            for pid in group.place_ids:
                if pid in seen_in_day:
                    total_removed += 1
                    continue
                seen_in_day.add(pid)
                deduped.append(pid)

            # 2. Remove cross-day duplicates for non-dining places
            final: list[str] = []
            for pid in deduped:
                if pid not in dining_ids and pid in seen_across_days:
                    total_removed += 1
                    continue
                final.append(pid)
                seen_across_days.add(pid)

            group.place_ids = final

        if total_removed > 0:
            logger.info(
                "[DayPlanner] Removed %d duplicate place references",
                total_removed,
            )
            # Rebuild selected_place_ids from deduped day groups
            all_ids: list[str] = []
            seen: set[str] = set()
            for group in plan.day_groups:
                for pid in group.place_ids:
                    if pid not in seen:
                        seen.add(pid)
                        all_ids.append(pid)
            plan.selected_place_ids = all_ids

        return plan

    def _build_user_prompt(
        self,
        candidates: list[PlaceCandidate],
        city_name: str,
        num_days: int,
        interests: list[str],
        pace: str,
    ) -> str:
        """Format the user prompt template with candidate data."""
        guide = _PACE_GUIDE.get(pace, _PACE_GUIDE["moderate"])

        # Separate attractions from dining places
        attractions: list[dict] = []
        dining: list[dict] = []
        other: list[dict] = []

        for c in candidates:
            entry = {
                "place_id": c.place_id,
                "name": c.name,
                "rating": c.rating,
                "reviews": c.user_ratings_total,
                "types": c.types,
                "lat": c.location.lat,
                "lng": c.location.lng,
            }
            if c.editorial_summary:
                entry["description"] = c.editorial_summary

            if _is_dining(c):
                dining.append(entry)
            elif any(
                t in c.types
                for t in (
                    "tourist_attraction",
                    "museum",
                    "park",
                    "historical_landmark",
                    "monument",
                    "art_gallery",
                    "church",
                    "temple",
                    "hindu_temple",
                    "mosque",
                    "palace",
                    "castle",
                    "fort",
                    "zoo",
                    "aquarium",
                    "amusement_park",
                    "national_park",
                    "garden",
                    "beach",
                )
            ):
                attractions.append(entry)
            else:
                other.append(entry)

        other_section = ""
        if other:
            other_section = (
                "=== OTHER PLACES ===\n" + json.dumps(other, indent=2)
            )

        # Build date range text
        travel_dates = f"{num_days} day(s)"

        return day_plan_prompts.load("planning_user").format(
            num_days=num_days,
            destination=city_name,
            travel_dates=travel_dates,
            interests=", ".join(interests) if interests else "general sightseeing",
            pace=pace,
            total=guide["total"],
            attractions=guide["attractions"],
            dining=guide["dining"],
            attractions_json=json.dumps(attractions, indent=2),
            dining_json=json.dumps(dining, indent=2),
            other_section=other_section,
        )

    def _parse_plan(self, data: dict, expected_days: int) -> AIPlan:
        """Parse the LLM response dict into an AIPlan model.

        Handles gracefully when the LLM returns fewer or more day groups
        than expected.

        Args:
            data: Raw dict from the LLM structured output.
            expected_days: Number of days we asked the LLM to plan.

        Returns:
            Validated AIPlan instance.
        """
        try:
            # Parse day groups
            day_groups: list[DayGroup] = []
            for group_data in data.get("day_groups", []):
                day_groups.append(
                    DayGroup(
                        theme=group_data.get("theme", f"Day {len(day_groups) + 1}"),
                        place_ids=group_data.get("place_ids", []),
                    )
                )

            # Warn if group count doesn't match expected days
            if day_groups and len(day_groups) != expected_days:
                logger.warning(
                    "[DayPlanner] LLM returned %d day groups but %d were expected. "
                    "Using what was returned.",
                    len(day_groups),
                    expected_days,
                )

            # Parse selected place IDs
            selected_ids = data.get("selected_place_ids", [])

            # If selected_place_ids is empty, derive from day_groups
            if not selected_ids and day_groups:
                selected_ids = []
                for group in day_groups:
                    selected_ids.extend(group.place_ids)
                # Deduplicate while preserving order
                seen: set[str] = set()
                unique_ids: list[str] = []
                for pid in selected_ids:
                    if pid not in seen:
                        seen.add(pid)
                        unique_ids.append(pid)
                selected_ids = unique_ids

            # Parse durations
            durations: dict[str, int] = {}
            raw_durations = data.get("durations", {})
            for place_id, minutes in raw_durations.items():
                if isinstance(minutes, (int, float)):
                    durations[str(place_id)] = int(minutes)

            return AIPlan(
                selected_place_ids=selected_ids,
                day_groups=day_groups,
                durations=durations,
            )

        except Exception as e:
            logger.error("[DayPlanner] Failed to parse LLM response: %s", e)
            # Return an empty plan rather than crashing
            return AIPlan(
                selected_place_ids=[],
                day_groups=[],
                durations={},
            )
