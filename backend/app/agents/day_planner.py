"""Day planner agent — uses LLM to select places and group them into themed days.

Given a set of discovered PlaceCandidates from the Google Places API, the agent
asks the LLM to pick the best subset, cluster them into geographically coherent
themed days, and estimate visit durations.
"""

import json
import logging

from app.models.internal import AIPlan, PlaceCandidate
from app.prompts import day_plan_prompts
from app.services.llm.base import LLMService
from app.services.llm.exceptions import LLMValidationError

logger = logging.getLogger(__name__)

# Pace → stops-per-day guidance (attractions, dining, total)
from app.config.planning import DAY_PLANNER_PACE_GUIDE as _PACE_GUIDE, DINING_TYPES

# Dining-related type identifiers
_DINING_TYPES: set[str] = DINING_TYPES


def _build_meal_time_guidance(country: str) -> str:
    """Build meal timing guidance for the LLM based on destination country.

    Follows the regional_transport.py pattern — provides context for the
    LLM rather than hardcoded meal times in prompts.
    """
    c = country.lower().strip() if country else ""

    if c in ("spain", "portugal", "argentina", "greece", "italy"):
        return (
            f"In {country}, locals eat lunch late (1:30-3:30 PM) and dinner very late "
            "(9:00-11:00 PM). Schedule meals accordingly — tourists often adapt to "
            "local dining hours for the best experience and availability."
        )
    if c in ("japan", "south korea", "korea", "taiwan", "china", "vietnam"):
        return (
            f"In {country}, meals are typically early: lunch around 11:30 AM-1:00 PM "
            "and dinner 5:30-7:30 PM. Many restaurants close between meals."
        )
    if c in ("india", "sri lanka", "nepal", "bangladesh", "pakistan"):
        return (
            f"In {country}, lunch is typically 12:30-2:30 PM and dinner 7:30-9:30 PM. "
            "Street food is available throughout the day."
        )
    if c in ("turkey", "iran", "lebanon", "jordan", "egypt",
             "saudi arabia", "uae", "united arab emirates"):
        return (
            f"In {country}, lunch is typically 1:00-3:00 PM and dinner 7:30-10:00 PM. "
            "Many restaurants are busiest after 8 PM."
        )
    if c in ("mexico", "colombia", "peru", "chile", "brazil"):
        return (
            f"In {country}, lunch (comida) is the main meal, typically 1:00-3:00 PM. "
            "Dinner is lighter and later, around 8:00-10:00 PM."
        )
    if c in ("germany", "austria", "switzerland", "netherlands", "belgium",
             "denmark", "sweden", "norway", "finland"):
        return (
            f"In {country}, lunch is around 12:00-1:30 PM and dinner is early, "
            "typically 6:00-8:00 PM. Many restaurants stop serving by 9 PM."
        )
    if c in ("thailand", "malaysia", "indonesia", "singapore", "philippines"):
        return (
            f"In {country}, meal times are flexible. Street food and hawker stalls "
            "serve throughout the day. Sit-down lunch is around noon, dinner 6:00-8:00 PM."
        )
    # Default generic guidance
    return (
        "Schedule lunch in the early afternoon and dinner in the evening, following "
        "local dining customs for this destination."
    )


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
        budget: str = "moderate",
        daily_budget_usd: float | None = None,
        must_include: list[str] | None = None,
        time_constraints: list[dict] | None = None,
        travelers_description: str = "1 adult",
        country: str = "",
        highlights: list | None = None,
        best_time_to_visit: str = "",
        hotel_location=None,
        experience_themes: list | None = None,
    ) -> AIPlan:
        """Given discovered place candidates, select and group into themed days.

        Args:
            candidates: Pre-vetted places from Google Places API.
            city_name: Name of the city being planned.
            num_days: Number of days to plan for this city.
            interests: User's stated interests (e.g. ["art", "food"]).
            pace: One of "relaxed", "moderate", "packed".
            budget: Budget tier — "budget", "moderate", or "luxury".
            daily_budget_usd: Optional daily budget target in USD.
            must_include: Optional list of place names that MUST appear in the plan.
            time_constraints: Optional per-day time constraints (arrival/departure days).

        Returns:
            AIPlan with selected_place_ids, day_groups (theme + place_ids),
            durations (place_id -> minutes), and cost_estimates (place_id -> USD).
        """
        system_prompt = day_plan_prompts.load("planning_system")
        user_prompt = self._build_user_prompt(
            candidates, city_name, num_days, interests, pace,
            budget=budget, daily_budget_usd=daily_budget_usd,
            must_include=must_include, time_constraints=time_constraints,
            travelers_description=travelers_description,
            country=country,
            highlights=highlights,
            best_time_to_visit=best_time_to_visit,
            hotel_location=hotel_location,
            experience_themes=experience_themes,
        )

        logger.info(
            "[DayPlanner] Planning %d day(s) in %s (%d candidates, pace=%s)",
            num_days,
            city_name,
            len(candidates),
            pace,
        )

        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_DEFAULT_TEMPERATURE

        # generate_structured now returns AIPlan model directly
        plan = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=AIPlan,
            max_tokens=LLM_DEFAULT_MAX_TOKENS,
            temperature=LLM_DEFAULT_TEMPERATURE,
        )

        if not plan.durations:
            logger.warning("[DayPlanner] LLM returned empty durations dict for %s — scheduler will use fallbacks", city_name)
        if not plan.cost_estimates:
            logger.warning("[DayPlanner] LLM returned empty cost_estimates for %s — costs will be $0", city_name)

        # Derive selected_place_ids from day_groups if empty
        if not plan.selected_place_ids and plan.day_groups:
            seen: set[str] = set()
            ids: list[str] = []
            for group in plan.day_groups:
                for pid in group.place_ids:
                    if pid not in seen:
                        seen.add(pid)
                        ids.append(pid)
            plan.selected_place_ids = ids

        # Semantic validation
        valid_ids = {c.place_id for c in candidates}
        self._validate_ai_plan(plan, valid_ids)

        # Deduplicate
        plan = self._deduplicate_plan(plan, candidates)

        # Clean orphan IDs (soft — not a hard error)
        orphan_ids = [pid for pid in plan.selected_place_ids if pid not in valid_ids]
        if orphan_ids:
            logger.warning("[DayPlanner] %d orphan place_ids removed (LLM hallucinated IDs): %s", len(orphan_ids), orphan_ids)
            plan.selected_place_ids = [pid for pid in plan.selected_place_ids if pid in valid_ids]
            for group in plan.day_groups:
                group.place_ids = [pid for pid in group.place_ids if pid in valid_ids]
            for oid in orphan_ids:
                plan.cost_estimates.pop(oid, None)
                plan.durations.pop(oid, None)

        # Validate dining presence per day
        dining_ids = {c.place_id for c in candidates if _is_dining(c)}
        for i, group in enumerate(plan.day_groups):
            day_dining_count = len([pid for pid in group.place_ids if pid in dining_ids])
            if day_dining_count < 1:
                raise LLMValidationError(
                    "AIPlan",
                    [f"Day {i+1} ({group.theme}) has {day_dining_count} dining places (need at least 1)"],
                    1,
                )

        logger.info("[DayPlanner] LLM selected %d places across %d day groups",
                    len(plan.selected_place_ids), len(plan.day_groups))
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
        budget: str = "moderate",
        daily_budget_usd: float | None = None,
        must_include: list[str] | None = None,
        time_constraints: list[dict] | None = None,
        travelers_description: str = "1 adult",
        country: str = "",
        highlights: list | None = None,
        best_time_to_visit: str = "",
        hotel_location=None,
        experience_themes: list | None = None,
    ) -> str:
        """Format the user prompt template with candidate data."""
        guide = _PACE_GUIDE.get(pace, _PACE_GUIDE["moderate"])
        meal_time_guidance = _build_meal_time_guidance(country)

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

            if c.good_for_children is not None:
                entry["good_for_children"] = c.good_for_children
            if c.good_for_groups is not None:
                entry["good_for_groups"] = c.good_for_groups
            if _is_dining(c):
                if c.serves_vegetarian_food is not None:
                    entry["serves_vegetarian"] = c.serves_vegetarian_food
                if c.serves_lunch is not None:
                    entry["serves_lunch"] = c.serves_lunch
                if c.serves_dinner is not None:
                    entry["serves_dinner"] = c.serves_dinner

            if _is_dining(c):
                dining.append(entry)
            else:
                # All non-dining places are potential attractions — let the
                # LLM decide which are sightseeing vs other based on context
                attractions.append(entry)

        other_section = ""
        if other:
            other_section = (
                "=== OTHER PLACES ===\n" + json.dumps(other, indent=2)
            )

        # Build date range text
        travel_dates = f"{num_days} day(s)"

        daily_budget_line = (
            f"Daily budget target: ~${daily_budget_usd:.0f}/day"
            if daily_budget_usd
            else "No specific daily budget set"
        )

        # Build must-include section if user specified required places
        must_include_section = ""
        if must_include:
            # Try to match must_include names to candidate place_ids
            matched: list[str] = []
            for mi in must_include:
                mi_lower = mi.lower()
                for c in candidates:
                    if mi_lower in c.name.lower() or c.name.lower() in mi_lower:
                        matched.append(f"- {mi} (place_id: {c.place_id})")
                        break
                else:
                    matched.append(f"- {mi} (find closest match from candidates)")
            must_include_section = (
                "\n## MUST-INCLUDE PLACES\n"
                "The user REQUIRES these places to appear in the itinerary. "
                "You MUST include them in one of the day groups:\n"
                + "\n".join(matched)
            )

        # Build time constraints section for arrival/departure days
        time_constraints_section = ""
        if time_constraints:
            lines = ["## TIME CONSTRAINTS (reduced-hours days)",
                      "Some days have limited sightseeing time due to travel. Plan FEWER activities on these days to fit the available window:"]
            for tc in time_constraints:
                day_num = tc.get("day_num", "?")
                reason = tc.get("reason", "travel")
                available_hours = tc.get("available_hours")
                if available_hours is not None:
                    lines.append(f"- Day {day_num}: only ~{available_hours:.0f} hours available ({reason}). Scale activity count proportionally.")
            time_constraints_section = "\n".join(lines)

        # Build experience themes or scout highlights section
        themes_section = ""
        if experience_themes:
            lines = ["## EXPERIENCE THEMES TO COVER",
                     "Build themed days covering these experience categories. Each theme should get at least one day or half-day.\n"]
            for et in experience_themes:
                if hasattr(et, 'excursion_type') and et.excursion_type:
                    continue  # Excursions are handled separately by orchestrator
                why = f' — "{et.why}"' if hasattr(et, 'why') and et.why else ""
                lines.append(f"- {et.theme} ({et.category}){why}")
            themes_section = "\n".join(lines)

        # Use themes section if available, otherwise fall back to scout highlights
        scout_highlights_section = ""
        if themes_section:
            scout_highlights_section = themes_section
        elif highlights:
            hl_lines = ["## MUST-INCLUDE ATTRACTIONS",
                        "These are the destination's signature attractions. You MUST include each one in a day plan unless it's scheduled as a full-day excursion. Missing a must-include attraction is a critical error."]
            for h in highlights:
                dur = f", {h.suggested_duration_hours}h" if hasattr(h, 'suggested_duration_hours') and h.suggested_duration_hours else ""
                desc = f': "{h.description}"' if hasattr(h, 'description') and h.description else ""
                cat = h.category if hasattr(h, 'category') and h.category else "attraction"
                exc = f" [{h.excursion_type}]" if hasattr(h, 'excursion_type') and h.excursion_type else ""
                hl_lines.append(f"- {h.name}{desc} ({cat}{dur}){exc}")
            scout_highlights_section = "\n".join(hl_lines)

        scheduling_hints = ""
        if best_time_to_visit:
            scheduling_hints = f"## SCHEDULING HINTS\n{best_time_to_visit}"

        hotel_section = ""
        if hotel_location and hasattr(hotel_location, 'lat') and hasattr(hotel_location, 'lng'):
            hotel_section = f"## HOTEL LOCATION\nHotel at ({hotel_location.lat:.4f}, {hotel_location.lng:.4f}) — cluster Day 1 morning activities near hotel for easy start"

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
            budget_tier=budget,
            daily_budget_line=daily_budget_line,
            city_name=city_name,
            must_include_section=must_include_section,
            time_constraints_section=time_constraints_section,
            travelers_description=travelers_description,
            meal_time_guidance=meal_time_guidance,
            scout_highlights_section=scout_highlights_section,
            scheduling_hints=scheduling_hints,
            hotel_section=hotel_section,
        )

    def _validate_ai_plan(self, plan: AIPlan, valid_ids: set[str]) -> None:
        """Validate semantic completeness of an AI plan.

        Raises:
            LLMValidationError: If the plan is structurally incomplete.
        """
        if not plan.day_groups:
            raise LLMValidationError("AIPlan", ["No day groups returned"], 1)

        for i, group in enumerate(plan.day_groups):
            valid_place_ids = [pid for pid in group.place_ids if pid in valid_ids]
            if not valid_place_ids:
                raise LLMValidationError(
                    "AIPlan",
                    [f"Day {i + 1} ({group.theme}) has no places after orphan removal"],
                    1,
                )

        # Warn if any day has very few activities
        for i, group in enumerate(plan.day_groups):
            valid_place_ids = [pid for pid in group.place_ids if pid in valid_ids]
            if 0 < len(valid_place_ids) < 3:
                logger.warning(
                    "[DayPlanner] Day %d (%s) has only %d activities — below minimum for any pace",
                    i + 1, group.theme, len(valid_place_ids),
                )
