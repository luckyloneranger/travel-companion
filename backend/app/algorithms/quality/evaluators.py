"""Quality metric evaluators for itinerary scoring.

All 7 evaluators ported from the original codebase.  Each evaluator
has an ``evaluate(day_plans, context)`` method that returns an
:class:`EvaluatorResult`.

The ``context`` dict may contain:
- ``destination`` (str): trip destination name
- ``theme`` (str): overall trip theme
- ``num_days`` (int): number of days
"""

import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from datetime import time
from typing import Any

from app.algorithms.quality.models import EvaluatorResult
from app.models.day_plan import Activity, DayPlan

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HAVERSINE_R = 6_371.0  # Earth radius in km


def _haversine_km(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """Haversine distance in kilometres between two lat/lng pairs."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(d_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _HAVERSINE_R * c


def _parse_time(time_str: str) -> time | None:
    """Parse ``HH:MM`` string to a :class:`time` object."""
    try:
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError, AttributeError):
        return None


def _in_window(t: time, window: tuple[time, time]) -> bool:
    """Return True if *t* falls within *window* (inclusive)."""
    return window[0] <= t <= window[1]


def _grade_from_score(score: float) -> str:
    """Map a 0-100 score to a letter grade."""
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 85:
        return "A-"
    if score >= 80:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 65:
        return "C+"
    if score >= 60:
        return "C"
    if score >= 55:
        return "C-"
    if score >= 50:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseEvaluator(ABC):
    """Abstract base class for quality metric evaluators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the metric."""

    @property
    @abstractmethod
    def weight(self) -> float:
        """Weight of this metric in overall score (0-1)."""

    @abstractmethod
    def evaluate(
        self, day_plans: list[DayPlan], context: dict[str, Any] | None = None
    ) -> EvaluatorResult:
        """Evaluate the itinerary day plans for this metric."""

    def _clamp(self, score: float) -> float:
        return max(0.0, min(100.0, score))


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Meal Timing Evaluator
# ═══════════════════════════════════════════════════════════════════════════════

# Default meal time windows (can be overridden via context["meal_windows"])
_LUNCH_WINDOW = (time(12, 0), time(14, 30))
_DINNER_WINDOW = (time(18, 30), time(21, 0))

# Acceptable (but not ideal) windows
_LUNCH_ACCEPTABLE = (time(11, 0), time(15, 30))
_DINNER_ACCEPTABLE = (time(17, 30), time(22, 0))

# Place types (from Google Places API) that are NOT dining
_NON_DINING_PLACE_TYPES: set[str] = {
    "place_of_worship", "hindu_temple", "church", "mosque", "synagogue",
    "museum", "art_gallery", "historical_landmark", "monument",
    "palace", "castle", "fort", "park", "garden", "zoo", "aquarium",
    "tourist_attraction", "stadium", "library", "university",
    "national_park", "cemetery", "memorial", "shrine",
}

# Categories that indicate dining
_DINING_CATEGORIES: set[str] = {"dining", "restaurant", "cafe", "food"}


class MealTimingEvaluator(BaseEvaluator):
    """
    Evaluates meal timing quality.

    Checks:
    - Each day has lunch and dinner.
    - Meals are at appropriate times.
    - Meals are actual restaurants (not temples/attractions).
    - Meals are positioned correctly in the schedule.
    """

    @property
    def name(self) -> str:
        return "Meal Timing"

    @property
    def weight(self) -> float:
        return 0.20

    def evaluate(
        self, day_plans: list[DayPlan], context: dict[str, Any] | None = None
    ) -> EvaluatorResult:
        issues: list[str] = []
        if not day_plans:
            return EvaluatorResult(
                name=self.name, score=0, grade="F", issues=["No days in itinerary"]
            )

        # Allow context to override default meal windows
        ctx = context or {}
        lunch_window = ctx.get("lunch_window", _LUNCH_WINDOW)
        lunch_acceptable = ctx.get("lunch_acceptable", _LUNCH_ACCEPTABLE)
        dinner_window = ctx.get("dinner_window", _DINNER_WINDOW)
        dinner_acceptable = ctx.get("dinner_acceptable", _DINNER_ACCEPTABLE)

        total_checks = 0
        passed_checks = 0

        for day in day_plans:
            day_result = self._evaluate_day(day, lunch_acceptable, dinner_acceptable)
            total_checks += day_result["total_checks"]
            passed_checks += day_result["passed_checks"]
            issues.extend(day_result["issues"])

        score = self._clamp((passed_checks / total_checks) * 100 if total_checks else 0)
        return EvaluatorResult(
            name=self.name, score=score, grade=_grade_from_score(score), issues=issues
        )

    # ------------------------------------------------------------------ helpers

    def _evaluate_day(
        self,
        day: DayPlan,
        lunch_acceptable: tuple[time, time] = _LUNCH_ACCEPTABLE,
        dinner_acceptable: tuple[time, time] = _DINNER_ACCEPTABLE,
    ) -> dict:
        result: dict[str, Any] = {
            "total_checks": 0,
            "passed_checks": 0,
            "issues": [],
        }

        dining = [
            a
            for a in day.activities
            if (a.place.category.lower() if a.place.category else "") in _DINING_CATEGORIES
        ]

        # Check 1: Has lunch?
        result["total_checks"] += 1
        lunch = self._find_meal_in_window(dining, lunch_acceptable)
        if lunch:
            result["passed_checks"] += 1
        else:
            result["issues"].append(
                f"Day {day.day_number}: No lunch found between 11:00-15:30"
            )

        # Check 2: Has dinner?
        result["total_checks"] += 1
        dinner = self._find_meal_in_window(dining, dinner_acceptable)
        if dinner:
            result["passed_checks"] += 1
        else:
            result["issues"].append(
                f"Day {day.day_number}: No dinner found between 17:30-22:00"
            )

        # Check 3: Lunch position (mid-day, not first or last)
        if lunch and len(day.activities) >= 3:
            result["total_checks"] += 1
            lunch_idx = self._index_of(day.activities, lunch)
            if 1 <= lunch_idx <= len(day.activities) - 2:
                result["passed_checks"] += 1
            else:
                result["issues"].append(
                    f"Day {day.day_number}: Lunch at position {lunch_idx + 1} (should be mid-day)"
                )

        # Check 4: Dinner position (near end)
        if dinner and len(day.activities) >= 3:
            result["total_checks"] += 1
            dinner_idx = self._index_of(day.activities, dinner)
            if dinner_idx >= len(day.activities) - 2:
                result["passed_checks"] += 1
            else:
                result["issues"].append(
                    f"Day {day.day_number}: Dinner at position {dinner_idx + 1} (should be near end)"
                )

        # Check 5: No dining misclassification (use Google Places types)
        for a in dining:
            result["total_checks"] += 1
            place_types = {t.lower() for t in (a.place.types if hasattr(a.place, 'types') and a.place.types else [])}
            if place_types & _NON_DINING_PLACE_TYPES:
                result["issues"].append(
                    f"Day {day.day_number}: '{a.place.name}' appears to be "
                    "a non-restaurant classified as dining"
                )
            else:
                result["passed_checks"] += 1

        return result

    def _find_meal_in_window(
        self, dining: list[Activity], window: tuple[time, time]
    ) -> Activity | None:
        for a in dining:
            t = _parse_time(a.time_start)
            if t and _in_window(t, window):
                return a
        return None

    @staticmethod
    def _index_of(activities: list[Activity], target: Activity) -> int:
        for i, a in enumerate(activities):
            if a.time_start == target.time_start and a.place.name == target.place.name:
                return i
        return -1


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Geographic Clustering Evaluator
# ═══════════════════════════════════════════════════════════════════════════════

# Default distance thresholds (overridable via context["city_scale"])
_DISTANCE_SCALES: dict[str, dict[str, float]] = {
    "compact": {"max_gap": 3.0, "ideal_gap": 1.5, "max_daily": 15.0, "ideal_daily": 8.0},
    "medium": {"max_gap": 5.0, "ideal_gap": 2.0, "max_daily": 30.0, "ideal_daily": 15.0},
    "sprawling": {"max_gap": 10.0, "ideal_gap": 4.0, "max_daily": 50.0, "ideal_daily": 25.0},
}
_DEFAULT_SCALE = _DISTANCE_SCALES["medium"]


class GeographicClusteringEvaluator(BaseEvaluator):
    """
    Evaluates geographic clustering quality.

    Checks:
    - Activities within each day are geographically close.
    - No excessive backtracking.
    - Reasonable daily travel distances.
    """

    @property
    def name(self) -> str:
        return "Geographic Clustering"

    @property
    def weight(self) -> float:
        return 0.15

    def evaluate(
        self, day_plans: list[DayPlan], context: dict[str, Any] | None = None
    ) -> EvaluatorResult:
        issues: list[str] = []
        if not day_plans:
            return EvaluatorResult(
                name=self.name, score=100, grade="A+", issues=[]
            )

        # Allow context to override distance thresholds per city scale
        scale_name = (context or {}).get("city_scale")
        if not scale_name:
            # Auto-detect city scale from coordinate spread
            scale_name = self._detect_city_scale(day_plans)
        scale = _DISTANCE_SCALES.get(scale_name, _DEFAULT_SCALE)

        day_scores: list[float] = []
        for day in day_plans:
            ds, day_issues = self._evaluate_day(day, scale)
            day_scores.append(ds)
            issues.extend(day_issues)

        score = self._clamp(sum(day_scores) / len(day_scores) if day_scores else 100)
        return EvaluatorResult(
            name=self.name, score=score, grade=_grade_from_score(score), issues=issues
        )

    def _evaluate_day(self, day: DayPlan, scale: dict[str, float] | None = None) -> tuple[float, list[str]]:
        issues: list[str] = []
        if len(day.activities) < 2:
            return 100.0, issues

        s = scale or _DEFAULT_SCALE
        max_gap_km = s["max_gap"]
        ideal_gap_km = s["ideal_gap"]
        max_daily_km = s["max_daily"]
        ideal_daily_km = s["ideal_daily"]

        locations = [
            (a.place.location.lat, a.place.location.lng) for a in day.activities
        ]
        distances: list[float] = []
        total_distance = 0.0

        for i in range(len(locations) - 1):
            d = _haversine_km(
                locations[i][0], locations[i][1],
                locations[i + 1][0], locations[i + 1][1],
            )
            distances.append(d)
            total_distance += d
            if d > max_gap_km:
                issues.append(
                    f"Day {day.day_number}: {d:.1f}km gap between "
                    f"'{day.activities[i].place.name}' and "
                    f"'{day.activities[i + 1].place.name}'"
                )

        backtracking = self._detect_backtracking(locations)
        if backtracking > 0:
            issues.append(
                f"Day {day.day_number}: Detected {backtracking} potential "
                "backtracking instance(s)"
            )

        # Penalty calculation
        penalty = 0.0
        for d in distances:
            if d > max_gap_km:
                penalty += 15
            elif d > ideal_gap_km:
                penalty += (d - ideal_gap_km) * 3

        if total_distance > max_daily_km:
            penalty += 20
        elif total_distance > ideal_daily_km:
            penalty += (total_distance - ideal_daily_km) * 1.5

        penalty += backtracking * 10

        return max(0.0, 100.0 - penalty), issues

    @staticmethod
    def _detect_city_scale(day_plans: list[DayPlan]) -> str:
        """Auto-detect city scale from the spread of activity coordinates."""
        lats: list[float] = []
        lngs: list[float] = []
        for day in day_plans:
            for a in day.activities:
                if a.place.location.lat and a.place.location.lng:
                    lats.append(a.place.location.lat)
                    lngs.append(a.place.location.lng)
        if len(lats) < 3:
            return "medium"
        lat_spread = max(lats) - min(lats)
        lng_spread = max(lngs) - min(lngs)
        spread = max(lat_spread, lng_spread)
        if spread < 0.02:
            return "compact"
        if spread > 0.06:
            return "sprawling"
        return "medium"

    @staticmethod
    def _detect_backtracking(
        locations: list[tuple[float, float]],
    ) -> int:
        if len(locations) < 3:
            return 0
        threshold_km = 1.0
        count = 0
        for i in range(len(locations) - 2):
            lat1, lng1 = locations[i]
            lat2, lng2 = locations[i + 1]
            lat3, lng3 = locations[i + 2]
            d1 = _haversine_km(lat1, lng1, lat2, lng2)
            d2 = _haversine_km(lat2, lng2, lat3, lng3)
            if d1 < threshold_km or d2 < threshold_km:
                continue
            d_start_end = _haversine_km(lat1, lng1, lat3, lng3)
            total_travel = d1 + d2
            if total_travel > 0 and d_start_end / total_travel < 0.25:
                count += 1
        return count


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Travel Efficiency Evaluator
# ═══════════════════════════════════════════════════════════════════════════════

MAX_TRAVEL_MINUTES = 60
IDEAL_TRAVEL_MINUTES = 25
MAX_DAILY_TRAVEL_MINUTES = 150
IDEAL_DAILY_TRAVEL_MINUTES = 75


class TravelEfficiencyEvaluator(BaseEvaluator):
    """
    Evaluates travel time efficiency.

    Checks:
    - Travel times between activities are reasonable.
    - No excessive commuting.
    - Total daily travel time is manageable.
    """

    @property
    def name(self) -> str:
        return "Travel Efficiency"

    @property
    def weight(self) -> float:
        return 0.15

    def evaluate(
        self, day_plans: list[DayPlan], context: dict[str, Any] | None = None
    ) -> EvaluatorResult:
        issues: list[str] = []
        if not day_plans:
            return EvaluatorResult(
                name=self.name, score=100, grade="A+", issues=[]
            )

        # Allow context to override travel time thresholds
        ctx = context or {}
        max_travel = ctx.get("max_travel_minutes", MAX_TRAVEL_MINUTES)
        ideal_travel = ctx.get("ideal_travel_minutes", IDEAL_TRAVEL_MINUTES)
        max_daily = ctx.get("max_daily_travel_minutes", MAX_DAILY_TRAVEL_MINUTES)
        ideal_daily = ctx.get("ideal_daily_travel_minutes", IDEAL_DAILY_TRAVEL_MINUTES)

        day_scores: list[float] = []
        for day in day_plans:
            ds, day_issues = self._evaluate_day(day, max_travel, ideal_travel, max_daily, ideal_daily)
            day_scores.append(ds)
            issues.extend(day_issues)

        score = self._clamp(sum(day_scores) / len(day_scores) if day_scores else 100)
        return EvaluatorResult(
            name=self.name, score=score, grade=_grade_from_score(score), issues=issues
        )

    def _evaluate_day(
        self,
        day: DayPlan,
        max_travel: int = MAX_TRAVEL_MINUTES,
        ideal_travel: int = IDEAL_TRAVEL_MINUTES,
        max_daily: int = MAX_DAILY_TRAVEL_MINUTES,
        ideal_daily: int = IDEAL_DAILY_TRAVEL_MINUTES,
    ) -> tuple[float, list[str]]:
        issues: list[str] = []
        if len(day.activities) < 2:
            return 100.0, issues

        total_travel = 0
        longest_leg = 0
        penalty = 0.0

        for i, activity in enumerate(day.activities[:-1]):
            if activity.route_to_next:
                travel_min = activity.route_to_next.duration_seconds // 60
                total_travel += travel_min
                longest_leg = max(longest_leg, travel_min)

                if travel_min > max_travel:
                    penalty += 20
                    issues.append(
                        f"Day {day.day_number}: {travel_min}min travel from "
                        f"'{activity.place.name}' to "
                        f"'{day.activities[i + 1].place.name}'"
                    )
                elif travel_min > ideal_travel:
                    penalty += (travel_min - ideal_travel) * 0.5

        if total_travel > max_daily:
            penalty += 25
        elif total_travel > ideal_daily:
            penalty += (total_travel - ideal_daily) * 0.3

        return max(0.0, 100.0 - penalty), issues


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Variety Evaluator
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_GROUPS: dict[str, set[str]] = {
    "cultural": {"museum", "culture", "art_gallery", "heritage", "historical_landmark"},
    "religious": {"temple", "church", "mosque", "place_of_worship", "shrine"},
    "nature": {"park", "garden", "nature", "lake", "beach", "viewpoint"},
    "entertainment": {"entertainment", "amusement_park", "zoo", "aquarium", "theme_park"},
    "shopping": {"shopping", "market", "mall", "bazaar"},
    "dining": {"dining", "restaurant", "cafe", "food", "bar"},
    "landmark": {"tourist_attraction", "attraction", "landmark", "monument", "fort", "palace"},
}


class VarietyEvaluator(BaseEvaluator):
    """
    Evaluates activity variety and diversity.

    Checks:
    - Mix of activity types across the trip.
    - No excessive repetition of same category.
    - Each day has some variety.
    """

    @property
    def name(self) -> str:
        return "Variety & Diversity"

    @property
    def weight(self) -> float:
        return 0.15

    def evaluate(
        self, day_plans: list[DayPlan], context: dict[str, Any] | None = None
    ) -> EvaluatorResult:
        issues: list[str] = []
        if not day_plans:
            return EvaluatorResult(
                name=self.name, score=100, grade="A+", issues=[]
            )

        all_categories: list[str] = []
        category_groups_found: set[str] = set()
        day_scores: list[float] = []

        for day in day_plans:
            ds, cats, groups, day_issues = self._evaluate_day(day)
            day_scores.append(ds)
            all_categories.extend(cats)
            category_groups_found.update(groups)
            issues.extend(day_issues)

        total_activities = len(all_categories)
        category_counts = Counter(all_categories)

        # Over-concentration check
        if total_activities > 0:
            for category, count in category_counts.items():
                pct = (count / total_activities) * 100
                if pct > 50 and count > 4:
                    issues.append(
                        f"Over-concentration: {category} makes up {pct:.0f}% of activities"
                    )

        # Missing essentials
        essential_groups = {"dining", "landmark"}
        missing = essential_groups - category_groups_found

        base_score = sum(day_scores) / len(day_scores) if day_scores else 100
        variety_bonus = min(10, len(category_groups_found) * 2)
        essential_penalty = len(missing) * 10

        for m in missing:
            issues.append(f"Missing essential category group: {m}")

        score = self._clamp(base_score + variety_bonus - essential_penalty)
        return EvaluatorResult(
            name=self.name, score=score, grade=_grade_from_score(score), issues=issues
        )

    def _evaluate_day(
        self, day: DayPlan
    ) -> tuple[float, list[str], set[str], list[str]]:
        issues: list[str] = []
        categories: list[str] = []
        groups_found: set[str] = set()
        score = 100.0

        if not day.activities:
            return score, categories, groups_found, issues

        for a in day.activities:
            cat = a.place.category.lower() if a.place.category else "other"
            categories.append(cat)
            for group, group_cats in CATEGORY_GROUPS.items():
                if cat in group_cats:
                    groups_found.add(group)
                    break

        cat_counts = Counter(categories)
        non_dining = [
            c for c in categories if c not in CATEGORY_GROUPS["dining"]
        ]

        if len(non_dining) >= 3:
            for cat, count in cat_counts.items():
                if count >= 3 and cat not in CATEGORY_GROUPS["dining"]:
                    score -= 15
                    issues.append(
                        f"Day {day.day_number}: {count} activities of type '{cat}' (repetitive)"
                    )

        if len(groups_found) >= 3:
            score = min(100, score + 5)
        elif len(groups_found) == 1 and len(day.activities) > 2:
            score -= 10
            issues.append(
                f"Day {day.day_number}: All activities are in one category group"
            )

        return score, categories, groups_found, issues


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Opening Hours Evaluator
# ═══════════════════════════════════════════════════════════════════════════════

class OpeningHoursEvaluator(BaseEvaluator):
    """
    Evaluates if activities are scheduled when places are open.

    Checks:
    - Scheduled time falls within opening hours.
    - Handles 24-hour and closed days.
    """

    @property
    def name(self) -> str:
        return "Opening Hours"

    @property
    def weight(self) -> float:
        return 0.15

    def evaluate(
        self, day_plans: list[DayPlan], context: dict[str, Any] | None = None
    ) -> EvaluatorResult:
        issues: list[str] = []
        if not day_plans:
            return EvaluatorResult(
                name=self.name, score=100, grade="A+", issues=[]
            )

        total_checked = 0
        valid = 0

        for day in day_plans:
            for activity in day.activities:
                status, issue = self._check_activity(activity, day.date)
                total_checked += 1
                if status in ("valid", "unknown"):
                    valid += 1
                else:
                    if issue:
                        issues.append(issue)

        score = self._clamp((valid / total_checked) * 100 if total_checked else 100)
        return EvaluatorResult(
            name=self.name, score=score, grade=_grade_from_score(score), issues=issues
        )

    def _check_activity(
        self, activity: Activity, date_str: str | None
    ) -> tuple[str, str | None]:
        opening_hours = activity.place.opening_hours
        if not opening_hours:
            return "unknown", None

        activity_time = _parse_time(activity.time_start)
        if not activity_time:
            return "unknown", None

        if not date_str:
            return "unknown", None

        # Derive day abbreviation from date string
        try:
            from datetime import date as _date

            d = _date.fromisoformat(date_str)
            day_abbrev = d.strftime("%a")
        except (ValueError, TypeError):
            return "unknown", None

        day_hours = self._find_day_hours(opening_hours, day_abbrev)

        if day_hours is None:
            return "unknown", None

        if day_hours == "closed":
            return (
                "closed",
                f"'{activity.place.name}' is closed on {day_abbrev}",
            )

        # day_hours is list of time windows
        time_windows: list[tuple[time, time]] = day_hours  # type: ignore[assignment]
        for window in time_windows:
            if self._time_in_window(activity_time, window):
                return "valid", None

        hours_str = ", ".join(
            f"{w[0].strftime('%H:%M')}-{w[1].strftime('%H:%M')}" for w in time_windows
        )
        return (
            "closed",
            f"'{activity.place.name}' scheduled at {activity.time_start} but opens {hours_str}",
        )

    @staticmethod
    def _find_day_hours(
        opening_hours: list[str], day_abbrev: str
    ) -> list[tuple[time, time]] | str | None:
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

        windows: list[tuple[time, time]] = []
        is_closed = False

        for hs in opening_hours:
            hs_lower = hs.lower()
            if not any(n.lower() in hs_lower for n in day_names):
                continue
            if "closed" in hs_lower:
                is_closed = True
                continue

            pattern = (
                r"(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*[-\u2013]\s*"
                r"(\d{1,2}):?(\d{2})?\s*(am|pm)?"
            )
            match = re.search(pattern, hs, re.IGNORECASE)
            if match:
                oh = int(match.group(1))
                om = int(match.group(2) or 0)
                oap = match.group(3)
                ch = int(match.group(4))
                cm = int(match.group(5) or 0)
                cap = match.group(6)

                if oap and oap.lower() == "pm" and oh < 12:
                    oh += 12
                elif oap and oap.lower() == "am" and oh == 12:
                    oh = 0
                if cap and cap.lower() == "pm" and ch < 12:
                    ch += 12
                elif cap and cap.lower() == "am" and ch == 12:
                    ch = 0

                try:
                    windows.append((time(oh, om), time(ch, cm)))
                except ValueError:
                    continue

        if windows:
            return windows
        if is_closed:
            return "closed"
        return None

    @staticmethod
    def _time_in_window(t: time, window: tuple[time, time]) -> bool:
        open_t, close_t = window
        if close_t < open_t:
            return t >= open_t or t <= close_t
        return open_t <= t <= close_t


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Theme Alignment Evaluator
# ═══════════════════════════════════════════════════════════════════════════════

# Common category terms that signal theme-relevant content.
# Used as a fallback when dynamic extraction finds no keywords.
_THEME_CATEGORY_POOL: set[str] = {
    "museum", "palace", "fort", "temple", "shrine", "mosque", "church",
    "park", "garden", "nature", "lake", "river", "beach", "zoo",
    "restaurant", "cafe", "dining", "food", "market", "shopping",
    "monument", "landmark", "historical", "heritage", "culture", "art",
    "gallery", "theater", "entertainment", "amusement", "waterfall",
    "attraction", "religious", "spiritual", "science", "aquarium",
    "opera", "boulevard", "plaza", "square", "bridge", "tower",
    "viewpoint", "scenic", "coastal", "harbour", "port",
}

# Bridges broad theme concepts to related place categories where
# substring matching alone would fail (e.g. "heritage" → "fort").
_THEME_CONCEPT_EXPANSIONS: dict[str, set[str]] = {
    "heritage": {"fort", "palace", "monument", "historical", "museum"},
    "culture": {"museum", "gallery", "temple", "church", "shrine", "theater"},
    "nature": {"park", "garden", "lake", "river", "beach", "waterfall", "scenic"},
    "adventure": {"park", "nature", "scenic", "beach", "waterfall"},
    "spiritual": {"temple", "shrine", "mosque", "church", "religious"},
    "nightlife": {"bar", "club", "entertainment"},
    "culinary": {"restaurant", "cafe", "market", "food", "dining"},
}


class ThemeAlignmentEvaluator(BaseEvaluator):
    """
    Evaluates how well activities match their day's theme.
    """

    @property
    def name(self) -> str:
        return "Theme Alignment"

    @property
    def weight(self) -> float:
        return 0.10

    def evaluate(
        self, day_plans: list[DayPlan], context: dict[str, Any] | None = None
    ) -> EvaluatorResult:
        issues: list[str] = []
        if not day_plans:
            return EvaluatorResult(
                name=self.name, score=100, grade="A+", issues=[]
            )

        day_scores: list[float] = []
        for day in day_plans:
            ds, day_issues = self._evaluate_day(day)
            day_scores.append(ds)
            issues.extend(day_issues)

        score = self._clamp(sum(day_scores) / len(day_scores) if day_scores else 100)
        return EvaluatorResult(
            name=self.name, score=score, grade=_grade_from_score(score), issues=issues
        )

    def _evaluate_day(self, day: DayPlan) -> tuple[float, list[str]]:
        issues: list[str] = []
        if not day.theme or not day.activities:
            return 100.0, issues

        theme_lower = day.theme.lower()
        expected = self._extract_expected_categories(theme_lower)

        if not expected:
            issues.append(f"Day {day.day_number}: Theme '{day.theme}' is too generic")
            return 70.0, issues

        non_dining = [
            a
            for a in day.activities
            if (a.place.category.lower() if a.place.category else "")
            not in {"dining", "restaurant", "cafe", "food"}
        ]
        if not non_dining:
            return 100.0, issues

        matching = 0
        for a in non_dining:
            cat = a.place.category.lower() if a.place.category else ""
            name_lower = a.place.name.lower()
            if cat in expected or any(kw in name_lower for kw in expected):
                matching += 1

        alignment = (matching / len(non_dining)) * 100
        if alignment < 40:
            issues.append(
                f"Day {day.day_number}: Only {matching}/{len(non_dining)} "
                f"activities match theme '{day.theme}'"
            )

        return alignment, issues

    @staticmethod
    def _extract_expected_categories(theme: str) -> set[str]:
        """Dynamically extract expected place categories from theme text.

        Instead of relying on a hardcoded keyword dict, extracts meaningful
        words from the theme and matches them against a broad category pool.
        This works for any theme the LLM generates, in any language or style.
        """
        theme_words = set(re.findall(r"\b\w+\b", theme.lower()))
        # Direct matches: theme words that are themselves category terms
        expected = theme_words & _THEME_CATEGORY_POOL
        # Also include words from the theme that partially match categories
        for word in theme_words:
            if len(word) < 3:
                continue
            for cat in _THEME_CATEGORY_POOL:
                if word in cat or cat in word:
                    expected.add(cat)
        # Expand broad concepts to related categories
        for word in theme_words:
            if word in _THEME_CONCEPT_EXPANSIONS:
                expected.update(_THEME_CONCEPT_EXPANSIONS[word])
        return expected


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Duration Appropriateness Evaluator
# ═══════════════════════════════════════════════════════════════════════════════

# Generous guardrail ranges. LLM-estimated durations take priority.
RECOMMENDED_DURATIONS: dict[str, tuple[int, int]] = {
    "museum": (60, 240),
    "culture": (45, 180),
    "art_gallery": (45, 150),
    "temple": (20, 120),
    "religious": (20, 90),
    "attraction": (30, 150),
    "park": (30, 120),
    "garden": (20, 90),
    "nature": (30, 120),
    "zoo": (90, 300),
    "monument": (15, 90),
    "landmark": (15, 90),
    "tourist_attraction": (30, 120),
    "dining": (30, 120),
    "restaurant": (30, 120),
    "cafe": (20, 75),
    "fort": (60, 240),
    "palace": (45, 180),
    "default": (30, 120),
}




class DurationAppropriatenessEvaluator(BaseEvaluator):
    """
    Evaluates if activity durations are appropriate.

    Checks:
    - Durations match place type requirements.
    - Major attractions get adequate time.
    - No rushed schedules.
    - No excessively long single-activity durations.
    """

    @property
    def name(self) -> str:
        return "Duration Appropriateness"

    @property
    def weight(self) -> float:
        return 0.10

    def evaluate(
        self, day_plans: list[DayPlan], context: dict[str, Any] | None = None
    ) -> EvaluatorResult:
        issues: list[str] = []
        if not day_plans:
            return EvaluatorResult(
                name=self.name, score=100, grade="A+", issues=[]
            )

        total = 0
        appropriate = 0

        for day in day_plans:
            for activity in day.activities:
                total += 1
                status, issue = self._check_duration(activity, day.day_number)
                if status == "appropriate":
                    appropriate += 1
                elif issue:
                    issues.append(issue)

        if total == 0:
            score = 100.0
        else:
            score = (appropriate / total) * 100
            # Partial credit for being close
            for day in day_plans:
                for activity in day.activities:
                    dur = activity.duration_minutes
                    min_d, max_d = self._get_recommended(activity)
                    if dur < min_d and dur >= min_d * 0.8:
                        score += 5
                    elif dur > max_d and dur <= max_d * 1.2:
                        score += 5

        score = self._clamp(score)
        return EvaluatorResult(
            name=self.name, score=score, grade=_grade_from_score(score), issues=issues
        )

    def _check_duration(
        self, activity: Activity, day_number: int
    ) -> tuple[str, str | None]:
        dur = activity.duration_minutes
        min_d, max_d = self._get_recommended(activity)

        if dur > 480:
            return (
                "too_long",
                f"Day {day_number}: '{activity.place.name}' has unrealistic {dur}min duration",
            )
        if dur < 15:
            return (
                "too_short",
                f"Day {day_number}: '{activity.place.name}' has only {dur}min (too short)",
            )
        if dur < min_d:
            return (
                "too_short",
                f"Day {day_number}: '{activity.place.name}' has {dur}min "
                f"(recommended: {min_d}-{max_d}min)",
            )
        if dur > max_d * 1.5:
            return (
                "too_long",
                f"Day {day_number}: '{activity.place.name}' has {dur}min "
                f"(recommended: {min_d}-{max_d}min)",
            )
        return "appropriate", None

    @staticmethod
    def _get_recommended(activity: Activity) -> tuple[int, int]:
        cat = activity.place.category.lower() if activity.place.category else ""
        name_lower = activity.place.name.lower()

        if cat in RECOMMENDED_DURATIONS:
            return RECOMMENDED_DURATIONS[cat]

        for c, dur in RECOMMENDED_DURATIONS.items():
            if c in name_lower:
                return dur

        return RECOMMENDED_DURATIONS["default"]
