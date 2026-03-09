# Excursion Day Rendering — Design

## Problem

Full-pipeline excursion days (with real activities, routes, weather, photos) are hidden behind a simplified stub card in the frontend. `DayTimeline.tsx:429` checks `if (dayPlan.is_excursion)` and renders ALL excursion days as a single card with just the excursion name and a generic "Full-day experience" label — regardless of whether the backend successfully planned 5-8 real activities with routes, photos, and weather.

Users can't see, interact with, or map excursion activities. No tips, no reorder, no quick-edit, no route visualization.

## Design

### Core Change
Remove the `is_excursion` early-return in `DayTimeline.tsx`. All excursion days render through the normal activity timeline — same as regular city days. An excursion banner is rendered above the timeline when `is_excursion` is true, showing destination context.

### Excursion Banner
When `dayPlan.is_excursion` is true, render a compact banner above the activity list:
- Accent-colored border/background (existing excursion palette)
- 🎯 icon + excursion name
- Text: "Excursion from {city_name}"
- No early return — timeline renders below

### Day Navigator Indicator
Day tabs in the sticky header get a small accent dot or ring when the day is an excursion, so users can identify excursion days without opening them.

### TypeScript Type Sync
Add `destination_name?: string` to `ExperienceTheme` interface in `frontend/src/types/index.ts`.

### Stub Excursions
Stub excursions (1 activity, geocoding/discovery failed) render as a single activity card in the normal timeline. The banner still shows. No special case needed — the timeline naturally renders 1 activity.

## Decision: No cross-city dedup needed
Excursion days are independent experiences. Same place in different excursions is fine.

## Files Changed
- `frontend/src/components/trip/DayTimeline.tsx` — Remove early-return, add excursion banner
- `frontend/src/components/trip/JourneyDashboard.tsx` — Add excursion indicator to day tabs
- `frontend/src/types/index.ts` — Add `destination_name` to ExperienceTheme
