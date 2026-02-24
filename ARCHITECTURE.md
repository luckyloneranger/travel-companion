# Travel Companion - Architecture & Implementation Plan

> **Purpose**: AI-powered travel itinerary generator using Azure OpenAI and Google APIs
> **Stack**: Python FastAPI (backend) + React/TypeScript (frontend)
> **Build Method**: AI-assisted coding

---

## Core Design Principle: AI as Orchestrator, Not Database

### The Problem with Pure AI Itinerary Generation

LLMs excel at **reasoning and creativity** but fail at:
- ❌ Real-time data (opening hours, traffic, weather)
- ❌ Accurate distance/time calculations
- ❌ Geographic optimization (traveling salesman problem)
- ❌ Price calculations and availability
- ❌ Consistent mathematical operations

### The Solution: Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RESPONSIBILITY SEPARATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────┐  ┌─────────────────────────────────┐  │
│   │         AI LAYER (LLM)          │  │    DETERMINISTIC SERVICES       │  │
│   │         "The Creative"          │  │       "The Calculator"          │  │
│   ├─────────────────────────────────┤  ├─────────────────────────────────┤  │
│   │                                 │  │                                 │  │
│   │  ✓ Understand user intent       │  │  ✓ Geocoding & coordinates      │  │
│   │  ✓ Select places matching       │  │  ✓ Distance calculations        │  │
│   │    interests from candidates    │  │  ✓ Travel time (real traffic)   │  │
│   │  ✓ Theme each day creatively    │  │  ✓ Route optimization           │  │
│   │  ✓ Write engaging descriptions  │  │  ✓ Opening hours validation     │  │
│   │  ✓ Suggest logical groupings    │  │  ✓ Time slot scheduling         │  │
│   │  ✓ Personalization reasoning    │  │  ✓ Conflict detection           │  │
│   │  ✓ Handle edge cases smartly    │  │  ✓ Budget calculations          │  │
│   │                                 │  │                                 │  │
│   │  OUTPUT: Selection + Order      │  │  OUTPUT: Times + Routes + Data  │  │
│   │                                 │  │                                 │  │
│   └─────────────────────────────────┘  └─────────────────────────────────┘  │
│                     │                              │                         │
│                     └──────────────┬───────────────┘                         │
│                                    ▼                                         │
│                    ┌───────────────────────────────┐                         │
│                    │      ORCHESTRATOR SERVICE     │                         │
│                    │   (Combines AI + Deterministic)│                         │
│                    └───────────────────────────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Pipeline: AI Decides WHAT, Services Calculate HOW

```
Step 1: GATHER DATA (Deterministic)
        Google Places API → Get real places with real data
        ↓
Step 2: AI SELECTION (LLM)
        "From these 80 places, pick 20 that best match
         art + food interests for a 3-day moderate trip"
        ↓
Step 3: AI ORDERING (LLM)  
        "Group these 20 places into 3 themed days,
         suggest a logical visit order per day"
        ↓
Step 4: ROUTE OPTIMIZATION (Deterministic)
        Google Routes API → Calculate actual distances
        Algorithm → Optimize visit order within each day
        ↓
Step 5: SCHEDULE BUILDING (Deterministic)
        Opening hours check → Validate each place is open
        Duration assignment → Allocate realistic time slots
        Gap filling → Add meals, breaks
        ↓
Step 6: VALIDATION (Deterministic)
        Check conflicts, verify all times work
        ↓
Step 7: ENRICHMENT (LLM + Deterministic)
        LLM → Write tips and descriptions
        API → Add photos, ratings, contact info
```

---

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Data Flow](#data-flow)
3. [Code Flow](#code-flow)
4. [API Contracts](#api-contracts)
5. [Data Models](#data-models)
6. [Service Specifications](#service-specifications)
7. [Frontend Components](#frontend-components)
8. [Implementation Phases](#implementation-phases)
9. [File Structure](#file-structure)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────┐                         │
│  │   React Web App     │    │  React Native App   │  (Future)               │
│  │   (Vite + TS)       │    │  (Expo)             │                         │
│  └──────────┬──────────┘    └──────────┬──────────┘                         │
│             │                          │                                     │
│             └──────────┬───────────────┘                                     │
│                        ▼                                                     │
│              ┌─────────────────┐                                             │
│              │   API Client    │  (Axios/Fetch with TypeScript types)       │
│              └────────┬────────┘                                             │
└───────────────────────┼─────────────────────────────────────────────────────┘
                        │ HTTP/REST
                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     FastAPI Application                              │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │    │
│  │  │   CORS      │  │  Validation │  │   Error     │                  │    │
│  │  │ Middleware  │  │ (Pydantic)  │  │  Handling   │                  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │    │
│  │                                                                      │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │                      ROUTERS                                   │  │    │
│  │  │  POST /api/itinerary  │  GET /api/places/search               │  │    │
│  │  │  GET /api/health      │  GET /api/places/{place_id}           │  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SERVICE LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   ItineraryGenerator Service                         │    │
│  │  - Orchestrates AI + Google APIs                                     │    │
│  │  - Validates and enriches itinerary data                            │    │
│  │  - Handles retry logic and fallbacks                                 │    │
│  └──────────────────────────┬──────────────────────────────────────────┘    │
│                              │                                               │
│         ┌───────────────────┼───────────────────┐                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │  Azure      │    │   Google    │    │   Google    │                      │
│  │  OpenAI     │    │   Places    │    │   Routes    │                      │
│  │  Service    │    │   Service   │    │   Service   │                      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                      │
│         │                  │                  │                              │
└─────────┼──────────────────┼──────────────────┼─────────────────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL APIS                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Azure OpenAI   │  │  Google Places  │  │  Google Routes  │              │
│  │  (GPT-4)        │  │  API (New)      │  │  API            │              │
│  │                 │  │                 │  │                 │              │
│  │  - Chat         │  │  - Text Search  │  │  - Directions   │              │
│  │  - Completions  │  │  - Place Details│  │  - Distance     │              │
│  │                 │  │  - Photos       │  │  - Duration     │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Itinerary Generation Flow (Hybrid AI + Deterministic)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│              HYBRID ITINERARY GENERATION - AI + DETERMINISTIC                │
└──────────────────────────────────────────────────────────────────────────────┘

[1] USER INPUT
    │
    │  {
    │    destination: "Paris, France",
    │    start_date: "2026-03-15",
    │    end_date: "2026-03-18",
    │    interests: ["art", "food", "history"],
    │    pace: "moderate"
    │  }
    │
    ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  PHASE 1: DATA GATHERING (100% Deterministic)                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  [2] GEOCODE DESTINATION                                                     ║
║      │  Service: Google Places Text Search                                   ║
║      │  Input: "Paris, France"                                               ║
║      │  Output: { lat: 48.8566, lng: 2.3522, place_id, timezone }            ║
║      │                                                                       ║
║      ▼                                                                       ║
║  [3] DISCOVER CANDIDATE PLACES                                               ║
║      │  Service: Google Places Nearby Search (parallel calls)                ║
║      │                                                                       ║
║      │  interest: "art" → types: ["museum", "art_gallery"]                   ║
║      │  interest: "food" → types: ["restaurant", "cafe"]                     ║
║      │  interest: "history" → types: ["historical_landmark"]                 ║
║      │                                                                       ║
║      │  For EACH candidate, fetch:                                           ║
║      │  - place_id, name, location (lat/lng)                                 ║
║      │  - rating, review_count, price_level                                  ║
║      │  - opening_hours (structured data!)                                   ║
║      │  - typical visit duration (if available)                              ║
║      │                                                                       ║
║      │  Output: 60-100 candidate places with REAL DATA                       ║
║      │                                                                       ║
║      ▼                                                                       ║
║  [4] PRE-FILTER CANDIDATES (Deterministic Rules)                             ║
║      │  - Remove permanently closed places                                   ║
║      │  - Remove places with rating < 3.5                                    ║
║      │  - Remove duplicates (same place, different categories)               ║
║      │  - Keep max 15 places per interest category                           ║
║      │                                                                       ║
║      │  Output: 40-50 quality candidates                                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    │
    ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  PHASE 2: AI SELECTION & CREATIVE PLANNING                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  [5] AI: SELECT BEST PLACES FOR THIS TRIP                                    ║
║      │                                                                       ║
║      │  Prompt to LLM:                                                       ║
║      │  """                                                                  ║
║      │  You are selecting places for a 3-day trip to Paris.                  ║
║      │  User interests: art, food, history                                   ║
║      │  Pace: moderate (4-5 activities per day)                              ║
║      │                                                                       ║
║      │  From these candidates, select 15-18 places that:                     ║
║      │  1. Best represent the user's interests                               ║
║      │  2. Include must-see landmarks for first-time visitors                ║
║      │  3. Mix famous spots with hidden gems                                 ║
║      │  4. Cover different neighborhoods for variety                         ║
║      │                                                                       ║
║      │  CANDIDATES:                                                          ║
║      │  [{ id: "louvre", name: "Louvre Museum", category: "museum",          ║
║      │     rating: 4.7, neighborhood: "1st arr" }, ...]                      ║
║      │                                                                       ║
║      │  Return JSON: { "selected_place_ids": ["louvre", ...] }               ║
║      │  """                                                                  ║
║      │                                                                       ║
║      │  AI Output: List of 15-18 place IDs                                   ║
║      │                                                                       ║
║      ▼                                                                       ║
║  [6] AI: GROUP INTO THEMED DAYS                                              ║
║      │                                                                       ║
║      │  Prompt to LLM:                                                       ║
║      │  """                                                                  ║
║      │  Group these 16 places into 3 days with themes.                       ║
║      │  Consider:                                                            ║
║      │  - Geographic proximity (places in same area = same day)              ║
║      │  - Thematic coherence (art day, food tour day, etc.)                  ║
║      │  - Energy flow (heavy museums not back-to-back)                       ║
║      │                                                                       ║
║      │  SELECTED PLACES (with neighborhoods):                                ║
║      │  [{ id: "louvre", neighborhood: "1st" }, ...]                         ║
║      │                                                                       ║
║      │  Return JSON:                                                         ║
║      │  {                                                                    ║
║      │    "days": [                                                          ║
║      │      {                                                                ║
║      │        "theme": "Art & Culture on the Right Bank",                    ║
║      │        "place_ids": ["louvre", "palais_royal", "cafe_marly", ...]     ║
║      │      }, ...                                                           ║
║      │    ]                                                                  ║
║      │  }                                                                    ║
║      │  """                                                                  ║
║      │                                                                       ║
║      │  AI Output: Grouped place IDs with themes (NO times, NO routes)       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    │
    ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  PHASE 3: ROUTE OPTIMIZATION (100% Deterministic)                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  [7] OPTIMIZE VISIT ORDER WITHIN EACH DAY                                    ║
║      │                                                                       ║
║      │  For each day's places:                                               ║
║      │                                                                       ║
║      │  Input:  [louvre, cafe_marly, palais_royal, orsay]                    ║
║      │          (AI's suggested order)                                       ║
║      │                                                                       ║
║      │  Algorithm: Nearest Neighbor or 2-opt TSP                             ║
║      │  Using: Google Distance Matrix for actual walk times                  ║
║      │                                                                       ║
║      │  Output: [palais_royal, louvre, cafe_marly, orsay]                    ║
║      │          (Optimized order minimizing travel time)                     ║
║      │                                                                       ║
║      ▼                                                                       ║
║  [8] CALCULATE ACTUAL ROUTES                                                 ║
║      │                                                                       ║
║      │  Service: Google Routes API                                           ║
║      │                                                                       ║
║      │  For each consecutive pair:                                           ║
║      │  palais_royal → louvre: { distance: 450m, duration: 6min, walk }      ║
║      │  louvre → cafe_marly: { distance: 100m, duration: 2min, walk }        ║
║      │  cafe_marly → orsay: { distance: 1.2km, duration: 15min, walk }       ║
║      │                                                                       ║
║      │  Output: Precise routes with polylines for map display                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    │
    ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  PHASE 4: SCHEDULE BUILDING (100% Deterministic)                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  [9] BUILD TIME SLOTS                                                        ║
║      │                                                                       ║
║      │  Scheduler Service (deterministic algorithm):                         ║
║      │                                                                       ║
║      │  CONFIG:                                                              ║
║      │  - Day starts: 09:00                                                  ║
║      │  - Day ends: 21:00                                                    ║
║      │  - Lunch window: 12:00-14:00                                          ║
║      │  - Dinner window: 19:00-21:00                                         ║
║      │                                                                       ║
║      │  DURATION RULES:                                                      ║
║      │  - Major museum: 180 min (from Google or default)                     ║
║      │  - Small museum: 90 min                                               ║
║      │  - Restaurant: 75 min                                                 ║
║      │  - Cafe: 45 min                                                       ║
║      │  - Landmark: 30 min                                                   ║
║      │                                                                       ║
║      │  ALGORITHM:                                                           ║
║      │  current_time = 09:00                                                 ║
║      │  for place in optimized_order:                                        ║
║      │      # Check opening hours                                            ║
║      │      if not place.is_open_at(current_time):                           ║
║      │          current_time = place.opens_at                                ║
║      │                                                                       ║
║      │      # Assign time slot                                               ║
║      │      place.start_time = current_time                                  ║
║      │      place.end_time = current_time + place.duration                   ║
║      │                                                                       ║
║      │      # Add travel time to next                                        ║
║      │      current_time = place.end_time + route_to_next.duration           ║
║      │                                                                       ║
║      │      # Insert meal breaks if needed                                   ║
║      │      if in_lunch_window and no_restaurant_yet:                        ║
║      │          insert_lunch_break()                                         ║
║      │                                                                       ║
║      ▼                                                                       ║
║  [10] VALIDATE SCHEDULE                                                      ║
║       │                                                                      ║
║       │  Checks:                                                             ║
║       │  ✓ No activity starts before place opens                             ║
║       │  ✓ No activity ends after place closes                               ║
║       │  ✓ Day doesn't exceed 21:00                                          ║
║       │  ✓ Adequate meal breaks included                                     ║
║       │  ✓ No overlapping time slots                                         ║
║       │                                                                      ║
║       │  If validation fails → Adjust or remove activities                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    │
    ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  PHASE 5: ENRICHMENT (AI + Deterministic)                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  [11] AI: GENERATE TIPS & DESCRIPTIONS                                       ║
║       │                                                                      ║
║       │  Prompt to LLM:                                                      ║
║       │  """                                                                 ║
║       │  Write a brief, helpful tip for visiting each place.                 ║
║       │  Consider the time of visit and what comes before/after.             ║
║       │                                                                      ║
║       │  Schedule:                                                           ║
║       │  09:00 - Louvre Museum (art museum)                                  ║
║       │  13:00 - Cafe Marly (restaurant, in Louvre courtyard)                ║
║       │  ...                                                                 ║
║       │                                                                      ║
║       │  Return tips like:                                                   ║
║       │  - "Louvre": "Enter via the Carrousel entrance to skip lines.        ║
║       │              Start with Mona Lisa before crowds build."              ║
║       │  """                                                                 ║
║       │                                                                      ║
║       ▼                                                                      ║
║  [12] FETCH FINAL DETAILS (Deterministic)                                    ║
║       │                                                                      ║
║       │  Google Place Details API:                                           ║
║       │  - High-res photos                                                   ║
║       │  - Current rating & review count                                     ║
║       │  - Website, phone number                                             ║
║       │  - Formatted address                                                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    │
    ▼
[13] ASSEMBLE FINAL RESPONSE
    │
    │  All data is now VERIFIED and CALCULATED:
    │  - Places selected by AI, data from Google
    │  - Times calculated by scheduler
    │  - Routes calculated by Google
    │  - Tips written by AI
    │
    │  ItineraryResponse { ... }
    │
    ▼
[14] FRONTEND DISPLAY
```

---

## Code Flow

### Backend Request Processing

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND CODE FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

main.py                          routers/itinerary.py
─────────                        ────────────────────
    │                                    │
    │  app = FastAPI()                   │
    │  app.include_router(              │
    │    itinerary_router               │
    │  )                                 │
    │                                    │
    └──────────────────────────────────►│
                                         │
                                         │  @router.post("/api/itinerary")
                                         │  async def generate_itinerary(
                                         │      request: ItineraryRequest
                                         │  ) -> ItineraryResponse:
                                         │
                                         │      # 1. Validate request
                                         │      validate_trip_duration(request)
                                         │
                                         │      # 2. Call generator service
                                         │      generator = ItineraryGenerator(
                                         │          openai_service,
                                         │          places_service,
                                         │          routes_service
                                         │      )
                                         │
                                         │      # 3. Generate itinerary
                                         │      itinerary = await generator.generate(request)
                                         │
                                         │      # 4. Return response
                                         │      return itinerary
                                         │
                                         ▼

services/itinerary_generator.py
───────────────────────────────
    │
    │  class ItineraryGenerator:
    │
    │      async def generate(self, request: ItineraryRequest):
    │
    │          # Step 1: Geocode destination
    │          destination = await self.places.geocode(
    │              request.destination
    │          )
    │
    │          # Step 2: Discover places
    │          candidates = await self.places.discover_places(
    │              location=destination.location,
    │              interests=request.interests,
    │              radius_km=15
    │          )
    │
    │          # Step 3: AI planning
    │          ai_plan = await self.openai.generate_itinerary(
    │              destination=destination,
    │              dates=(request.start_date, request.end_date),
    │              interests=request.interests,
    │              pace=request.pace,
    │              candidate_places=candidates
    │          )
    │
    │          # Step 4: Enrich with details
    │          enriched = await self.enrich_activities(ai_plan)
    │
    │          # Step 5: Calculate routes
    │          with_routes = await self.add_routes(enriched)
    │
    │          return with_routes
    │
    ▼

services/azure_openai.py              services/google_places.py
────────────────────────              ─────────────────────────
    │                                      │
    │  class AzureOpenAIService:           │  class GooglePlacesService:
    │                                      │
    │    async def generate_itinerary(     │    async def geocode(query):
    │        self,                         │        # Text Search API
    │        destination,                  │        response = await self.client.post(
    │        dates,                        │            "places:searchText",
    │        interests,                    │            {"textQuery": query}
    │        pace,                         │        )
    │        candidate_places              │        return response.places[0]
    │    ):                                │
    │                                      │    async def discover_places(
    │      prompt = self.build_prompt(     │        location, interests, radius
    │          destination,                │    ):
    │          dates,                      │        # Nearby Search for each interest
    │          interests,                  │        tasks = [
    │          pace,                       │            self.nearby_search(
    │          candidate_places            │                location,
    │      )                               │                interest_to_types(i),
    │                                      │                radius
    │      response = await self.client    │            )
    │          .chat.completions.create(   │            for i in interests
    │              model="gpt-4",          │        ]
    │              messages=[              │        results = await asyncio.gather(*tasks)
    │                  {"role": "system",  │        return flatten_and_dedupe(results)
    │                   "content": SYSTEM_PROMPT},
    │                  {"role": "user",    │    async def get_place_details(place_id):
    │                   "content": prompt} │        # Place Details API
    │              ],                      │        return await self.client.get(
    │              response_format={       │            f"places/{place_id}"
    │                  "type": "json_object"│        )
    │              }                       │
    │          )                           │
    │                                      │
    │      return parse_ai_response(       │
    │          response.choices[0]         │
    │          .message.content            │
    │      )                               │
    │                                      │
    ▼                                      ▼

services/google_routes.py
─────────────────────────
    │
    │  class GoogleRoutesService:
    │
    │    async def get_route(
    │        origin: Location,
    │        destination: Location,
    │        mode: TravelMode = "WALK"
    │    ):
    │        response = await self.client.post(
    │            "directions/v2:computeRoutes",
    │            {
    │                "origin": {"location": origin},
    │                "destination": {"location": destination},
    │                "travelMode": mode
    │            }
    │        )
    │
    │        route = response.routes[0]
    │        return RouteInfo(
    │            distance=route.distanceMeters,
    │            duration=route.duration,
    │            polyline=route.polyline.encodedPolyline
    │        )
    │
    ▼
```

---

## Service Specifications

### 1. Azure OpenAI Service (AI Layer - Selection & Creativity)

**File:** `services/azure_openai.py`

**Role:** ONLY selection, grouping, and creative content. NO time calculations.

**Configuration:**
```python
AZURE_OPENAI_ENDPOINT = "https://{resource}.openai.azure.com"
AZURE_OPENAI_API_KEY = "..."
AZURE_OPENAI_DEPLOYMENT = "gpt-4"
AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
```

**Prompt Strategy - Constrained AI:**
```
# BAD PROMPT (asking AI to do logistics):
"Create a detailed 3-day itinerary for Paris with exact times and distances..."

# GOOD PROMPT (AI only selects and groups):
"From these 45 candidate places, select 16 that best match the user's interests.
Group them into 3 themed days based on geographic proximity.
Return ONLY place IDs and groupings. Do NOT include times or durations."
```

**Key Methods:**
- `select_places(candidates, interests, num_days, pace) -> list[str]` (place IDs)
- `group_into_days(places, num_days) -> list[DayGroup]` (themes + place IDs)
- `generate_tips(schedule) -> dict[str, str]` (place_id → tip text)

### 2. Google Places Service (Deterministic - Real Data)

**File:** `services/google_places.py`

**Role:** Provide REAL, VERIFIED data for places

**Configuration:**
```python
GOOGLE_PLACES_API_KEY = "..."
GOOGLE_PLACES_BASE_URL = "https://places.googleapis.com/v1"
```

**Key Methods:**
- `geocode(query: str) -> Destination`
- `discover_places(location, interests, radius_km) -> list[PlaceCandidate]`
- `get_place_details(place_id) -> Place` (includes opening_hours!)
- `get_photo_url(photo_reference) -> str`

### 3. Google Routes Service (Deterministic - Real Routes)

**File:** `services/google_routes.py`

**Role:** Calculate ACTUAL distances and travel times

**Key Methods:**
- `compute_route(origin, destination, mode) -> Route`
- `get_distance_matrix(origins, destinations) -> Matrix`

### 4. Schedule Builder Service (Deterministic - Time Calculations)

**File:** `services/schedule_builder.py`

**Role:** Calculate exact time slots - NO AI INVOLVED

**Duration Defaults:**
```python
DURATION_BY_TYPE = {
    # Museums & Attractions
    "museum": 120,
    "art_gallery": 90,
    "tourist_attraction": 45,
    "church": 45,
    "park": 60,
    
    # Food & Drink
    "restaurant": 75,
    "cafe": 45,
    "bar": 60,
    
    # Shopping
    "shopping_mall": 90,
    "store": 30,
}

PACE_MULTIPLIERS = {
    "relaxed": 1.3,    # More time per activity
    "moderate": 1.0,
    "packed": 0.8,     # Less time, more activities
}
```

**Schedule Config:**
```python
@dataclass
class ScheduleConfig:
    day_start: time = time(9, 0)
    day_end: time = time(21, 0)
    lunch_window: tuple = (time(12, 0), time(14, 0))
    dinner_window: tuple = (time(19, 0), time(21, 0))
    buffer_minutes: int = 15  # Transition padding
```

**Key Algorithm:**
```python
class ScheduleBuilder:
    def build_schedule(
        self, 
        places: list[Place], 
        routes: list[Route],
        date: date,
        pace: str
    ) -> list[ScheduledActivity]:
        """100% deterministic time slot assignment."""
        schedule = []
        current_time = datetime.combine(date, self.config.day_start)
        
        for i, place in enumerate(places):
            # Get duration (from Google data or defaults)
            duration = self._get_duration(place, pace)
            
            # Validate against opening hours
            if not self._is_open(place, current_time, duration):
                current_time = self._next_open_time(place, current_time)
            
            # Assign slot
            end_time = current_time + timedelta(minutes=duration)
            schedule.append(ScheduledActivity(
                place=place,
                start_time=current_time.strftime("%H:%M"),
                end_time=end_time.strftime("%H:%M"),
                duration_minutes=duration
            ))
            
            # Add travel time to next
            if i < len(routes):
                travel_mins = routes[i].duration_seconds // 60
                current_time = end_time + timedelta(
                    minutes=travel_mins + self.config.buffer_minutes
                )
            else:
                current_time = end_time + timedelta(
                    minutes=self.config.buffer_minutes
                )
        
        return schedule
```

### 5. Route Optimizer Service (Deterministic - TSP)

**File:** `services/route_optimizer.py`

**Role:** Optimize visit order to minimize total travel time

---

#### Why TSP Matters for Travel Itineraries

```
UNOPTIMIZED (AI's grouping):          OPTIMIZED (TSP solved):
                                      
    ┌─── Louvre ◄────────┐               ┌─── Palais Royal
    │        │           │               │        │
    │    2.1 km         │               │     450m
    │        ▼           │               │        ▼
    │   Eiffel Tower     │               │     Louvre
    │        │           │               │        │
    │    3.5 km         │               │     800m
    │        ▼           │               │        ▼
    │   Palais Royal ────┘               │     Tuileries
    │        │                           │        │
    │    1.8 km                          │     1.2km
    │        ▼                           │        ▼
    └── Tuileries                        └── Eiffel Tower
                                      
    Total: 7.4 km                        Total: 2.45 km
    ~90 min walking                      ~30 min walking
```

**Savings: 60 minutes of walking per day!**

---

#### Our TSP Approach

**Problem Scale Analysis:**
```
Places per day by pace:
- Relaxed: 3-4 places → 6-12 permutations (trivial)
- Moderate: 5-6 places → 60-360 permutations (easy)  
- Packed: 7-8 places → 2,520-20,160 permutations (still manageable)

Conclusion: We DON'T need heavy optimization libraries.
A simple heuristic + local search is sufficient.
```

**Algorithm: Nearest Neighbor + 2-Opt**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TSP SOLUTION: 2-PHASE APPROACH                            │
└─────────────────────────────────────────────────────────────────────────────┘

PHASE 1: NEAREST NEIGHBOR (Build initial tour)
══════════════════════════════════════════════

Start at first place, always go to nearest unvisited place.

Example with 5 places (A, B, C, D, E):

Distance Matrix (walking minutes):
        A    B    C    D    E
    A   -   15   25    8   20
    B  15    -   10   18   12
    C  25   10    -   22    5
    D   8   18   22    -   15
    E  20   12    5   15    -

Algorithm:
1. Start at A (first in list)
2. Nearest to A: D (8 min) → Visit D
3. Nearest unvisited to D: E (15 min) → Visit E  
4. Nearest unvisited to E: C (5 min) → Visit C
5. Nearest unvisited to C: B (10 min) → Visit B

Result: A → D → E → C → B
Total: 8 + 15 + 5 + 10 = 38 min

Time Complexity: O(n²)


PHASE 2: 2-OPT IMPROVEMENT (Local optimization)
═══════════════════════════════════════════════

Try reversing segments to find improvements.

2-opt swap: Reverse a segment of the tour

Before: A → D → E → C → B
        ─────────────────
Try reversing [D, E]:
After:  A → E → D → C → B
        
Calculate new distance:
A→E: 20, E→D: 15, D→C: 22, C→B: 10
Total: 20 + 15 + 22 + 10 = 67 min (worse, reject)

Try reversing [E, C]:
After:  A → D → C → E → B

Calculate: 8 + 22 + 5 + 12 = 47 min (worse, reject)

Try reversing [D, E, C]:
After:  A → C → E → D → B

Calculate: 25 + 5 + 15 + 18 = 63 min (worse, reject)

Keep original: A → D → E → C → B = 38 min ✓

Time Complexity: O(n²) per iteration, typically 2-3 iterations
```

---

#### Implementation

```python
# services/route_optimizer.py

from dataclasses import dataclass
from typing import Optional
import asyncio

@dataclass
class OptimizationResult:
    places: list[Place]
    total_distance_meters: int
    total_duration_seconds: int
    
class RouteOptimizer:
    def __init__(self, routes_service: GoogleRoutesService):
        self.routes = routes_service
        
    async def optimize_day(
        self,
        places: list[Place],
        start_location: Optional[Location] = None,
        consider_time_windows: bool = True
    ) -> OptimizationResult:
        """
        Optimize visit order for a single day.
        
        Args:
            places: List of places to visit
            start_location: Optional starting point (e.g., hotel)
            consider_time_windows: If True, respect opening hours
            
        Returns:
            OptimizationResult with optimized place order
        """
        n = len(places)
        
        # Trivial cases
        if n <= 1:
            return OptimizationResult(places, 0, 0)
        if n == 2:
            route = await self.routes.compute_route(
                places[0].location, places[1].location
            )
            return OptimizationResult(places, route.distance_meters, route.duration_seconds)
        
        # Step 1: Get distance matrix from Google
        matrix = await self._build_distance_matrix(places)
        
        # Step 2: Nearest neighbor to build initial tour
        order = self._nearest_neighbor(matrix, start_idx=0)
        
        # Step 3: 2-opt improvement
        order = self._two_opt_improve(order, matrix)
        
        # Step 4: If considering time windows, validate and adjust
        if consider_time_windows:
            order = self._adjust_for_time_windows(order, places)
        
        # Build result
        optimized_places = [places[i] for i in order]
        total_dist, total_dur = self._calculate_totals(order, matrix)
        
        return OptimizationResult(
            places=optimized_places,
            total_distance_meters=total_dist,
            total_duration_seconds=total_dur
        )
    
    async def _build_distance_matrix(
        self, 
        places: list[Place]
    ) -> list[list[int]]:
        """
        Get real walking times between all pairs of places.
        Uses Google Distance Matrix API (one call for n×n pairs).
        """
        locations = [p.location for p in places]
        
        # Google Distance Matrix API call
        response = await self.routes.get_distance_matrix(
            origins=locations,
            destinations=locations,
            mode="WALK"
        )
        
        # Parse into 2D matrix of durations (seconds)
        n = len(places)
        matrix = [[0] * n for _ in range(n)]
        
        for i, row in enumerate(response.rows):
            for j, element in enumerate(row.elements):
                matrix[i][j] = element.duration_seconds
        
        return matrix
    
    def _nearest_neighbor(
        self, 
        matrix: list[list[int]], 
        start_idx: int = 0
    ) -> list[int]:
        """
        Build tour using nearest neighbor heuristic.
        
        Time: O(n²)
        Quality: Typically within 25% of optimal
        """
        n = len(matrix)
        visited = {start_idx}
        tour = [start_idx]
        current = start_idx
        
        while len(tour) < n:
            # Find nearest unvisited node
            nearest = None
            nearest_dist = float('inf')
            
            for j in range(n):
                if j not in visited and matrix[current][j] < nearest_dist:
                    nearest = j
                    nearest_dist = matrix[current][j]
            
            tour.append(nearest)
            visited.add(nearest)
            current = nearest
        
        return tour
    
    def _two_opt_improve(
        self, 
        tour: list[int], 
        matrix: list[list[int]],
        max_iterations: int = 100
    ) -> list[int]:
        """
        Improve tour using 2-opt swaps.
        
        2-opt: Remove two edges, reconnect differently.
        Keep swapping until no improvement found.
        
        Time: O(n²) per iteration
        """
        n = len(tour)
        improved = True
        iterations = 0
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            for i in range(n - 1):
                for j in range(i + 2, n):
                    # Calculate current distance for edges (i, i+1) and (j, j+1 or wrap)
                    # vs swapped edges (i, j) and (i+1, j+1 or wrap)
                    
                    gain = self._two_opt_gain(tour, i, j, matrix)
                    
                    if gain > 0:
                        # Reverse segment between i+1 and j
                        tour[i+1:j+1] = reversed(tour[i+1:j+1])
                        improved = True
        
        return tour
    
    def _two_opt_gain(
        self, 
        tour: list[int], 
        i: int, 
        j: int, 
        matrix: list[list[int]]
    ) -> int:
        """
        Calculate improvement from 2-opt swap.
        
        Current edges: (tour[i], tour[i+1]) and (tour[j], tour[j+1])
        New edges:     (tour[i], tour[j]) and (tour[i+1], tour[j+1])
        
        Returns positive value if swap improves tour.
        """
        n = len(tour)
        
        # Current edges
        a, b = tour[i], tour[i + 1]
        c, d = tour[j], tour[(j + 1) % n]
        
        current_dist = matrix[a][b] + matrix[c][d]
        new_dist = matrix[a][c] + matrix[b][d]
        
        return current_dist - new_dist  # Positive = improvement
    
    def _adjust_for_time_windows(
        self,
        order: list[int],
        places: list[Place]
    ) -> list[int]:
        """
        Adjust order to respect opening hours.
        
        Example: If museum opens at 10am but cafe opens at 7am,
        visit cafe first even if it's slightly farther.
        """
        # Sort by opening time, keeping geographic clusters
        # This is a simplified version - full TSPTW is much harder
        
        ordered_places = [(i, places[i]) for i in order]
        
        # Group into morning (opens before 10) and regular
        morning_places = [
            (i, p) for i, p in ordered_places 
            if p.opening_hours and p.opens_before(time(10, 0))
        ]
        regular_places = [
            (i, p) for i, p in ordered_places 
            if (i, p) not in morning_places
        ]
        
        # Morning places first, then regular
        return [i for i, p in morning_places] + [i for i, p in regular_places]
    
    def _calculate_totals(
        self,
        order: list[int],
        matrix: list[list[int]]
    ) -> tuple[int, int]:
        """Calculate total distance and duration for tour."""
        total = 0
        for i in range(len(order) - 1):
            total += matrix[order[i]][order[i + 1]]
        
        # Estimate distance from duration (avg walking speed 5 km/h)
        distance = int(total * 5000 / 3600)  # meters
        
        return distance, total
```

---

#### Time Window Considerations (TSPTW)

For places with strict opening hours, we may need **TSP with Time Windows (TSPTW)**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HANDLING OPENING HOURS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Problem: Louvre opens 9am, Restaurant opens 12pm
         TSP might suggest: Restaurant → Louvre (shorter walk)
         But: Restaurant isn't open at 9am!

Solution: 2-Phase Approach

PHASE 1: Categorize by time windows
──────────────────────────────────

Morning slots (9am-12pm):
  - Museums (open 9am-10am)
  - Parks (always open)
  - Landmarks (always open)

Afternoon slots (12pm-5pm):  
  - Restaurants (open 11am-12pm)
  - Shops (open 10am-11am)

Evening slots (5pm-9pm):
  - Restaurants (dinner)
  - Bars (open 5pm+)
  - Night attractions

PHASE 2: Optimize within each time block
────────────────────────────────────────

┌─────────────────────────────────────────────┐
│ Morning Block (9am-12pm)                    │
│                                             │
│   Optimize TSP for: [Museum A, Park, Museum B]│
│   Result: Park → Museum A → Museum B        │
│           (geographically optimal)          │
└─────────────────────────────────────────────┘
              │
              ▼ (travel to lunch area)
┌─────────────────────────────────────────────┐
│ Afternoon Block (12pm-5pm)                  │
│                                             │
│   Optimize TSP for: [Restaurant, Shop, Cafe]│
│   Result: Restaurant → Cafe → Shop          │
└─────────────────────────────────────────────┘
              │
              ▼ (travel to evening area)
┌─────────────────────────────────────────────┐
│ Evening Block (5pm-9pm)                     │
│                                             │
│   Optimize TSP for: [Bar, Night Market]     │
│   Result: Night Market → Bar                │
└─────────────────────────────────────────────┘
```

---

#### Algorithm Comparison for Our Scale

| Algorithm | Time Complexity | Quality | Best For |
|-----------|----------------|---------|----------|
| **Brute Force** | O(n!) | Optimal | n ≤ 8 |
| **Nearest Neighbor** | O(n²) | ~75-80% | Quick baseline |
| **NN + 2-opt** | O(n³) | ~95-98% | **Our choice** |
| **Branch & Bound** | O(2ⁿ) | Optimal | n ≤ 15 |
| **OR-Tools** | Varies | Optimal | Large n, complex constraints |

**Our Choice: Nearest Neighbor + 2-opt** because:
1. ✅ Fast enough for n ≤ 8 (milliseconds)
2. ✅ No external dependencies
3. ✅ Gets within 5% of optimal
4. ✅ Easy to implement and debug
5. ✅ Can add time window handling

---

#### For Future: Using OR-Tools (if needed)

If we add more constraints (multi-day optimization, vehicle routing, strict time windows):

```python
# Alternative using Google OR-Tools (heavier dependency)

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

def solve_with_ortools(distance_matrix: list[list[int]]) -> list[int]:
    """
    Use Google OR-Tools for complex TSP variants.
    Handles: time windows, capacity, multiple vehicles, etc.
    """
    manager = pywrapcp.RoutingIndexManager(
        len(distance_matrix), 1, 0  # nodes, vehicles, depot
    )
    routing = pywrapcp.RoutingModel(manager)
    
    def distance_callback(from_idx, to_idx):
        from_node = manager.IndexToNode(from_idx)
        to_node = manager.IndexToNode(to_idx)
        return distance_matrix[from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # Solve
    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    
    solution = routing.SolveWithParameters(search_params)
    
    # Extract route
    route = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    
    return route
```

**When to upgrade to OR-Tools:**
- Multi-day trip optimization (all days together)
- Vehicle/transport mode selection
- Hotel location as fixed depot
- Strict time windows that can't be approximated

---

## The Orchestration Flow

```python
# services/itinerary_generator.py

class ItineraryGenerator:
    """Orchestrates AI + Deterministic services."""
    
    async def generate(self, request: ItineraryRequest) -> Itinerary:
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 1: DATA GATHERING (Deterministic)
        # ═══════════════════════════════════════════════════════════
        
        # 1. Geocode destination
        destination = await self.places.geocode(request.destination)
        
        # 2. Discover candidate places with REAL data
        candidates = await self.places.discover_places(
            location=destination.location,
            interests=request.interests,
            radius_km=15
        )
        # candidates now have: ratings, opening_hours, types, etc.
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 2: AI SELECTION (Creative)
        # ═══════════════════════════════════════════════════════════
        
        num_days = (request.end_date - request.start_date).days + 1
        
        # 3. AI selects best places (returns IDs only)
        selected_ids = await self.openai.select_places(
            candidates=candidates,
            interests=request.interests,
            num_days=num_days,
            pace=request.pace
        )
        
        # 4. AI groups into themed days (returns IDs + themes)
        day_groups = await self.openai.group_into_days(
            places=[c for c in candidates if c.id in selected_ids],
            num_days=num_days
        )
        # day_groups = [
        #   { theme: "Art & Culture", place_ids: ["louvre", "orsay", ...] },
        #   ...
        # ]
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 3: ROUTE OPTIMIZATION (Deterministic)
        # ═══════════════════════════════════════════════════════════
        
        days = []
        for i, group in enumerate(day_groups):
            places = [self._get_place(id) for id in group.place_ids]
            
            # 5. Optimize visit order using real distances
            optimized_places = await self.optimizer.optimize_day(places)
            
            # 6. Calculate actual routes
            routes = await self.routes.compute_routes_batch(optimized_places)
            
            # ═══════════════════════════════════════════════════════
            # PHASE 4: SCHEDULE BUILDING (Deterministic)
            # ═══════════════════════════════════════════════════════
            
            # 7. Build time slots using real opening hours
            date = request.start_date + timedelta(days=i)
            scheduled = self.scheduler.build_schedule(
                places=optimized_places,
                routes=routes,
                date=date,
                pace=request.pace
            )
            
            days.append(DayPlan(
                date=date,
                day_number=i + 1,
                theme=group.theme,
                activities=scheduled
            ))
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 5: ENRICHMENT (AI for tips, Deterministic for data)
        # ═══════════════════════════════════════════════════════════
        
        # 8. AI generates tips (creative, not logistics)
        tips = await self.openai.generate_tips(days)
        
        # 9. Attach tips and final data
        for day in days:
            for activity in day.activities:
                activity.notes = tips.get(activity.place.place_id, "")
        
        return Itinerary(
            destination=destination,
            days=days,
            # ... summary calculated deterministically
        )
```

---

## Summary: What Each Layer Does

| Component | Type | Responsibility |
|-----------|------|----------------|
| **Azure OpenAI** | AI | Select places, group by theme, write tips |
| **Google Places** | Deterministic | Real place data, ratings, opening hours |
| **Google Routes** | Deterministic | Real distances, travel times, polylines |
| **Route Optimizer** | Deterministic | TSP algorithm for visit order |
| **Schedule Builder** | Deterministic | Time slot calculation, validation |
| **Orchestrator** | Hybrid | Coordinates all services |

**Key Insight:** The AI never sees or generates:
- ❌ Exact times (09:00, 13:30)
- ❌ Durations in minutes
- ❌ Distances in meters
- ❌ Opening/closing hours
- ❌ Route calculations

These are ALL handled by deterministic services using real API data.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND COMPONENT FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

App.tsx
───────
    │
    │  function App() {
    │    const [itinerary, setItinerary] = useState<Itinerary | null>(null)
    │    const [loading, setLoading] = useState(false)
    │    const [error, setError] = useState<string | null>(null)
    │
    │    return (
    │      <div className="app">
    │        <Header />
    │        {!itinerary ? (
    │          <TripInputForm onSubmit={handleSubmit} loading={loading} />
    │        ) : (
    │          <ItineraryView itinerary={itinerary} onReset={handleReset} />
    │        )}
    │      </div>
    │    )
    │  }
    │
    ├──────────────────────────────────────────────────────────────────────────┐
    │                                                                          │
    ▼                                                                          ▼

components/TripInputForm.tsx                    components/ItineraryView.tsx
────────────────────────────                    ────────────────────────────
    │                                               │
    │  - DestinationInput (autocomplete)            │  - ItinerarySummary
    │  - DateRangePicker                            │  - DayTabs / DaySelector
    │  - InterestSelector (chips)                   │  - DayCard (for each day)
    │  - PaceSelector (radio)                       │      - ActivityCard (for each activity)
    │  - SubmitButton                               │      - RouteConnector
    │                                               │  - MapView (Google Maps)
    │  onSubmit: async (data) => {                  │
    │    setLoading(true)                           │
    │    try {                                      │
    │      const result = await api.generateItinerary(data)
    │      setItinerary(result)                     │
    │    } catch (err) {                            │
    │      setError(err.message)                    │
    │    } finally {                                │
    │      setLoading(false)                        │
    │    }                                          │
    │  }                                            │
    │                                               │
    ▼                                               ▼

services/api.ts                                 components/MapView.tsx
───────────────                                 ──────────────────────
    │                                               │
    │  const API_BASE = '/api'                      │  - Google Maps JavaScript API
    │                                               │  - Markers for each activity
    │  export async function generateItinerary(    │  - Polylines for routes
    │    request: ItineraryRequest                  │  - Info windows on click
    │  ): Promise<ItineraryResponse> {              │  - Day filter controls
    │    const response = await fetch(              │
    │      `${API_BASE}/itinerary`,                 │  useEffect(() => {
    │      {                                        │    // Initialize map
    │        method: 'POST',                        │    const map = new google.maps.Map(ref, {
    │        headers: {                             │      center: itinerary.destination.location,
    │          'Content-Type': 'application/json'  │      zoom: 13
    │        },                                     │    })
    │        body: JSON.stringify(request)          │
    │      }                                        │    // Add markers
    │    )                                          │    activities.forEach(a => {
    │                                               │      new google.maps.Marker({
    │    if (!response.ok) {                        │        position: a.place.location,
    │      throw new ApiError(response)             │        map,
    │    }                                          │        title: a.place.name
    │                                               │      })
    │    return response.json()                     │    })
    │  }                                            │  }, [selectedDay])
    │                                               │
    ▼                                               ▼
```

---

## API Contracts

### POST /api/itinerary

**Request Model:**
```typescript
interface ItineraryRequest {
  destination: string;           // "Paris, France"
  start_date: string;            // ISO 8601: "2026-03-15"
  end_date: string;              // ISO 8601: "2026-03-18"
  interests: string[];           // ["art", "food", "history"]
  pace: "relaxed" | "moderate" | "packed";
  preferences?: {
    budget?: "budget" | "moderate" | "luxury";
    accessibility?: boolean;
    avoid_crowds?: boolean;
  };
}
```

**Response Model:**
```typescript
interface ItineraryResponse {
  id: string;                    // UUID for this itinerary
  destination: {
    name: string;
    place_id: string;
    location: { lat: number; lng: number };
    country: string;
    timezone: string;
  };
  trip_dates: {
    start: string;
    end: string;
    duration_days: number;
  };
  days: DayPlan[];
  summary: {
    total_activities: number;
    total_distance_km: number;
    interests_covered: string[];
    estimated_cost_range?: string;
  };
  generated_at: string;          // ISO 8601 timestamp
}

interface DayPlan {
  date: string;                  // "2026-03-15"
  day_number: number;            // 1, 2, 3...
  theme: string;                 // "Art & Culture Day"
  activities: Activity[];
}

interface Activity {
  id: string;
  time_start: string;            // "09:00"
  time_end: string;              // "12:00"
  duration_minutes: number;
  place: Place;
  notes: string;                 // AI-generated tips
  route_to_next?: Route;         // null for last activity
}

interface Place {
  place_id: string;
  name: string;
  address: string;
  location: { lat: number; lng: number };
  category: string;              // "museum", "restaurant", etc.
  rating?: number;
  photo_url?: string;
  opening_hours?: string[];
  website?: string;
}

interface Route {
  distance_meters: number;
  duration_seconds: number;
  duration_text: string;         // "15 min"
  travel_mode: "WALK" | "DRIVE" | "TRANSIT";
  polyline: string;              // Encoded polyline for map
}
```

### Error Response

```typescript
interface ErrorResponse {
  error: {
    code: string;                // "INVALID_DESTINATION", "API_ERROR", etc.
    message: string;
    details?: Record<string, any>;
  };
}
```

---

## Data Models

### Backend Pydantic Models

```python
# models/itinerary.py

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from enum import Enum

class Pace(str, Enum):
    RELAXED = "relaxed"
    MODERATE = "moderate"
    PACKED = "packed"

class Budget(str, Enum):
    BUDGET = "budget"
    MODERATE = "moderate"
    LUXURY = "luxury"

class TravelMode(str, Enum):
    WALK = "WALK"
    DRIVE = "DRIVE"
    TRANSIT = "TRANSIT"

class Location(BaseModel):
    lat: float
    lng: float

class Preferences(BaseModel):
    budget: Optional[Budget] = Budget.MODERATE
    accessibility: bool = False
    avoid_crowds: bool = False

class ItineraryRequest(BaseModel):
    destination: str = Field(..., min_length=2, max_length=200)
    start_date: date
    end_date: date
    interests: list[str] = Field(..., min_length=1, max_length=10)
    pace: Pace = Pace.MODERATE
    preferences: Optional[Preferences] = None

    @validator('end_date')
    def end_after_start(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        if 'start_date' in values and (v - values['start_date']).days > 14:
            raise ValueError('Trip duration cannot exceed 14 days')
        return v

class Place(BaseModel):
    place_id: str
    name: str
    address: str
    location: Location
    category: str
    rating: Optional[float] = None
    photo_url: Optional[str] = None
    opening_hours: Optional[list[str]] = None
    website: Optional[str] = None

class Route(BaseModel):
    distance_meters: int
    duration_seconds: int
    duration_text: str
    travel_mode: TravelMode
    polyline: str

class Activity(BaseModel):
    id: str
    time_start: str
    time_end: str
    duration_minutes: int
    place: Place
    notes: str
    route_to_next: Optional[Route] = None

class DayPlan(BaseModel):
    date: date
    day_number: int
    theme: str
    activities: list[Activity]

class Destination(BaseModel):
    name: str
    place_id: str
    location: Location
    country: str
    timezone: str

class TripDates(BaseModel):
    start: date
    end: date
    duration_days: int

class Summary(BaseModel):
    total_activities: int
    total_distance_km: float
    interests_covered: list[str]
    estimated_cost_range: Optional[str] = None

class ItineraryResponse(BaseModel):
    id: str
    destination: Destination
    trip_dates: TripDates
    days: list[DayPlan]
    summary: Summary
    generated_at: str
```

---

## Service Specifications

### 1. Azure OpenAI Service

**File:** `services/azure_openai.py`

**Configuration:**
```python
AZURE_OPENAI_ENDPOINT = "https://{resource}.openai.azure.com"
AZURE_OPENAI_API_KEY = "..."
AZURE_OPENAI_DEPLOYMENT = "gpt-4"
AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
```

**System Prompt:**
```
You are an expert travel planner with deep knowledge of destinations worldwide.
Your task is to create personalized, day-by-day travel itineraries.

Guidelines:
1. Create a logical flow of activities considering:
   - Geographic proximity (minimize travel time)
   - Opening hours of attractions
   - Meal times (breakfast, lunch, dinner)
   - Energy levels throughout the day

2. Match pace to user preference:
   - Relaxed: 2-3 activities per day, plenty of free time
   - Moderate: 4-5 activities per day, balanced
   - Packed: 6-7 activities per day, maximizing sights

3. Balance interests across days, don't cluster all similar activities

4. Include practical tips in activity notes

5. Output valid JSON matching the specified schema
```

**Key Methods:**
- `generate_itinerary(destination, dates, interests, pace, candidates) -> AIPlan`
- `build_prompt(context) -> str`
- `parse_response(content) -> AIPlan`

### 2. Google Places Service

**File:** `services/google_places.py`

**Configuration:**
```python
GOOGLE_PLACES_API_KEY = "..."
GOOGLE_PLACES_BASE_URL = "https://places.googleapis.com/v1"
```

**Interest to Place Types Mapping:**
```python
INTEREST_TYPE_MAP = {
    "art": ["art_gallery", "museum"],
    "history": ["historical_landmark", "museum", "monument"],
    "food": ["restaurant", "cafe", "bakery", "bar"],
    "nature": ["park", "natural_feature", "hiking_area"],
    "shopping": ["shopping_mall", "market", "clothing_store"],
    "nightlife": ["night_club", "bar", "casino"],
    "architecture": ["church", "historical_landmark", "tourist_attraction"],
    "culture": ["cultural_center", "performing_arts_theater", "museum"],
    "adventure": ["amusement_park", "tourist_attraction", "sports_complex"],
    "relaxation": ["spa", "park", "beach"],
}
```

**Key Methods:**
- `geocode(query: str) -> Destination`
- `discover_places(location, interests, radius_km) -> list[PlaceCandidate]`
- `nearby_search(location, types, radius) -> list[PlaceCandidate]`
- `get_place_details(place_id) -> Place`
- `get_photo_url(photo_reference) -> str`

### 3. Google Routes Service

**File:** `services/google_routes.py`

**Configuration:**
```python
GOOGLE_ROUTES_API_KEY = "..."
GOOGLE_ROUTES_BASE_URL = "https://routes.googleapis.com/directions/v2"
```

**Key Methods:**
- `compute_route(origin, destination, mode) -> Route`
- `compute_routes_batch(waypoints, mode) -> list[Route]`

---

## Frontend Components

### Component Tree

```
App
├── Header
│   └── Logo, Title
├── TripInputForm (when no itinerary)
│   ├── DestinationInput
│   │   └── Google Places Autocomplete
│   ├── DateRangePicker
│   │   └── Calendar component
│   ├── InterestSelector
│   │   └── InterestChip[] (art, food, history, etc.)
│   ├── PaceSelector
│   │   └── RadioGroup (relaxed, moderate, packed)
│   └── GenerateButton
├── ItineraryView (when itinerary exists)
│   ├── ItineraryHeader
│   │   └── Destination, Dates, Summary stats
│   ├── ViewToggle (List / Map)
│   ├── DaySelector
│   │   └── DayTab[] (Day 1, Day 2, ...)
│   ├── DayCard
│   │   ├── DayHeader (date, theme)
│   │   └── ActivityList
│   │       ├── ActivityCard
│   │       │   ├── TimeSlot
│   │       │   ├── PlaceInfo (name, photo, rating)
│   │       │   ├── ActivityNotes
│   │       │   └── ExpandButton
│   │       └── RouteConnector
│   │           └── Distance, Duration, Mode icon
│   └── MapView
│       ├── Google Map
│       ├── PlaceMarkers
│       ├── RoutePolylines
│       └── InfoWindow
└── Footer
    └── Credits, Links
```

### Key Component Props

```typescript
// TripInputForm
interface TripInputFormProps {
  onSubmit: (request: ItineraryRequest) => Promise<void>;
  loading: boolean;
  error?: string;
}

// ItineraryView
interface ItineraryViewProps {
  itinerary: ItineraryResponse;
  onReset: () => void;
}

// DayCard
interface DayCardProps {
  day: DayPlan;
  isExpanded: boolean;
  onToggle: () => void;
}

// ActivityCard
interface ActivityCardProps {
  activity: Activity;
  isLast: boolean;
}

// MapView
interface MapViewProps {
  destination: Location;
  activities: Activity[];
  selectedDay?: number;
  onMarkerClick: (activity: Activity) => void;
}
```

---

## Map Visualization Component

### Features

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MAP VISUALIZATION FEATURES                           │
└─────────────────────────────────────────────────────────────────────────────┘

1. INTERACTIVE MAP
   ├── Google Maps JavaScript API
   ├── Centered on destination city
   ├── Auto-zoom to fit all markers
   └── Smooth pan/zoom animations

2. PLACE MARKERS
   ├── Numbered markers (1, 2, 3...) matching itinerary order
   ├── Color-coded by category:
   │   🔵 Museum/Art    🟢 Park/Nature
   │   🔴 Restaurant    🟡 Landmark
   │   🟣 Shopping      🟠 Nightlife
   ├── Click → Info window with details
   └── Hover → Place name tooltip

3. ROUTE POLYLINES
   ├── Walking routes between places
   ├── Dashed lines showing path
   ├── Color matches the day
   └── Distance/duration labels

4. DAY FILTERING
   ├── Toggle to show specific day
   ├── "Show All Days" option
   └── Different colors per day

5. TIMELINE SYNC
   ├── Click marker → Scroll to activity card
   └── Click activity card → Highlight marker
```

### Implementation

```typescript
// components/MapView/index.tsx

import { useEffect, useRef, useState } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import type { Activity, DayPlan, Location } from '@/types/itinerary';

interface MapViewProps {
  destination: Location;
  days: DayPlan[];
  selectedDay: number | null;  // null = show all
  onActivitySelect: (activity: Activity) => void;
  highlightedActivityId?: string;
}

// Category to marker color mapping
const CATEGORY_COLORS: Record<string, string> = {
  museum: '#3B82F6',      // blue
  art_gallery: '#3B82F6',
  restaurant: '#EF4444',  // red
  cafe: '#F97316',        // orange
  park: '#22C55E',        // green
  landmark: '#EAB308',    // yellow
  shopping: '#A855F7',    // purple
  bar: '#EC4899',         // pink
  default: '#6B7280',     // gray
};

// Day colors for routes
const DAY_COLORS = [
  '#3B82F6',  // Day 1: Blue
  '#22C55E',  // Day 2: Green  
  '#F59E0B',  // Day 3: Amber
  '#EF4444',  // Day 4: Red
  '#8B5CF6',  // Day 5: Purple
];

export function MapView({
  destination,
  days,
  selectedDay,
  onActivitySelect,
  highlightedActivityId,
}: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [markers, setMarkers] = useState<google.maps.Marker[]>([]);
  const [polylines, setPolylines] = useState<google.maps.Polyline[]>([]);
  const [infoWindow, setInfoWindow] = useState<google.maps.InfoWindow | null>(null);

  // Initialize map
  useEffect(() => {
    const loader = new Loader({
      apiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY,
      version: 'weekly',
      libraries: ['places', 'geometry'],
    });

    loader.load().then(() => {
      if (!mapRef.current) return;

      const mapInstance = new google.maps.Map(mapRef.current, {
        center: { lat: destination.lat, lng: destination.lng },
        zoom: 13,
        styles: MAP_STYLES, // Custom styling
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
      });

      setMap(mapInstance);
      setInfoWindow(new google.maps.InfoWindow());
    });
  }, [destination]);

  // Update markers when days or selectedDay changes
  useEffect(() => {
    if (!map) return;

    // Clear existing markers and polylines
    markers.forEach(m => m.setMap(null));
    polylines.forEach(p => p.setMap(null));

    const newMarkers: google.maps.Marker[] = [];
    const newPolylines: google.maps.Polyline[] = [];
    const bounds = new google.maps.LatLngBounds();

    // Filter days to display
    const daysToShow = selectedDay !== null 
      ? [days[selectedDay]] 
      : days;

    let activityNumber = 1;

    daysToShow.forEach((day, dayIndex) => {
      const dayColor = DAY_COLORS[dayIndex % DAY_COLORS.length];
      const routeCoordinates: google.maps.LatLngLiteral[] = [];

      day.activities.forEach((activity, activityIndex) => {
        const position = {
          lat: activity.place.location.lat,
          lng: activity.place.location.lng,
        };

        // Add to bounds
        bounds.extend(position);
        routeCoordinates.push(position);

        // Create numbered marker
        const marker = new google.maps.Marker({
          position,
          map,
          label: {
            text: String(activityNumber++),
            color: 'white',
            fontWeight: 'bold',
          },
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: CATEGORY_COLORS[activity.place.category] || CATEGORY_COLORS.default,
            fillOpacity: 1,
            strokeColor: 'white',
            strokeWeight: 2,
            scale: 15,
          },
          title: activity.place.name,
          animation: highlightedActivityId === activity.id 
            ? google.maps.Animation.BOUNCE 
            : undefined,
        });

        // Marker click handler
        marker.addListener('click', () => {
          infoWindow?.setContent(createInfoWindowContent(activity));
          infoWindow?.open(map, marker);
          onActivitySelect(activity);
        });

        newMarkers.push(marker);

        // Draw route to next activity
        if (activity.route_to_next && activityIndex < day.activities.length - 1) {
          const nextActivity = day.activities[activityIndex + 1];
          
          // Decode polyline if available
          const path = activity.route_to_next.polyline
            ? google.maps.geometry.encoding.decodePath(activity.route_to_next.polyline)
            : [position, { lat: nextActivity.place.location.lat, lng: nextActivity.place.location.lng }];

          const polyline = new google.maps.Polyline({
            path,
            geodesic: true,
            strokeColor: dayColor,
            strokeOpacity: 0.8,
            strokeWeight: 4,
            map,
          });

          newPolylines.push(polyline);
        }
      });
    });

    // Fit map to show all markers
    if (newMarkers.length > 0) {
      map.fitBounds(bounds, { padding: 50 });
    }

    setMarkers(newMarkers);
    setPolylines(newPolylines);
  }, [map, days, selectedDay, highlightedActivityId]);

  return (
    <div className="relative w-full h-[500px] rounded-lg overflow-hidden shadow-lg">
      <div ref={mapRef} className="w-full h-full" />
      
      {/* Day Filter Controls */}
      <div className="absolute top-4 left-4 bg-white rounded-lg shadow-md p-2">
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedDay(null)}
            className={`px-3 py-1 rounded ${selectedDay === null ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}
          >
            All Days
          </button>
          {days.map((day, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedDay(idx)}
              className={`px-3 py-1 rounded ${selectedDay === idx ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}
              style={{ borderLeft: `4px solid ${DAY_COLORS[idx]}` }}
            >
              Day {idx + 1}
            </button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-md p-3">
        <div className="text-sm font-semibold mb-2">Categories</div>
        <div className="grid grid-cols-2 gap-1 text-xs">
          {Object.entries(CATEGORY_COLORS).slice(0, -1).map(([cat, color]) => (
            <div key={cat} className="flex items-center gap-1">
              <span 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: color }}
              />
              {cat.replace('_', ' ')}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Info window content generator
function createInfoWindowContent(activity: Activity): string {
  return `
    <div class="p-2 max-w-xs">
      <h3 class="font-bold text-lg">${activity.place.name}</h3>
      <p class="text-gray-600 text-sm">${activity.place.category}</p>
      <div class="mt-2 text-sm">
        <div>🕐 ${activity.time_start} - ${activity.time_end}</div>
        <div>⏱️ ${activity.duration_minutes} minutes</div>
        ${activity.place.rating ? `<div>⭐ ${activity.place.rating}</div>` : ''}
      </div>
      ${activity.notes ? `<p class="mt-2 text-sm italic">"${activity.notes}"</p>` : ''}
    </div>
  `;
}

// Custom map styles (optional - cleaner look)
const MAP_STYLES: google.maps.MapTypeStyle[] = [
  {
    featureType: 'poi',
    elementType: 'labels',
    stylers: [{ visibility: 'off' }], // Hide default POI labels
  },
  {
    featureType: 'transit',
    stylers: [{ visibility: 'simplified' }],
  },
];
```

### Map + Itinerary Sync

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BIDIRECTIONAL SYNC                                  │
└─────────────────────────────────────────────────────────────────────────────┘

           MAP                                    ITINERARY LIST
    ┌──────────────┐                         ┌──────────────────────┐
    │              │   Click Marker          │                      │
    │   📍 ──────────────────────────────────►  Activity Card       │
    │     Louvre   │                         │  [Highlighted]       │
    │              │                         │                      │
    │              │   Click Card            │                      │
    │   📍 ◄──────────────────────────────────  Activity Card       │
    │   [Bouncing] │                         │     Louvre           │
    │              │                         │                      │
    └──────────────┘                         └──────────────────────┘

Implementation:
- Parent component holds `selectedActivityId` state
- MapView receives it as `highlightedActivityId` prop
- ItineraryList receives it as `selectedId` prop
- Both components call `onActivitySelect` when user interacts
```

### Mobile-Responsive Layout

```
DESKTOP (side-by-side):
┌────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │                     │  │                                 │  │
│  │    ITINERARY        │  │           MAP                   │  │
│  │    LIST             │  │                                 │  │
│  │                     │  │                                 │  │
│  │    Day 1            │  │      📍──────📍                 │  │
│  │    - Louvre         │  │        \    /                   │  │
│  │    - Cafe           │  │         📍──                    │  │
│  │    - Orsay          │  │                                 │  │
│  │                     │  │                                 │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
│        40%                           60%                       │
└────────────────────────────────────────────────────────────────┘

MOBILE (stacked with toggle):
┌────────────────────────────┐
│  [List View] [Map View]    │  ← Toggle tabs
├────────────────────────────┤
│                            │
│    (shows selected view)   │
│                            │
│                            │
│                            │
│                            │
└────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Backend Foundation (Days 1-2)
```
□ backend-setup      → FastAPI project, dependencies, folder structure
□ env-config         → Environment variables, config loading
□ itinerary-model    → Pydantic models for all data structures
```

### Phase 2: External Service Integration (Days 3-4)
```
□ google-places-service  → Geocoding, place search, details
□ google-routes-service  → Route computation
□ azure-openai-service   → Chat completion, prompt handling
```

### Phase 3: Core Logic (Days 5-6)
```
□ prompt-engineering     → System prompt, user prompt templates
□ itinerary-generator    → Orchestration service
□ itinerary-endpoint     → POST /api/itinerary router
```

### Phase 4: Frontend (Days 7-9)
```
□ frontend-setup         → Vite + React + TypeScript + Tailwind
□ api-client            → Typed API client
□ input-form            → Trip input form components
□ itinerary-display     → Day/activity cards
□ map-integration       → Google Maps with markers/routes
```

### Phase 5: Polish (Day 10)
```
□ error-handling        → User-friendly error messages
□ loading-states        → Skeletons, spinners
□ integration-testing   → End-to-end tests
```

---

## File Structure

```
travel-companion/
├── ARCHITECTURE.md              # This file
├── README.md                    # Project overview & setup instructions
├── .gitignore
├── docker-compose.yml           # Local development setup
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app initialization
│   │   ├── config.py            # Environment & settings
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── itinerary.py     # Pydantic models
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── azure_openai.py  # Azure OpenAI integration
│   │   │   ├── google_places.py # Google Places API
│   │   │   ├── google_routes.py # Google Routes API
│   │   │   └── itinerary_generator.py  # Orchestration
│   │   │
│   │   └── routers/
│   │       ├── __init__.py
│   │       └── itinerary.py     # /api/itinerary endpoint
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_itinerary.py
│   │   └── conftest.py
│   │
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   │
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── TripInputForm/
│   │   │   │   ├── index.tsx
│   │   │   │   ├── DestinationInput.tsx
│   │   │   │   ├── DateRangePicker.tsx
│   │   │   │   ├── InterestSelector.tsx
│   │   │   │   └── PaceSelector.tsx
│   │   │   ├── ItineraryView/
│   │   │   │   ├── index.tsx
│   │   │   │   ├── DaySelector.tsx
│   │   │   │   ├── DayCard.tsx
│   │   │   │   ├── ActivityCard.tsx
│   │   │   │   └── RouteConnector.tsx
│   │   │   └── MapView/
│   │   │       └── index.tsx
│   │   │
│   │   ├── services/
│   │   │   └── api.ts           # Backend API client
│   │   │
│   │   ├── types/
│   │   │   └── itinerary.ts     # TypeScript interfaces
│   │   │
│   │   └── hooks/
│   │       └── useItinerary.ts
│   │
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
└── docs/
    ├── api.md                   # API documentation
    └── deployment.md            # Deployment guide
```

---

## Environment Variables

### Backend (.env)
```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Google APIs
GOOGLE_PLACES_API_KEY=your-places-api-key
GOOGLE_ROUTES_API_KEY=your-routes-api-key

# App Config
APP_ENV=development
DEBUG=true
CORS_ORIGINS=http://localhost:5173
```

### Frontend (.env)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_MAPS_API_KEY=your-maps-api-key
```

---

## Next Steps

1. **Review this plan** - Any changes to architecture or scope?
2. **Set up API keys** - Ensure Azure OpenAI and Google APIs are ready
3. **Start implementation** - Begin with Phase 1 (Backend Foundation)

Ready to proceed? Say "start building" to begin implementation!
