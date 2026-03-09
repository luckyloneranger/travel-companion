"""Unit tests for the schedule builder."""

from datetime import date, time

import pytest
from app.algorithms.scheduler import ScheduleBuilder, ScheduleConfig, DURATION_BY_CATEGORY, PACE_MULTIPLIERS
from app.models.common import Location, Pace
from app.models.internal import OpeningHours, PlaceCandidate


def _make_place(
    place_id: str = "p1",
    name: str = "Test Place",
    types: list[str] | None = None,
    lat: float = 48.0,
    lng: float = 2.0,
    suggested_duration_minutes: int | None = None,
    opening_hours: list | None = None,
) -> PlaceCandidate:
    """Helper to build a PlaceCandidate."""
    return PlaceCandidate(
        place_id=place_id,
        name=name,
        address="123 Test St",
        location=Location(lat=lat, lng=lng),
        types=types or ["tourist_attraction"],
        rating=4.5,
        suggested_duration_minutes=suggested_duration_minutes,
        opening_hours=opening_hours,
    )


class TestScheduleBuilderBasic:
    """Basic scheduling tests."""

    def test_empty_places(self):
        builder = ScheduleBuilder()
        result = builder.build_schedule([])
        assert result == []

    def test_single_activity(self):
        builder = ScheduleBuilder()
        places = [_make_place(name="Museum", types=["museum"])]
        result = builder.build_schedule(places, schedule_date=date(2026, 3, 4))
        assert len(result) == 1
        assert result[0].place.name == "Museum"
        assert result[0].time_start == "09:00"

    def test_multiple_activities_sequential(self):
        builder = ScheduleBuilder()
        places = [
            _make_place(place_id="a", name="A", types=["tourist_attraction"]),
            _make_place(place_id="b", name="B", types=["tourist_attraction"]),
            _make_place(place_id="c", name="C", types=["tourist_attraction"]),
        ]
        result = builder.build_schedule(places, schedule_date=date(2026, 3, 4))
        assert len(result) == 3
        # Each start should be after the previous end
        for i in range(1, len(result)):
            assert result[i].time_start >= result[i - 1].time_end

    def test_custom_start_time(self):
        builder = ScheduleBuilder()
        places = [_make_place(name="A")]
        result = builder.build_schedule(
            places,
            schedule_date=date(2026, 3, 4),
            day_start_time=time(14, 0),
        )
        assert result[0].time_start == "14:00"

    def test_custom_end_time_caps_activities(self):
        builder = ScheduleBuilder()
        places = [
            _make_place(place_id="a", name="A", types=["amusement_park"]),  # 180 min
            _make_place(place_id="b", name="B", types=["amusement_park"]),  # 180 min
            _make_place(place_id="c", name="C", types=["amusement_park"]),  # 180 min
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
        place = _make_place(name="Museum", types=["museum"])  # 90 min base
        relaxed = builder.build_schedule(
            [place], pace=Pace.RELAXED, schedule_date=date(2026, 3, 4)
        )
        moderate = builder.build_schedule(
            [place], pace=Pace.MODERATE, schedule_date=date(2026, 3, 4)
        )
        assert relaxed[0].duration_minutes >= moderate[0].duration_minutes

    def test_packed_shorter_durations(self):
        builder = ScheduleBuilder()
        place = _make_place(name="Museum", types=["museum"])  # 90 min base
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
            _make_place(name="Morning activity", types=["museum"]),  # 90 min: 09:00-10:30
            _make_place(name="Stroll", types=["park"]),               # 60 min: 10:45-11:45
            _make_place(name="Lunch spot", types=["restaurant"]),
        ]
        result = builder.build_schedule(places, schedule_date=date(2026, 3, 4))
        lunch = next(a for a in result if a.place.name == "Lunch spot")
        # Lunch should start at or after 12:00
        assert lunch.time_start >= "12:00"

    def test_dinner_scheduled_in_window(self):
        builder = ScheduleBuilder()
        places = [
            _make_place(name="Activity 1", types=["museum"]),            # 90 min: 09:00-10:30
            _make_place(name="Activity 2", types=["park"]),              # 60 min: 10:45-11:45
            _make_place(name="Lunch", types=["restaurant"]),             # 75 min: ~12:30-13:45
            _make_place(name="Activity 3", types=["museum"]),            # 90 min: ~14:00-15:30
            _make_place(name="Activity 4", types=["park"]),              # 60 min: ~15:45-16:45
            _make_place(name="Activity 5", types=["tourist_attraction"]),  # 45 min: ~17:00-17:45
            _make_place(name="Dinner", types=["restaurant"]),            # Should wait for 18:00+
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
        place = _make_place(name="Custom", suggested_duration_minutes=90)
        result = builder.build_schedule([place], schedule_date=date(2026, 3, 4))
        assert result[0].duration_minutes == 90

    def test_explicit_override_used(self):
        builder = ScheduleBuilder()
        place = _make_place(place_id="place_A", name="A", types=["museum"])  # 120 base
        result = builder.build_schedule(
            [place],
            durations={"place_A": 30},
            schedule_date=date(2026, 3, 4),
        )
        assert result[0].duration_minutes == 30

    def test_category_duration_defaults(self):
        """Museum default is 90 min at moderate pace."""
        builder = ScheduleBuilder()
        place = _make_place(name="A", types=["museum"])
        result = builder.build_schedule([place], schedule_date=date(2026, 3, 4))
        assert result[0].duration_minutes == 90


class TestScheduleBuilderValidation:
    """Schedule validation tests."""

    def test_no_overlaps_in_valid_schedule(self):
        builder = ScheduleBuilder()
        places = [
            _make_place(place_id="a", name="A", types=["museum"]),
            _make_place(place_id="b", name="B", types=["park"]),
        ]
        schedule = builder.build_schedule(places, schedule_date=date(2026, 3, 4))
        warnings = builder.validate_schedule(schedule)
        overlap_warnings = [w for w in warnings if "Overlap" in w]
        assert len(overlap_warnings) == 0

    def test_validate_empty_schedule(self):
        builder = ScheduleBuilder()
        warnings = builder.validate_schedule([])
        assert warnings == []


class TestScheduleBuilderOpeningHours:
    """Opening hours constraint tests."""

    def test_activity_truncated_to_fit_closing(self):
        """Place closes at 17:00, start at 16:00 with 90min duration -> truncate to 60min."""
        builder = ScheduleBuilder()
        # Wednesday: Python weekday 2 -> Google day 3
        hours = [OpeningHours(day=3, open_time="09:00", close_time="17:00")]
        place = _make_place(
            name="Museum",
            types=["museum"],
            suggested_duration_minutes=90,
            opening_hours=hours,
        )
        result = builder.build_schedule(
            [place],
            schedule_date=date(2026, 4, 15),  # Wednesday
            day_start_time=time(16, 0),
        )
        assert len(result) == 1
        assert result[0].duration_minutes == 60
        assert result[0].time_start == "16:00"
        assert result[0].time_end == "17:00"

    def test_activity_skipped_when_no_time_before_close(self):
        """Place closes at 17:00, day starts at 16:45 -> skip (only 15min, below min_activity_duration=30)."""
        builder = ScheduleBuilder()
        hours = [OpeningHours(day=3, open_time="09:00", close_time="17:00")]
        place = _make_place(
            name="Museum",
            types=["museum"],
            suggested_duration_minutes=90,
            opening_hours=hours,
        )
        result = builder.build_schedule(
            [place],
            schedule_date=date(2026, 4, 15),  # Wednesday
            day_start_time=time(16, 45),
        )
        assert len(result) == 0

    def test_activity_not_truncated_when_fits(self):
        """Place closes at 22:00, start at 09:00, 60min duration -> full duration kept."""
        builder = ScheduleBuilder()
        hours = [OpeningHours(day=3, open_time="09:00", close_time="22:00")]
        place = _make_place(
            name="Museum",
            types=["museum"],
            suggested_duration_minutes=60,
            opening_hours=hours,
        )
        result = builder.build_schedule(
            [place],
            schedule_date=date(2026, 4, 15),  # Wednesday
        )
        assert len(result) == 1
        assert result[0].duration_minutes == 60
        assert result[0].time_start == "09:00"
        assert result[0].time_end == "10:00"

    def test_no_opening_hours_schedules_normally(self):
        """Place without opening_hours -> schedule normally with full duration."""
        builder = ScheduleBuilder()
        place = _make_place(
            name="Museum",
            types=["museum"],
            suggested_duration_minutes=90,
        )
        result = builder.build_schedule(
            [place],
            schedule_date=date(2026, 4, 15),
        )
        assert len(result) == 1
        assert result[0].duration_minutes == 90
        assert result[0].time_start == "09:00"

    def test_opening_hours_preserved_in_activity(self):
        """Opening hours from PlaceCandidate should flow into Activity.place."""
        place = _make_place(
            place_id="museum1", name="Art Museum", types=["museum"],
            opening_hours=[
                OpeningHours(day=3, open_time="09:00", close_time="17:00"),
                OpeningHours(day=4, open_time="09:00", close_time="21:00"),
            ],
        )
        builder = ScheduleBuilder()
        result = builder.build_schedule(
            places=[place],
            durations={"museum1": 90},
            pace=Pace.MODERATE,
            schedule_date=date(2026, 4, 15),  # Wednesday
        )
        assert len(result) == 1
        assert len(result[0].place.opening_hours) == 2
        assert "09:00" in result[0].place.opening_hours[0]
        assert "17:00" in result[0].place.opening_hours[0]


class TestDurationByCategory:
    """Verify duration constants are reasonable."""

    def test_all_durations_positive(self):
        for category, duration in DURATION_BY_CATEGORY.items():
            assert duration > 0, f"{category} has non-positive duration"

    def test_default_exists(self):
        assert "default" in DURATION_BY_CATEGORY


class TestFallbackDurations:
    """Verify fallback duration table has sensible values."""

    def test_temple_types_have_entries(self):
        """Shinto shrines and Buddhist temples should have duration entries."""
        from app.config.planning import DURATION_BY_TYPE
        assert "shinto_shrine" in DURATION_BY_TYPE
        assert "buddhist_temple" in DURATION_BY_TYPE
        assert 30 <= DURATION_BY_TYPE["shinto_shrine"] <= 60
        assert 30 <= DURATION_BY_TYPE["buddhist_temple"] <= 60

    def test_observation_deck_has_entry(self):
        """Observation decks should have duration entry."""
        from app.config.planning import DURATION_BY_TYPE
        assert "observation_deck" in DURATION_BY_TYPE
        assert 45 <= DURATION_BY_TYPE["observation_deck"] <= 90

    def test_quick_stops_are_short(self):
        """Bridges and sculptures should be quick stops."""
        from app.config.planning import DURATION_BY_TYPE
        assert DURATION_BY_TYPE.get("bridge", 999) <= 30
        assert DURATION_BY_TYPE.get("sculpture", 999) <= 30

    def test_all_durations_are_positive(self):
        """All duration values should be positive integers."""
        from app.config.planning import DURATION_BY_TYPE
        for place_type, duration in DURATION_BY_TYPE.items():
            assert duration > 0, f"{place_type} has non-positive duration"


class TestPaceMultipliers:
    """Verify pace multiplier constants."""

    def test_all_paces_have_multipliers(self):
        for pace in Pace:
            assert pace in PACE_MULTIPLIERS

    def test_relaxed_greater_than_packed(self):
        assert PACE_MULTIPLIERS[Pace.RELAXED] > PACE_MULTIPLIERS[Pace.PACKED]

    def test_moderate_is_one(self):
        assert PACE_MULTIPLIERS[Pace.MODERATE] == 1.0
