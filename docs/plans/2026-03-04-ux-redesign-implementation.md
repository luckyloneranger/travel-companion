# UX Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Travel Companion from a single-page phase-based app into a guided wizard flow with dashboard preview, timeline day plans, and improved chat editing for public launch.

**Architecture:** Replace InputForm with a multi-step wizard (5 steps), replace PlanProgress with a rich dashboard, restructure JourneyPreview as a dashboard layout with compact expandable city cards, and replace the day-plans card list with a timeline view + sticky day navigation. All existing backend APIs remain unchanged — this is a frontend-only redesign.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, shadcn/ui, Zustand, Lucide icons. Existing components in `frontend/src/components/ui/` (badge, button, card, collapsible, input, select, separator, sheet).

---

## Phase 1: Wizard Input (Steps 1-5)

### Task 1: Add wizard step state to uiStore

**Files:**
- Modify: `frontend/src/stores/uiStore.ts`

**Step 1:** Add wizard state fields and actions to the UIState interface and store:

```typescript
// Add to UIState interface (after existing fields):
wizardStep: number;  // 1-5
setWizardStep: (step: number) => void;

// Add to store initial state:
wizardStep: 1,
setWizardStep: (step) => set({ wizardStep: step }),

// Update resetUI to also reset wizard:
wizardStep: 1,
```

**Step 2:** Verify TypeScript compiles: `cd frontend && npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: add wizard step state to uiStore"`

---

### Task 2: Create WizardStepper component

**Files:**
- Create: `frontend/src/components/trip/WizardStepper.tsx`

**Step 1:** Create the stepper component showing 5 steps with active/completed/pending states:

```typescript
// Steps: 1=Where, 2=When, 3=Style, 4=Budget, 5=Review
// Props: currentStep (number), onStepClick (step: number) => void
// Visual: horizontal bar with numbered circles, labels below, connecting lines
// Active step = primary color filled circle
// Completed steps = checkmark in green circle, clickable
// Pending steps = gray outline circle, not clickable
```

The component renders a horizontal flex row with 5 step indicators connected by lines. Each indicator is a circle with the step number (or checkmark if completed). Below each circle is the step label. Steps are clickable only if completed (allows going back).

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: add WizardStepper component"`

---

### Task 3: Create TemplateGallery component

**Files:**
- Create: `frontend/src/components/trip/TemplateGallery.tsx`

**Step 1:** Create a gallery of 6-8 quick-start trip template cards:

```typescript
// Template data: array of { title, destination, origin, totalDays, interests, pace, budget, image (emoji/icon) }
// Examples:
//   "Weekend in Paris" - 3 days, food+culture+art, moderate
//   "10 Days in Japan" - 10 days, food+culture+nature, moderate
//   "SE Asia Backpacking" - 14 days, adventure+food+nature, budget
//   "Italian Food Trail" - 7 days, food+culture+history, moderate
//   "Greek Island Hopping" - 10 days, beach+nature+food, moderate
//   "NYC City Break" - 4 days, food+culture+shopping+nightlife, moderate
//
// Props: onSelectTemplate(template: Partial<TripRequest>) => void
// Visual: grid of cards (2 cols on mobile, 3 on desktop), each with emoji/icon, title, subtitle with days + key interests
// onClick prefills the wizard form and jumps to step 5 (Review)
```

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: add TemplateGallery component"`

---

### Task 4: Create wizard step components (Where, When, Style, Budget, Review)

**Files:**
- Create: `frontend/src/components/trip/wizard/WizardStepWhere.tsx`
- Create: `frontend/src/components/trip/wizard/WizardStepWhen.tsx`
- Create: `frontend/src/components/trip/wizard/WizardStepStyle.tsx`
- Create: `frontend/src/components/trip/wizard/WizardStepBudget.tsx`
- Create: `frontend/src/components/trip/wizard/WizardStepReview.tsx`
- Create: `frontend/src/components/trip/wizard/index.ts` (barrel export)

**Step 1:** Create all 5 step components. Each receives form state + setters as props, plus `onNext`/`onBack` callbacks:

**WizardStepWhere:** Large centered destination input, optional origin input, TemplateGallery below. "Next" button enabled when destination is set.

**WizardStepWhen:** Date picker for start date (defaults tomorrow), duration slider 1-30 with number display. Smart suggestion text based on destination.

**WizardStepStyle:** Interest cards as toggleable grid (larger cards with icons, not chips). Pace selection as 3 visual cards (Relaxed/Moderate/Packed with icons and descriptions). Must-include and Avoid tag inputs.

**WizardStepBudget:** Budget tier as 3 visual cards (Budget/Moderate/Luxury with icons). Optional total budget USD input. Live per-day calculation shown below.

**WizardStepReview:** Summary card showing all selections grouped by step. Each section clickable to jump back to that step. Primary CTA: "Plan My Trip".

**Step 2:** Create barrel export in `wizard/index.ts`

**Step 3:** Verify: `npx tsc --noEmit`

**Step 4:** Commit: `git commit -m "feat: add wizard step components"`

---

### Task 5: Create WizardForm container and wire into App.tsx

**Files:**
- Create: `frontend/src/components/trip/WizardForm.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1:** Create WizardForm that manages form state and renders the current wizard step:

```typescript
// Internal state: all TripRequest fields (destination, origin, startDate, totalDays, interests, pace, mustInclude, avoid, budget, budgetUsd)
// Renders: WizardStepper at top, current step component below, saved trips section at bottom (from old InputForm)
// onSubmit: calls startPlanning(request) same as old InputForm
// Template handler: fills all fields and jumps to step 5
```

**Step 2:** Update App.tsx to render WizardForm instead of InputForm in the `phase === 'input'` block. Keep the InputForm import temporarily for reference during development.

**Step 3:** Verify: `npx tsc --noEmit` and `npm run build`

**Step 4:** Test manually: wizard steps 1-5 work, template select prefills, "Plan My Trip" triggers planning

**Step 5:** Commit: `git commit -m "feat: replace InputForm with WizardForm in App.tsx"`

---

### Task 6: Remove old InputForm

**Files:**
- Delete: `frontend/src/components/trip/InputForm.tsx`
- Modify: `frontend/src/App.tsx` — remove InputForm import

**Step 1:** Remove InputForm import from App.tsx, delete InputForm.tsx file

**Step 2:** Verify: `npx tsc --noEmit` and `npm run build`

**Step 3:** Commit: `git commit -m "refactor: remove old InputForm, replaced by WizardForm"`

---

## Phase 2: Planning Dashboard (Tasks 7-8)

### Task 7: Create PlanningDashboard component

**Files:**
- Create: `frontend/src/components/trip/PlanningDashboard.tsx`

**Step 1:** Create the rich planning dashboard with:

- Progress stepper showing pipeline stages (Scouting → Enriching → Reviewing → Improving → Done)
- Live status area with descriptive text based on current phase
- Elapsed time counter (useEffect with setInterval)
- Estimated remaining text: "Usually takes 2-4 minutes"
- Activity log: scrollable list of completed steps from progress events
- Cancel button

```typescript
// Props: onCancel() => void
// Reads from uiStore: progress (ProgressEvent)
// Internal state: activityLog (string[]), elapsedSeconds (number)
// On each progress event, append descriptive message to activityLog
// Timer increments elapsedSeconds every second while phase !== 'complete'
```

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: add PlanningDashboard component"`

---

### Task 8: Wire PlanningDashboard into App.tsx, remove PlanProgress

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/components/trip/PlanProgress.tsx`

**Step 1:** Replace PlanProgress with PlanningDashboard in App.tsx `phase === 'planning'` block

**Step 2:** Remove PlanProgress import, delete file

**Step 3:** Update stall timeout in `useStreamingPlan.ts` and `useStreamingDayPlans.ts` from 90s to 180s

**Step 4:** Verify: `npx tsc --noEmit` and `npm run build`

**Step 5:** Commit: `git commit -m "feat: replace PlanProgress with PlanningDashboard"`

---

## Phase 3: Journey Preview Dashboard (Tasks 9-11)

### Task 9: Create CompactCityCard component

**Files:**
- Create: `frontend/src/components/trip/CompactCityCard.tsx`

**Step 1:** Create a compact, expandable city card for the dashboard layout:

```typescript
// Props: city (CityStop), index (number), departureLeg? (TravelLeg), defaultExpanded? (boolean)
// Compact view: city name+country, days, estimated cost (accommodation * days), top 3 highlights (names only), accommodation name + nightly cost
// Expanded view: full highlights with descriptions/categories/durations, why_visit, accommodation photo/rating/address, transport leg details
// Toggle via Collapsible component
// Estimated city cost = (accommodation.estimated_nightly_usd || 0) * city.days
```

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: add CompactCityCard component"`

---

### Task 10: Create JourneyDashboard component

**Files:**
- Create: `frontend/src/components/trip/JourneyDashboard.tsx`

**Step 1:** Create the dashboard layout replacing JourneyPreview:

```typescript
// Props: onGenerateDayPlans(), onOpenChat(), onNewTrip()
// Layout:
//   Header: theme title, summary, score badge, stats row (cities, days, km, estimated total cost)
//   Route visualization: horizontal city cards with transport icons between
//   City cards section: CompactCityCard for each city with departureLeg
//   Map: auto-visible TripMap (no toggle)
//   Actions: primary CTA "Generate Day-by-Day Itinerary", secondary row (Edit via Chat, Share, Export dropdown, New Trip)
//   Share URL section (same as current JourneyPreview)
//
// Export dropdown: Button with ChevronDown, shows PDF + Calendar options on click (use simple state toggle, no need for a dropdown component)
//
// Estimated total cost = sum of (accommodation.estimated_nightly_usd * city.days) for all cities + sum of fare_usd for all travel legs
```

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: add JourneyDashboard component"`

---

### Task 11: Wire JourneyDashboard into App.tsx, remove old JourneyPreview

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/components/trip/JourneyPreview.tsx`

**Step 1:** Replace JourneyPreview with JourneyDashboard in App.tsx `phase === 'preview'` block

**Step 2:** Remove old import, delete JourneyPreview.tsx

**Step 3:** Verify: `npx tsc --noEmit` and `npm run build`

**Step 4:** Commit: `git commit -m "feat: replace JourneyPreview with JourneyDashboard"`

---

## Phase 4: Timeline Day Plans (Tasks 12-15)

### Task 12: Create DayNav component

**Files:**
- Create: `frontend/src/components/trip/DayNav.tsx`

**Step 1:** Create sticky horizontal day navigation bar:

```typescript
// Props: dayPlans (DayPlan[]), activeDay (number), onDayClick (dayNumber: number) => void
// Renders: horizontal scrollable row of pill buttons
// Each pill shows: "Day N", city name below, daily cost below
// Active pill = primary background + white text
// Inactive = surface background + text-secondary
// Sticky: `sticky top-0 z-10 bg-surface border-b`
```

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: add DayNav component"`

---

### Task 13: Create DayTimeline component

**Files:**
- Create: `frontend/src/components/trip/DayTimeline.tsx`

**Step 1:** Create timeline view for a single day's activities:

```typescript
// Props: dayPlan (DayPlan), tips (Record<string, string>)
// Layout: vertical timeline with left time markers, right activity details
// Each activity:
//   Time marker: "09:00" in primary color, vertical line connecting to next
//   Activity bubble: name, duration, category icon, cost, rating
//   Below: transport to next activity (mode icon + duration text)
//   Weather warning inline if present (orange text)
//   Expandable: click to show photos, address, website, notes, tips
// Tips shown as subtle amber callout under activity (auto-visible, no click needed)
// Skip zero-duration hotel markers in rendering
```

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: add DayTimeline component"`

---

### Task 14: Create DayPlansView container

**Files:**
- Create: `frontend/src/components/trip/DayPlansView.tsx`

**Step 1:** Create the day plans container with nav + timeline + map:

```typescript
// No props — reads from tripStore (dayPlans, costBreakdown, tips) and uiStore
// Internal state: activeDay (number, defaults to 1)
// Layout:
//   DayNav (sticky top, all days)
//   Active day header: day number, theme, date, city, weather, daily cost
//   DayTimeline for active day
//   DayMap for active day (auto-visible)
//   Budget footer: running total "Day 1-3: $300 of $2,800"
//   Action bar: Edit via Chat, Export dropdown, Back to Overview, New Trip
// Scroll to top when active day changes
```

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: add DayPlansView container"`

---

### Task 15: Wire DayPlansView into App.tsx, remove old day-plans code

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/components/trip/DayCard.tsx` (replaced by DayTimeline)
- Delete: `frontend/src/components/trip/ActivityCard.tsx` (replaced by DayTimeline)

**Step 1:** Replace the `phase === 'day-plans'` block in App.tsx with `<DayPlansView />`

**Step 2:** Remove old DayCard and ActivityCard imports and files

**Step 3:** Move BudgetSummary rendering into DayPlansView (remove from App.tsx)

**Step 4:** Verify: `npx tsc --noEmit` and `npm run build`

**Step 5:** Commit: `git commit -m "feat: replace day-plans cards with DayPlansView timeline"`

---

## Phase 5: Chat & Header Improvements (Tasks 16-18)

### Task 16: Add suggestion chips to ChatPanel

**Files:**
- Modify: `frontend/src/components/trip/ChatPanel.tsx`

**Step 1:** Add suggestion chips below the intro message:

```typescript
// After the intro message, render 3-4 tappable chip buttons
// Journey context suggestions: "Add a beach day", "Swap two cities", "Make it cheaper", "Add 2 more days"
// Day plan context suggestions: "Replace dinner", "Add a museum", "Make today relaxed", "Move activity to tomorrow"
// On click: fill the input field with the suggestion text and auto-send
// Visual: flex-wrap row of outline badges/buttons, text-xs
```

**Step 2:** Add change highlighting: after chat response with updated_journey or updated_day_plans, briefly set a `changesApplied` state that triggers a CSS animation on the main content

**Step 3:** Verify: `npx tsc --noEmit`

**Step 4:** Commit: `git commit -m "feat: add suggestion chips and change highlighting to ChatPanel"`

---

### Task 17: Update Header to show trip context

**Files:**
- Modify: `frontend/src/components/layout/Header.tsx`

**Step 1:** Show trip name in header during preview/day-plans phases:

```typescript
// Read from tripStore: journey
// Read from uiStore: phase
// If phase is 'preview' or 'day-plans' and journey exists:
//   Show " · {journey.theme}" truncated after the app title
//   On mobile: show only first 20 chars with ellipsis
// Add subtle "Saved" text or check icon next to title when tripId exists
```

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: show trip context in header"`

---

### Task 18: Update SharedTrip to use new components

**Files:**
- Modify: `frontend/src/pages/SharedTrip.tsx`

**Step 1:** Replace the current SharedTrip layout with the new components:

- Use CompactCityCard instead of CityCard
- Use DayTimeline instead of DayCard for day plans
- Use DayNav for day plan navigation
- Add "Plan your own trip" CTA at bottom

**Step 2:** Verify: `npx tsc --noEmit`

**Step 3:** Commit: `git commit -m "feat: update SharedTrip to use new dashboard/timeline components"`

---

## Phase 6: Cleanup & Polish (Tasks 19-20)

### Task 19: Remove unused components and clean imports

**Files:**
- Modify: `frontend/src/App.tsx` — verify clean imports
- Delete any orphaned component files (CityCard.tsx if fully replaced)
- Update `frontend/src/components/trip/index.ts` barrel exports if exists

**Step 1:** Search for unused imports across all files: `npx tsc --noEmit`

**Step 2:** Remove any dead code or unused component files

**Step 3:** Commit: `git commit -m "refactor: remove unused components after UX redesign"`

---

### Task 20: Update docs, verify, and final commit

**Files:**
- Modify: `CLAUDE.md` — update component descriptions
- Modify: `README.md` — update features list, project structure

**Step 1:** Update CLAUDE.md to reflect new component names (WizardForm, JourneyDashboard, DayPlansView, DayTimeline, etc.)

**Step 2:** Update README.md features list and project structure

**Step 3:** Full verification:
- `cd frontend && npx tsc --noEmit` — no errors
- `cd frontend && npm run build` — production build succeeds
- `cd backend && source venv/bin/activate && pytest -x -q` — 163 tests pass
- Manual test: full flow wizard → planning → preview → day plans → chat edit → export

**Step 4:** Commit: `git commit -m "docs: update CLAUDE.md and README for UX redesign"`

---

## Summary

| Phase | Tasks | Components | Effort |
|-------|-------|-----------|--------|
| 1. Wizard Input | 1-6 | WizardStepper, TemplateGallery, 5 step components, WizardForm | ~3 days |
| 2. Planning Dashboard | 7-8 | PlanningDashboard | ~0.5 day |
| 3. Journey Preview | 9-11 | CompactCityCard, JourneyDashboard | ~1.5 days |
| 4. Timeline Day Plans | 12-15 | DayNav, DayTimeline, DayPlansView | ~2 days |
| 5. Chat & Header | 16-18 | ChatPanel updates, Header updates, SharedTrip | ~1 day |
| 6. Cleanup & Polish | 19-20 | Remove old files, update docs | ~0.5 day |
| **Total** | **20 tasks** | **~10 new components** | **~8-9 days** |
