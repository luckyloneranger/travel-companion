# Phase 2: Budget & Cost Tracking — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-activity cost estimation, daily cost aggregation, budget tracking, and cost display across the app.

**Architecture:** LLM estimates costs during day planning via updated prompts. Cost data flows through AIPlan → Scheduler → Activity → DayPlan. Frontend shows price tiers, daily costs, and a budget summary. User can optionally set a budget tier and total USD budget.

**Tech Stack:** Existing stack (FastAPI, Pydantic, React, Zustand). No new dependencies.

---

### Task 1: Extend Backend Models with Cost Fields

**Files:**
- Modify: `backend/app/models/trip.py`
- Modify: `backend/app/models/day_plan.py`
- Modify: `backend/app/models/internal.py`
- Create: `backend/tests/test_budget.py`

**What to do:**

1. Add to `TripRequest` in `trip.py`:
```python
from .common import Budget
budget: Budget = Budget.MODERATE
budget_usd: float | None = None
home_currency: str = "USD"
```

2. Add to `Activity` in `day_plan.py`:
```python
estimated_cost_local: str | None = None
estimated_cost_usd: float | None = None
price_tier: str | None = None  # "free", "budget", "moderate", "expensive", "luxury"
```

3. Add to `DayPlan` in `day_plan.py`:
```python
daily_cost_usd: float | None = None
```

4. Add new model `CostBreakdown` in `day_plan.py`:
```python
class CostBreakdown(BaseModel):
    accommodation_usd: float = 0
    transport_usd: float = 0
    activities_usd: float = 0
    dining_usd: float = 0
    total_usd: float = 0
    budget_usd: float | None = None
    budget_remaining_usd: float | None = None
```

5. Add `cost_breakdown: CostBreakdown | None = None` to `TripResponse` in `trip.py`.

6. Add `cost_estimates: dict[str, float] = {}` to `AIPlan` in `internal.py`.

7. Write test in `test_budget.py` validating the models.

**Commit:** `feat: add cost and budget fields to backend models`

---

### Task 2: Update Day Planner Prompts for Cost Estimation

**Files:**
- Modify: `backend/app/prompts/day_plan/planning_user.md`
- Modify: `backend/app/agents/day_planner.py`

**What to do:**

1. Read the existing planning_user.md prompt template. Add a budget section:
```markdown
## BUDGET CONTEXT
Budget tier: {budget_tier}
{daily_budget_line}

For each place you select, estimate the cost in local currency AND USD.
Return a "cost_estimates" dict mapping place_id to USD cost:
- Free attractions: 0
- Budget meals: $5-15
- Moderate meals: $15-40
- Museum/attraction entry: varies by destination
- Luxury dining: $40+

Include "cost_estimates" in your JSON output alongside "selected_place_ids", "day_groups", and "durations".
```

2. Update `plan_days()` method signature to accept `budget: str = "moderate"` and `daily_budget_usd: float | None = None`.

3. Update `_build_user_prompt()` to format the budget variables into the prompt template.

4. Update `_parse_plan()` to extract `cost_estimates` from LLM response and populate `AIPlan.cost_estimates`.

**Commit:** `feat: update day planner prompts and agent for cost estimation`

---

### Task 3: Wire Cost Data Through Scheduler

**Files:**
- Modify: `backend/app/algorithms/scheduler.py`

**What to do:**

1. Update `build_schedule()` signature to accept `cost_estimates: dict[str, float] | None = None`.

2. When building each `Activity`, set cost fields:
```python
cost = cost_estimates.get(place.place_id) if cost_estimates else None
price_tier = _price_level_to_tier(place.price_level)

# In Activity creation:
estimated_cost_usd=cost,
price_tier=price_tier,
```

3. Add helper function:
```python
def _price_level_to_tier(price_level: int | None) -> str | None:
    if price_level is None:
        return None
    tiers = ["free", "budget", "moderate", "expensive", "luxury"]
    return tiers[min(price_level, 4)]
```

**Commit:** `feat: wire cost estimates through scheduler to activities`

---

### Task 4: Aggregate Costs in Day Plan Orchestrator

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py`

**What to do:**

1. Pass `budget` and `daily_budget_usd` from `request` to `self.day_planner.plan_days()`.

2. Pass `cost_estimates=ai_plan.cost_estimates` to `self.scheduler.build_schedule()`.

3. After building activities for each day, calculate `daily_cost_usd`:
```python
daily_cost = sum(
    a.estimated_cost_usd for a in activities
    if a.estimated_cost_usd is not None
)
```

4. Set `daily_cost_usd=daily_cost if daily_cost > 0 else None` on the `DayPlan`.

**Commit:** `feat: aggregate daily costs in day plan orchestrator`

---

### Task 5: Compute Trip-Level Cost Breakdown

**Files:**
- Modify: `backend/app/db/repository.py`
- Modify: `backend/app/routers/trips.py`

**What to do:**

1. In the repository's `get_trip()` method (or in the router), after loading day_plans, compute the `CostBreakdown`:
```python
def _compute_cost_breakdown(trip: TripResponse) -> CostBreakdown | None:
    if not trip.day_plans:
        return None
    total = 0.0
    dining = 0.0
    activities = 0.0
    for dp in trip.day_plans:
        for a in dp.activities:
            if a.estimated_cost_usd:
                total += a.estimated_cost_usd
                cat = (a.place.category or "").lower()
                if cat in ("restaurant", "cafe", "bakery", "food", "dining"):
                    dining += a.estimated_cost_usd
                else:
                    activities += a.estimated_cost_usd
    # Transport from journey legs
    transport = 0.0  # Could parse fare strings in future
    # Accommodation estimate
    accommodation = 0.0  # Could estimate from price_level in future

    return CostBreakdown(
        accommodation_usd=accommodation,
        transport_usd=transport,
        activities_usd=activities,
        dining_usd=dining,
        total_usd=total,
        budget_usd=trip.request.budget_usd if hasattr(trip.request, 'budget_usd') else None,
        budget_remaining_usd=(trip.request.budget_usd - total) if trip.request.budget_usd else None,
    )
```

2. Attach `cost_breakdown` to `TripResponse` before returning.

**Commit:** `feat: compute trip-level cost breakdown`

---

### Task 6: Update Frontend Types

**Files:**
- Modify: `frontend/src/types/index.ts`

**What to do:**

1. Add to `Activity` interface:
```typescript
estimated_cost_local: string | null;
estimated_cost_usd: number | null;
price_tier: string | null;
```

2. Add to `DayPlan` interface:
```typescript
daily_cost_usd: number | null;
```

3. Add to `TripRequest` interface:
```typescript
budget?: Budget;
budget_usd?: number | null;
home_currency?: string;
```

4. Add `CostBreakdown` interface:
```typescript
export interface CostBreakdown {
  accommodation_usd: number;
  transport_usd: number;
  activities_usd: number;
  dining_usd: number;
  total_usd: number;
  budget_usd: number | null;
  budget_remaining_usd: number | null;
}
```

5. Add to `TripResponse`:
```typescript
cost_breakdown: CostBreakdown | null;
```

**Commit:** `feat: add cost types to frontend`

---

### Task 7: Add Budget Input to InputForm

**Files:**
- Modify: `frontend/src/components/trip/InputForm.tsx`

**What to do:**

1. Add state: `budget` (Budget type, default 'moderate') and `budgetUsd` (string, default '').

2. Add a Budget Tier selector (3-button toggle like the old travel mode selector) with icons: Wallet (budget), CreditCard (moderate), Gem (luxury).

3. Add an optional "Total Budget (USD)" number input.

4. Put both in the collapsible "Advanced options" section alongside must_include/avoid.

5. Wire into `handleSubmit` to include `budget` and `budget_usd` in the TripRequest.

**Commit:** `feat: add budget tier and total budget to InputForm`

---

### Task 8: Display Costs on ActivityCard

**Files:**
- Modify: `frontend/src/components/trip/ActivityCard.tsx`

**What to do:**

1. Import `DollarSign` from lucide-react.

2. After the place name/rating section, add a price tier badge:
```tsx
{activity.price_tier && (
  <Badge variant="outline" className="text-xs capitalize">
    {'$'.repeat(
      activity.price_tier === 'free' ? 0 :
      activity.price_tier === 'budget' ? 1 :
      activity.price_tier === 'moderate' ? 2 :
      activity.price_tier === 'expensive' ? 3 : 4
    ) || 'Free'}
  </Badge>
)}
```

3. After notes, show estimated cost if available:
```tsx
{activity.estimated_cost_usd != null && (
  <div className="flex items-center gap-1 text-xs text-text-muted mt-1">
    <DollarSign className="h-3 w-3" />
    ~${activity.estimated_cost_usd.toFixed(0)}
    {activity.estimated_cost_local && (
      <span className="text-text-muted">({activity.estimated_cost_local})</span>
    )}
  </div>
)}
```

**Commit:** `feat: display cost estimates on ActivityCard`

---

### Task 9: Display Daily Cost on DayCard

**Files:**
- Modify: `frontend/src/components/trip/DayCard.tsx`

**What to do:**

1. Import `DollarSign` from lucide-react.

2. Add a daily cost badge in the header (after weather badge):
```tsx
{dayPlan.daily_cost_usd != null && dayPlan.daily_cost_usd > 0 && (
  <Badge variant="outline" className="text-xs flex items-center gap-1">
    <DollarSign className="h-3 w-3" />
    ~${dayPlan.daily_cost_usd.toFixed(0)}/day
  </Badge>
)}
```

**Commit:** `feat: display daily cost on DayCard`

---

### Task 10: Create BudgetSummary Component

**Files:**
- Create: `frontend/src/components/trip/BudgetSummary.tsx`
- Modify: `frontend/src/App.tsx`

**What to do:**

1. Create `BudgetSummary.tsx` — a card showing:
   - Total estimated trip cost
   - Cost breakdown by category (dining, activities, transport, accommodation) as horizontal bars
   - Budget vs actual comparison if user set a budget
   - Per-day average

2. Render it in `App.tsx` in the `day-plans` phase, above the day cards.

**Commit:** `feat: add BudgetSummary component`

---

### Task 11: Final Verification

**Steps:**
1. `cd backend && source venv/bin/activate && pytest --tb=short -q`
2. `cd frontend && npx tsc --noEmit`
3. `cd frontend && npm run build`
4. Manual test: plan a trip with budget set, verify costs flow through

**Commit:** `feat: Phase 2 complete — budget and cost tracking`
