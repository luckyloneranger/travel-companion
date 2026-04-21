"""Batch pipeline — full quality generation for content library."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID
from typing import Any, Callable, Awaitable

from app.pipelines.discovery import DiscoveryPipeline
from app.pipelines.curation import CurationPipeline
from app.pipelines.routing import RoutingPipeline
from app.pipelines.scheduling import SchedulingPipeline
from app.pipelines.review import ReviewPipeline
from app.pipelines.costing import CostingPipeline
from app.db.repository import PlaceRepository, VariantRepository, DayPlanRepository
from app.config.planning import BATCH_MAX_ITERATIONS, BATCH_MIN_SCORE

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int], Awaitable[None]] | None


@dataclass
class BatchResult:
    variant_id: UUID | None
    status: str  # published / draft
    quality_score: int
    iterations_used: int


class BatchPipeline:
    """Chains all 6 pipeline steps for offline high-quality generation.

    Steps: Discover -> Curate -> Route -> Schedule -> Review/Fix -> Cost -> Store
    """

    def __init__(
        self,
        discovery: DiscoveryPipeline,
        curation: CurationPipeline,
        routing: RoutingPipeline,
        scheduling: SchedulingPipeline,
        review: ReviewPipeline,
        costing: CostingPipeline,
        place_repo: PlaceRepository,
        variant_repo: VariantRepository,
        day_plan_repo: DayPlanRepository,
    ):
        self.discovery = discovery
        self.curation = curation
        self.routing = routing
        self.scheduling = scheduling
        self.review = review
        self.costing = costing
        self.place_repo = place_repo
        self.variant_repo = variant_repo
        self.day_plan_repo = day_plan_repo

    async def generate(
        self,
        city_id: UUID,
        city_name: str,
        country: str,
        pace: str,
        budget: str,
        day_count: int,
        on_progress: ProgressCallback = None,
    ) -> BatchResult:
        """Generate a high-quality city plan variant.

        Steps: Discover -> Curate -> Route -> Schedule -> Review/Fix -> Cost -> Store
        """
        # Step 1: Discover (10%)
        if on_progress:
            await on_progress(5)
        discovery_result = await self.discovery.discover(city_name)
        if on_progress:
            await on_progress(15)

        # Upsert all candidates to places table
        place_id_map = await self._upsert_places(
            city_id, discovery_result.candidates + discovery_result.lodging_candidates
        )
        if on_progress:
            await on_progress(25)

        # Step 2: Curate (35%)
        curation_result = await self.curation.curate(
            city_name=city_name,
            country=country,
            candidates=discovery_result.candidates,
            lodging_candidates=discovery_result.lodging_candidates,
            pace=pace,
            budget=budget,
            day_count=day_count,
        )
        if on_progress:
            await on_progress(40)

        # Step 3-4: Route + Schedule each day (55%)
        scheduled_days = await self._route_and_schedule_days(
            curation_result, discovery_result, place_id_map, country, pace
        )
        if on_progress:
            await on_progress(55)

        # Step 5: Review + Fix (75%)
        plan_for_review = self._build_review_plan(scheduled_days)
        review_result = await self.review.review_and_fix(
            plan=plan_for_review,
            city_name=city_name,
            pace=pace,
            day_count=day_count,
            candidates=discovery_result.candidates,
            max_iterations=BATCH_MAX_ITERATIONS,
            min_score=BATCH_MIN_SCORE,
        )
        if on_progress:
            await on_progress(80)

        # Step 6: Cost (85%)
        accommodation_nightly = (
            curation_result.accommodation.estimated_nightly_usd
            if curation_result.accommodation
            else 100.0
        )
        day_plan_dicts = [
            {
                "activities": [
                    {
                        "estimated_cost_usd": a.data.get("estimated_cost_usd", 0),
                        "is_meal": a.data.get("is_meal", False),
                    }
                    for a in scheduled
                ]
            }
            for _, _, scheduled in scheduled_days
        ]
        routes_by_day = [
            [
                {
                    "travel_mode": r.travel_mode,
                    "distance_meters": r.distance_meters,
                    "duration_seconds": r.duration_seconds,
                }
                for r in routing.routes
            ]
            for _, routing, _ in scheduled_days
        ]
        cost = self.costing.compute(
            accommodation_nightly, day_count, day_plan_dicts, routes_by_day
        )
        if on_progress:
            await on_progress(90)

        # Step 7: Store (100%)
        status = "published" if review_result.best_score >= BATCH_MIN_SCORE else "draft"
        accom_gpid = (
            curation_result.accommodation.google_place_id
            if curation_result.accommodation
            else None
        )
        accom_db_id = place_id_map.get(accom_gpid) if accom_gpid else None

        variant = await self.variant_repo.create(
            city_id=city_id,
            pace=pace,
            budget=budget,
            day_count=day_count,
            status=status,
            quality_score=review_result.best_score,
            accommodation_id=accom_db_id,
            accommodation_alternatives=[
                {
                    "place_id": str(place_id_map.get(alt.google_place_id, "")),
                    "nightly_usd": alt.estimated_nightly_usd,
                }
                for alt in curation_result.accommodation_alternatives
            ],
            booking_hint=curation_result.booking_hint,
            cost_breakdown={
                "accommodation": cost.accommodation,
                "transport": cost.transport,
                "dining": cost.dining,
                "activities": cost.activities,
                "total": cost.total,
                "per_day": cost.per_day,
            },
            data_hash=discovery_result.data_hash,
        )

        # Store day plans + activities + routes
        await self._store_day_plans(variant.id, scheduled_days, place_id_map)

        if on_progress:
            await on_progress(100)

        return BatchResult(
            variant_id=variant.id,
            status=status,
            quality_score=review_result.best_score,
            iterations_used=review_result.iterations_used,
        )

    async def _upsert_places(
        self, city_id: UUID, candidates: list[dict[str, Any]]
    ) -> dict[str, UUID]:
        """Upsert candidates into the places table. Returns google_place_id -> db UUID map."""
        place_id_map: dict[str, UUID] = {}
        for candidate in candidates:
            gpid = candidate.get("google_place_id") or candidate.get("place_id")
            if not gpid:
                continue
            place = await self.place_repo.upsert_from_google(
                city_id=city_id,
                google_place_id=gpid,
                name=candidate.get("name", ""),
                address=candidate.get("address"),
                location=candidate.get("location", {}),
                types=candidate.get("types", []),
                rating=candidate.get("rating"),
                user_rating_count=candidate.get("user_rating_count")
                or candidate.get("user_ratings_total"),
                price_level=candidate.get("price_level"),
                opening_hours=candidate.get("opening_hours"),
                photo_references=candidate.get("photo_references", []),
                editorial_summary=candidate.get("editorial_summary"),
                website_url=candidate.get("website_url"),
                is_lodging=candidate.get("is_lodging", False),
                last_verified_at=datetime.now(timezone.utc),
            )
            place_id_map[gpid] = place.id
        return place_id_map

    async def _route_and_schedule_days(
        self,
        curation_result: Any,
        discovery_result: Any,
        place_id_map: dict[str, UUID],
        country: str,
        pace: str,
    ) -> list[tuple[Any, Any, list]]:
        """Route and schedule each curated day. Returns list of (day, routing_result, scheduled)."""
        scheduled_days = []
        all_candidates = discovery_result.candidates + discovery_result.lodging_candidates

        for day in curation_result.days:
            activities = []
            for act in day.activities:
                gpid = act.google_place_id
                candidate = next(
                    (
                        c
                        for c in all_candidates
                        if (c.get("google_place_id") or c.get("place_id")) == gpid
                    ),
                    {},
                )
                activities.append(
                    {
                        "google_place_id": gpid,
                        "place_id": str(place_id_map.get(gpid, "")),
                        "location": candidate.get("location", {}),
                        "name": candidate.get("name", ""),
                        "category": act.category,
                        "description": act.description,
                        "duration_minutes": act.duration_minutes,
                        "is_meal": act.is_meal,
                        "meal_type": act.meal_type,
                        "estimated_cost_usd": act.estimated_cost_usd,
                        "opening_hours": candidate.get("opening_hours"),
                    }
                )

            routing_result = await self.routing.route_day(activities, pace=pace)

            routes_as_dicts = [
                {
                    "duration_seconds": r.duration_seconds,
                    "distance_meters": r.distance_meters,
                    "travel_mode": r.travel_mode,
                }
                for r in routing_result.routes
            ]
            scheduled = self.scheduling.schedule_day(
                activities=routing_result.ordered_activities,
                routes=routes_as_dicts,
                country=country,
                pace=pace,
            )
            scheduled_days.append((day, routing_result, scheduled))

        return scheduled_days

    def _build_review_plan(self, scheduled_days: list[tuple]) -> dict:
        """Build plan dict for the reviewer from scheduled days."""
        return {
            "days": [
                {
                    "day_number": day.day_number,
                    "theme": day.theme,
                    "activities": [
                        {
                            "google_place_id": a.data.get("google_place_id", ""),
                            "category": a.data.get("category", ""),
                            "duration_minutes": a.duration_minutes,
                            "is_meal": a.data.get("is_meal", False),
                        }
                        for a in scheduled
                    ],
                }
                for day, _, scheduled in scheduled_days
            ]
        }

    async def _store_day_plans(
        self,
        variant_id: UUID,
        scheduled_days: list[tuple],
        place_id_map: dict[str, UUID],
    ) -> None:
        """Persist day plans, activities, and routes to the database."""
        for day, routing_result, scheduled in scheduled_days:
            activities_data = []
            for s in scheduled:
                gpid = s.data.get("google_place_id", "")
                db_place_id = place_id_map.get(gpid)
                if not db_place_id:
                    continue
                activities_data.append(
                    {
                        "place_id": db_place_id,
                        "sequence": s.sequence,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "duration_minutes": s.duration_minutes,
                        "category": s.data.get("category", ""),
                        "description": s.data.get("description"),
                        "is_meal": s.data.get("is_meal", False),
                        "meal_type": s.data.get("meal_type"),
                        "estimated_cost_usd": s.data.get("estimated_cost_usd"),
                    }
                )

            routes_data = [
                {
                    "travel_mode": r.travel_mode,
                    "distance_meters": r.distance_meters,
                    "duration_seconds": r.duration_seconds,
                    "polyline": r.polyline,
                }
                for r in routing_result.routes
            ]

            await self.day_plan_repo.create_with_activities(
                variant_id=variant_id,
                day_number=day.day_number,
                theme=day.theme,
                theme_description=day.theme_description,
                activities=activities_data,
                routes=routes_data,
            )
