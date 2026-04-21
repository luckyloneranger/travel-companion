"""Tests for the scheduling pipeline."""

import pytest
from datetime import time

from app.pipelines.scheduling import SchedulingPipeline, ScheduledActivity


@pytest.fixture
def pipeline():
    return SchedulingPipeline()


def test_schedule_basic(pipeline: SchedulingPipeline):
    """3 activities get start/end times assigned sequentially."""
    activities = [
        {"name": "Temple", "duration_minutes": 60, "sequence": 1},
        {"name": "Museum", "duration_minutes": 90, "sequence": 2},
        {"name": "Park", "duration_minutes": 45, "sequence": 3},
    ]
    result = pipeline.schedule_day(activities, routes=[], pace="moderate")

    assert len(result) == 3
    assert result[0].start_time == time(9, 0)
    assert result[0].duration_minutes == 60
    assert result[0].end_time == time(10, 0)
    # Second starts after first + buffer (15 min)
    assert result[1].start_time == time(10, 15)
    assert result[1].duration_minutes == 90
    # Verify sequential ordering
    for i in range(1, len(result)):
        assert result[i].start_time > result[i - 1].start_time


def test_schedule_respects_pace(pipeline: SchedulingPipeline):
    """Relaxed pace makes activities longer (1.3x multiplier)."""
    activities = [
        {"name": "Museum", "duration_minutes": 60, "sequence": 1},
    ]
    moderate = pipeline.schedule_day(activities, routes=[], pace="moderate")
    relaxed = pipeline.schedule_day(activities, routes=[], pace="relaxed")

    assert relaxed[0].duration_minutes > moderate[0].duration_minutes
    assert moderate[0].duration_minutes == 60
    assert relaxed[0].duration_minutes == 78  # int(60 * 1.3)


def test_schedule_meal_alignment(pipeline: SchedulingPipeline):
    """Lunch activity aligns with lunch window when gap is small."""
    # Default lunch window starts at 12:00. Place current time near it.
    # 2 short activities (30 min each + 15 buffer = 90 min total) start at 9:00,
    # so by activity 3 we're at ~10:30. Lunch at that point is too early (gap > 30).
    # Use fewer activities so we land close to 12:00.
    activities = [
        {"name": "Walk", "duration_minutes": 60, "sequence": 1},
        {"name": "Temple", "duration_minutes": 60, "sequence": 2},
        {"name": "Lunch Spot", "duration_minutes": 60, "sequence": 3, "is_meal": True, "meal_type": "lunch"},
    ]
    result = pipeline.schedule_day(activities, routes=[], pace="moderate")

    assert len(result) == 3
    lunch = result[2]
    # After 2 activities (60+15+60+15 = 150 min from 9:00 = 11:30),
    # lunch window starts at 12:00, gap is 30 min — should align
    assert lunch.start_time == time(12, 0)


def test_schedule_opening_hours_truncation(pipeline: SchedulingPipeline):
    """Activity ending after close is truncated to fit."""
    activities = [
        {"name": "Early Visit", "duration_minutes": 60, "sequence": 1},
        {"name": "Late Museum", "duration_minutes": 120, "sequence": 2,
         "opening_hours": [{"close": "11:00"}]},
    ]
    result = pipeline.schedule_day(activities, routes=[], pace="moderate")

    assert len(result) == 2
    museum = result[1]
    # Starts at 10:15 (9:00 + 60 + 15 buffer), closes at 11:00
    # Available: 45 min, so truncated from 120 to 45
    assert museum.duration_minutes == 45
    assert museum.end_time == time(11, 0)


def test_schedule_empty(pipeline: SchedulingPipeline):
    """Empty activities returns empty list."""
    result = pipeline.schedule_day([], routes=[])
    assert result == []
