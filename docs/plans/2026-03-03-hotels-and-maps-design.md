# Hotels & Map Visualization Design

## Overview

Add two features to the travel companion app:
1. **Hotel/accommodation suggestions** — one hotel per city, suggested by LLM and validated via Google Places API, integrated as bookend activities in day plans
2. **Map visualization** — journey-level and day-level interactive Google Maps with markers and route polylines

## Decisions

- One hotel per city stop (suggested by Scout LLM, enriched via Google Places)
- Day plans start and end at the hotel (bookend activities)
- Two map levels: journey map (cities + travel legs) and day map (activities + routes)
- Maps are inline toggleable sections (show/hide)
- Library: `@vis.gl/react-google-maps` (Google's official React wrapper)

## Feature 1: Hotel/Accommodation Integration

### Backend

**Model additions (`backend/app/generators/journey_plan/v6/models.py`)**

New `Accommodation` dataclass:
```python
@dataclass
class Accommodation:
    name: str
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None
    rating: Optional[float] = None
    photo_url: Optional[str] = None
    price_level: Optional[int] = None  # 0-4 from Google
```

Add `accommodation: Optional[Accommodation] = None` to `CityStop`.

**Scout prompt changes (`backend/app/prompts/journey/scout_system.md`, `scout_user.md`)**

- Add rule asking LLM to suggest one accommodation per city
- Add `accommodation` field to JSON output schema:
  ```json
  "accommodation": {
    "name": "Hotel Name",
    "why": "Brief reason"
  }
  ```

**Enricher changes (`backend/app/generators/journey_plan/v6/enricher.py`)**

After geocoding each city:
- Search Google Places API for the LLM-suggested hotel using `textSearch` with `includedType: "lodging"` scoped near city center
- If found: populate Accommodation with real coordinates, rating, photo, address
- If not found: fall back to top-rated lodging near city center

**Day plan generation (`backend/app/generators/journey_plan/v6/day_plan_generator.py` + `backend/app/generators/day_plan/fast/generator.py`)**

- Add optional `start_location: Optional[Location]` to `ItineraryRequest`
- `V6DayPlanGenerator` passes hotel location to `FastItineraryGenerator`
- `FastItineraryGenerator` uses hotel as start/end point:
  - Route optimization (TSP) starts/ends at hotel
  - Route computation: hotel → first activity, last activity → hotel
  - Bookend activities added with `category = "accommodation"`, zero duration

### Frontend

- Add `V6Accommodation` interface to `frontend/src/types/journey.ts`
- Add `accommodation?: V6Accommodation` to `V6CityStop`
- Accommodation bookend activities render with hotel icon and muted styling

## Feature 2: Map Visualization

### Library

`@vis.gl/react-google-maps` — declarative React components (`<Map>`, `<AdvancedMarker>`, `<Polyline>`). Remove existing `@googlemaps/js-api-loader` since the new library handles loading.

### Components

**`JourneyMap`** (journey preview phase)
- City markers with name labels
- Hotel markers (bed icon) at each city's accommodation
- Lines connecting cities (straight/dashed — no inter-city polyline data)
- Auto-fits bounds to all cities
- Inline toggle: "Show Map" / "Hide Map" in journey header

**`DayMap`** (per-day within DayCard)
- Numbered markers for each activity in visit order
- Hotel marker at start/end
- Polyline routes between consecutive activities (decoded from `route_to_next.polyline`)
- Color-coded markers by category
- Auto-fits bounds to day's activities
- Inline toggle in DayCard header

### Setup

- Wrap journey views with `<APIProvider apiKey={...}>` in `App.tsx`
- Maps render only when toggled open (lazy API usage)
- Lazy-load map components with `React.lazy()`

### Polyline Utility

`frontend/src/utils/polyline.ts` — `decodePolyline(encoded: string): {lat, lng}[]` (~30 lines, standard Google algorithm)

## Data Flow

```
SCOUT (LLM) — suggests hotel name per city
  ↓
ENRICH (Google APIs) — validates hotel, gets coordinates/rating/photo
  ↓
REVIEW (LLM) — unchanged
  ↓
JOURNEY PLAN → Frontend — CityStop has accommodation, JourneyMap renders
  ↓
DAY PLAN GENERATION — hotel location used as TSP start/end, bookend activities added
  ↓
DAY PLANS → Frontend — accommodation activities styled differently, DayMap renders
```

## Change Summary

| Layer | Changes | Untouched |
|-------|---------|-----------|
| Scout prompt | Add accommodation suggestion | City/highlight/transport logic |
| Enricher | Add hotel Places API lookup | Existing geocoding/directions |
| Reviewer | None | All 7 review metrics |
| V6 models | Add Accommodation dataclass to CityStop | JourneyPlan, TravelLeg, ReviewResult |
| Itinerary models | Add optional start_location to ItineraryRequest | All existing models |
| FastItineraryGenerator | Use start_location for TSP + bookend activities | Discovery, AI planning phases |
| RouteOptimizer | Accept optional start/end location | TSP algorithm itself |
| Frontend types | Add V6Accommodation, update V6CityStop | All existing types |
| Frontend components | Add JourneyMap, DayMap, update CityDaySection/DayCard | JourneyChat, InputForm |

## Chat Editing

- Journey chat: user can say "change hotel in Kyoto" — updates accommodation, re-enriches
- Day plan chat: no hotel changes (hotel is city-level, not day-level)

## Error Handling

- Hotel enrichment failure: city proceeds without accommodation (graceful degradation)
- Missing hotel location: day plans generate without bookend activities (current behavior)
- Missing coordinates: map toggle button hidden for that entity
