# Phase 2: Budget & Cost Tracking — Design

**Date:** 2026-03-04
**Status:** Approved

## Goal

Add cost estimation and budget tracking so users can see how much their trip will cost and track it against their budget.

## Approach

**Cost sources:**
- **Activities/attractions:** LLM estimates during day planning (e.g., "Louvre Museum: €17 entry")
- **Meals:** LLM estimates based on restaurant price_level + destination context
- **Transport:** Already have `fare` strings on travel legs — parse to numeric
- **Accommodation:** LLM estimates based on price_level + destination
- **Currency conversion:** Free exchange rate API for converting to user's home currency

**Key principles:**
- LLM does the estimation (it knows "a moderate restaurant in Tokyo costs ¥3,000-5,000")
- All costs normalized to USD for aggregation, but displayed in both local + home currency
- User can optionally set a total budget to track against
- Price tier indicators ($-$$$$) shown on all activities and accommodations

## Data Model Changes

### Backend

```python
# TripRequest — add budget fields
budget_usd: float | None = None
home_currency: str = "USD"

# Activity — add cost fields
estimated_cost_local: str | None = None    # "€17", "¥5,000"
estimated_cost_usd: float | None = None    # Normalized

# DayPlan — add daily total
daily_cost_usd: float | None = None

# New model on TripResponse
class CostBreakdown(BaseModel):
    accommodation_usd: float = 0
    transport_usd: float = 0
    activities_usd: float = 0
    dining_usd: float = 0
    total_usd: float = 0
    total_home_currency: str = ""
    budget_usd: float | None = None
    budget_remaining_usd: float | None = None
```

### Frontend

- Mirror backend types in `types/index.ts`
- `BudgetSummary` component: cost breakdown card with category bars
- Price tier indicators ($-$$$$) on ActivityCard and CityCard accommodation
- Budget input field on InputForm (optional)
- Currency selector on InputForm (default USD)

## Implementation Areas

1. **LLM prompt changes:** Update day_plan prompts to ask LLM for `estimated_cost_local` and `estimated_cost_usd` per activity
2. **Orchestrator:** Aggregate daily costs after scheduling, compute CostBreakdown
3. **Currency service:** Simple exchange rate fetcher (cache rates for 24h)
4. **Frontend components:** BudgetSummary card, price indicators, budget input
5. **Display existing data:** Show accommodation price_level and travel fare data that's already flowing through but not displayed
