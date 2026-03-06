# UX Improvements Design — 25 Features

## Context
Comprehensive UX improvements for the journey and day plan experience. All 25 features span frontend components, stores, API layer, and some backend endpoints.

## Feature Scoping

### Group A: Planning Experience (Features 1-3)

**Feature 1: Smarter Wizard Defaults**
- Browser geolocation for origin auto-fill (Geolocation API)
- LLM-powered trip duration suggestion: new backend endpoint `GET /api/trips/suggest-duration?destination=X` → returns `{ suggested_days: [min, max], reason: string }`
- Seasonal suitability badge next to date picker: new backend endpoint `GET /api/trips/seasonal-info?destination=X&month=Y` → returns `{ rating: string, description: string }`
- Files: `WizardStepWhere.tsx`, `WizardStepWhen.tsx`, `api.ts`, backend `routers/trips.py`, new service method

**Feature 2: Planning Progress That Educates**
- "Did you know?" fun facts during planning: LLM generates 3-5 facts per destination during scouting, included in progress events
- Live map during scouting: show cities appearing on map as they're selected
- ETA countdown based on average planning time
- Files: `PlanningDashboard.tsx`, backend `orchestrators/journey.py` (add facts to progress events)

**Feature 3: Comparison Mode**
- "Generate Alternative" button on JourneyDashboard → runs pipeline with higher temperature
- Side-by-side comparison view component
- Mix-and-match: swap individual cities between plans
- Files: `JourneyDashboard.tsx`, new `ComparisonView.tsx`, `api.ts`, backend `routers/trips.py`

### Group B: Journey Dashboard (Features 4-7)

**Feature 4: Visual Route Timeline**
- Replace horizontal route badges with vertical interactive timeline
- City photos, transport icons, day counts, all in a visual card flow
- Drag-to-reorder (install `@dnd-kit/core` + `@dnd-kit/sortable`)
- Files: new `RouteTimeline.tsx`, `JourneyDashboard.tsx` overview tab

**Feature 5: Accommodation Comparison**
- Show 2-3 alternative hotels per city at different price points
- New backend: `GET /api/places/alternatives?place_id=X&location=lat,lng&type=lodging`
- "Swap hotel" button per alternative
- Files: `CompactCityCard.tsx`, new `AccommodationAlternatives.tsx`, `api.ts`, backend `routers/places.py`

**Feature 6: Cost Confidence Indicators**
- Tag each cost with source: "Google data" (green) vs "AI estimate" (amber)
- Currency toggle: show in home_currency alongside USD
- Files: `BudgetSummary.tsx`, `DayTimeline.tsx`, `CompactCityCard.tsx`

**Feature 7: Shareable Trip Cards**
- Generate OG image with route map + theme + stats for social sharing
- Backend: `GET /api/trips/{id}/og-image` → returns PNG
- Use `<canvas>` or server-side rendering with the map
- Files: backend `routers/export.py`, `JourneyDashboard.tsx` share action

### Group C: Day Plans (Features 8-12)

**Feature 8: Weather-Integrated Daily View**
- Weather summary card at top of each day (temp range, icon, sunrise/sunset)
- Subtle background color tinting based on weather
- Indoor alternative suggestions when weather is bad
- Files: `DayTimeline.tsx`, `CompactCityCard.tsx`, new `WeatherCard.tsx`

**Feature 9: Interactive Day Timeline**
- Install `@dnd-kit` for drag-to-reorder activities within a day
- Quick action buttons: swap, remove, extend/shorten, "find similar"
- Mini-map alongside timeline
- Files: `DayTimeline.tsx` (major rewrite), new dependencies

**Feature 10: Time Gap Detection**
- Detect gaps > 1 hour between activities
- Show "Free time" card with duration and nearby suggestions
- Files: `DayTimeline.tsx`

**Feature 11: Activity Cards 2.0**
- Photo hero at top of each activity card
- Google review snippet
- "Why this place?" tooltip
- "Get Directions" button → opens Google Maps
- Files: `DayTimeline.tsx` (TimelineActivity subcomponent)

**Feature 12: Daily Cost Tracker**
- Running cost bar per day relative to daily budget
- Color gradient: green → amber → red
- Tap to expand per-activity breakdown
- Files: `CompactCityCard.tsx`, `DayTimeline.tsx`

### Group D: Navigation (Features 13-15)

**Feature 13: Sticky Day Navigator**
- Sticky header with day pills while scrolling Cities tab
- Highlights current day based on scroll position
- Tap to jump
- Files: `JourneyDashboard.tsx` cities tab, new `DayNavigator.tsx`

**Feature 14: Full-Screen Day View**
- Swipeable single-day view (weather → map → timeline → cost)
- Navigation arrows between days
- Files: new `FullDayView.tsx`, `JourneyDashboard.tsx`

**Feature 15: Quick Navigation Sidebar**
- Desktop: persistent left sidebar with city/day tree
- Mobile: floating action button with picker
- Files: new `NavigationSidebar.tsx`, `JourneyDashboard.tsx`

### Group E: Maps & Spatial (Features 16-18)

**Feature 16: Unified Map Mode**
- Single full-screen map with journey ↔ day toggle
- Day selector dropdown overlaid on map
- Cluster pins at journey level, expand on zoom
- Files: new `UnifiedMap.tsx` or refactor `TripMap.tsx`

**Feature 17: Walking Route Preview**
- Step count + calories estimate for walking segments
- Street View thumbnails along the route
- Files: `DayTimeline.tsx` route section, Google Street View Static API

**Feature 18: "What's Nearby" Overlay**
- Toggle layer on map showing restaurants, ATMs, transit, pharmacies
- Uses Google Places nearby search
- Files: `DayMap.tsx`, `TripMap.tsx`, new `NearbyOverlay.tsx`

### Group F: Chat & Editing (Features 19-21)

**Feature 19: Contextual Chat**
- Tap activity → pre-fill chat with "About [Activity] on Day X..."
- Inline chat bubble near the element being edited
- Files: `DayTimeline.tsx`, `ChatPanel.tsx`, `uiStore.ts`

**Feature 20: Visual Diff After Edits**
- Highlight changes: green (added), red (removed), amber (modified)
- "Undo last edit" button with 30s window
- Files: `ChatPanel.tsx`, `DayTimeline.tsx`, `tripStore.ts`

**Feature 21: Quick Edit Actions**
- Inline buttons per activity: swap, remove, ±duration, "find similar"
- Deterministic (no LLM needed): remove recalculates times, ±duration adjusts schedule
- Backend: new `PUT /api/trips/{id}/activities/{activity_id}` for quick edits
- Files: `DayTimeline.tsx`, `api.ts`, backend `routers/trips.py`

### Group G: Export & Sharing (Features 22-25)

**Feature 22: Google Calendar Integration**
- OAuth flow for Google Calendar scope
- Direct calendar creation with event details + locations
- Files: `JourneyDashboard.tsx` export section, new `CalendarIntegration.tsx`, backend OAuth scope

**Feature 23: PDF Trip Book**
- Redesigned PDF: cover page, daily spreads with photos, maps, checklists
- Backend: upgrade `services/export.py` WeasyPrint template
- Files: backend `services/export.py`, new HTML/CSS templates

**Feature 24: Offline Mode (PWA)**
- Service worker for caching trip data
- manifest.json for installability
- Cache map tiles for offline viewing
- Files: new `public/manifest.json`, new `src/sw.ts`, `vite.config.ts` PWA plugin

**Feature 25: Live Trip Mode**
- "Today" view highlighting current day's plan
- GPS-aware "Next up" with navigation
- "Running late" button → auto-adjust remaining activities
- Files: new `LiveTripView.tsx`, `api.ts`, backend endpoint for schedule adjustment

## Dependencies to Install

```bash
cd frontend
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities  # Drag-and-drop (Features 4, 9)
npm install vite-plugin-pwa workbox-precaching                    # PWA (Feature 24)
```

## Backend Endpoints to Add

| Endpoint | Feature | Purpose |
|----------|---------|---------|
| `GET /api/trips/suggest-duration` | 1 | LLM suggests trip length |
| `GET /api/trips/seasonal-info` | 1 | Seasonal suitability |
| `GET /api/places/alternatives` | 5 | Hotel alternatives |
| `GET /api/trips/{id}/og-image` | 7 | Social share image |
| `PUT /api/trips/{id}/activities/{aid}` | 21 | Quick activity edit |
| `PUT /api/trips/{id}/reorder` | 9 | Reorder activities |
| `POST /api/trips/{id}/adjust-schedule` | 25 | Running late adjustment |

## Implementation Order

### Phase 1: Foundation (no new deps)
Features 6, 8, 10, 11, 12, 13, 17, 19 — Pure frontend enhancements to existing components

### Phase 2: New components (no new deps)
Features 1, 2, 14, 15, 20 — New components + minor backend

### Phase 3: Backend + frontend
Features 3, 5, 7, 21, 23, 25 — New backend endpoints + frontend

### Phase 4: Drag-and-drop
Features 4, 9 — Install @dnd-kit, complex interaction patterns

### Phase 5: External integrations
Features 16, 18, 22, 24 — Maps refactor, OAuth, PWA
