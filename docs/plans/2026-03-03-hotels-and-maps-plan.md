# Hotels & Map Visualization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add hotel accommodation suggestions (one per city, integrated as day plan bookends) and interactive Google Maps visualization (journey-level + day-level).

**Architecture:** Hotels flow through the existing Scout→Enrich pipeline: Scout LLM suggests a hotel name per city, Enricher validates via Google Places API. Day plan generation uses hotel as TSP start/end point and adds bookend activities. Maps use `@vis.gl/react-google-maps` with inline toggle rendering.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/Vite (frontend), `@vis.gl/react-google-maps`, Google Places API (textSearch with lodging type)

---

### Task 1: Add Accommodation model to V6 models

**Files:**
- Modify: `backend/app/generators/journey_plan/v6/models.py:57-70`

**Step 1: Add Accommodation dataclass**

Add after `TravelLeg` (line 55) and before `CityStop` (line 58):

```python
@dataclass
class Accommodation:
    """Recommended accommodation for a city stop."""
    name: str
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None
    rating: Optional[float] = None
    photo_url: Optional[str] = None
    price_level: Optional[int] = None  # 0-4 from Google
```

**Step 2: Add accommodation field to CityStop**

Add to `CityStop` dataclass after `place_id` field (line 70):

```python
    # Accommodation
    accommodation: Optional[Accommodation] = None
```

**Step 3: Run existing tests to verify no breakage**

Run: `cd backend && python -m pytest tests/test_itinerary.py tests/test_quality.py -v`
Expected: All PASS (new optional field doesn't break existing code)

**Step 4: Commit**

```bash
git add backend/app/generators/journey_plan/v6/models.py
git commit -m "feat: add Accommodation dataclass to V6 models"
```

---

### Task 2: Update Scout prompt to suggest hotels

**Files:**
- Modify: `backend/app/prompts/journey/scout_system.md`
- Modify: `backend/app/prompts/journey/scout_user.md`

**Step 1: Add accommodation rule to scout_system.md**

Add after rule 6 (HIGHLIGHTS, around line 50) as a new rule:

```markdown
### 7. ACCOMMODATION — One Per City
- Suggest ONE well-located hotel or guesthouse per city
- Choose accommodation that is:
  - Centrally located (near main attractions)
  - Well-rated and appropriate for the trip's style
  - A real, named property (not generic "a hotel")
- Consider the traveler's interests when suggesting (e.g., boutique hotel for culture lovers, resort for beach trips)
```

Renumber existing rules 7 (SAFETY) and 8 (SEASONAL) to 8 and 9.

**Step 2: Add accommodation to scout_user.md JSON schema**

Add `accommodation` field to the city object in the JSON Output Format section:

Inside the city object in the example output (around line 26), add after `"highlights"`:
```json
      "accommodation": {
        "name": "Hotel Granvia Kyoto",
        "why": "Connected to Kyoto Station, perfect base for day trips with excellent access to all rail lines"
      }
```

In the JSON Output Format template, add after `"highlights"` array:
```json
      "accommodation": {
        "name": "Specific Hotel or Guesthouse Name",
        "why": "Brief reason — location advantage, style match, or value"
      }
```

Add to STRICT RULES:
```
- Each city MUST have an accommodation suggestion with a specific, real hotel name
```

**Step 3: Commit**

```bash
git add backend/app/prompts/journey/scout_system.md backend/app/prompts/journey/scout_user.md
git commit -m "feat: add accommodation suggestion to Scout prompts"
```

---

### Task 3: Parse accommodation from Scout LLM response

**Files:**
- Modify: `backend/app/generators/journey_plan/v6/scout.py:109-128`

**Step 1: Update import to include Accommodation**

At line 17, add `Accommodation` to the import:
```python
from app.generators.journey_plan.v6.models import (
    JourneyPlan,
    CityStop,
    CityHighlight,
    TravelLeg,
    TransportMode,
    Accommodation,
)
```

**Step 2: Parse accommodation from LLM JSON**

In the city parsing loop (after line 127, before `cities.append`), add:

```python
            # Parse accommodation
            accommodation = None
            acc_data = c.get("accommodation")
            if acc_data and acc_data.get("name"):
                accommodation = Accommodation(name=acc_data["name"])
```

Then add `accommodation=accommodation` to the `CityStop(...)` constructor call.

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/ -v -k "not live"`
Expected: All PASS

**Step 4: Commit**

```bash
git add backend/app/generators/journey_plan/v6/scout.py
git commit -m "feat: parse accommodation from Scout LLM response"
```

---

### Task 4: Enrich accommodation via Google Places API

**Files:**
- Modify: `backend/app/generators/journey_plan/v6/enricher.py:36-77`
- Modify: `backend/app/services/external/google_places.py` (add `search_lodging` method)

**Step 1: Add search_lodging method to GooglePlacesService**

Add to `google_places.py` after `text_search` method (around line 155):

```python
    async def search_lodging(
        self,
        query: str,
        location: Location,
        radius_meters: int = 10000,
    ) -> Optional[PlaceCandidate]:
        """Search for a lodging establishment near a location.

        Args:
            query: Hotel name to search for
            location: Center point for search
            radius_meters: Search radius

        Returns:
            Best matching PlaceCandidate or None
        """
        field_mask = "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.rating,places.userRatingCount,places.priceLevel,places.photos,places.websiteUri"

        try:
            response = await self.client.post(
                f"{self.BASE_URL}/places:searchText",
                headers=self._get_headers(field_mask),
                timeout=_REQUEST_TIMEOUT,
                json={
                    "textQuery": query,
                    "includedType": "lodging",
                    "maxResultCount": 1,
                    "locationBias": {
                        "circle": {
                            "center": {
                                "latitude": location.lat,
                                "longitude": location.lng,
                            },
                            "radius": float(radius_meters),
                        }
                    },
                },
            )

            if response.status_code != 200:
                logger.warning(f"Lodging search failed: {response.text}")
                return None

            data = response.json()
            places = data.get("places", [])
            if not places:
                return None

            place = places[0]
            photo_ref = None
            if place.get("photos"):
                photo_ref = place["photos"][0].get("name")

            return PlaceCandidate(
                place_id=place["id"],
                name=place["displayName"]["text"],
                address=place.get("formattedAddress", ""),
                location=Location(
                    lat=place["location"]["latitude"],
                    lng=place["location"]["longitude"],
                ),
                types=place.get("types", []),
                rating=place.get("rating"),
                user_ratings_total=place.get("userRatingCount"),
                price_level=self._parse_price_level(place.get("priceLevel")),
                photo_reference=photo_ref,
                website=place.get("websiteUri"),
            )
        except Exception as e:
            logger.warning(f"Lodging search error for '{query}': {e}")
            return None
```

**Step 2: Add accommodation enrichment to Enricher**

Add import of `Accommodation` at top of enricher.py (line 19):
```python
from app.generators.journey_plan.v6.models import (
    JourneyPlan,
    EnrichedPlan,
    TravelLeg,
    TransportMode,
    Accommodation,
)
```

Add new method to Enricher class:

```python
    async def _enrich_accommodation(self, plan: JourneyPlan) -> None:
        """Enrich accommodation data for each city using Google Places."""
        tasks = []
        for city in plan.cities:
            if city.accommodation and city.accommodation.name:
                # Search for the LLM-suggested hotel near the city
                city_location = None
                if city.latitude and city.longitude:
                    from app.models import Location
                    city_location = Location(lat=city.latitude, lng=city.longitude)
                tasks.append(self._enrich_city_accommodation(city, city_location))
            else:
                tasks.append(asyncio.coroutine(lambda: None)())

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _enrich_city_accommodation(
        self, city, city_location
    ) -> None:
        """Enrich a single city's accommodation."""
        from app.models import Location
        try:
            query = f"{city.accommodation.name} hotel {city.name}"

            # Use city center if available, otherwise geocode
            if not city_location:
                geo = await self._geocode_city(city.name)
                if geo:
                    city_location = Location(lat=geo["lat"], lng=geo["lng"])

            if not city_location:
                logger.warning(f"No location for {city.name}, skipping accommodation enrichment")
                return

            result = await self.places_service.search_lodging(
                query=query,
                location=city_location,
            )

            if result:
                city.accommodation.address = result.address
                city.accommodation.latitude = result.location.lat
                city.accommodation.longitude = result.location.lng
                city.accommodation.place_id = result.place_id
                city.accommodation.rating = result.rating
                city.accommodation.price_level = (
                    result.price_level if result.price_level is not None else None
                )
                if result.photo_reference:
                    city.accommodation.photo_url = self.places_service.get_photo_url(
                        result.photo_reference
                    )
                logger.info(f"[Enricher] Enriched accommodation for {city.name}: {result.name}")
            else:
                logger.warning(f"[Enricher] No lodging found for {city.accommodation.name} in {city.name}")
        except Exception as e:
            logger.warning(f"[Enricher] Accommodation enrichment failed for {city.name}: {e}")
```

**Step 3: Call accommodation enrichment in enrich_plan**

In `enrich_plan` method, add after `_geocode_cities` call (after line 49) and before the travel legs loop:

```python
        # Phase 1.5: Enrich accommodations
        await self._enrich_accommodation(plan)
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/ -v -k "not live"`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/services/external/google_places.py backend/app/generators/journey_plan/v6/enricher.py
git commit -m "feat: enrich hotel accommodation via Google Places API"
```

---

### Task 5: Add start_location to ItineraryRequest and integrate hotel into day plan generation

**Files:**
- Modify: `backend/app/models/itinerary.py:54-64`
- Modify: `backend/app/generators/day_plan/fast/generator.py:78-307`
- Modify: `backend/app/generators/journey_plan/v6/day_plan_generator.py:119-126`

**Step 1: Add start_location to ItineraryRequest**

In `itinerary.py`, add after `mode` field (line 64):

```python
    start_location: Optional[Location] = None  # e.g., hotel location
```

**Step 2: Pass hotel location from V6DayPlanGenerator**

In `day_plan_generator.py`, when creating `city_request` (around line 119), add the hotel location:

```python
            # Get hotel location if available
            hotel_location = None
            if city.accommodation and city.accommodation.latitude and city.accommodation.longitude:
                from app.models import Location
                hotel_location = Location(
                    lat=city.accommodation.latitude,
                    lng=city.accommodation.longitude,
                )

            # Create request for this city
            city_request = ItineraryRequest(
                destination=f"{city.name}, {city.country}",
                start_date=city_start_date,
                end_date=city_end_date,
                interests=interests,
                pace=pace,
                travel_mode=travel_mode,
                start_location=hotel_location,
            )
```

Do the same in `generate_day_plans_stream` method (around line 234).

**Step 3: Use start_location in FastItineraryGenerator for bookend activities**

In `generator.py`, after route computation (line 243) and schedule building (line 249), add hotel bookend logic. After the `activities` list is built (around line 271) and before `days.append`:

```python
            # Add hotel bookend activities if start_location is provided
            if request.start_location and activities:
                hotel_place = Place(
                    place_id="hotel",
                    name="Hotel",
                    address="",
                    location=request.start_location,
                    category="accommodation",
                )

                # Route from hotel to first activity
                try:
                    hotel_to_first = await self.routes.compute_route(
                        request.start_location,
                        activities[0].place.location,
                        mode=request.travel_mode,
                    )
                except Exception:
                    hotel_to_first = None

                # Route from last activity to hotel
                try:
                    last_to_hotel = await self.routes.compute_route(
                        activities[-1].place.location,
                        request.start_location,
                        mode=request.travel_mode,
                    )
                except Exception:
                    last_to_hotel = None

                # Prepend departure activity
                first_start = activities[0].time_start
                depart_activity = Activity(
                    id=str(uuid4()),
                    time_start=first_start,
                    time_end=first_start,
                    duration_minutes=0,
                    place=hotel_place,
                    notes="Depart from hotel",
                    route_to_next=hotel_to_first,
                )
                activities.insert(0, depart_activity)

                # Append return activity
                last_end = activities[-1].time_end
                return_activity = Activity(
                    id=str(uuid4()),
                    time_start=last_end,
                    time_end=last_end,
                    duration_minutes=0,
                    place=hotel_place,
                    notes="Return to hotel",
                    route_to_next=None,
                )
                # Remove route_to_next from the previously-last activity
                activities[-1].route_to_next = last_to_hotel
                activities.append(return_activity)
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/ -v -k "not live"`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/models/itinerary.py backend/app/generators/day_plan/fast/generator.py backend/app/generators/journey_plan/v6/day_plan_generator.py
git commit -m "feat: integrate hotel as day plan start/end point with bookend activities"
```

---

### Task 6: Update frontend types for accommodation

**Files:**
- Modify: `frontend/src/types/journey.ts`

**Step 1: Add V6Accommodation interface**

Add after `V6CityHighlight` interface (around line 65):

```typescript
/** V6 Accommodation - hotel for a city stop */
export interface V6Accommodation {
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  place_id?: string;
  rating?: number;
  photo_url?: string;
  price_level?: number;
}
```

**Step 2: Add accommodation to V6CityStop**

Add field to `V6CityStop` after `longitude` (line 77):

```typescript
  accommodation?: V6Accommodation;
```

**Step 3: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/types/journey.ts
git commit -m "feat: add V6Accommodation type to frontend"
```

---

### Task 7: Display accommodation in CityCard and CityDaySection

**Files:**
- Modify: `frontend/src/components/V6JourneyPlanView/CityCard.tsx`
- Modify: `frontend/src/components/V6JourneyPlanView/CityDaySection.tsx`

**Step 1: Add hotel display to CityCard**

Import `Hotel` icon from lucide-react. After the `highlights` section (around line 125, before closing `</div>` of card), add:

```tsx
          {/* Accommodation */}
          {expanded && city.accommodation && (
            <div className="px-4 pb-4">
              <div
                className="flex items-center gap-3 p-3 rounded-xl"
                style={{ backgroundColor: `${palette.accentColor}08`, border: `1px solid ${palette.borderColor}` }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: `linear-gradient(135deg, ${palette.gradientFrom}, ${palette.gradientTo})` }}
                >
                  <Hotel className="h-5 w-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-display font-semibold text-gray-900 text-sm truncate">
                    {city.accommodation.name}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {city.accommodation.rating && (
                      <span className="text-xs text-gray-600 flex items-center gap-1">
                        <Star className="h-3 w-3 text-amber-400 fill-amber-400" />
                        {city.accommodation.rating.toFixed(1)}
                      </span>
                    )}
                    {city.accommodation.address && (
                      <span className="text-xs text-gray-500 truncate">{city.accommodation.address}</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
```

**Step 2: Add hotel display to CityDaySection header**

In `CityDaySection.tsx`, import `Hotel` from lucide-react. After the stats spans in the city header (around line 58, after the activities span), add:

```tsx
                  {city.accommodation && (
                    <span className="flex items-center gap-1.5 bg-white/15 px-2.5 py-0.5 rounded-full">
                      <Hotel className="h-3.5 w-3.5" />
                      {city.accommodation.name}
                    </span>
                  )}
```

**Step 3: Style accommodation bookend activities in ActivityCard**

In `frontend/src/styles/index.ts` (or wherever `categoryStyles` is defined), add an `accommodation` entry:

```typescript
  accommodation: {
    bg: '#F3F0FF',
    text: '#6B5B95',
    border: '#D4CCE6',
    accent: '#6B5B95',
    gradient: 'linear-gradient(135deg, #6B5B95, #8B7FB5)',
  },
```

**Step 4: Run type check and dev server**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/components/V6JourneyPlanView/CityCard.tsx frontend/src/components/V6JourneyPlanView/CityDaySection.tsx frontend/src/styles/
git commit -m "feat: display accommodation in city cards and day sections"
```

---

### Task 8: Add polyline decode utility

**Files:**
- Create: `frontend/src/utils/polyline.ts`

**Step 1: Create polyline decoder**

```typescript
/**
 * Decode a Google Maps encoded polyline string into an array of coordinates.
 * Based on the Google Encoded Polyline Algorithm.
 */
export function decodePolyline(encoded: string): { lat: number; lng: number }[] {
  const points: { lat: number; lng: number }[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    // Decode latitude
    let shift = 0;
    let result = 0;
    let byte: number;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lat += result & 1 ? ~(result >> 1) : result >> 1;

    // Decode longitude
    shift = 0;
    result = 0;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lng += result & 1 ? ~(result >> 1) : result >> 1;

    points.push({ lat: lat / 1e5, lng: lng / 1e5 });
  }

  return points;
}
```

**Step 2: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/utils/polyline.ts
git commit -m "feat: add polyline decode utility for Google Maps routes"
```

---

### Task 9: Install @vis.gl/react-google-maps and set up APIProvider

**Files:**
- Modify: `frontend/package.json` (via npm install)
- Modify: `frontend/src/App.tsx`

**Step 1: Install the library**

Run: `cd frontend && npm install @vis.gl/react-google-maps`

**Step 2: Remove @googlemaps/js-api-loader (unused)**

Run: `cd frontend && npm uninstall @googlemaps/js-api-loader`

**Step 3: Wrap App with APIProvider**

In `App.tsx`, add import at top:

```typescript
import { APIProvider } from '@vis.gl/react-google-maps';
```

Wrap the return JSX. The outermost element in the return should be:

```tsx
<APIProvider apiKey={import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''}>
  {/* existing JSX */}
</APIProvider>
```

**Step 4: Run dev server to verify no errors**

Run: `cd frontend && npm run dev`
Expected: App loads without errors

**Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/App.tsx
git commit -m "feat: install @vis.gl/react-google-maps and add APIProvider"
```

---

### Task 10: Create JourneyMap component

**Files:**
- Create: `frontend/src/components/maps/JourneyMap.tsx`

**Step 1: Create the component**

```tsx
import { useMemo, useCallback } from 'react';
import { Map, AdvancedMarker, useMap } from '@vis.gl/react-google-maps';
import { MapPin, Hotel } from 'lucide-react';
import type { V6CityStop, V6TravelLeg } from '@/types';
import { cityColorPalettes } from '@/components/V6JourneyPlanView/styles';

interface JourneyMapProps {
  cities: V6CityStop[];
  travelLegs: V6TravelLeg[];
  origin?: string;
}

export function JourneyMap({ cities, travelLegs }: JourneyMapProps) {
  // Calculate bounds to fit all cities
  const bounds = useMemo(() => {
    const coords = cities
      .filter(c => c.latitude != null && c.longitude != null)
      .map(c => ({ lat: c.latitude!, lng: c.longitude! }));

    // Add accommodation coords
    cities.forEach(c => {
      if (c.accommodation?.latitude && c.accommodation?.longitude) {
        coords.push({ lat: c.accommodation.latitude, lng: c.accommodation.longitude });
      }
    });

    if (coords.length === 0) return null;

    const lats = coords.map(c => c.lat);
    const lngs = coords.map(c => c.lng);

    return {
      north: Math.max(...lats) + 0.5,
      south: Math.min(...lats) - 0.5,
      east: Math.max(...lngs) + 0.5,
      west: Math.min(...lngs) - 0.5,
    };
  }, [cities]);

  if (!bounds) return null;

  const center = {
    lat: (bounds.north + bounds.south) / 2,
    lng: (bounds.east + bounds.west) / 2,
  };

  return (
    <div className="rounded-xl overflow-hidden border border-gray-200" style={{ height: 400 }}>
      <Map
        defaultCenter={center}
        defaultZoom={5}
        defaultBounds={bounds}
        gestureHandling="cooperative"
        disableDefaultUI={false}
        mapId="journey-map"
      >
        {/* City markers */}
        {cities.map((city, idx) => {
          if (city.latitude == null || city.longitude == null) return null;
          const palette = cityColorPalettes[idx % cityColorPalettes.length];
          return (
            <AdvancedMarker
              key={`city-${idx}`}
              position={{ lat: city.latitude, lng: city.longitude }}
              title={`${city.name} (${city.days} days)`}
            >
              <div
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-white text-xs font-bold shadow-lg"
                style={{ backgroundColor: palette.accentColor }}
              >
                <MapPin className="h-3.5 w-3.5" />
                {city.name}
              </div>
            </AdvancedMarker>
          );
        })}

        {/* Hotel markers */}
        {cities.map((city, idx) => {
          const acc = city.accommodation;
          if (!acc?.latitude || !acc?.longitude) return null;
          return (
            <AdvancedMarker
              key={`hotel-${idx}`}
              position={{ lat: acc.latitude, lng: acc.longitude }}
              title={acc.name}
            >
              <div className="flex items-center gap-1 px-2 py-1 bg-purple-600 text-white text-xs font-semibold rounded-full shadow-lg">
                <Hotel className="h-3 w-3" />
                <span className="max-w-[80px] truncate">{acc.name}</span>
              </div>
            </AdvancedMarker>
          );
        })}
      </Map>
    </div>
  );
}
```

**Step 2: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/maps/JourneyMap.tsx
git commit -m "feat: add JourneyMap component with city and hotel markers"
```

---

### Task 11: Create DayMap component

**Files:**
- Create: `frontend/src/components/maps/DayMap.tsx`

**Step 1: Create the component**

```tsx
import { useMemo } from 'react';
import { Map, AdvancedMarker } from '@vis.gl/react-google-maps';
import { Hotel } from 'lucide-react';
import type { V6Activity } from '@/types';
import { categoryStyles } from '@/styles';
import { decodePolyline } from '@/utils/polyline';
import { DayMapPolylines } from './DayMapPolylines';

interface DayMapProps {
  activities: V6Activity[];
}

export function DayMap({ activities }: DayMapProps) {
  // Calculate bounds from all activity locations
  const { bounds, center } = useMemo(() => {
    const coords = activities.map(a => a.place.location);
    if (coords.length === 0) return { bounds: null, center: { lat: 0, lng: 0 } };

    const lats = coords.map(c => c.lat);
    const lngs = coords.map(c => c.lng);

    const b = {
      north: Math.max(...lats) + 0.005,
      south: Math.min(...lats) - 0.005,
      east: Math.max(...lngs) + 0.005,
      west: Math.min(...lngs) - 0.005,
    };

    return {
      bounds: b,
      center: { lat: (b.north + b.south) / 2, lng: (b.east + b.west) / 2 },
    };
  }, [activities]);

  // Decode polylines for routes
  const routePaths = useMemo(() => {
    return activities
      .filter(a => a.route_to_next?.polyline)
      .map(a => decodePolyline(a.route_to_next!.polyline!));
  }, [activities]);

  if (!bounds || activities.length === 0) return null;

  return (
    <div className="rounded-xl overflow-hidden border border-gray-200" style={{ height: 350 }}>
      <Map
        defaultCenter={center}
        defaultZoom={13}
        defaultBounds={bounds}
        gestureHandling="cooperative"
        disableDefaultUI={false}
        mapId="day-map"
      >
        {/* Activity markers */}
        {activities.map((activity, idx) => {
          const category = activity.place.category?.toLowerCase() || 'default';
          const isAccommodation = category === 'accommodation';
          const style = categoryStyles[category] || categoryStyles.default;

          return (
            <AdvancedMarker
              key={idx}
              position={activity.place.location}
              title={activity.place.name}
            >
              {isAccommodation ? (
                <div className="w-8 h-8 rounded-full bg-purple-600 text-white flex items-center justify-center shadow-lg">
                  <Hotel className="h-4 w-4" />
                </div>
              ) : (
                <div
                  className="w-7 h-7 rounded-full text-white flex items-center justify-center text-xs font-bold shadow-lg"
                  style={{ background: style.gradient }}
                >
                  {idx + 1}
                </div>
              )}
            </AdvancedMarker>
          );
        })}

        {/* Route polylines */}
        <DayMapPolylines paths={routePaths} />
      </Map>
    </div>
  );
}
```

**Step 2: Create DayMapPolylines helper component**

Create `frontend/src/components/maps/DayMapPolylines.tsx`:

```tsx
import { useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import { useEffect } from 'react';

interface DayMapPolylinesProps {
  paths: { lat: number; lng: number }[][];
}

export function DayMapPolylines({ paths }: DayMapPolylinesProps) {
  const map = useMap();
  const mapsLib = useMapsLibrary('maps');

  useEffect(() => {
    if (!map || !mapsLib) return;

    const polylines = paths.map(path => {
      const polyline = new mapsLib.Polyline({
        path,
        strokeColor: '#6B5B95',
        strokeOpacity: 0.7,
        strokeWeight: 3,
        map,
      });
      return polyline;
    });

    return () => {
      polylines.forEach(p => p.setMap(null));
    };
  }, [map, mapsLib, paths]);

  return null;
}
```

**Step 3: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/components/maps/DayMap.tsx frontend/src/components/maps/DayMapPolylines.tsx
git commit -m "feat: add DayMap component with numbered markers and route polylines"
```

---

### Task 12: Integrate maps into journey views with toggle buttons

**Files:**
- Modify: `frontend/src/components/V6JourneyPlanView/index.tsx`
- Modify: `frontend/src/components/V6JourneyPlanView/DayCard.tsx`

**Step 1: Add JourneyMap toggle to V6JourneyPlanView**

Import at top:
```typescript
import { lazy, Suspense, useState as useMapState } from 'react';
import { Map as MapIcon } from 'lucide-react';

const JourneyMap = lazy(() => import('@/components/maps/JourneyMap').then(m => ({ default: m.JourneyMap })));
```

Add state inside the component:
```typescript
const [showJourneyMap, setShowJourneyMap] = useState(false);
const hasCoordinates = journey.cities.some(c => c.latitude != null && c.longitude != null);
```

After the route visualization section (after line 129), add:

```tsx
      {/* Journey Map Toggle */}
      {hasCoordinates && (
        <div className="mb-6">
          <button
            onClick={() => setShowJourneyMap(!showJourneyMap)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-display font-semibold rounded-xl bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 transition-all duration-200 shadow-sm"
          >
            <MapIcon className="h-4 w-4" />
            {showJourneyMap ? 'Hide Map' : 'Show Map'}
          </button>
          {showJourneyMap && (
            <div className="mt-3">
              <Suspense fallback={<div className="h-[400px] rounded-xl bg-gray-100 animate-pulse" />}>
                <JourneyMap
                  cities={journey.cities}
                  travelLegs={journey.travel_legs}
                  origin={journey.origin}
                />
              </Suspense>
            </div>
          )}
        </div>
      )}
```

**Step 2: Add DayMap toggle to DayCard**

In `DayCard.tsx`, add imports:
```typescript
import { lazy, Suspense } from 'react';
import { Map as MapIcon } from 'lucide-react';

const DayMap = lazy(() => import('@/components/maps/DayMap').then(m => ({ default: m.DayMap })));
```

Add state:
```typescript
const [showMap, setShowMap] = useState(false);
const hasLocations = dayPlan.activities.some(a => a.place.location);
```

Inside the expanded activities section (around line 167, after `<div className="p-4 bg-gray-50/50">`), add before the activities list:

```tsx
            {/* Day Map Toggle */}
            {hasLocations && (
              <div className="mb-4">
                <button
                  onClick={() => setShowMap(!showMap)}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs font-display font-semibold rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-all duration-200"
                >
                  <MapIcon className="h-3.5 w-3.5" />
                  {showMap ? 'Hide Map' : 'Show Map'}
                </button>
                {showMap && (
                  <div className="mt-3">
                    <Suspense fallback={<div className="h-[350px] rounded-xl bg-gray-100 animate-pulse" />}>
                      <DayMap activities={dayPlan.activities} />
                    </Suspense>
                  </div>
                )}
              </div>
            )}
```

**Step 3: Run type check and dev server**

Run: `cd frontend && npx tsc --noEmit && npm run dev`
Expected: No errors, maps render on toggle

**Step 4: Commit**

```bash
git add frontend/src/components/V6JourneyPlanView/index.tsx frontend/src/components/V6JourneyPlanView/DayCard.tsx
git commit -m "feat: integrate maps into journey views with toggle buttons"
```

---

### Task 13: Update V6DayPlanGenerator stream to include accommodation in serialized output

**Files:**
- Modify: `backend/app/generators/journey_plan/v6/day_plan_generator.py:340-370`

**Step 1: Include accommodation data in complete event serialization**

In the `generate_day_plans_stream` method, the `complete` event serializes `all_day_plans` (around line 334). This already serializes activities from `result.all_day_plans`, which will now include bookend activities with `category="accommodation"` — no change needed there.

However, update the `city_summaries` in the complete event to include accommodation data. In the city_summaries list comprehension (around line 325), add accommodation:

```python
                "city_summaries": [
                    {
                        "city": cp.city_name,
                        "days": cp.days,
                        "day_plans_count": len(cp.day_plans),
                        "error": cp.error,
                    }
                    for cp in result.city_plans
                ],
```

This is already correct — accommodation data flows via the journey plan's `V6CityStop`, not through day plan generation. No changes needed here.

**Step 2: Verify accommodation is included in journey plan serialization**

Check `backend/app/routers/journey.py` to confirm the journey plan response includes accommodation. The journey router serializes the plan using dataclass dict conversion. Since `Accommodation` is a dataclass with default fields, it will be serialized automatically.

Run: `cd backend && python -c "from app.generators.journey_plan.v6.models import CityStop, Accommodation; import dataclasses; c = CityStop(name='Test', country='X', days=2, accommodation=Accommodation(name='Hotel Test')); print(dataclasses.asdict(c))"`
Expected: Dict includes `accommodation` key

**Step 3: Commit (if any changes were needed)**

No commit needed for this task — it's a verification step.

---

### Task 14: Add accommodation category icon to frontend styles

**Files:**
- Modify: `frontend/src/styles/icons.tsx` (or wherever `getCategoryIcon` is defined)

**Step 1: Find and update getCategoryIcon**

Search for the `getCategoryIcon` function and add accommodation case:

```typescript
case 'accommodation':
  return <Hotel className={iconClass} />;
```

Import `Hotel` from `lucide-react` if not already imported.

**Step 2: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/styles/
git commit -m "feat: add accommodation category icon and styles"
```

---

### Task 15: End-to-end integration test (manual)

**Step 1: Start backend**

Run: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000`

**Step 2: Start frontend**

Run: `cd frontend && npm run dev`

**Step 3: Test journey flow**

1. Create a journey plan (e.g., "7 days in Northern Italy" from Milan)
2. Verify: each city in the plan shows an accommodation name
3. Click "Show Map" on the journey view — verify city and hotel markers render
4. Click "Generate Day Plans"
5. Verify: first and last activities in each day show hotel bookend (accommodation category)
6. Expand a day card, click "Show Map" — verify numbered activity markers and route polylines
7. Verify: hotel markers appear at start/end on the day map

**Step 4: Run backend tests**

Run: `cd backend && python -m pytest tests/ -v -k "not live"`
Expected: All PASS

**Step 5: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript or build errors

**Step 6: Final commit (if any fixups needed)**

```bash
git add -A
git commit -m "fix: integration fixes for hotels and maps features"
```
