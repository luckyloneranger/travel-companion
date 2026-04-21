"""Draft pipeline — fast single-pass generation for cache misses."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID
from typing import Any

from app.pipelines.discovery import DiscoveryPipeline
from app.pipelines.curation import CurationPipeline
from app.pipelines.routing import RoutingPipeline
from app.pipelines.scheduling import SchedulingPipeline
from app.pipelines.costing import CostingPipeline
from app.db.repository import PlaceRepository, VariantRepository, DayPlanRepository, JobRepository
from app.config.planning import DRAFT_DISCOVERY_CANDIDATES

logger = logging.getLogger(__name__)


@dataclass
class DraftResult:
    variant_id: UUID | None
    status: str  # always "draft"
    upgrade_job_id: UUID | None  # batch job queued to replace this draft


class DraftPipeline:
    """Fast single-pass generation. No review/fix loop.

    Produces a draft variant and queues a batch upgrade job to replace it
    with a higher-quality published variant.
    """

    def __init__(
        self,
        discovery: DiscoveryPipeline,
        curation: CurationPipeline,
        routing: RoutingPipeline,
        scheduling: SchedulingPipeline,
        costing: CostingPipeline,
        place_repo: PlaceRepository,
        variant_repo: VariantRepository,
        day_plan_repo: DayPlanRepository,
        job_repo: JobRepository,
    ):
        self.discovery = discovery
        self.curation = curation
        self.routing = routing
        self.scheduling = scheduling
        self.costing = costing
        self.place_repo = place_repo
        self.variant_repo = variant_repo
        self.day_plan_repo = day_plan_repo
        self.job_repo = job_repo

    async def generate(
        self,
        city_id: UUID,
        city_name: str,
        country: str,
        pace: str,
        budget: str,
        day_count: int,
    ) -> DraftResult:
        """Fast single-pass generation. No review/fix loop."""
        # 1. Discover (reduced candidates)
        discovery_result = await self.discovery.discover(
            city_name, max_candidates=DRAFT_DISCOVERY_CANDIDATES
        )

        # 2. Upsert places
        place_id_map = await self._upsert_places(
            city_id, discovery_result.candidates + discovery_result.lodging_candidates
        )

        # 3. Curate (single pass, no review)
        curation_result = await self.curation.curate(
            city_name=city_name,
            country=country,
            candidates=discovery_result.candidates,
            lodging_candidates=discovery_result.lodging_candidates,
            pace=pace,
            budget=budget,
            day_count=day_count,
        )

        # 4. Route + Schedule each day
        scheduled_days = await self._route_and_schedule_days(
            curation_result, discovery_result, place_id_map, country, pace
        )

        # 5. Cost
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

        # 6. Store as draft
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
            status="draft",
            quality_score=0,
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

        # Store day plans
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
                variant_id=variant.id,
                day_number=day.day_number,
                theme=day.theme,
                theme_description=day.theme_description,
                activities=activities_data,
                routes=routes_data,
            )

        # 7. Queue upgrade job
        upgrade_job = await self.job_repo.create(
            job_type="upgrade_draft",
            city_id=city_id,
            parameters={
                "city_name": city_name,
                "country": country,
                "pace": pace,
                "budget": budget,
                "day_count": day_count,
                "draft_variant_id": str(variant.id),
            },
            priority=5,
        )

        return DraftResult(
            variant_id=variant.id,
            status="draft",
            upgrade_job_id=upgrade_job.id,
        )

    async def _upsert_places(
        self, city_id: UUID, candidates: list[dict[str, Any]]
    ) -> dict[str, UUID]:
        """Upsert candidates into places table. Returns google_place_id -> db UUID map."""
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
        """Route and schedule each curated day."""
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
