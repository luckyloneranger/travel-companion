"""Scheduling pipeline — time slot assignment for day plan activities."""

import logging
from datetime import time, datetime, timedelta
from dataclasses import dataclass

from app.algorithms.scheduler import ScheduleConfig
from app.config.planning import PACE_CONFIGS, DURATION_BY_TYPE

logger = logging.getLogger(__name__)

# Pace multipliers for activity duration
PACE_MULTIPLIERS = {
    "relaxed": 1.3,
    "moderate": 1.0,
    "packed": 0.8,
}


@dataclass
class ScheduledActivity:
    """Activity with assigned time slot."""
    sequence: int
    start_time: time
    end_time: time
    duration_minutes: int
    # Pass through all other fields from input
    data: dict  # original activity data


class SchedulingPipeline:
    def schedule_day(
        self,
        activities: list[dict],
        routes: list[dict],
        country: str = "",
        pace: str = "moderate",
    ) -> list[ScheduledActivity]:
        """Assign time slots to a day's activities.

        Respects:
        - Culture-aware meal windows (via ScheduleConfig.for_region)
        - Pace multipliers (relaxed=1.3x, moderate=1.0x, packed=0.8x)
        - Opening hours (truncate/skip if activity would end after close)
        - Transit time between activities
        """
        if not activities:
            return []

        config = ScheduleConfig.for_region(country)
        multiplier = PACE_MULTIPLIERS.get(pace, 1.0)

        scheduled = []
        current_time = self._time_to_minutes(config.day_start)

        for i, activity in enumerate(activities):
            # Get base duration
            base_duration = activity.get("duration_minutes", 0)
            if not base_duration:
                # Fallback from type
                category = activity.get("category", "")
                base_duration = DURATION_BY_TYPE.get(category, 45)

            # Apply pace multiplier
            duration = max(15, int(base_duration * multiplier))

            # Check if this is a meal — try to align with meal windows
            is_meal = activity.get("is_meal", False)
            meal_type = activity.get("meal_type")

            if is_meal and meal_type == "lunch":
                lunch_start = self._time_to_minutes(config.lunch_window_start)
                lunch_end = self._time_to_minutes(config.lunch_window_end)
                if current_time < lunch_start:
                    # Too early for lunch — could wait, but only if gap is small
                    gap = lunch_start - current_time
                    if gap <= 30:
                        current_time = lunch_start
                elif current_time > lunch_end:
                    pass  # Too late, just schedule when we can
            elif is_meal and meal_type == "dinner":
                dinner_start = self._time_to_minutes(config.dinner_window_start)
                dinner_end = self._time_to_minutes(config.dinner_window_end)
                if current_time < dinner_start:
                    gap = dinner_start - current_time
                    if gap <= 30:
                        current_time = dinner_start

            # Check opening hours
            opening_hours = activity.get("opening_hours") or activity.get("place_opening_hours")
            if opening_hours:
                close_minutes = self._get_close_time(opening_hours)
                if close_minutes and current_time + duration > close_minutes:
                    if current_time >= close_minutes:
                        logger.warning(f"Skipping activity {activity.get('name', '?')} — already past closing")
                        continue
                    # Truncate
                    duration = max(15, close_minutes - current_time)

            start = self._minutes_to_time(current_time)
            end = self._minutes_to_time(current_time + duration)

            scheduled.append(ScheduledActivity(
                sequence=activity.get("sequence", i + 1),
                start_time=start,
                end_time=end,
                duration_minutes=duration,
                data=activity,
            ))

            # Advance clock: duration + transit to next
            transit = 0
            if i < len(routes):
                transit = routes[i].get("duration_seconds", 0) // 60
            current_time += duration + transit + config.buffer_minutes

            # Don't schedule past day end
            day_end = self._time_to_minutes(config.day_end)
            if current_time >= day_end:
                break

        return scheduled

    def _time_to_minutes(self, t: time) -> int:
        return t.hour * 60 + t.minute

    def _minutes_to_time(self, minutes: int) -> time:
        minutes = max(0, min(minutes, 23 * 60 + 59))
        return time(minutes // 60, minutes % 60)

    def _get_close_time(self, opening_hours) -> int | None:
        """Extract closing time in minutes from opening hours data."""
        if not opening_hours:
            return None
        # Opening hours could be a list of dicts with 'close' key
        # or formatted strings — handle both
        for oh in opening_hours:
            if isinstance(oh, dict) and "close" in oh:
                close_str = oh["close"]
                if isinstance(close_str, str) and ":" in close_str:
                    parts = close_str.split(":")
                    h, m = int(parts[0]), int(parts[1])
                    if h == 0 and m == 0:
                        return 24 * 60  # midnight = open until midnight
                    return h * 60 + m
        return None
