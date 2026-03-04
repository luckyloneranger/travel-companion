"""Schedule builder for deterministic time-slot calculation.

Ported from the battle-tested ScheduleBuilder in the original codebase.
Duration defaults are inlined here; pace multipliers follow the same
relaxed=1.3, moderate=1.0, packed=0.8 convention.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional

from app.models.common import Pace
from app.models.day_plan import Activity, Place, Route
from app.models.internal import DayGroup, PlaceCandidate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Inline duration defaults (avoid importing from config for now)
# ---------------------------------------------------------------------------
DURATION_BY_CATEGORY: dict[str, int] = {
    # Museums and galleries
    "museum": 120,
    "art_gallery": 60,
    "culture": 90,
    # Religious / historical
    "temple": 45,
    "church": 30,
    "hindu_temple": 45,
    "mosque": 45,
    "place_of_worship": 30,
    "historical_landmark": 45,
    "monument": 30,
    "palace": 60,
    "castle": 60,
    "fort": 60,
    # Nature and outdoors
    "park": 60,
    "garden": 45,
    "zoo": 120,
    "aquarium": 90,
    "national_park": 120,
    "beach": 90,
    "nature": 60,
    # Entertainment
    "amusement_park": 180,
    "tourist_attraction": 45,
    "entertainment": 90,
    # Dining
    "restaurant": 75,
    "cafe": 45,
    "bar": 60,
    "bakery": 20,
    "food": 60,
    "dining": 75,
    # Shopping
    "shopping": 60,
    "market": 60,
    "mall": 90,
    # Default
    "default": 45,
}

PACE_MULTIPLIERS: dict[Pace, float] = {
    Pace.RELAXED: 1.3,
    Pace.MODERATE: 1.0,
    Pace.PACKED: 0.8,
}


def _parse_time_str(time_str: str) -> time:
    """Parse HH:MM time string to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


# Meal-related type identifiers
_MEAL_TYPES: set[str] = {"restaurant", "cafe", "bakery", "bar", "food", "dining"}


@dataclass
class ScheduleConfig:
    """Configuration for schedule building."""

    day_start: time = field(default_factory=lambda: time(9, 0))
    day_end: time = field(default_factory=lambda: time(21, 0))
    lunch_window_start: time = field(default_factory=lambda: time(12, 0))
    lunch_window_end: time = field(default_factory=lambda: time(14, 0))
    dinner_window_start: time = field(default_factory=lambda: time(18, 0))
    dinner_window_end: time = field(default_factory=lambda: time(21, 0))
    lunch_target: time = field(default_factory=lambda: time(12, 30))
    dinner_target: time = field(default_factory=lambda: time(18, 30))
    buffer_minutes: int = 15
    min_activity_duration: int = 30
    max_meal_wait_minutes: int = 90


class ScheduleBuilder:
    """
    Service for building deterministic schedules.

    Takes an ordered list of places and produces a list of
    :class:`Activity` objects with calculated start/end times,
    respecting meal windows, opening hours, pace multipliers, and
    a configurable transition buffer.
    """

    def __init__(self, config: Optional[ScheduleConfig] = None):
        """Initialise schedule builder with optional custom config."""
        self.config = config or ScheduleConfig()

    def build_schedule(
        self,
        places: list[PlaceCandidate],
        day_groups: list[DayGroup] | None = None,
        routes: list[Route] | None = None,
        pace: Pace = Pace.MODERATE,
        durations: dict[str, int] | None = None,
        start_location=None,
        schedule_date: date | None = None,
        day_start_time: time | None = None,
        day_end_time: time | None = None,
    ) -> list[Activity]:
        """
        Build a time-slotted schedule for a day's activities.

        Meals are scheduled at appropriate times:
        - Lunch: 12:00-14:00 (target 12:30)
        - Dinner: 18:00-21:00 (target 18:30)

        If a meal activity arrives before its window, we wait.

        Args:
            places: Ordered list of places to visit.
            day_groups: Optional day grouping information (unused in core
                scheduling but accepted for interface compatibility).
            routes: Routes between consecutive places.
            pace: Trip pace affecting durations.
            durations: Optional per-place duration overrides keyed by place_id.
            start_location: Optional starting location (reserved for future use).
            schedule_date: The date for this schedule (defaults to today).
            day_start_time: Custom start time (e.g. for arrival days). Defaults
                to config.day_start.
            day_end_time: Custom end time (e.g. for departure days). Defaults
                to config.day_end.

        Returns:
            List of Activity with calculated time slots.
        """
        if not places:
            return []

        routes = routes or []
        durations = durations or {}
        the_date = schedule_date or date.today()

        schedule: list[Activity] = []
        effective_start = day_start_time or self.config.day_start
        effective_end = day_end_time or self.config.day_end
        current_time = datetime.combine(the_date, effective_start)
        day_end = datetime.combine(the_date, effective_end)

        has_lunch = False
        has_dinner = False

        # Count meal places for smart meal assignment
        meal_places = [p for p in places if self._is_meal_place(p)]
        num_meals = len(meal_places)
        meals_scheduled = 0

        for i, place in enumerate(places):
            # Determine duration
            duration = self._get_duration(place, pace, durations)

            # Adjust for opening hours
            adjusted_time = self._adjust_for_opening_hours(place, current_time)
            if adjusted_time:
                current_time = adjusted_time

            current_time_only = current_time.time()
            is_meal = self._is_meal_place(place)

            # Smart meal timing: wait for appropriate meal window,
            # but never wait more than max_meal_wait_minutes.
            # Skip meal-wait entirely if no non-meal activities have been
            # scheduled yet (don't delay the day start for a meal).
            if is_meal:
                meals_scheduled += 1
                has_prior_activities = any(
                    not self._is_meal_place(places[j]) for j in range(i)
                )
                is_lunch_slot = meals_scheduled == 1 and num_meals >= 1
                is_dinner_slot = (
                    meals_scheduled == 2
                    or (
                        meals_scheduled == 1
                        and current_time_only >= self.config.dinner_window_start
                    )
                )

                if is_lunch_slot and not has_lunch:
                    if (
                        has_prior_activities
                        and current_time_only < self.config.lunch_window_start
                    ):
                        target = datetime.combine(
                            the_date, self.config.lunch_target
                        )
                        wait_mins = (target - current_time).total_seconds() / 60
                        if wait_mins <= self.config.max_meal_wait_minutes:
                            current_time = target
                        # else: schedule immediately, don't create large gap
                    has_lunch = True

                elif is_dinner_slot and not has_dinner:
                    if current_time_only < self.config.dinner_window_start:
                        target = datetime.combine(
                            the_date, self.config.dinner_target
                        )
                        wait_mins = (target - current_time).total_seconds() / 60
                        if wait_mins <= self.config.max_meal_wait_minutes:
                            current_time = target
                        # else: schedule immediately, don't create large gap
                    has_dinner = True

            # Calculate end time
            end_time = current_time + timedelta(minutes=duration)

            # Check day-end boundary
            if end_time > day_end:
                if current_time >= day_end:
                    logger.warning("Skipping %s: already past day end", place.name)
                    continue
                available_minutes = int(
                    (day_end - current_time).total_seconds()
                ) // 60
                if available_minutes >= self.config.min_activity_duration:
                    duration = available_minutes
                    end_time = day_end
                else:
                    logger.warning(
                        "Skipping %s: not enough time remaining", place.name
                    )
                    continue

            # Build the Place model for Activity
            activity_place = Place(
                place_id=place.place_id,
                name=place.name,
                address=place.address,
                location=place.location,
                category=place.types[0] if place.types else "",
                rating=place.rating,
                photo_url=place.photo_reference,
                photo_urls=place.photo_references,
                opening_hours=[],
                website=place.website,
            )

            # Route to next (if available)
            route_to_next: Route | None = None
            if i < len(routes):
                route_to_next = routes[i]

            schedule.append(
                Activity(
                    time_start=current_time.strftime("%H:%M"),
                    time_end=end_time.strftime("%H:%M"),
                    duration_minutes=duration,
                    place=activity_place,
                    route_to_next=route_to_next,
                )
            )

            # Advance current_time past this activity + travel + buffer
            travel_minutes = 0
            if i < len(routes):
                travel_minutes = routes[i].duration_seconds // 60

            current_time = end_time + timedelta(
                minutes=travel_minutes + self.config.buffer_minutes
            )

        return schedule

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_duration(
        self,
        place: PlaceCandidate,
        pace: Pace,
        durations: dict[str, int],
    ) -> int:
        """
        Get duration for a place based on overrides, LLM estimate, type, and pace.

        Priority:
        1. Explicit override from ``durations`` dict.
        2. LLM-estimated duration (``suggested_duration_minutes``).
        3. Type-based fallback (``DURATION_BY_CATEGORY``).
        """
        # Explicit override
        if place.place_id in durations:
            base_duration = durations[place.place_id]
        elif place.suggested_duration_minutes:
            base_duration = place.suggested_duration_minutes
        else:
            base_duration = DURATION_BY_CATEGORY["default"]
            for place_type in place.types:
                if place_type in DURATION_BY_CATEGORY:
                    base_duration = DURATION_BY_CATEGORY[place_type]
                    break

        # Apply pace multiplier
        multiplier = PACE_MULTIPLIERS.get(pace, 1.0)
        adjusted = int(base_duration * multiplier)

        # Round to nearest 15 minutes
        return ((adjusted + 7) // 15) * 15

    def _adjust_for_opening_hours(
        self,
        place: PlaceCandidate,
        current_time: datetime,
    ) -> Optional[datetime]:
        """
        Adjust start time if place isn't open yet.

        Returns None if no adjustment needed, otherwise the adjusted time.
        """
        if not place.opening_hours:
            return None

        day_of_week = current_time.weekday()
        # Convert to Google's format (0=Sunday)
        google_day = (day_of_week + 1) % 7

        for hours in place.opening_hours:
            if hours.day == google_day:
                open_time = datetime.strptime(hours.open_time, "%H:%M").time()
                if current_time.time() < open_time:
                    return datetime.combine(current_time.date(), open_time)
                break

        return None

    def _is_meal_place(self, place: PlaceCandidate) -> bool:
        """Check if a place is a restaurant/cafe suitable for meals."""
        return bool(set(place.types) & _MEAL_TYPES)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_schedule(
        self,
        schedule: list[Activity],
    ) -> list[str]:
        """
        Validate a schedule for conflicts and issues.

        Returns a list of warning messages.
        """
        warnings: list[str] = []

        for i, activity in enumerate(schedule):
            # Overlap check
            if i > 0:
                prev_end = datetime.strptime(schedule[i - 1].time_end, "%H:%M")
                curr_start = datetime.strptime(activity.time_start, "%H:%M")
                if curr_start < prev_end:
                    warnings.append(
                        f"Overlap: {schedule[i-1].place.name} ends after "
                        f"{activity.place.name} starts"
                    )

            # Opening hours check
            if activity.place.opening_hours:
                end_time_obj = datetime.strptime(activity.time_end, "%H:%M").time()
                for hours_str in activity.place.opening_hours:
                    # Opening hours are stored as strings in the Place model
                    # e.g. "Mon: 09:00 - 17:00"
                    if "closed" in hours_str.lower():
                        warnings.append(
                            f"{activity.place.name} may be closed"
                        )
                        break

        return warnings
