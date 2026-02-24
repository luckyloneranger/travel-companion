"""Geographic clustering quality evaluator."""

import math
from typing import TYPE_CHECKING

from app.generators.day_plan.quality.evaluators.base import BaseEvaluator
from app.generators.day_plan.quality.models import MetricResult, METRIC_WEIGHTS
from app.utils.geo import haversine_distance

if TYPE_CHECKING:
    from app.models import ItineraryResponse, DayPlan, Location


# Maximum acceptable distance between consecutive activities (km)
MAX_CONSECUTIVE_DISTANCE_KM = 5.0
IDEAL_CONSECUTIVE_DISTANCE_KM = 2.0

# Maximum acceptable total travel per day (km)
MAX_DAILY_TRAVEL_KM = 30.0
IDEAL_DAILY_TRAVEL_KM = 15.0


class GeographicClusteringEvaluator(BaseEvaluator):
    """
    Evaluates geographic clustering quality.
    
    Checks:
    - Activities within each day are geographically close
    - No excessive backtracking
    - Reasonable daily travel distances
    """
    
    @property
    def name(self) -> str:
        return "Geographic Clustering"
    
    @property
    def weight(self) -> float:
        return METRIC_WEIGHTS["geographic_clustering"]
    
    def evaluate(self, itinerary: "ItineraryResponse") -> MetricResult:
        issues: list[str] = []
        suggestions: list[str] = []
        
        if not itinerary.days:
            return self._create_result(
                score=100,  # No days = nothing wrong with clustering
                issues=[],
                suggestions=[],
            )
        
        day_scores: list[float] = []
        details = {
            "days_analyzed": len(itinerary.days),
            "total_distance_km": 0.0,
            "avg_daily_distance_km": 0.0,
            "max_consecutive_gap_km": 0.0,
            "backtracking_instances": 0,
        }
        
        for day in itinerary.days:
            day_result = self._evaluate_day(day)
            day_scores.append(day_result["score"])
            details["total_distance_km"] += day_result["total_distance"]
            details["max_consecutive_gap_km"] = max(
                details["max_consecutive_gap_km"],
                day_result["max_gap"]
            )
            details["backtracking_instances"] += day_result["backtracking_count"]
            
            issues.extend(day_result["issues"])
            suggestions.extend(day_result["suggestions"])
        
        if itinerary.days:
            details["avg_daily_distance_km"] = round(
                details["total_distance_km"] / len(itinerary.days), 1
            )
        
        details["total_distance_km"] = round(details["total_distance_km"], 1)
        details["max_consecutive_gap_km"] = round(details["max_consecutive_gap_km"], 1)
        
        # Overall score is average of day scores
        score = sum(day_scores) / len(day_scores) if day_scores else 100
        
        return self._create_result(
            score=score,
            issues=issues,
            suggestions=suggestions,
            details=details,
        )
    
    def _evaluate_day(self, day: "DayPlan") -> dict:
        """Evaluate geographic clustering for a single day."""
        result = {
            "score": 100.0,
            "total_distance": 0.0,
            "max_gap": 0.0,
            "backtracking_count": 0,
            "issues": [],
            "suggestions": [],
        }
        
        if len(day.activities) < 2:
            return result
        
        # Calculate distances between consecutive activities
        distances: list[float] = []
        locations: list[tuple[float, float]] = []
        
        for activity in day.activities:
            loc = activity.place.location
            locations.append((loc.lat, loc.lng))
        
        for i in range(len(locations) - 1):
            dist = haversine_distance(
                locations[i][0], locations[i][1],
                locations[i+1][0], locations[i+1][1]
            )
            distances.append(dist)
            result["total_distance"] += dist
            result["max_gap"] = max(result["max_gap"], dist)
            
            # Check for excessive gaps
            if dist > MAX_CONSECUTIVE_DISTANCE_KM:
                result["issues"].append(
                    f"Day {day.day_number}: {dist:.1f}km gap between "
                    f"'{day.activities[i].place.name}' and '{day.activities[i+1].place.name}'"
                )
                result["suggestions"].append(
                    f"Day {day.day_number}: Consider reordering activities or finding closer alternatives"
                )
        
        # Check for backtracking (simplified: if we significantly increase then decrease longitude/latitude)
        backtracking = self._detect_backtracking(locations)
        result["backtracking_count"] = backtracking
        if backtracking > 0:
            result["issues"].append(
                f"Day {day.day_number}: Detected {backtracking} potential backtracking instance(s)"
            )
        
        # Calculate score
        # Penalize based on:
        # 1. Consecutive distances exceeding ideal
        # 2. Total daily distance exceeding ideal
        # 3. Backtracking
        
        penalty = 0.0
        
        # Penalty for large gaps
        for dist in distances:
            if dist > MAX_CONSECUTIVE_DISTANCE_KM:
                penalty += 15  # Severe penalty
            elif dist > IDEAL_CONSECUTIVE_DISTANCE_KM:
                penalty += (dist - IDEAL_CONSECUTIVE_DISTANCE_KM) * 3
        
        # Penalty for excessive daily travel
        if result["total_distance"] > MAX_DAILY_TRAVEL_KM:
            penalty += 20
        elif result["total_distance"] > IDEAL_DAILY_TRAVEL_KM:
            over = result["total_distance"] - IDEAL_DAILY_TRAVEL_KM
            penalty += over * 1.5
        
        # Penalty for backtracking
        penalty += backtracking * 10
        
        result["score"] = max(0, 100 - penalty)
        
        return result
    
    def _detect_backtracking(self, locations: list[tuple[float, float]]) -> int:
        """
        Detect potential backtracking in a sequence of locations.
        
        Simple heuristic: if we move significantly east then west (or north then south),
        that's potential backtracking.
        """
        if len(locations) < 3:
            return 0
        
        backtracking_count = 0
        threshold_km = 1.5  # Minimum distance to consider as intentional movement
        
        for i in range(len(locations) - 2):
            # Get vectors for two consecutive movements
            lat1, lon1 = locations[i]
            lat2, lon2 = locations[i + 1]
            lat3, lon3 = locations[i + 2]
            
            # Distance of first movement
            dist1 = haversine_distance(lat1, lon1, lat2, lon2)
            # Distance of second movement  
            dist2 = haversine_distance(lat2, lon2, lat3, lon3)
            
            # Only check substantial movements
            if dist1 < threshold_km or dist2 < threshold_km:
                continue
            
            # Check if we're moving back toward the start
            dist_start_to_end = haversine_distance(lat1, lon1, lat3, lon3)
            total_travel = dist1 + dist2
            
            # If total travel is much greater than start-to-end distance, that's backtracking
            if total_travel > 0 and dist_start_to_end / total_travel < 0.3:
                backtracking_count += 1
        
        return backtracking_count
