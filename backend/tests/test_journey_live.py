"""
Live test for Journey Planning API.
Run with: python tests/test_journey_live.py
"""

import asyncio
import httpx
import json
import pytest
from datetime import date, timedelta


@pytest.mark.asyncio
async def test_journey():
    """Test the journey planning API with real data."""
    async with httpx.AsyncClient(timeout=300) as client:
        # Test journey request
        request = {
            "origin": "Mumbai, India",
            "region": "Northern Italy",
            "start_date": str(date.today() + timedelta(days=14)),
            "total_days": 7,
            "interests": ["art", "food", "history"],
            "pace": "moderate",
            "return_to_origin": False,
            "max_cities": 3,
        }

        print("=" * 60)
        print("Testing Journey Planning API")
        print("=" * 60)
        print(f"Request: {json.dumps(request, indent=2)}")
        print()

        try:
            response = await client.post(
                "http://localhost:8000/api/journey",
                json=request,
            )

            if response.status_code == 200:
                result = response.json()
                print("SUCCESS!")
                print()
                print(f"Journey Theme: {result['journey']['journey_theme']}")
                print(f"Total Days: {result['journey']['total_days']}")
                print(f"Destinations: {result['journey']['num_destinations']}")
                print(f"Quality Score: {result['total_quality_score']}")
                print(f"Generation Time: {result['generation_time_seconds']}s")
                print()
                print("Route:")
                for leg in result["journey"]["legs"]:
                    print(f"  {leg['leg_number']}. {leg['destination']} ({leg['days']} days)")
                    if leg.get("rationale"):
                        print(f"     Why: {leg['rationale'][:80]}...")
                    if leg.get("highlights"):
                        print(f"     Highlights: {', '.join(leg['highlights'][:3])}")
                    if leg.get("transport_to_next"):
                        t = leg["transport_to_next"]
                        print(f"     -> {t['mode']} ({t['duration_hours']}h)")
                    print()

                # Print itinerary summary for each leg
                print("=" * 60)
                print("Leg Itineraries Summary")
                print("=" * 60)
                for i, itin in enumerate(result["legs_itineraries"], 1):
                    dest = itin.get("destination", {})
                    quality = itin.get("quality_score", {})
                    print(f"Leg {i}: {dest.get('name', 'Unknown')}")
                    print(f"  Days: {len(itin.get('days', []))}")
                    if quality:
                        print(f"  Quality: {quality.get('overall', 0):.1f} ({quality.get('grade', 'N/A')})")
                    print()

            else:
                print(f"FAILED: HTTP {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_journey())
