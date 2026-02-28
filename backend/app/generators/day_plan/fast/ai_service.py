"""FAST mode AI service for itinerary planning."""

import json
import logging
from typing import Optional

from openai import AsyncAzureOpenAI

from app.config.planning import PACE_CONFIGS
from app.config.tuning import FAST_MODE
from app.core.clients import OpenAIClient
from app.models import AIPlan, DayGroup, PlaceCandidate, Pace
from app.generators.day_plan.fast.prompts import (
    PLANNING_SYSTEM_PROMPT,
    build_planning_prompt,
    VALIDATION_SYSTEM_PROMPT,
    build_validation_prompt,
)
from app.utils import classify_place

logger = logging.getLogger(__name__)


class FastAIService:
    """FAST mode AI service for planning and validation.
    
    Uses shared OpenAI client from OpenAIClient singleton.
    """

    def __init__(self):
        """Initialize the Azure OpenAI service."""
        pass  # Uses OpenAIClient singleton

    @property
    def client(self) -> AsyncAzureOpenAI:
        """Get the shared OpenAI client."""
        return OpenAIClient.get_client()

    @property
    def deployment(self) -> str:
        """Get the deployment name."""
        return OpenAIClient.get_deployment()

    async def select_and_group_places(
        self,
        candidates: list[PlaceCandidate],
        interests: list[str],
        num_days: int,
        pace: Pace,
        destination: str = "",
        travel_dates: str = "",
    ) -> AIPlan:
        """
        AI selects best places and creates a practical day-by-day itinerary.

        Args:
            candidates: List of candidate places with real data
            interests: User's interests
            num_days: Number of days in the trip
            pace: Trip pace (relaxed/moderate/packed)
            destination: Destination city name for context
            travel_dates: Travel date range for seasonal awareness

        Returns:
            AIPlan with selected place IDs and day groupings
        """
        # Helper functions for formatting place data
        def format_hours(place: PlaceCandidate) -> str:
            """Format opening hours for LLM understanding."""
            if not place.opening_hours:
                return "hours unknown"
            days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            hours_by_time = {}
            for h in place.opening_hours:
                time_str = f"{h.open_time}-{h.close_time}"
                if time_str not in hours_by_time:
                    hours_by_time[time_str] = []
                hours_by_time[time_str].append(days[h.day])
            if hours_by_time:
                most_common = max(hours_by_time.items(), key=lambda x: len(x[1]))
                return f"{most_common[0]} ({','.join(most_common[1][:3])}...)"
            return "hours unknown"
        
        def format_price(price_level: int | None) -> str:
            """Format price level for LLM."""
            if price_level is None:
                return ""
            return ["free", "$", "$$", "$$$", "$$$$"][price_level]
        
        # Categorize candidates using the shared classifier
        attractions = []
        dining = []
        other = []
        
        for c in candidates:
            # Skip permanently closed places
            if c.business_status == "CLOSED_PERMANENTLY":
                continue
                
            summary = {
                "id": c.place_id,
                "name": c.name,
                "types": c.types[:3],
                "rating": c.rating,
                "reviews": c.user_ratings_total or 0,
                "price": format_price(c.price_level),
                "hours": format_hours(c),
                "neighborhood": c.address.split(",")[0] if c.address else "",
                "lat": round(c.location.lat, 5) if c.location else None,
                "lng": round(c.location.lng, 5) if c.location else None,
            }
            if c.editorial_summary:
                summary["description"] = c.editorial_summary
            
            category = classify_place(c.types, c.name)
            if category == "dining":
                dining.append(summary)
            elif category == "attraction":
                attractions.append(summary)
            else:
                other.append(summary)
        
        logger.info(f"Categorized places: {len(attractions)} attractions, {len(dining)} dining, {len(other)} other")

        # Build prompt using the prompt module
        prompt = build_planning_prompt(
            attractions=attractions,
            dining=dining,
            other=other,
            interests=interests,
            num_days=num_days,
            pace=pace,
            destination=destination,
            travel_dates=travel_dates,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=FAST_MODE.max_tokens,
            )

            content = response.choices[0].message.content
            logger.debug(f"AI response content: {content[:500] if content else 'EMPTY'}")
            
            if not content:
                logger.warning("AI returned empty response, using fallback")
                return self._fallback_plan(candidates, num_days, pace)
            
            data = json.loads(content)

            # Extract duration estimates (place_id -> minutes)
            durations = data.get("durations", {})
            # Ensure values are integers
            durations = {k: int(v) for k, v in durations.items() if isinstance(v, (int, float))}
            logger.info(f"AI provided duration estimates for {len(durations)} places")

            return AIPlan(
                selected_place_ids=data.get("selected_place_ids", []),
                day_groups=[
                    DayGroup(
                        theme=group.get("theme", f"Day {i + 1}"),
                        place_ids=group.get("place_ids", []),
                    )
                    for i, group in enumerate(data.get("day_groups", []))
                ],
                durations=durations,
            )

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"AI planning failed: {e}")
            # Fallback: simple distribution
            return self._fallback_plan(candidates, num_days, pace)

    async def validate_and_refine_plan(
        self,
        plan: AIPlan,
        candidates: list[PlaceCandidate],
        num_days: int,
        destination: str = "",
        interests: str = "",
        pace: str = "",
        travel_dates: str = "",
    ) -> AIPlan:
        """
        Second LLM call to validate and refine the itinerary plan.
        """
        # Build lookup for place details
        place_lookup = {c.place_id: c for c in candidates}
        
        # Build compact current plan summary
        plan_data = []
        for i, group in enumerate(plan.day_groups, 1):
            day_places = []
            for pid in group.place_ids:
                if pid in place_lookup:
                    p = place_lookup[pid]
                    ptype = "restaurant" if classify_place(p.types, p.name) == "dining" else "attraction"
                    day_places.append({"id": pid, "name": p.name, "type": ptype})
            plan_data.append({"day": i, "places": day_places})
        
        # Get available dining and attractions not already in the plan
        used_ids = set(plan.selected_place_ids)
        available_dining = []
        available_attractions = []
        for c in candidates:
            if c.place_id not in used_ids:
                entry = {
                    "id": c.place_id,
                    "name": c.name,
                    "rating": c.rating,
                    "reviews": c.user_ratings_total or 0,
                    "lat": round(c.location.lat, 5) if c.location else None,
                    "lng": round(c.location.lng, 5) if c.location else None,
                }
                if classify_place(c.types, c.name) == "dining":
                    available_dining.append(entry)
                else:
                    available_attractions.append(entry)

        # Build prompt using the prompt module
        prompt = build_validation_prompt(
            plan_data=plan_data,
            available_dining=available_dining,
            available_attractions=available_attractions,
            destination=destination,
            interests=interests,
            pace=pace,
            travel_dates=travel_dates,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=FAST_MODE.validation_max_tokens,
            )

            content = response.choices[0].message.content
            logger.info(f"Validation response length: {len(content) if content else 0}")
            
            if not content:
                logger.warning("Validation returned empty response, keeping original plan")
                return plan
            
            data = json.loads(content)
            
            issues = data.get("issues_found", [])
            changes = data.get("changes_made", [])
            
            if issues:
                logger.info(f"Plan validation found {len(issues)} issues: {issues}")
                logger.info(f"Changes made: {changes}")
            else:
                logger.info("Plan validation: No issues found")
            
            refined = data.get("refined_plan", {})
            
            # If refined plan is empty or invalid, keep original
            if not refined or not refined.get("day_groups"):
                logger.warning("Validation returned empty refined_plan, keeping original")
                return plan
            
            return AIPlan(
                selected_place_ids=refined.get("selected_place_ids", plan.selected_place_ids),
                day_groups=[
                    DayGroup(
                        theme=group.get("theme", f"Day {i + 1}"),
                        place_ids=group.get("place_ids", []),
                    )
                    for i, group in enumerate(refined.get("day_groups", []))
                ],
            )

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Plan validation failed: {e}")
            # Return original plan if validation fails
            return plan

    def _fallback_plan(
        self,
        candidates: list[PlaceCandidate],
        num_days: int,
        pace: Pace,
    ) -> AIPlan:
        """
        Create a simple fallback plan if AI fails.
        
        This just distributes places evenly across days.
        The validation LLM (validate_and_refine_plan) will fix any issues
        like missing meals or poor ordering.
        """
        config = PACE_CONFIGS[pace]
        places_per_day = config.places_per_day
        
        total_places = min(len(candidates), places_per_day * num_days)
        selected = candidates[:total_places]
        
        logger.info(f"Fallback: distributing {total_places} places across {num_days} days")
        
        day_groups = []
        for day in range(num_days):
            start_idx = day * places_per_day
            end_idx = min(start_idx + places_per_day, len(selected))
            day_places = selected[start_idx:end_idx]
            
            day_groups.append(
                DayGroup(
                    theme=f"Day {day + 1} Exploration",
                    place_ids=[p.place_id for p in day_places],
                )
            )
        
        return AIPlan(
            selected_place_ids=[p.place_id for p in selected],
            day_groups=day_groups,
        )
