# Excursion Day Rendering Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show full activity timelines for excursion days instead of hiding them behind a stub card.

**Architecture:** Remove the `is_excursion` early-return in DayTimeline.tsx. Add an excursion banner above the normal timeline. Add excursion indicators to day navigator tabs. Sync `destination_name` to frontend types.

**Tech Stack:** React, TypeScript, Tailwind CSS, lucide-react icons

---

### Task 1: Add `destination_name` to frontend TypeScript types

**Files:**
- Modify: `frontend/src/types/index.ts:45-61`

**Step 1: Add field to ExperienceTheme and CityHighlight**

In `ExperienceTheme` (line 54), add `destination_name`:
```typescript
export interface ExperienceTheme {
  theme: string;
  category: string;
  destination_name?: string;  // ADD THIS
  excursion_type?: string;
  excursion_days?: number;
  distance_from_city_km?: number;
  why?: string;
}
```

In `CityHighlight` (line 45), add `destination_name`:
```typescript
export interface CityHighlight {
  name: string;
  description: string;
  category: string;
  destination_name?: string;  // ADD THIS
  suggested_duration_hours: number | null;
  excursion_type: string | null;
  excursion_days: number | null;
}
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS (no type errors)

**Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "types: add destination_name to ExperienceTheme and CityHighlight"
```

---

### Task 2: Replace excursion stub card with banner + normal timeline

**Files:**
- Modify: `frontend/src/components/trip/DayTimeline.tsx:1-6,428-454`

**Step 1: Add MapPinned to lucide imports**

At line 1-6, add `MapPinned` to the lucide-react import:
```typescript
import {
  Clock, Star, MapPin, MapPinned, Navigation, ExternalLink, DollarSign,
  ...
} from 'lucide-react';
```

**Step 2: Replace the excursion early-return block**

Replace lines 428-454 (the `if (dayPlan.is_excursion) { return ... }` block) with an excursion banner that does NOT return early:

```typescript
  // Excursion banner — rendered above normal timeline, no early return
  const excursionBanner = dayPlan.is_excursion ? (
    <div className="rounded-lg border border-accent-300 dark:border-accent-700 bg-accent-50 dark:bg-accent-950/30 px-3 py-2 mb-3 flex items-center gap-2">
      <MapPinned className="h-4 w-4 text-accent-500 shrink-0" />
      <span className="text-sm font-medium text-accent-700 dark:text-accent-300">
        {dayPlan.excursion_name || dayPlan.theme}
      </span>
      <span className="text-xs text-text-muted">
        Excursion from {dayPlan.city_name}
      </span>
    </div>
  ) : null;
```

**Step 3: Render the banner before the activity list**

Find where the activity list is rendered (after the empty check at line 456). Insert `{excursionBanner}` at the top of the returned JSX, before the activity list. The exact insertion point is just before `renderActivityList()` is called in the return statement.

Read the full return block to find the right place — it should be the first child inside the outer wrapper div.

**Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/components/trip/DayTimeline.tsx
git commit -m "feat: render full timeline for excursion days with excursion banner"
```

---

### Task 3: Add excursion indicator to day navigator tabs

**Files:**
- Modify: `frontend/src/components/trip/JourneyDashboard.tsx:446-457`

**Step 1: Add accent ring styling for excursion days**

At line 453, the day button has a className. Add conditional styling when the day is an excursion:

Replace the button's className (line 453) to conditionally apply accent styling:

```typescript
{cityDays.map(dp => (
  <button
    key={dp.day_number}
    type="button"
    onClick={() => {
      document.getElementById(`day-${dp.day_number}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }}
    className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
      dp.is_excursion
        ? 'bg-accent-100 dark:bg-accent-900/40 text-accent-700 dark:text-accent-300 ring-1 ring-accent-400 hover:bg-accent-200 dark:hover:bg-accent-800/50'
        : 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/50'
    }`}
    title={`Day ${dp.day_number}: ${dp.theme}${dp.is_excursion ? ' (Excursion)' : ''}`}
  >
    {dp.day_number}
  </button>
))}
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/src/components/trip/JourneyDashboard.tsx
git commit -m "feat: add accent indicator for excursion days in day navigator"
```

---

### Task 4: Verify end-to-end and final commit

**Step 1: Run frontend build**

Run: `cd frontend && npm run build`
Expected: PASS, no TypeScript errors

**Step 2: Visual verification**

Open the app at localhost:5173, generate day plans for a trip with excursions (e.g., Japan 10d). Verify:
- Excursion days show full activity timeline with photos, routes, weather
- Excursion banner appears above timeline with "Excursion from {city}"
- Day navigator tabs show accent-colored circles for excursion days
- Stub excursions (if any) show as single-activity timeline with banner
- Regular city days are unaffected

**Step 3: Push**

```bash
git push origin main
```
