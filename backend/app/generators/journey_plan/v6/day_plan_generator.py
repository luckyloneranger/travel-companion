"""V6 Day Plan Generator - Generates detailed itineraries for journey cities.

Reuses FastItineraryGenerator for each city in a V6 journey plan.
Generates day-by-day activities for the complete multi-city trip.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import AsyncIterator, Callable, Optional, Awaitable

from app.generators.day_plan.fast.generator import FastItineraryGenerator
from app.models import ItineraryRequest, ItineraryResponse, Pace, TravelMode, DayPlan
from .models import JourneyPlan, CityStop


logger = logging.getLogger(__name__)


@dataclass
class CityDayPlans:
    """Day plans for a single city in the journey."""
    city_name: str
    country: str
    days: int
    start_date: date
    day_plans: list[DayPlan] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class JourneyDayPlansResult:
    """Complete day plans for all cities in the journey."""
    journey_theme: str
    total_days: int
    city_plans: list[CityDayPlans] = field(default_factory=list)
    all_day_plans: list[DayPlan] = field(default_factory=list)  # Flattened view


@dataclass
class DayPlanProgress:
    """Progress event for day plan generation."""
    phase: str  # "city_start", "discovering", "planning", "city_complete", "complete", "error"
    city_name: Optional[str]
    city_index: int
    total_cities: int
    message: str
    progress: int  # 0-100 overall
    city_progress: int  # 0-100 for current city
    data: Optional[dict] = None


# Type alias for progress callback
ProgressCallback = Callable[[str, str, int, Optional[dict]], Awaitable[None]]


class V6DayPlanGenerator:
    """Generates detailed day plans for V6 journey cities.
    
    Takes a finalized V6 JourneyPlan and generates detailed itineraries
    for each city using the FastItineraryGenerator.
    """
    
    def __init__(self):
        """Initialize the generator."""
        self.fast_generator = FastItineraryGenerator()
    
    async def generate_day_plans(
        self,
        journey: JourneyPlan,
        start_date: date,
        interests: list[str],
        pace: Pace = Pace.MODERATE,
        travel_mode: TravelMode = TravelMode.WALK,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> JourneyDayPlansResult:
        """
        Generate day plans for all cities in the journey.
        
        Args:
            journey: The V6 JourneyPlan with cities and durations
            start_date: Trip start date
            interests: User interests for activity selection
            pace: Daily activity pace
            travel_mode: Preferred travel mode within cities
            progress_callback: Optional callback for progress updates
            
        Returns:
            JourneyDayPlansResult with day plans for each city
        """
        logger.info(f"Generating day plans for {len(journey.cities)} cities")
        
        result = JourneyDayPlansResult(
            journey_theme=journey.theme,
            total_days=journey.total_days,
        )
        
        current_date = start_date
        total_cities = len(journey.cities)
        
        for city_idx, city in enumerate(journey.cities):
            city_start_date = current_date
            city_end_date = current_date + timedelta(days=city.days - 1)
            
            logger.info(f"Generating for {city.name} ({city.days} days: {city_start_date} - {city_end_date})")
            
            # Report city start
            if progress_callback:
                overall_progress = int((city_idx / total_cities) * 100)
                await progress_callback(
                    "city_start",
                    f"Starting {city.name} ({city.days} days)...",
                    overall_progress,
                    {"city": city.name, "days": city.days, "city_index": city_idx + 1}
                )
            
            # Create request for this city
            city_request = ItineraryRequest(
                destination=f"{city.name}, {city.country}",
                start_date=city_start_date,
                end_date=city_end_date,
                interests=interests,
                pace=pace,
                travel_mode=travel_mode,
            )
            
            city_plans = CityDayPlans(
                city_name=city.name,
                country=city.country,
                days=city.days,
                start_date=city_start_date,
            )
            
            try:
                # Create city-specific progress callback
                async def city_progress(phase: str, message: str, percent: int, data: Optional[dict] = None):
                    if progress_callback:
                        # Calculate overall progress
                        city_weight = 1.0 / total_cities
                        overall = int((city_idx * city_weight + (percent / 100.0) * city_weight) * 100)
                        await progress_callback(
                            phase,
                            f"[{city.name}] {message}",
                            overall,
                            {"city": city.name, "city_progress": percent, **(data or {})}
                        )
                
                # Generate itinerary for this city
                itinerary = await self.fast_generator.generate(
                    city_request,
                    progress_callback=city_progress
                )
                
                # Extract day plans
                city_plans.day_plans = itinerary.days
                result.all_day_plans.extend(itinerary.days)
                
                logger.info(f"Generated {len(city_plans.day_plans)} days for {city.name}")
                
            except Exception as e:
                logger.error(f"Failed to generate day plans for {city.name}: {e}", exc_info=True)
                city_plans.error = str(e)
                
                if progress_callback:
                    await progress_callback(
                        "city_error",
                        f"Error generating {city.name}: {str(e)[:50]}",
                        int((city_idx + 1) / total_cities * 100),
                        {"city": city.name, "error": str(e)}
                    )
            
            result.city_plans.append(city_plans)
            
            # Move to next city's start date (add travel day after city days)
            # Note: Travel legs connect cities, so next city starts after travel
            current_date = city_end_date + timedelta(days=1)
        
        logger.info(f"Completed day plans: {len(result.all_day_plans)} total days across {len(result.city_plans)} cities")
        
        if progress_callback:
            await progress_callback(
                "complete",
                f"Generated {len(result.all_day_plans)} day plans for {len(result.city_plans)} cities",
                100,
                {"total_days": len(result.all_day_plans), "total_cities": len(result.city_plans)}
            )
        
        return result
    
    async def generate_day_plans_stream(
        self,
        journey: JourneyPlan,
        start_date: date,
        interests: list[str],
        pace: Pace = Pace.MODERATE,
        travel_mode: TravelMode = TravelMode.WALK,
    ) -> AsyncIterator[DayPlanProgress]:
        """
        Stream day plan generation progress.
        
        Yields progress events as itineraries are generated for each city.
        """
        logger.info(f"[Stream] Generating day plans for {len(journey.cities)} cities")
        
        result = JourneyDayPlansResult(
            journey_theme=journey.theme,
            total_days=journey.total_days,
        )
        
        current_date = start_date
        total_cities = len(journey.cities)
        
        for city_idx, city in enumerate(journey.cities):
            city_start_date = current_date
            city_end_date = current_date + timedelta(days=city.days - 1)
            
            overall_progress = int((city_idx / total_cities) * 100)
            
            # Yield city start
            yield DayPlanProgress(
                phase="city_start",
                city_name=city.name,
                city_index=city_idx + 1,
                total_cities=total_cities,
                message=f"Planning {city.name} ({city.days} days)",
                progress=overall_progress,
                city_progress=0,
                data={"country": city.country, "start_date": str(city_start_date)}
            )
            
            # Create request
            city_request = ItineraryRequest(
                destination=f"{city.name}, {city.country}",
                start_date=city_start_date,
                end_date=city_end_date,
                interests=interests,
                pace=pace,
                travel_mode=travel_mode,
            )
            
            city_plans = CityDayPlans(
                city_name=city.name,
                country=city.country,
                days=city.days,
                start_date=city_start_date,
            )
            
            try:
                # Progress tracking for this city
                last_city_progress = [0]
                
                async def track_progress(phase: str, message: str, percent: int, data: Optional[dict] = None):
                    last_city_progress[0] = percent
                
                # Generate itinerary
                itinerary = await self.fast_generator.generate(
                    city_request,
                    progress_callback=track_progress
                )
                
                city_plans.day_plans = itinerary.days
                result.city_plans.append(city_plans)
                result.all_day_plans.extend(itinerary.days)
                
                # Yield city complete with day plans
                city_complete_progress = int(((city_idx + 1) / total_cities) * 100)
                yield DayPlanProgress(
                    phase="city_complete",
                    city_name=city.name,
                    city_index=city_idx + 1,
                    total_cities=total_cities,
                    message=f"Completed {city.name}: {len(city_plans.day_plans)} days planned",
                    progress=city_complete_progress,
                    city_progress=100,
                    data={
                        "days_generated": len(city_plans.day_plans),
                        "day_plans": [
                            {
                                "date": str(dp.date),
                                "day_number": dp.day_number,
                                "theme": dp.theme,
                                "activity_count": len(dp.activities),
                            }
                            for dp in city_plans.day_plans
                        ]
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to generate for {city.name}: {e}", exc_info=True)
                city_plans.error = str(e)
                result.city_plans.append(city_plans)
                
                yield DayPlanProgress(
                    phase="city_error",
                    city_name=city.name,
                    city_index=city_idx + 1,
                    total_cities=total_cities,
                    message=f"Error with {city.name}: {str(e)[:50]}",
                    progress=int(((city_idx + 1) / total_cities) * 100),
                    city_progress=0,
                    data={"error": str(e)}
                )
            
            current_date = city_end_date + timedelta(days=1)
        
        # Final complete event with all data
        yield DayPlanProgress(
            phase="complete",
            city_name=None,
            city_index=total_cities,
            total_cities=total_cities,
            message=f"Journey complete: {len(result.all_day_plans)} days across {total_cities} cities",
            progress=100,
            city_progress=100,
            data={
                "journey_theme": result.journey_theme,
                "total_days": len(result.all_day_plans),
                "total_cities": total_cities,
                "city_summaries": [
                    {
                        "city": cp.city_name,
                        "days": cp.days,
                        "day_plans_count": len(cp.day_plans),
                        "error": cp.error,
                    }
                    for cp in result.city_plans
                ],
                "all_day_plans": [
                    {
                        "date": str(dp.date),
                        "day_number": dp.day_number,
                        "theme": dp.theme,
                        "activities": [
                            {
                                "time_start": a.time_start,
                                "time_end": a.time_end,
                                "place": {
                                    "name": a.place.name,
                                    "category": a.place.category,
                                    "address": a.place.address,
                                    "location": {"lat": a.place.location.lat, "lng": a.place.location.lng},
                                    "rating": a.place.rating,
                                },
                                "duration_minutes": a.duration_minutes,
                            }
                            for a in dp.activities
                        ],
                    }
                    for dp in result.all_day_plans
                ]
            }
        )
