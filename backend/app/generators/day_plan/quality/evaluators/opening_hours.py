"""Opening hours quality evaluator."""

import re
from datetime import time
from typing import TYPE_CHECKING

from app.generators.day_plan.quality.evaluators.base import BaseEvaluator
from app.generators.day_plan.quality.models import MetricResult, METRIC_WEIGHTS

if TYPE_CHECKING:
    from app.models import ItineraryResponse, DayPlan, Activity


class OpeningHoursEvaluator(BaseEvaluator):
    """
    Evaluates if activities are scheduled when places are open.
    
    Checks:
    - Scheduled time falls within opening hours
    - Accounts for lunch breaks at some venues
    - Handles 24-hour and closed days
    """
    
    @property
    def name(self) -> str:
        return "Opening Hours"
    
    @property
    def weight(self) -> float:
        return METRIC_WEIGHTS["opening_hours"]
    
    def evaluate(self, itinerary: "ItineraryResponse") -> MetricResult:
        issues: list[str] = []
        suggestions: list[str] = []
        
        if not itinerary.days:
            return self._create_result(score=100, issues=[], suggestions=[])
        
        total_checked = 0
        valid_schedules = 0
        unknown_hours = 0
        
        details = {
            "activities_checked": 0,
            "activities_valid": 0,
            "activities_closed": 0,
            "activities_unknown": 0,
        }
        
        for day in itinerary.days:
            for activity in day.activities:
                result = self._check_activity(activity, day.date)
                total_checked += 1
                details["activities_checked"] += 1
                
                if result["status"] == "valid":
                    valid_schedules += 1
                    details["activities_valid"] += 1
                elif result["status"] == "unknown":
                    unknown_hours += 1
                    details["activities_unknown"] += 1
                    # Don't penalize unknown - give benefit of doubt
                    valid_schedules += 1
                else:
                    details["activities_closed"] += 1
                    issues.append(result["issue"])
                    if result.get("suggestion"):
                        suggestions.append(result["suggestion"])
        
        # Calculate score
        if total_checked == 0:
            score = 100.0
        else:
            # Count unknowns as valid (give benefit of doubt)
            score = (valid_schedules / total_checked) * 100
        
        return self._create_result(
            score=score,
            issues=issues,
            suggestions=suggestions,
            details=details,
        )
    
    def _check_activity(self, activity: "Activity", date) -> dict:
        """Check if an activity is scheduled during open hours."""
        opening_hours = activity.place.opening_hours
        
        # If no opening hours data, we can't verify
        if not opening_hours:
            return {"status": "unknown"}
        
        # Parse activity time
        activity_time = self._parse_time(activity.time_start)
        if not activity_time:
            return {"status": "unknown"}
        
        # Get day of week
        if date:
            day_name = date.strftime("%a")  # "Mon", "Tue", etc.
        else:
            return {"status": "unknown"}
        
        # Find matching hours for this day
        day_hours = self._find_day_hours(opening_hours, day_name)
        
        if day_hours is None:
            # Couldn't parse hours
            return {"status": "unknown"}
        
        if day_hours == "closed":
            return {
                "status": "closed",
                "issue": f"'{activity.place.name}' is closed on {day_name}",
                "suggestion": f"Reschedule '{activity.place.name}' to a different day",
            }
        
        # Check if activity time falls within opening hours
        # At this point, day_hours is list[tuple[time, time]] (not str or None)
        time_windows: list[tuple[time, time]] = day_hours  # type: ignore[assignment]
        for window in time_windows:
            if self._time_in_window(activity_time, window):
                return {"status": "valid"}
        
        # Not within any window
        hours_str = ", ".join([f"{w[0].strftime('%H:%M')}-{w[1].strftime('%H:%M')}" for w in time_windows])
        return {
            "status": "closed",
            "issue": f"'{activity.place.name}' scheduled at {activity.time_start} but opens {hours_str}",
            "suggestion": f"Adjust timing for '{activity.place.name}' to match opening hours",
        }
    
    def _parse_time(self, time_str: str) -> time | None:
        """Parse time string like '12:30' to time object."""
        try:
            parts = time_str.split(":")
            return time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError, AttributeError):
            return None
    
    def _find_day_hours(self, opening_hours: list[str], day_abbrev: str) -> list[tuple[time, time]] | str | None:
        """
        Find opening hours for a specific day.
        
        Returns:
            - List of (open_time, close_time) windows
            - "closed" if explicitly closed
            - None if couldn't determine
        """
        # Map abbreviations
        day_map = {
            "Mon": ["Mon", "Monday"],
            "Tue": ["Tue", "Tuesday"],
            "Wed": ["Wed", "Wednesday"],
            "Thu": ["Thu", "Thursday"],
            "Fri": ["Fri", "Friday"],
            "Sat": ["Sat", "Saturday"],
            "Sun": ["Sun", "Sunday"],
        }
        
        day_names = day_map.get(day_abbrev, [day_abbrev])
        
        windows = []
        is_closed = False
        
        for hours_str in opening_hours:
            # Check if this entry is for our day
            hours_lower = hours_str.lower()
            if not any(name.lower() in hours_lower for name in day_names):
                continue
            
            # Check for closed
            if "closed" in hours_lower:
                is_closed = True
                continue
            
            # Parse time range (e.g., "Mon: 09:00 - 17:00" or "Monday: 9:00 AM - 5:00 PM")
            time_pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?'
            match = re.search(time_pattern, hours_str, re.IGNORECASE)
            
            if match:
                open_hour = int(match.group(1))
                open_min = int(match.group(2) or 0)
                open_ampm = match.group(3)
                
                close_hour = int(match.group(4))
                close_min = int(match.group(5) or 0)
                close_ampm = match.group(6)
                
                # Convert to 24-hour
                if open_ampm and open_ampm.lower() == 'pm' and open_hour < 12:
                    open_hour += 12
                elif open_ampm and open_ampm.lower() == 'am' and open_hour == 12:
                    open_hour = 0
                    
                if close_ampm and close_ampm.lower() == 'pm' and close_hour < 12:
                    close_hour += 12
                elif close_ampm and close_ampm.lower() == 'am' and close_hour == 12:
                    close_hour = 0
                
                try:
                    open_time = time(open_hour, open_min)
                    close_time = time(close_hour, close_min)
                    windows.append((open_time, close_time))
                except ValueError:
                    continue
        
        if windows:
            return windows
        elif is_closed:
            return "closed"
        else:
            return None
    
    def _time_in_window(self, t: time, window: tuple[time, time]) -> bool:
        """Check if time t falls within the window."""
        open_time, close_time = window
        
        # Handle overnight windows (e.g., 22:00 - 02:00)
        if close_time < open_time:
            return t >= open_time or t <= close_time
        else:
            return open_time <= t <= close_time
