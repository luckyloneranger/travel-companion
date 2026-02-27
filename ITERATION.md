# Iteration Log

## V0.1 — Initial Release

**Status:** Complete

### What's Working

**Multi-City Journey Planning (V6 Architecture)**
- Region or specific destination input with origin city
- AI-driven city selection via Scout agent (Azure OpenAI GPT-4o)
- Google APIs enrichment for real transport times, coordinates, and distances
- Iterative quality refinement: Scout → Enrich → Review → Planner loop (up to 3 iterations, min score 70)
- Multi-modal transport: flight, bus, train, ferry, car
- SSE streaming with real-time progress updates
- Day plan generation for each city stop
- Natural language chat editing for both journey structure and day plans

**Single-City Itinerary (FAST Mode)**
- Single-pass generation in ~15-30s
- Google Places discovery for real venue data (ratings, hours, photos)
- LLM-driven place selection and theming
- TSP-based route optimization to minimize backtracking
- Time-slotted schedule builder with conflict validation
- 7-metric quality scoring (meal timing, geographic efficiency, travel efficiency, variety, opening hours, theme alignment, duration balance)

**Frontend**
- Dual-mode UI: toggle between Journey and Itinerary planning
- Journey phase flow: input → planning → preview → day-plans
- Real-time SSE progress display with phase tracking
- Journey visualization: city cards, travel leg cards, route arrows
- Itinerary visualization: day cards with activity timelines
- Chat interface for editing plans via natural language
- Side panel UX for day plan generation
- Tailwind CSS styling with glass-morphism cards and gradient backgrounds
- Cancellation support via AbortController

**Backend**
- FastAPI with async throughout (httpx.AsyncClient)
- Service registry for lazy singleton clients
- Centralized prompt templates (Markdown files)
- Pydantic v2 models with validation
- Backend pytest suite (model validation, quality scoring, integration tests)

### Known Limitations

- No frontend state persistence — plans are lost on page reload
- Budget field exists in models but is not deeply integrated into generation logic
- Limited error recovery if external APIs (Google, Azure) fail mid-generation
- No frontend tests
- Chat editing capabilities are functional but basic — limited to single-turn regeneration
- Destination type constraints (e.g., "islands only") are supported but not exhaustive
