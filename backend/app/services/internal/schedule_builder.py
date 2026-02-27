"""Schedule builder service for deterministic time slot calculation."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional

from app.config.planning import DURATION_BY_TYPE
from app.config.tuning import SCHEDULING
from app.models import Pace, PlaceCandidate, Route, ScheduledActivity

logger = logging.getLogger(__name__)


# Pace multipliers for duration
PACE_MULTIPLIERS = {
    Pace.RELAXED: 1.3,  # More time per activity
    Pace.MODERATE: 1.0,
    Pace.PACKED: 0.8,  # Less time per activity
}


def _parse_time_str(time_str: str) -> time:
    """Parse HH:MM time string to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


@dataclass
class ScheduleConfig:
    """Configuration for schedule building.
    
    Defaults are loaded from app/config/tuning.py.
    """

    day_start: time = field(default_factory=lambda: _parse_time_str(SCHEDULING.default_day_start))
    day_end: time = field(default_factory=lambda: _parse_time_str(SCHEDULING.default_day_end))
    lunch_window_start: time = field(default_factory=lambda: _parse_time_str(SCHEDULING.lunch_start))
    lunch_window_end: time = field(default_factory=lambda: _parse_time_str(SCHEDULING.lunch_end))
    dinner_window_start: time = field(default_factory=lambda: _parse_time_str(SCHEDULING.dinner_start))
    dinner_window_end: time = field(default_factory=lambda: _parse_time_str(SCHEDULING.dinner_end))
    # Target times for meals when we need to wait
    lunch_target: time = time(12, 30)
    dinner_target: time = time(19, 0)
    buffer_minutes: int = SCHEDULING.transition_buffer


class ScheduleBuilder:
    """Service for building deterministic schedules."""

    def __init__(self, config: Optional[ScheduleConfig] = None):
        """Initialize schedule builder with optional custom config."""
        self.config = config or ScheduleConfig()

    def build_schedule(
        self,
        places: list[PlaceCandidate],
        routes: list[Route],
        schedule_date: date,
        pace: Pace,
    ) -> list[ScheduledActivity]:
        """
        Build a time-slotted schedule for a day's activities.
        
        Meals are scheduled at appropriate times:
        - Lunch: 12:00-14:00 (target 12:30)
        - Dinner: 18:30-21:00 (target 19:00)
        
        If a meal activity arrives before its window, we wait.

        Args:
            places: Ordered list of places to visit
            routes: Routes between consecutive places
            schedule_date: The date for this schedule
            pace: Trip pace affecting durations

        Returns:
            List of ScheduledActivity with calculated time slots
        """
        if not places:
            return []

        schedule = []
        current_time = datetime.combine(schedule_date, self.config.day_start)
        day_end = datetime.combine(schedule_date, self.config.day_end)

        has_lunch = False
        has_dinner = False
        
        # Count meal places to understand meal distribution
        meal_places = [p for p in places if self._is_meal_place(p)]
        num_meals = len(meal_places)
        meals_scheduled = 0

        for i, place in enumerate(places):
            # Get duration for this place
            duration = self._get_duration(place, pace)

            # Check if place is open at current time
            adjusted_time = self._adjust_for_opening_hours(place, current_time)
            if adjusted_time:
                current_time = adjusted_time

            current_time_only = current_time.time()
            is_meal = self._is_meal_place(place)

            # Smart meal timing: wait for appropriate meal window
            if is_meal:
                meals_scheduled += 1
                # Determine if this should be lunch or dinner
                # First meal = lunch, second meal = dinner (or only meal in evening = dinner)
                is_lunch_slot = (meals_scheduled == 1 and num_meals >= 1)
                is_dinner_slot = (meals_scheduled == 2) or (meals_scheduled == 1 and current_time_only >= self.config.dinner_window_start)
                
                if is_lunch_slot and not has_lunch:
                    # This is lunch - wait for lunch window if too early
                    if current_time_only < self.config.lunch_window_start:
                        logger.info(f"Waiting for lunch window: {current_time_only} -> {self.config.lunch_target}")
                        current_time = datetime.combine(schedule_date, self.config.lunch_target)
                    has_lunch = True
                    
                elif is_dinner_slot and not has_dinner:
                    # This is dinner - wait for dinner window if too early
                    if current_time_only < self.config.dinner_window_start:
                        logger.info(f"Waiting for dinner window: {current_time_only} -> {self.config.dinner_target}")
                        current_time = datetime.combine(schedule_date, self.config.dinner_target)
                    has_dinner = True
            
            # Handle non-meal activities during meal windows (insert break if needed)
            elif not is_meal:
                # If we're in lunch window without having had lunch, and there's a meal coming later
                remaining_meals = num_meals - meals_scheduled
                if (
                    not has_lunch
                    and remaining_meals > 0
                    and self.config.lunch_window_start <= current_time_only < self.config.lunch_window_end
                ):
                    # Skip to after lunch window - a meal will fill this time
                    pass  # Don't skip, let the meal place handle timing

            # Calculate end time
            end_time = current_time + timedelta(minutes=duration)

            # Check if exceeds day end
            if end_time > day_end:
                # If already past day_end, skip entirely
                if current_time >= day_end:
                    logger.warning(f"Skipping {place.name}: already past day end")
                    continue
                logger.warning(
                    f"Activity {place.name} would exceed day end, adjusting or skipping"
                )
                # Try to fit with reduced duration
                available_minutes = int((day_end - current_time).total_seconds()) // 60
                if available_minutes >= SCHEDULING.min_activity_duration:
                    duration = available_minutes
                    end_time = day_end
                else:
                    # Skip this activity
                    continue

            # Add to schedule
            schedule.append(
                ScheduledActivity(
                    place=place,
                    start_time=current_time.strftime("%H:%M"),
                    end_time=end_time.strftime("%H:%M"),
                    duration_minutes=duration,
                )
            )

            # Calculate next start time (end + travel + buffer)
            if i < len(routes):
                travel_minutes = routes[i].duration_seconds // 60
            else:
                travel_minutes = 0

            current_time = end_time + timedelta(
                minutes=travel_minutes + self.config.buffer_minutes
            )

        return schedule

    def _get_duration(self, place: PlaceCandidate, pace: Pace) -> int:
        """Get duration for a place based on LLM estimate, type, and pace.
        
        Priority:
        1. LLM-estimated duration (from suggested_duration_minutes)
        2. Type-based fallback (DURATION_BY_TYPE)
        """
        # Use LLM-suggested duration if available
        if place.suggested_duration_minutes:
            base_duration = place.suggested_duration_minutes
            logger.debug(f"Using LLM duration for {place.name}: {base_duration} min")
        else:
            # Fallback to type-based duration
            base_duration = DURATION_BY_TYPE["default"]
            for place_type in place.types:
                if place_type in DURATION_BY_TYPE:
                    base_duration = DURATION_BY_TYPE[place_type]
                    break

        # Apply pace multiplier
        multiplier = PACE_MULTIPLIERS.get(pace, 1.0)
        adjusted = int(base_duration * multiplier)

        # Round to nearest 15 minutes
        return ((adjusted + 7) // 15) * 15

    def _adjust_for_opening_hours(
        self, place: PlaceCandidate, current_time: datetime
    ) -> Optional[datetime]:
        """
        Adjust start time if place isn't open yet.

        Returns None if no adjustment needed, otherwise returns adjusted time.
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
        """Check if place is a restaurant/cafe suitable for meals."""
        meal_types = {"restaurant", "cafe", "bakery", "bar", "food"}
        return bool(set(place.types) & meal_types)

    def validate_schedule(
        self, schedule: list[ScheduledActivity], places: list[PlaceCandidate]
    ) -> list[str]:
        """
        Validate a schedule for conflicts and issues.

        Returns list of warning messages.
        """
        warnings = []

        for i, activity in enumerate(schedule):
            # Check for overlapping times
            if i > 0:
                prev_end = datetime.strptime(schedule[i - 1].end_time, "%H:%M")
                curr_start = datetime.strptime(activity.start_time, "%H:%M")
                if curr_start < prev_end:
                    warnings.append(
                        f"Overlap: {schedule[i-1].place.name} ends after {activity.place.name} starts"
                    )

            # Check opening hours
            if activity.place.opening_hours:
                start_time = datetime.strptime(activity.start_time, "%H:%M").time()
                end_time = datetime.strptime(activity.end_time, "%H:%M").time()

                # Find today's hours (simplified check)
                for hours in activity.place.opening_hours:
                    close_time = datetime.strptime(hours.close_time, "%H:%M").time()
                    if end_time > close_time:
                        warnings.append(
                            f"{activity.place.name} may close before visit ends"
                        )
                        break

        return warnings
