"""Costing pipeline — deterministic cost breakdown computation."""

from dataclasses import dataclass


@dataclass
class CostBreakdown:
    accommodation: float
    transport: float
    dining: float
    activities: float
    total: float
    per_day: list[float]


class CostingPipeline:
    # Transport cost estimates per mode
    TRANSPORT_COST_PER_KM = {
        "walk": 0.0,
        "drive": 0.15,  # ~$0.15/km (taxi/rideshare avg)
        "transit": 0.0,  # flat rate per trip below
    }
    TRANSIT_FLAT_RATE = 2.5  # avg transit fare per trip

    def compute(
        self,
        accommodation_nightly_usd: float,
        day_count: int,
        day_plans: list[dict],
        routes_by_day: list[list[dict]],
    ) -> CostBreakdown:
        """Compute cost breakdown from plan data.

        Args:
            accommodation_nightly_usd: nightly hotel cost
            day_count: number of days
            day_plans: list of day dicts, each with 'activities' list
            routes_by_day: list of route lists per day
        """
        accommodation_total = accommodation_nightly_usd * day_count

        transport_total = 0.0
        dining_total = 0.0
        activities_total = 0.0
        per_day = []

        for day_idx in range(len(day_plans)):
            day = day_plans[day_idx]
            day_transport = 0.0
            day_dining = 0.0
            day_activities = 0.0

            # Activity costs
            for activity in day.get("activities", []):
                cost = activity.get("estimated_cost_usd", 0) or 0
                if activity.get("is_meal"):
                    day_dining += cost
                else:
                    day_activities += cost

            # Route transport costs
            if day_idx < len(routes_by_day):
                for route in routes_by_day[day_idx]:
                    mode = route.get("travel_mode", "walk")
                    distance_km = route.get("distance_meters", 0) / 1000
                    if mode == "transit":
                        day_transport += self.TRANSIT_FLAT_RATE
                    else:
                        rate = self.TRANSPORT_COST_PER_KM.get(mode, 0)
                        day_transport += distance_km * rate

            transport_total += day_transport
            dining_total += day_dining
            activities_total += day_activities
            per_day.append(round(day_transport + day_dining + day_activities + accommodation_nightly_usd, 2))

        total = round(accommodation_total + transport_total + dining_total + activities_total, 2)

        return CostBreakdown(
            accommodation=round(accommodation_total, 2),
            transport=round(transport_total, 2),
            dining=round(dining_total, 2),
            activities=round(activities_total, 2),
            total=total,
            per_day=per_day,
        )
