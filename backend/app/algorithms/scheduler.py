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
from app.config.planning import PACE_CONFIGS, DINING_TYPES as _DINING_TYPES_SET
from app.models.day_plan import Activity, Place, Route
from app.models.internal import DayGroup, PlaceCandidate
from app.config.planning import DURATION_BY_TYPE

logger = logging.getLogger(__name__)

# Day-name abbreviations for formatting opening hours (Google format: 0=Sunday)
_OH_DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# Use the single consolidated duration map from config
DURATION_BY_CATEGORY = DURATION_BY_TYPE

PACE_MULTIPLIERS: dict[Pace, float] = {
    p: PACE_CONFIGS[p.value].duration_multiplier for p in Pace
}


def _parse_time_str(time_str: str) -> time:
    """Parse HH:MM time string to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


# Meal-related type identifiers
_MEAL_TYPES: set[str] = _DINING_TYPES_SET


@dataclass
class ScheduleConfig:
    """Configuration for schedule building.

    Meal windows default to common international times but can be
    overridden per-city for culture-appropriate scheduling.
    Meal windows cover ~80 countries across 10 regional profiles.
    LLM-provided meal windows take priority via from_context().
    """

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

    @classmethod
    def for_region(cls, country: str) -> "ScheduleConfig":
        """Return a ScheduleConfig with meal windows adapted to local culture.

        Uses broad regional patterns rather than a per-country database.
        The LLM day planner already suggests culture-appropriate meal
        times; this ensures the scheduler doesn't penalize them.
        """
        c = country.lower().strip()

        # Late-dining cultures (Spain, Portugal, Argentina, Greece, Italy)
        if c in ("spain", "portugal", "argentina", "greece", "italy"):
            return cls(
                lunch_window_start=time(13, 30),
                lunch_window_end=time(15, 30),
                dinner_window_start=time(20, 0),
                dinner_window_end=time(22, 30),
                lunch_target=time(14, 0),
                dinner_target=time(21, 0),
            )

        # Early-dining cultures (Japan, Korea, parts of SE Asia)
        if c in ("japan", "south korea", "korea", "taiwan"):
            return cls(
                lunch_window_start=time(11, 30),
                lunch_window_end=time(13, 30),
                dinner_window_start=time(17, 30),
                dinner_window_end=time(20, 0),
                lunch_target=time(12, 0),
                dinner_target=time(18, 30),
            )

        # South Asian patterns (India, Sri Lanka, Nepal)
        if c in ("india", "sri lanka", "nepal", "bangladesh", "pakistan"):
            return cls(
                lunch_window_start=time(12, 30),
                lunch_window_end=time(14, 30),
                dinner_window_start=time(19, 30),
                dinner_window_end=time(21, 30),
                lunch_target=time(13, 0),
                dinner_target=time(20, 0),
            )

        # Middle Eastern patterns (late lunch, late dinner)
        if c in ("turkey", "iran", "iraq", "lebanon", "syria", "jordan",
                 "saudi arabia", "uae", "united arab emirates", "qatar",
                 "bahrain", "kuwait", "oman", "egypt"):
            return cls(
                lunch_window_start=time(13, 0),
                lunch_window_end=time(15, 0),
                dinner_window_start=time(19, 0),
                dinner_window_end=time(22, 0),
                lunch_target=time(13, 30),
                dinner_target=time(20, 0),
            )

        # China and Vietnam (early and structured meals)
        if c in ("china", "vietnam", "hong kong", "macau"):
            return cls(
                lunch_window_start=time(11, 30),
                lunch_window_end=time(13, 0),
                dinner_window_start=time(17, 30),
                dinner_window_end=time(19, 30),
                lunch_target=time(12, 0),
                dinner_target=time(18, 0),
            )

        # Southeast Asian patterns (flexible, many snack meals)
        if c in ("thailand", "malaysia", "indonesia", "philippines",
                 "singapore", "myanmar", "cambodia", "laos"):
            return cls(
                lunch_window_start=time(11, 30),
                lunch_window_end=time(13, 30),
                dinner_window_start=time(18, 0),
                dinner_window_end=time(20, 30),
                lunch_target=time(12, 0),
                dinner_target=time(18, 30),
            )

        # Northern/Central European (early dinner)
        if c in ("germany", "austria", "switzerland", "netherlands",
                 "belgium", "denmark", "sweden", "norway", "finland",
                 "iceland", "poland", "czech republic", "czechia",
                 "hungary", "slovakia"):
            return cls(
                lunch_window_start=time(12, 0),
                lunch_window_end=time(13, 30),
                dinner_window_start=time(18, 0),
                dinner_window_end=time(20, 0),
                lunch_target=time(12, 30),
                dinner_target=time(18, 30),
            )

        # Eastern European patterns
        if c in ("russia", "ukraine", "romania", "bulgaria", "serbia",
                 "croatia", "slovenia", "bosnia", "montenegro", "albania",
                 "north macedonia", "georgia", "armenia", "azerbaijan"):
            return cls(
                lunch_window_start=time(12, 30),
                lunch_window_end=time(14, 0),
                dinner_window_start=time(19, 0),
                dinner_window_end=time(21, 0),
                lunch_target=time(13, 0),
                dinner_target=time(19, 30),
            )

        # Latin American patterns (late meals, similar to Spain)
        if c in ("mexico", "colombia", "peru", "chile", "brazil",
                 "ecuador", "bolivia", "venezuela", "uruguay", "paraguay",
                 "costa rica", "panama", "cuba", "dominican republic"):
            return cls(
                lunch_window_start=time(13, 0),
                lunch_window_end=time(15, 0),
                dinner_window_start=time(19, 30),
                dinner_window_end=time(22, 0),
                lunch_target=time(13, 30),
                dinner_target=time(20, 30),
            )

        # African patterns (varied, moderate defaults)
        if c in ("south africa", "kenya", "tanzania", "morocco",
                 "tunisia", "ethiopia", "ghana", "nigeria", "senegal",
                 "uganda", "rwanda", "mozambique", "namibia", "botswana"):
            return cls(
                lunch_window_start=time(12, 0),
                lunch_window_end=time(14, 0),
                dinner_window_start=time(18, 30),
                dinner_window_end=time(21, 0),
                lunch_target=time(12, 30),
                dinner_target=time(19, 0),
            )

        # Australia / New Zealand (early dinner)
        if c in ("australia", "new zealand"):
            return cls(
                lunch_window_start=time(12, 0),
                lunch_window_end=time(13, 30),
                dinner_window_start=time(18, 0),
                dinner_window_end=time(20, 0),
                lunch_target=time(12, 30),
                dinner_target=time(18, 30),
            )

        # Default international windows
        return cls()

    @classmethod
    def from_context(
        cls,
        country: str,
        meal_windows: dict[str, str] | None = None,
    ) -> "ScheduleConfig":
        """Create a ScheduleConfig from optional LLM-provided meal windows.

        If the LLM day planner suggests meal windows, those take priority
        over hardcoded regional defaults. Falls back to for_region().

        Args:
            country: Country name for regional defaults.
            meal_windows: Optional dict with keys like 'lunch_start',
                'lunch_end', 'dinner_start', 'dinner_end' in HH:MM format.
        """
        base = cls.for_region(country)
        if not meal_windows:
            return base
        try:
            if "lunch_start" in meal_windows:
                base.lunch_window_start = _parse_time_str(meal_windows["lunch_start"])
            if "lunch_end" in meal_windows:
                base.lunch_window_end = _parse_time_str(meal_windows["lunch_end"])
            if "dinner_start" in meal_windows:
                base.dinner_window_start = _parse_time_str(meal_windows["dinner_start"])
            if "dinner_end" in meal_windows:
                base.dinner_window_end = _parse_time_str(meal_windows["dinner_end"])
        except (ValueError, IndexError):
            pass  # Fall back to regional defaults on parse error
        return base


def _price_level_to_tier(price_level: int | None) -> str | None:
    """Map Google Places price_level (0-4) to budget tier string."""
    if price_level is None:
        return None
    tiers = ["free", "budget", "moderate", "expensive", "luxury"]
    return tiers[min(price_level, 4)]


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
        cost_estimates: dict[str, float] | None = None,
        country: str | None = None,
    ) -> list[Activity]:
        """
        Build a time-slotted schedule for a day's activities.

        Meals are scheduled at culture-appropriate times based on *country*.
        If no country is provided, default international windows are used.

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
            cost_estimates: Optional per-place cost estimates (USD) keyed by
                place_id.

        Returns:
            List of Activity with calculated time slots.
        """
        if not places:
            return []

        # Apply culture-aware meal windows if country is provided
        config = self.config
        if country:
            config = ScheduleConfig.for_region(country)

        routes = routes or []
        durations = durations or {}
        the_date = schedule_date or date.today()

        schedule: list[Activity] = []
        effective_start = day_start_time or config.day_start
        effective_end = day_end_time or config.day_end
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

            # Apply opening hours constraints (start time + closing time)
            oh_result = self._apply_opening_hours_constraints(place, current_time, duration)
            if oh_result is None:
                logger.warning(
                    "Skipping %s: closed or insufficient time before closing", place.name
                )
                continue
            current_time, duration = oh_result

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
                        and current_time_only >= config.dinner_window_start
                    )
                )

                if is_lunch_slot and not has_lunch:
                    if (
                        has_prior_activities
                        and current_time_only < config.lunch_window_start
                    ):
                        target = datetime.combine(
                            the_date, config.lunch_target
                        )
                        wait_mins = (target - current_time).total_seconds() / 60
                        if wait_mins <= config.max_meal_wait_minutes:
                            current_time = target
                        # else: schedule immediately, don't create large gap
                    has_lunch = True

                elif is_dinner_slot and not has_dinner:
                    if current_time_only < config.dinner_window_start:
                        target = datetime.combine(
                            the_date, config.dinner_target
                        )
                        wait_mins = (target - current_time).total_seconds() / 60
                        if wait_mins <= config.max_meal_wait_minutes:
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

            # Format opening hours as human-readable strings for downstream consumers
            formatted_hours = []
            if place.opening_hours:
                for oh in place.opening_hours:
                    day_name = _OH_DAY_NAMES[oh.day] if 0 <= oh.day <= 6 else f"Day{oh.day}"
                    formatted_hours.append(f"{day_name}: {oh.open_time} \u2013 {oh.close_time}")

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
                opening_hours=formatted_hours,
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
                    estimated_cost_usd=cost_estimates.get(place.place_id) if cost_estimates else None,
                    price_tier=_price_level_to_tier(place.price_level),
                )
            )

            # Advance current_time past this activity + travel + buffer
            travel_minutes = 0
            if i < len(routes):
                travel_minutes = routes[i].duration_seconds // 60

            current_time = end_time + timedelta(
                minutes=travel_minutes + config.buffer_minutes
            )

        # Validate meal count
        meal_count = sum(
            1 for a in schedule
            if a.place.category.lower() in {"restaurant", "cafe", "bakery", "bar", "dining", "food"}
            and a.duration_minutes > 0
        )
        if meal_count < 2:
            logger.warning(
                "[Scheduler] Schedule has only %d dining activities (expected 2: lunch + dinner)",
                meal_count,
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
            logger.debug(
                "[Scheduler] No LLM/Google duration for %s (%s) — using fallback %d min",
                place.name, place.types[0] if place.types else "unknown", base_duration,
            )

        # Apply pace multiplier
        multiplier = PACE_MULTIPLIERS.get(pace, 1.0)
        adjusted = int(base_duration * multiplier)

        # Round to nearest 15 minutes
        return ((adjusted + 7) // 15) * 15

    def _apply_opening_hours_constraints(
        self,
        place: PlaceCandidate,
        current_time: datetime,
        duration: int,
    ) -> tuple[datetime, int] | None:
        """
        Apply opening-hours constraints to an activity.

        Returns None if the place is closed or there's insufficient time
        before closing (less than min_activity_duration).  Otherwise returns
        an ``(adjusted_start, adjusted_duration)`` tuple — pushing the start
        forward when the place hasn't opened yet, and truncating the duration
        when the activity would otherwise run past closing time.

        If no opening-hours data is available, returns the inputs unchanged.
        """
        if not place.opening_hours:
            return current_time, duration

        day_of_week = current_time.weekday()
        # Convert to Google's format (0=Sunday)
        google_day = (day_of_week + 1) % 7

        for hours in place.opening_hours:
            if hours.day == google_day:
                open_time = datetime.strptime(hours.open_time, "%H:%M").time()
                close_time = datetime.strptime(hours.close_time, "%H:%M").time()

                # Push start forward if place hasn't opened yet
                start = current_time
                if start.time() < open_time:
                    start = datetime.combine(current_time.date(), open_time)

                # Midnight (00:00) means "open until midnight" or 24h — no truncation needed
                if close_time == time(0, 0):
                    return start, duration

                # Already past closing time
                if start.time() >= close_time:
                    return None

                # Truncate duration to fit within closing time
                close_dt = datetime.combine(current_time.date(), close_time)
                available_minutes = int((close_dt - start).total_seconds()) // 60

                if available_minutes < self.config.min_activity_duration:
                    return None

                adjusted_duration = min(duration, available_minutes)
                return start, adjusted_duration

        # No matching day found — schedule normally
        return current_time, duration

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
