"""Tests for the curation pipeline."""

import pytest

from app.pipelines.curation import (
    CuratedAccommodation,
    CuratedActivity,
    CuratedDay,
    CurationOutput,
    CurationPipeline,
)
from app.services.llm.base import LLMService, T


# ---------------------------------------------------------------------------
# Mock LLM service
# ---------------------------------------------------------------------------


class MockLLMService(LLMService):
    """LLM service that returns a pre-configured CurationOutput."""

    def __init__(self, output: CurationOutput | None = None):
        self._output = output
        self.last_system: str | None = None
        self.last_user: str | None = None

    async def generate(self, system_prompt, user_prompt, **kwargs) -> str:
        return ""

    async def generate_structured(
        self, system_prompt, user_prompt, schema=None, **kwargs
    ) -> T:
        self.last_system = system_prompt
        self.last_user = user_prompt
        return self._output  # type: ignore[return-value]

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CANDIDATES = [
    {"google_place_id": "place_temple", "name": "Golden Temple", "types": ["temple"], "rating": 4.8},
    {"google_place_id": "place_park", "name": "City Park", "types": ["park"], "rating": 4.5},
    {"google_place_id": "place_museum", "name": "National Museum", "types": ["museum"], "rating": 4.6},
    {"google_place_id": "place_cafe", "name": "Morning Cafe", "types": ["cafe"], "rating": 4.3},
    {"google_place_id": "place_restaurant", "name": "Dinner Spot", "types": ["restaurant"], "rating": 4.4},
    {"google_place_id": "place_bakery", "name": "Local Bakery", "types": ["bakery"], "rating": 4.2},
]

LODGING = [
    {"google_place_id": "hotel_main", "name": "Grand Hotel", "types": ["hotel"], "rating": 4.5},
    {"google_place_id": "hotel_alt1", "name": "Budget Inn", "types": ["hotel"], "rating": 3.8},
    {"google_place_id": "hotel_alt2", "name": "Boutique Stay", "types": ["hotel"], "rating": 4.2},
]


def _make_valid_output(day_count: int = 2) -> CurationOutput:
    """Build a valid CurationOutput using only known candidate IDs."""
    days = []
    activity_ids = ["place_temple", "place_park", "place_museum"]
    meal_ids = ["place_cafe", "place_restaurant", "place_bakery"]

    for d in range(1, day_count + 1):
        activities = [
            CuratedActivity(
                google_place_id=activity_ids[(d - 1) % len(activity_ids)],
                category="cultural",
                description="A wonderful attraction.",
                duration_minutes=60,
            ),
            CuratedActivity(
                google_place_id=meal_ids[(d - 1) % len(meal_ids)],
                category="dining",
                description="Great local food.",
                duration_minutes=45,
                is_meal=True,
                meal_type="lunch",
                estimated_cost_usd=12.0,
            ),
        ]
        days.append(
            CuratedDay(
                day_number=d,
                theme=f"Day {d} Theme",
                activities=activities,
            )
        )

    return CurationOutput(
        days=days,
        accommodation=CuratedAccommodation(google_place_id="hotel_main", estimated_nightly_usd=120.0),
        accommodation_alternatives=[
            CuratedAccommodation(google_place_id="hotel_alt1", estimated_nightly_usd=60.0),
            CuratedAccommodation(google_place_id="hotel_alt2", estimated_nightly_usd=95.0),
        ],
        booking_hint="Search Booking.com for best rates.",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_curate_returns_valid_plan():
    """Verify day count matches request and accommodation is present."""
    output = _make_valid_output(day_count=3)
    llm = MockLLMService(output=output)
    pipeline = CurationPipeline(llm)

    result = await pipeline.curate(
        city_name="Tokyo",
        country="Japan",
        candidates=CANDIDATES,
        lodging_candidates=LODGING,
        day_count=3,
    )

    assert len(result.days) == 3
    assert result.accommodation.google_place_id == "hotel_main"
    assert len(result.accommodation_alternatives) == 2
    assert result.booking_hint is not None


@pytest.mark.asyncio
async def test_curate_validates_place_ids():
    """Unknown place_id in LLM output raises ValueError."""
    output = _make_valid_output(day_count=1)
    # Inject an unknown ID
    output.days[0].activities[0].google_place_id = "FAKE_ID_NOT_IN_CANDIDATES"

    llm = MockLLMService(output=output)
    pipeline = CurationPipeline(llm)

    with pytest.raises(ValueError, match="unknown place ID"):
        await pipeline.curate(
            city_name="Paris",
            country="France",
            candidates=CANDIDATES,
            lodging_candidates=LODGING,
            day_count=1,
        )


@pytest.mark.asyncio
async def test_curate_formats_prompts():
    """Verify prompt placeholders are filled with city/country/pace/budget."""
    output = _make_valid_output(day_count=2)
    llm = MockLLMService(output=output)
    pipeline = CurationPipeline(llm)

    await pipeline.curate(
        city_name="Barcelona",
        country="Spain",
        candidates=CANDIDATES,
        lodging_candidates=LODGING,
        pace="relaxed",
        budget="luxury",
        day_count=2,
    )

    assert "Barcelona" in llm.last_user
    assert "Spain" in llm.last_user
    assert "relaxed" in llm.last_user
    assert "luxury" in llm.last_user
    assert "2 days" in llm.last_user
    # Meal guidance for Spain (late dining)
    assert "Lunch window" in llm.last_user
    assert "Dinner window" in llm.last_user
