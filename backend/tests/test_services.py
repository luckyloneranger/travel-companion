"""Unit tests for TipsService, ChatService helpers, and GoogleRoutesService."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.tips import TipsService, _format_schedule
from app.services.chat import ChatService, _needs_place_search, _format_place_results


# ═══════════════════════════════════════════════════════════════════════════════
# TipsService helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestFormatSchedule:
    def test_empty_list(self):
        assert _format_schedule([]) == "No activities."

    def test_single_activity(self):
        activities = [
            {
                "place": {"name": "Louvre", "place_id": "abc123"},
                "time_start": "09:00",
                "time_end": "11:00",
            }
        ]
        result = _format_schedule(activities)
        assert "Louvre" in result
        assert "09:00-11:00" in result
        assert "abc123" in result

    def test_activity_with_category_and_notes(self):
        activities = [
            {
                "place": {"name": "Café", "place_id": "xyz", "category": "restaurant"},
                "time_start": "12:00",
                "time_end": "13:00",
                "notes": "Try the croissants",
            }
        ]
        result = _format_schedule(activities)
        assert "(restaurant)" in result
        assert "Try the croissants" in result


class TestTipsService:
    @pytest.mark.asyncio
    async def test_generate_tips_valid_json(self):
        """TipsService parses valid JSON response."""
        mock_llm = MagicMock()
        tips_data = {"tips": {"place_abc": "Visit early morning to avoid crowds"}}
        mock_llm.generate = AsyncMock(return_value=json.dumps(tips_data))

        service = TipsService(llm=mock_llm)
        result = await service.generate_tips(
            activities=[{"place": {"name": "Museum", "place_id": "place_abc"}, "time_start": "09:00", "time_end": "11:00"}],
            destination="Paris",
        )
        assert result["tips"]["place_abc"] == "Visit early morning to avoid crowds"

    @pytest.mark.asyncio
    async def test_generate_tips_markdown_fenced(self):
        """TipsService handles markdown-fenced JSON responses."""
        mock_llm = MagicMock()
        tips_data = {"tips": {"abc": "Tip text"}}
        mock_llm.generate = AsyncMock(return_value=f"```json\n{json.dumps(tips_data)}\n```")

        service = TipsService(llm=mock_llm)
        result = await service.generate_tips(
            activities=[{"place": {"name": "A", "place_id": "abc"}, "time_start": "09:00", "time_end": "10:00"}],
            destination="Paris",
        )
        assert result["tips"]["abc"] == "Tip text"

    @pytest.mark.asyncio
    async def test_generate_tips_invalid_json(self):
        """TipsService returns empty tips on parse failure."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="This is not JSON at all")

        service = TipsService(llm=mock_llm)
        result = await service.generate_tips(
            activities=[{"place": {"name": "A", "place_id": "abc"}, "time_start": "09:00", "time_end": "10:00"}],
            destination="Paris",
        )
        assert result == {"tips": {}}

    @pytest.mark.asyncio
    async def test_generate_tips_flat_dict_wrapped(self):
        """TipsService wraps flat dict response into {"tips": ...}."""
        mock_llm = MagicMock()
        flat = {"place_a": "Tip A", "place_b": "Tip B"}
        mock_llm.generate = AsyncMock(return_value=json.dumps(flat))

        service = TipsService(llm=mock_llm)
        result = await service.generate_tips(
            activities=[
                {"place": {"name": "A", "place_id": "place_a"}, "time_start": "09:00", "time_end": "10:00"},
                {"place": {"name": "B", "place_id": "place_b"}, "time_start": "10:00", "time_end": "11:00"},
            ],
            destination="Paris",
        )
        assert result["tips"]["place_a"] == "Tip A"


# ═══════════════════════════════════════════════════════════════════════════════
# ChatService helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestNeedsPlaceSearch:
    def test_place_related_message(self):
        assert _needs_place_search("add a restaurant for dinner") is True
        assert _needs_place_search("I want to visit a museum") is True
        assert _needs_place_search("find me a good cafe") is True

    def test_generic_message(self):
        # With the permissive approach, most messages > 10 chars trigger a search.
        # Only very short messages are excluded — false positives are harmless.
        assert _needs_place_search("ok") is False
        assert _needs_place_search("yes") is False
        assert _needs_place_search("     ") is False


class TestFormatPlaceResults:
    def test_empty_results(self):
        assert _format_place_results([]) == "No nearby places found."

    def test_with_results(self):
        results = [
            {
                "name": "Le Jules Verne",
                "address": "Eiffel Tower, Paris",
                "rating": 4.5,
                "editorial_summary": "Fine dining at the Eiffel Tower",
            }
        ]
        output = _format_place_results(results)
        assert "Le Jules Verne" in output
        assert "4.5" in output
        assert "Fine dining" in output

    def test_limits_to_10(self):
        results = [{"name": f"Place {i}", "address": f"Addr {i}"} for i in range(20)]
        output = _format_place_results(results)
        # Should have at most 10 lines
        assert output.count("\n") <= 9


# ═══════════════════════════════════════════════════════════════════════════════
# GoogleRoutesService.compute_best_route
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeBestRoute:
    """Test the best route selection logic."""

    @pytest.mark.asyncio
    async def test_prefers_walk_when_short(self):
        """Walk should be preferred when it's under 20 minutes."""
        from app.services.google.routes import GoogleRoutesService
        from app.models.common import Location, TravelMode
        from app.models.day_plan import Route

        service = GoogleRoutesService(api_key="fake", client=MagicMock())
        walk_route = Route(distance_meters=800, duration_seconds=600, travel_mode=TravelMode.WALK)
        drive_route = Route(distance_meters=800, duration_seconds=300, travel_mode=TravelMode.DRIVE)

        service.compute_route = AsyncMock(side_effect=[walk_route, drive_route])

        origin = Location(lat=48.86, lng=2.34)
        dest = Location(lat=48.87, lng=2.35)
        result = await service.compute_best_route(origin, dest)

        assert result.travel_mode == TravelMode.WALK

    @pytest.mark.asyncio
    async def test_prefers_drive_when_walk_is_much_longer(self):
        """Drive should be preferred when walk is much longer."""
        from app.services.google.routes import GoogleRoutesService
        from app.models.common import Location, TravelMode
        from app.models.day_plan import Route

        service = GoogleRoutesService(api_key="fake", client=MagicMock())
        walk_route = Route(distance_meters=5000, duration_seconds=3600, travel_mode=TravelMode.WALK)  # 60 min
        drive_route = Route(distance_meters=5000, duration_seconds=900, travel_mode=TravelMode.DRIVE)  # 15 min

        service.compute_route = AsyncMock(side_effect=[walk_route, drive_route])

        origin = Location(lat=48.86, lng=2.34)
        dest = Location(lat=49.0, lng=2.5)
        result = await service.compute_best_route(origin, dest)

        assert result.travel_mode == TravelMode.DRIVE

    @pytest.mark.asyncio
    async def test_fallback_when_both_fail(self):
        """Should return a fallback when both modes fail."""
        from app.services.google.routes import GoogleRoutesService
        from app.models.common import Location, TravelMode

        service = GoogleRoutesService(api_key="fake", client=MagicMock())
        service.compute_route = AsyncMock(side_effect=Exception("API down"))

        origin = Location(lat=48.86, lng=2.34)
        dest = Location(lat=48.87, lng=2.35)
        result = await service.compute_best_route(origin, dest)

        assert result.travel_mode == TravelMode.WALK  # fallback

    @pytest.mark.asyncio
    async def test_walk_preferred_when_similar_to_drive(self):
        """Walk should be preferred when it's only slightly slower than drive."""
        from app.services.google.routes import GoogleRoutesService
        from app.models.common import Location, TravelMode
        from app.models.day_plan import Route

        service = GoogleRoutesService(api_key="fake", client=MagicMock())
        walk_route = Route(distance_meters=2000, duration_seconds=1500, travel_mode=TravelMode.WALK)  # 25 min
        drive_route = Route(distance_meters=2000, duration_seconds=1200, travel_mode=TravelMode.DRIVE)  # 20 min

        service.compute_route = AsyncMock(side_effect=[walk_route, drive_route])

        origin = Location(lat=48.86, lng=2.34)
        dest = Location(lat=48.87, lng=2.35)
        result = await service.compute_best_route(origin, dest)

        # 25 min walk <= 20 min drive * 1.5 (30 min) → prefer walk
        assert result.travel_mode == TravelMode.WALK
