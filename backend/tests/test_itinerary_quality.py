"""
Integration tests to evaluate itinerary quality.
These tests call real APIs to verify the AI generates proper itineraries.

Run with: pytest tests/test_itinerary_quality.py -v -s
"""

import asyncio
import pytest
from datetime import date, timedelta

from app.services.external.google_places import GooglePlacesService
from app.services.external.azure_openai import AzureOpenAIService
from app.generators.day_plan.fast import FastItineraryGenerator as ItineraryGenerator
from app.models import ItineraryRequest, Pace
from app.generators.day_plan.quality import ItineraryScorer, QualityReport, QualityGrade


# Test destinations
TEST_DESTINATIONS = [
    "Hyderabad, India",
    "Paris, France", 
    "New York City, USA",
]


def print_quality_report(report: QualityReport, destination: str):
    """Pretty print the quality report."""
    print(f"\n{'='*60}")
    print(f"ITINERARY QUALITY REPORT: {destination}")
    print(f"{'='*60}")
    
    status = "✅ PASSED" if report.overall_grade.value.startswith(('A', 'B')) else "❌ NEEDS IMPROVEMENT"
    print(f"Overall Grade: {report.overall_grade.value} ({report.overall_score:.1f}/100)")
    print(f"Status: {status}")
    print(f"Total Days: {report.num_days}")
    
    print(f"\n--- Metric Breakdown ---")
    for result in report.metrics:
        grade_emoji = "✅" if result.grade.value.startswith(('A', 'B')) else "⚠️"
        print(f"  {grade_emoji} {result.name}: {result.score:.1f}% ({result.grade.value})")
        if result.issues:
            for issue in result.issues[:2]:  # Show first 2 issues
                print(f"      - {issue}")
    
    print(f"\n--- Quality Scores ---")
    print(f"  Meal Timing: {report.scores.meal_timing:.1f}%")
    print(f"  Geographic Clustering: {report.scores.geographic_clustering:.1f}%")
    print(f"  Travel Efficiency: {report.scores.travel_efficiency:.1f}%")
    print(f"  Variety: {report.scores.variety:.1f}%")
    print(f"  Opening Hours: {report.scores.opening_hours:.1f}%")
    print(f"  Theme Alignment: {report.scores.theme_alignment:.1f}%")
    print(f"  Duration Appropriateness: {report.scores.duration_appropriateness:.1f}%")
    
    print(f"\n{'='*60}\n")


@pytest.fixture
def places_service():
    return GooglePlacesService()


@pytest.fixture
def ai_service():
    return AzureOpenAIService()


@pytest.fixture  
def itinerary_generator():
    return ItineraryGenerator()


@pytest.fixture
def quality_scorer():
    return ItineraryScorer()


class TestItineraryQuality:
    """Test suite for itinerary quality evaluation using the quality module."""
    
    @pytest.mark.asyncio
    async def test_hyderabad_itinerary_quality(self, itinerary_generator, quality_scorer):
        """Test itinerary quality for Hyderabad, India."""
        request = ItineraryRequest(
            destination="Hyderabad, India",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=9),  # 3 days
            interests=["food", "history", "culture"],
            pace=Pace.MODERATE,
        )
        
        itinerary = await itinerary_generator.generate(request)
        
        # Evaluate using the quality module
        report = quality_scorer.evaluate(itinerary)
        
        print_quality_report(report, "Hyderabad, India")
        
        # Assertions
        assert report.num_days == 3, f"Expected 3 days, got {report.num_days}"
        assert report.overall_score >= 50, f"Quality score too low: {report.overall_score}"
        
        # Check each day has activities
        for day in itinerary.days:
            assert len(day.activities) >= 3, f"Day should have at least 3 activities"
    
    @pytest.mark.asyncio
    async def test_place_categorization(self, places_service):
        """Test that places are correctly categorized."""
        # Geocode Hyderabad
        destination = await places_service.geocode("Hyderabad, India")
        
        # Discover places 
        candidates = await places_service.discover_places(
            location=destination.location,
            interests=["food", "history"],
            radius_km=15
        )
        
        print(f"\n{'='*60}")
        print("PLACE CATEGORIZATION TEST")
        print(f"{'='*60}")
        print(f"Total candidates: {len(candidates)}")
        
        # Categorize
        dining_keywords = {"restaurant", "cafe", "bakery", "bar", "food", "biryani", "hotel"}
        attraction_keywords = {"temple", "mosque", "fort", "palace", "museum", "park", "monument", "tourist_attraction"}
        
        dining = []
        attractions = []
        other = []
        
        for c in candidates:
            types_lower = [t.lower() for t in c.types]
            name_lower = c.name.lower()
            
            is_dining = any(kw in t or kw in name_lower for kw in dining_keywords for t in types_lower)
            is_attraction = any(kw in t or kw in name_lower for kw in attraction_keywords for t in types_lower)
            
            if is_dining:
                dining.append(c)
            elif is_attraction:
                attractions.append(c)
            else:
                other.append(c)
        
        print(f"\nDining spots ({len(dining)}):")
        for d in dining[:10]:
            print(f"  - {d.name} | types: {d.types[:3]}")
        
        print(f"\nAttractions ({len(attractions)}):")
        for a in attractions[:10]:
            print(f"  - {a.name} | types: {a.types[:3]}")
        
        print(f"\nOther ({len(other)}):")
        for o in other[:5]:
            print(f"  - {o.name} | types: {o.types[:3]}")
        
        # Assertions
        assert len(dining) > 0, "Should find dining spots"
        assert len(attractions) > 0, "Should find attractions"
        
        print(f"\n✅ Found {len(attractions)} attractions and {len(dining)} dining spots")
        print(f"{'='*60}\n")
    
    @pytest.mark.asyncio
    async def test_quality_grade_thresholds(self, quality_scorer):
        """Test that quality grades are assigned correctly."""
        # Test grade boundaries
        assert QualityGrade.from_score(95) == QualityGrade.A_PLUS
        assert QualityGrade.from_score(90) == QualityGrade.A
        assert QualityGrade.from_score(85) == QualityGrade.A_MINUS
        assert QualityGrade.from_score(80) == QualityGrade.B_PLUS
        assert QualityGrade.from_score(75) == QualityGrade.B
        assert QualityGrade.from_score(70) == QualityGrade.B_MINUS
        assert QualityGrade.from_score(65) == QualityGrade.C_PLUS
        assert QualityGrade.from_score(60) == QualityGrade.C
        assert QualityGrade.from_score(55) == QualityGrade.C_MINUS
        assert QualityGrade.from_score(50) == QualityGrade.D
        assert QualityGrade.from_score(45) == QualityGrade.F


@pytest.mark.asyncio
async def test_full_itinerary_quality():
    """Standalone test for full itinerary generation and quality check."""
    generator = ItineraryGenerator()
    scorer = ItineraryScorer()
    
    request = ItineraryRequest(
        destination="Hyderabad, India",
        start_date=date.today() + timedelta(days=7),
        end_date=date.today() + timedelta(days=9),
        interests=["food", "history", "culture"],
        pace=Pace.MODERATE,
    )
    
    print("\n🚀 Generating itinerary...")
    itinerary = await generator.generate(request)
    
    print("\n📊 Evaluating quality using quality module...")
    report = scorer.evaluate(itinerary)
    
    print_quality_report(report, request.destination)
    
    # Return report for inspection
    return report


if __name__ == "__main__":
    # Run standalone test
    report = asyncio.run(test_full_itinerary_quality())
    
    # Consider B- or better as passing
    is_passing = report.overall_grade.value in ["A+", "A", "A-", "B+", "B", "B-"]
    
    if not is_passing:
        print(f"\n⚠️ Quality grade {report.overall_grade.value} needs improvement.")
        exit(1)
    else:
        print(f"\n✅ Itinerary passed quality checks with grade {report.overall_grade.value}!")
        exit(0)
