"""Unit tests for the schedule builder."""

from datetime import date, time

import pytest
from app.algorithms.scheduler import ScheduleBuilder, ScheduleConfig, DURATION_BY_CATEGORY, PACE_MULTIPLIERS
from app.models.common import Location, Pace
from app.models.internal import PlaceCandidate


def _make_place(
    name: str,
    types: list[str] | None = None,
    suggested_duration: int | None = None,
) -> PlaceCandidate:
    """Helper to build a PlaceCandidate."""
    return PlaceCandidate(
        place_id=f"place_{name}",
        name=name,
        address=f"{name} address",
        location=Location(lat=48.0, lng=2.0),
        types=types or ["tourist_attraction"],
        suggested_duration_minutes=suggested_duration,
    )


class TestScheduleBuilderBasic:
    """Basic scheduling tests."""

    def test_empty_places(self):
        builder = ScheduleBuilder()
        result = builder.build_schedule([])
        assert result == []

    def test_single_activity(self):
        builder = ScheduleBuilder()
        places = [_make_place("Museum", types=["museum"])]
        result = builder.build_schedule(places, schedule_date=date(2026, 3, 4))
        assert len(result) == 1
        assert result[0].place.name == "Museum"
        assert result[0].time_start == "09:00"

    def test_multiple_activities_sequential(self):
        builder = ScheduleBuilder()
        places = [
            _make_place("A", types=["tourist_attraction"]),
            _make_place("B", types=["tourist_attraction"]),
            _make_place("C", types=["tourist_attraction"]),
        ]
        result = builder.build_schedule(places, schedule_date=date(2026, 3, 4))
        assert len(result) == 3
        # Each start should be after the previous end
        for i in range(1, len(result)):
            assert result[i].time_start >= result[i - 1].time_end

    def test_custom_start_time(self):
        builder = ScheduleBuilder()
        places = [_make_place("A")]
        result = builder.build_schedule(
            places,
            schedule_date=date(2026, 3, 4),
            day_start_time=time(14, 0),
        )
        assert result[0].time_start == "14:00"

    def test_custom_end_time_caps_activities(self):
        builder = ScheduleBuilder()
        places = [
            _make_place("A", types=["amusement_park"]),  # 180 min
            _make_place("B", types=["amusement_park"]),  # 180 min
            _make_place("C", types=["amusement_park"]),  # 180 min
        ]
        result = builder.build_schedule(
            places,
            schedule_date=date(2026, 3, 4),
            day_start_time=time(9, 0),
            day_end_time=time(14, 0),  # Only 5 hours
        )
        # Should not schedule all 3 (9h needed for 3x 180min + buffers)
        assert len(result) < 3


class TestScheduleBuilderPace:
    """Pace multiplier tests."""

    def test_relaxed_longer_durations(self):
        builder = ScheduleBuilder()
        place = _make_place("Museum", types=["museum"])  # 90 min base
        relaxed = builder.build_schedule(
            [place], pace=Pace.RELAXED, schedule_date=date(2026, 3, 4)
        )
        moderate = builder.build_schedule(
            [place], pace=Pace.MODERATE, schedule_date=date(2026, 3, 4)
        )
        assert relaxed[0].duration_minutes >= moderate[0].duration_minutes

    def test_packed_shorter_durations(self):
        builder = ScheduleBuilder()
        place = _make_place("Museum", types=["museum"])  # 90 min base
        packed = builder.build_schedule(
            [place], pace=Pace.PACKED, schedule_date=date(2026, 3, 4)
        )
        moderate = builder.build_schedule(
            [place], pace=Pace.MODERATE, schedule_date=date(2026, 3, 4)
        )
        assert packed[0].duration_minutes <= moderate[0].duration_minutes


class TestScheduleBuilderMeals:
    """Meal window scheduling tests."""

    def test_lunch_scheduled_in_window(self):
        builder = ScheduleBuilder()
        places = [
            _make_place("Morning activity", types=["museum"]),  # 90 min: 09:00-10:30
            _make_place("Stroll", types=["park"]),               # 60 min: 10:45-11:45
            _make_place("Lunch spot", types=["restaurant"]),
        ]
        result = builder.build_schedule(places, schedule_date=date(2026, 3, 4))
        lunch = next(a for a in result if a.place.name == "Lunch spot")
        # Lunch should start at or after 12:00
        assert lunch.time_start >= "12:00"

    def test_dinner_scheduled_in_window(self):
        builder = ScheduleBuilder()
        places = [
            _make_place("Activity 1", types=["museum"]),            # 90 min: 09:00-10:30
            _make_place("Activity 2", types=["park"]),              # 60 min: 10:45-11:45
            _make_place("Lunch", types=["restaurant"]),             # 75 min: ~12:30-13:45
            _make_place("Activity 3", types=["museum"]),            # 90 min: ~14:00-15:30
            _make_place("Activity 4", types=["park"]),              # 60 min: ~15:45-16:45
            _make_place("Activity 5", types=["tourist_attraction"]),  # 45 min: ~17:00-17:45
            _make_place("Dinner", types=["restaurant"]),            # Should wait for 18:00+
        ]
        result = builder.build_schedule(places, schedule_date=date(2026, 3, 4))
        dinner = next(a for a in result if a.place.name == "Dinner")
        # Dinner should be scheduled at or after 18:00
        assert dinner.time_start >= "18:00"


class TestScheduleBuilderDurations:
    """Duration calculation tests."""

    def test_suggested_duration_used(self):
        builder = ScheduleBuilder()
        # 90 min suggested, moderate pace -> rounds to 90
        place = _make_place("Custom", suggested_duration=90)
        result = builder.build_schedule([place], schedule_date=date(2026, 3, 4))
        assert result[0].duration_minutes == 90

    def test_explicit_override_used(self):
        builder = ScheduleBuilder()
        place = _make_place("A", types=["museum"])  # 120 base
        result = builder.build_schedule(
            [place],
            durations={"place_A": 30},
            schedule_date=date(2026, 3, 4),
        )
        assert result[0].duration_minutes == 30

    def test_category_duration_defaults(self):
        """Museum default is 90 min at moderate pace."""
        builder = ScheduleBuilder()
        place = _make_place("A", types=["museum"])
        result = builder.build_schedule([place], schedule_date=date(2026, 3, 4))
        assert result[0].duration_minutes == 90


class TestScheduleBuilderValidation:
    """Schedule validation tests."""

    def test_no_overlaps_in_valid_schedule(self):
        builder = ScheduleBuilder()
        places = [
            _make_place("A", types=["museum"]),
            _make_place("B", types=["park"]),
        ]
        schedule = builder.build_schedule(places, schedule_date=date(2026, 3, 4))
        warnings = builder.validate_schedule(schedule)
        overlap_warnings = [w for w in warnings if "Overlap" in w]
        assert len(overlap_warnings) == 0

    def test_validate_empty_schedule(self):
        builder = ScheduleBuilder()
        warnings = builder.validate_schedule([])
        assert warnings == []


class TestDurationByCategory:
    """Verify duration constants are reasonable."""

    def test_all_durations_positive(self):
        for category, duration in DURATION_BY_CATEGORY.items():
            assert duration > 0, f"{category} has non-positive duration"

    def test_default_exists(self):
        assert "default" in DURATION_BY_CATEGORY


class TestPaceMultipliers:
    """Verify pace multiplier constants."""

    def test_all_paces_have_multipliers(self):
        for pace in Pace:
            assert pace in PACE_MULTIPLIERS

    def test_relaxed_greater_than_packed(self):
        assert PACE_MULTIPLIERS[Pace.RELAXED] > PACE_MULTIPLIERS[Pace.PACKED]

    def test_moderate_is_one(self):
        assert PACE_MULTIPLIERS[Pace.MODERATE] == 1.0
