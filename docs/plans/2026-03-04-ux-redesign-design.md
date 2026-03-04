# UX Redesign — Guided Wizard Flow

## Context

Regular Everyday Traveller AI is preparing for public launch. The current UX has functional foundations (streaming, maps, chat editing, budget tracking, OAuth, sharing) but suffers from discoverability issues, information overload, and lack of guided flow. Users don't know what to do next, can't see costs until late in the flow, and find features like chat editing and tips hidden behind unintuitive interactions.

This redesign transforms the app from a phase-based single-page form into a **guided wizard flow** with a dashboard preview, timeline day plans, and improved trust signals throughout.

## Target Audience

Public users — first-time visitors, personal travel planners, people sharing trips with friends/family. The design must be intuitive without any onboarding docs.

---

## Design

### 1. Input — Multi-Step Wizard

Replace the single form with a **5-step wizard** and progress stepper:

```
[1. Where] → [2. When] → [3. Style] → [4. Budget] → [5. Review]
```

**Step 1 — Where:**
- Large centered destination input with autocomplete (Google Places)
- Optional origin field: "Where are you starting from?"
- **Quick Start Templates** below: 6-8 clickable cards ("Weekend in Paris", "10 Days in Japan", "SE Asia Backpacking", "Italian Food Trail"). Clicking pre-fills all steps.

**Step 2 — When:**
- Calendar date picker for start date
- Duration slider (1-30 days) with smart suggestion: "Recommended: 5-7 days for Japan"
- Visual preview: "March 1 → March 7 (7 days)"

**Step 3 — Style:**
- Interests as toggleable cards with icons (larger, more tappable than current chips)
- Pace as visual cards with illustrations: Relaxed (hammock, "3-5/day"), Moderate (walking, "5-7/day"), Packed (running, "7-10/day")
- Must-include / Avoid as tag inputs with placeholder examples

**Step 4 — Budget:**
- Budget tier as visual cards: Budget (backpack), Moderate (suitcase), Luxury (diamond)
- Optional total budget USD with live per-day breakdown: "$3000 ÷ 7 = ~$429/day"
- Contextual hint: "Moderate budget in Japan is typically $150-250/day"

**Step 5 — Review:**
- Summary card showing all selections at a glance
- "Plan My Trip" primary CTA
- Click any section to edit it

---

### 2. Planning Phase — Rich Progress Dashboard

Replace the simple progress card with a trust-building dashboard:

- **Progress stepper** showing pipeline stages: Scouting → Enriching → Reviewing → Improving → Done
- **Live status** with descriptive text: "Finding the best cities for your 7-day Japan trip based on your food and culture interests..."
- **Animated icons** per stage (map for scouting, magnifying glass for enriching, checkmark for reviewing)
- **Time info:** elapsed timer + estimated remaining ("Usually takes 2-4 minutes")
- **Activity log:** scrollable list of completed steps with timestamps ("Identified 4 cities", "Verified transport routes", "Quality score: 82/100")
- **Stall timeout** raised to 180 seconds with friendlier message
- Clear "Cancel and start over" button

---

### 3. Journey Preview — Dashboard Layout

Structured dashboard showing everything at a glance:

**Header section:**
- Theme title, summary, review score badge
- Stats row: cities · days · km · estimated total cost

**Route visualization:**
- Horizontal city cards with transport icons/durations between them
- Each compact city card shows:
  - City name + country, days, estimated cost
  - Top 3 highlights (bullet list)
  - Accommodation name + nightly cost
  - "See all details" expand toggle
- Expanded card: full highlights with descriptions/categories/durations, why-visit, accommodation photo/rating/address, transport details with fare/booking tips

**Map:** Auto-visible (no toggle needed)

**Actions:**
- Single primary CTA: "Generate Day-by-Day Itinerary" (prominent, colored)
- Secondary row: Edit via Chat, Share, Export dropdown (PDF + Calendar), New Trip

---

### 4. Day Plans — Timeline View

Replace stacked cards with vertical timeline + sticky day navigation:

**Sticky day navigation bar (top):**
- Horizontal pill buttons: Day 1, Day 2, ... Day N
- Each shows city name and daily cost
- Active day highlighted, click to jump

**Timeline for active day:**
- Day header: number, theme, date, city, activity count, weather, daily cost
- Vertical timeline with time markers on left, activity details on right:
  - Time, activity name, duration
  - Category icon, cost, rating
  - Transport to next (mode icon + duration) shown inline between activities
  - Weather warnings shown inline next to affected outdoor activities
  - Expandable for photos, address, website, notes
- Tips auto-loaded and shown as subtle callouts (no hidden lightbulb click)

**Below timeline:**
- Map auto-visible showing day's route
- Budget running total: "$300 of $2,800 spent so far"
- Action bar: Edit via Chat, Get Tips, Export dropdown, Back to Overview

---

### 5. Chat Editing — Improved

Chat sidebar remains but gets these additions:

- **Suggestion chips** on open: 3-4 tappable contextual suggestions
  - Journey: "Add a beach day", "Swap Paris and Lyon", "Make it more budget-friendly"
  - Day plans: "Replace dinner restaurant", "Add a museum", "Make today more relaxed"
- **Change highlighting:** modified elements flash green border briefly after changes applied
- **Scope explanation** in intro message: what chat can and can't do
- **Day plans cleared warning:** explicit message when journey edits invalidate day plans

---

### 6. Cross-Cutting

- **Header:** shows trip name during preview/day-plans ("Regular Everyday Traveller · 10 Days in Japan"), "Saved" indicator
- **Landing page:** quick-start templates above form, tagline "AI plans your perfect multi-city trip in minutes"
- **Shared trip view:** same dashboard + timeline layout, with "Plan your own trip" CTA
- **Mobile:** wizard steps as swipeable screens, day nav as horizontal scroll pills, compact timeline, expandable map section

---

## Files Affected

### New Components
- `WizardStepper.tsx` — step indicator with progress
- `WizardStep*.tsx` — individual step screens (Where, When, Style, Budget, Review)
- `TemplateGallery.tsx` — quick-start trip templates
- `PlanningDashboard.tsx` — rich progress view replacing PlanProgress
- `JourneyDashboard.tsx` — dashboard preview replacing JourneyPreview
- `CompactCityCard.tsx` — compact expandable city card for dashboard
- `DayTimeline.tsx` — timeline view for a single day
- `DayNav.tsx` — sticky horizontal day navigation
- `SuggestionChips.tsx` — chat suggestion chips

### Modified Components
- `App.tsx` — phase routing to use new components
- `ChatPanel.tsx` — suggestion chips, change highlighting
- `Header.tsx` — trip name display
- `InputForm.tsx` — extracted into wizard steps (will be replaced)
- `BudgetSummary.tsx` — running total display
- `SharedTrip.tsx` — use new dashboard/timeline components

### Stores
- `uiStore.ts` — wizard step tracking, day navigation state
- `tripStore.ts` — template presets, change highlighting state

### Backend (minimal)
- Add a `/api/templates` endpoint or hardcode 6-8 template presets in frontend
- No other backend changes needed — all existing APIs remain the same

---

## Verification

1. Walk through full user flow: template select → wizard → planning → preview → day plans → chat edit → export
2. Test on mobile viewport (375px width)
3. Test with 1-day trip (edge case) and 21-day trip (many days in nav)
4. Test chat editing in both journey and day_plans contexts
5. Test shared trip view uses new components
6. `npx tsc --noEmit` — no TypeScript errors
7. `npm run build` — production build succeeds
8. Backend tests still pass: `pytest -x -q`
