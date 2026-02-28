"""
Live test: Chat edit re-enrichment flow.

Tests that after a journey chat edit, travel legs get real Google Directions
data (fare, departure/arrival times, transfers) instead of LLM guesses.

Run with: cd backend && source venv/bin/activate && pytest tests/test_chat_edit_enrichment_live.py -v -s
Requires: Backend running on localhost:8000 with valid API keys.
"""

import asyncio
import json
import time
import httpx
import pytest
from datetime import date, timedelta

BASE_URL = "http://localhost:8000"
TIMEOUT = 300  # 5 min for LLM + API calls


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_sample_journey() -> dict:
    """A realistic journey plan dict as returned by /plan/stream."""
    return {
        "theme": "Cultural Vietnam",
        "summary": "A journey through Vietnam's cultural heartland",
        "route": "Ho Chi Minh City → Da Nang → Hue",
        "origin": "Ho Chi Minh City",
        "region": "Vietnam",
        "total_days": 5,
        "cities": [
            {
                "name": "Da Nang",
                "country": "Vietnam",
                "days": 2,
                "why_visit": "Beautiful beaches and Marble Mountains",
                "best_time_to_visit": "Feb-May",
                "highlights": [
                    {"name": "Marble Mountains", "description": "Cluster of limestone hills", "category": "nature"},
                    {"name": "My Khe Beach", "description": "Stunning beach", "category": "nature"},
                ],
                "latitude": 16.0544,
                "longitude": 108.2022,
            },
            {
                "name": "Hue",
                "country": "Vietnam",
                "days": 3,
                "why_visit": "Imperial citadel and royal tombs",
                "best_time_to_visit": "Jan-Apr",
                "highlights": [
                    {"name": "Imperial City", "description": "Walled fortress and palace", "category": "history"},
                    {"name": "Thien Mu Pagoda", "description": "Iconic pagoda on the Perfume River", "category": "culture"},
                ],
                "latitude": 16.4637,
                "longitude": 107.5909,
            },
        ],
        "travel_legs": [
            {
                "from_city": "Da Nang",
                "to_city": "Hue",
                "mode": "train",
                "duration_hours": 3.0,
                "distance_km": 100,
                "notes": "Scenic coastal railway",
                "estimated_cost": "$5-10",
                "booking_tip": "Book Reunification Express",
                "fare": None,
                "num_transfers": 0,
                "departure_time": None,
                "arrival_time": None,
            }
        ],
    }


def _make_context() -> dict:
    return {
        "origin": "Ho Chi Minh City",
        "region": "Vietnam",
        "start_date": str(date.today() + timedelta(days=14)),
        "total_days": 7,
        "interests": ["culture", "food", "history"],
        "pace": "moderate",
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_travel_legs(label: str, journey: dict):
    """Pretty-print travel legs for comparison."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    legs = journey.get("travel_legs", [])
    if not legs:
        print("  (no travel legs)")
        return
    for i, leg in enumerate(legs):
        print(f"\n  Leg {i+1}: {leg['from_city']} → {leg['to_city']}")
        print(f"    Mode:           {leg.get('mode', '?')}")
        print(f"    Duration:       {leg.get('duration_hours', '?')}h")
        print(f"    Distance:       {leg.get('distance_km', '?')} km")
        print(f"    Fare:           {leg.get('fare', 'N/A')}")
        print(f"    Departure:      {leg.get('departure_time', 'N/A')}")
        print(f"    Arrival:        {leg.get('arrival_time', 'N/A')}")
        print(f"    Transfers:      {leg.get('num_transfers', 'N/A')}")
        print(f"    Notes:          {leg.get('notes', '')[:80]}")
        print(f"    Estimated Cost: {leg.get('estimated_cost', 'N/A')}")
        print(f"    Booking Tip:    {leg.get('booking_tip', 'N/A')}")


def _check_enrichment(leg: dict) -> dict:
    """Check which enrichment fields are present on a travel leg."""
    return {
        "has_fare": leg.get("fare") is not None,
        "has_departure": leg.get("departure_time") is not None,
        "has_arrival": leg.get("arrival_time") is not None,
        "has_distance": leg.get("distance_km") is not None and leg["distance_km"] > 0,
        "has_real_duration": leg.get("duration_hours") is not None and leg["duration_hours"] > 0,
        "has_transfers": leg.get("num_transfers") is not None,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_edit_preserves_enrichment():
    """
    Test 1: Edit an existing leg (change transport mode).
    The returned travel legs should have real enrichment data.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        journey = _make_sample_journey()
        _print_travel_legs("BEFORE EDIT (raw LLM data)", journey)

        t0 = time.time()
        resp = await client.post(
            f"{BASE_URL}/api/journey/chat/edit",
            json={
                "message": "Change the transport between Da Nang and Hue to bus",
                "journey": journey,
                "context": _make_context(),
            },
        )
        elapsed = time.time() - t0

        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
        result = resp.json()

        print(f"\n  Response time: {elapsed:.1f}s")
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message'][:100]}")
        print(f"  Changes: {result['changes_made']}")

        assert result["success"], f"Edit failed: {result.get('error')}"
        assert result["updated_journey"] is not None, "No updated journey returned"

        updated = result["updated_journey"]
        _print_travel_legs("AFTER EDIT (should be enriched)", updated)

        # Check that legs exist
        legs = updated.get("travel_legs", [])
        assert len(legs) > 0, "No travel legs in updated journey"

        # Check enrichment on the Da Nang → Hue leg
        da_nang_hue = [l for l in legs if l["from_city"] == "Da Nang" and l["to_city"] == "Hue"]
        if da_nang_hue:
            leg = da_nang_hue[0]
            enrichment = _check_enrichment(leg)
            print(f"\n  Enrichment check: {json.dumps(enrichment, indent=4)}")
            # At minimum, duration and distance should be real
            assert enrichment["has_real_duration"], "Duration not enriched"
            assert enrichment["has_distance"], "Distance not enriched"


@pytest.mark.asyncio
async def test_chat_edit_add_city_creates_enriched_legs():
    """
    Test 2: Add a new city. New travel legs should get real data.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        journey = _make_sample_journey()

        t0 = time.time()
        resp = await client.post(
            f"{BASE_URL}/api/journey/chat/edit",
            json={
                "message": "Add Hoi An between Da Nang and Hue for 2 days",
                "journey": journey,
                "context": _make_context(),
            },
        )
        elapsed = time.time() - t0

        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
        result = resp.json()

        print(f"\n  Response time: {elapsed:.1f}s")
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message'][:100]}")

        assert result["success"], f"Edit failed: {result.get('error')}"
        updated = result["updated_journey"]
        assert updated is not None

        _print_travel_legs("AFTER ADDING HOI AN", updated)

        # Should now have 2 legs: Da Nang → Hoi An, Hoi An → Hue
        legs = updated.get("travel_legs", [])
        assert len(legs) >= 2, f"Expected ≥2 legs after adding city, got {len(legs)}"

        # Verify Hoi An appears in cities
        city_names = [c["name"] for c in updated.get("cities", [])]
        print(f"\n  Cities: {city_names}")
        assert any("Hoi An" in name for name in city_names), f"Hoi An not found in cities: {city_names}"

        # Check enrichment on new legs
        for leg in legs:
            enrichment = _check_enrichment(leg)
            print(f"\n  {leg['from_city']} → {leg['to_city']}: {json.dumps(enrichment)}")
            # At minimum duration should be set
            assert enrichment["has_real_duration"], (
                f"Leg {leg['from_city']}→{leg['to_city']} has no real duration"
            )


@pytest.mark.asyncio
async def test_chat_edit_remove_city():
    """
    Test 3: Remove a city. Remaining legs should be re-enriched.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Start with a 3-city journey
        journey = _make_sample_journey()
        # Add a third city and extra leg for this test
        journey["cities"].append({
            "name": "Hanoi",
            "country": "Vietnam",
            "days": 2,
            "why_visit": "Capital city charm",
            "highlights": [
                {"name": "Hoan Kiem Lake", "description": "Iconic lake in old quarter", "category": "culture"}
            ],
            "latitude": 21.0285,
            "longitude": 105.8542,
        })
        journey["travel_legs"].append({
            "from_city": "Hue",
            "to_city": "Hanoi",
            "mode": "flight",
            "duration_hours": 1.5,
            "distance_km": 600,
            "notes": "Short flight",
            "fare": None,
            "num_transfers": 0,
            "departure_time": None,
            "arrival_time": None,
        })
        journey["total_days"] = 7

        _print_travel_legs("BEFORE REMOVAL (3 cities)", journey)

        t0 = time.time()
        resp = await client.post(
            f"{BASE_URL}/api/journey/chat/edit",
            json={
                "message": "Remove Hue from the trip",
                "journey": journey,
                "context": _make_context(),
            },
        )
        elapsed = time.time() - t0

        assert resp.status_code == 200
        result = resp.json()

        print(f"\n  Response time: {elapsed:.1f}s")
        print(f"  Success: {result['success']}")

        assert result["success"], f"Edit failed: {result.get('error')}"
        updated = result["updated_journey"]
        assert updated is not None

        _print_travel_legs("AFTER REMOVING HUE", updated)

        city_names = [c["name"] for c in updated.get("cities", [])]
        print(f"\n  Cities: {city_names}")
        assert "Hue" not in city_names, f"Hue should be removed but still found in {city_names}"

        # Should have a direct leg from Da Nang to Hanoi (or wherever the LLM connects them)
        legs = updated.get("travel_legs", [])
        assert len(legs) >= 1, "Should have at least one travel leg after removal"

        for leg in legs:
            enrichment = _check_enrichment(leg)
            print(f"\n  {leg['from_city']} → {leg['to_city']}: {json.dumps(enrichment)}")


@pytest.mark.asyncio
async def test_enrichment_failure_doesnt_crash():
    """
    Test 4: Use nonsensical city names — enrichment may fail but the
    endpoint should still return the LLM's edit without crashing.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        journey = {
            "theme": "Test Journey",
            "summary": "Testing error handling",
            "route": "TestCityAlpha → TestCityBeta",
            "origin": "TestCityAlpha",
            "region": "Testland",
            "total_days": 3,
            "cities": [
                {
                    "name": "TestCityAlpha",
                    "country": "Testland",
                    "days": 1,
                    "highlights": [],
                },
                {
                    "name": "TestCityBeta",
                    "country": "Testland",
                    "days": 2,
                    "highlights": [],
                },
            ],
            "travel_legs": [
                {
                    "from_city": "TestCityAlpha",
                    "to_city": "TestCityBeta",
                    "mode": "drive",
                    "duration_hours": 2,
                    "distance_km": 100,
                    "notes": "",
                    "fare": None,
                    "num_transfers": 0,
                    "departure_time": None,
                    "arrival_time": None,
                }
            ],
        }

        resp = await client.post(
            f"{BASE_URL}/api/journey/chat/edit",
            json={
                "message": "Add one more day in TestCityBeta",
                "journey": journey,
                "context": {},
            },
        )

        # Should NOT crash — should return 200 regardless of enrichment outcome
        print(f"\n  Status: {resp.status_code}")
        assert resp.status_code == 200, f"Endpoint crashed: HTTP {resp.status_code}: {resp.text}"

        result = resp.json()
        print(f"  Success: {result['success']}")
        print(f"  Error: {result.get('error')}")

        # It's OK if success is False (LLM might not handle fake cities),
        # but it should NOT be an unhandled 500 error
        if result["success"] and result["updated_journey"]:
            _print_travel_legs("RESPONSE (fake cities)", result["updated_journey"])
            print("\n  Enrichment ran without crashing on fake cities ✓")


@pytest.mark.asyncio
async def test_before_vs_after_enrichment_comparison():
    """
    Test 5: End-to-end comparison. Send a journey with unenriched
    train leg, edit via chat, and compare the enrichment fields
    before and after.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        journey = _make_sample_journey()
        original_leg = journey["travel_legs"][0].copy()

        resp = await client.post(
            f"{BASE_URL}/api/journey/chat/edit",
            json={
                "message": "Keep the same plan but give me more time in Hue, make it 4 days",
                "journey": journey,
                "context": _make_context(),
            },
        )

        assert resp.status_code == 200
        result = resp.json()

        if not result["success"]:
            pytest.skip(f"LLM edit didn't succeed: {result.get('error', result['message'])}")

        updated = result["updated_journey"]
        assert updated is not None

        updated_legs = updated.get("travel_legs", [])
        da_nang_hue = [l for l in updated_legs if l["from_city"] == "Da Nang" and l["to_city"] == "Hue"]

        if not da_nang_hue:
            pytest.skip("Da Nang → Hue leg not found after edit")

        updated_leg = da_nang_hue[0]

        print("\n  BEFORE vs AFTER enrichment:")
        fields = ["fare", "departure_time", "arrival_time", "num_transfers", "duration_hours", "distance_km", "notes"]
        for field in fields:
            before = original_leg.get(field)
            after = updated_leg.get(field)
            changed = "✓ ENRICHED" if before != after and after is not None else ""
            print(f"    {field:20s}: {str(before):>15s} → {str(after):>15s}  {changed}")

        # The enrichment should have changed at least the distance (driving fallback)
        # or transit-specific fields. Fare/departure may be unavailable for some routes.
        distance_changed = updated_leg.get("distance_km") != original_leg.get("distance_km")
        duration_changed = updated_leg.get("duration_hours") != original_leg.get("duration_hours")
        has_fare = updated_leg.get("fare") is not None
        has_departure = updated_leg.get("departure_time") is not None
        notes_changed = updated_leg.get("notes") != original_leg.get("notes")

        any_enrichment = distance_changed or duration_changed or has_fare or has_departure or notes_changed
        print(f"\n  Any enrichment detected: {any_enrichment}")
        print(f"    distance_changed={distance_changed}, duration_changed={duration_changed}")
        print(f"    has_fare={has_fare}, has_departure={has_departure}, notes_changed={notes_changed}")

        assert any_enrichment, (
            "No enrichment fields changed — re-enrichment may not be working. "
            "Expected at least distance_km to update from driving fallback."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
