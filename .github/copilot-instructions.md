# Travel Companion - AI Agent Guidelines

## Architecture

Hybrid AI + deterministic approach: LLMs (Azure OpenAI) handle creative decisions (place selection, theming), while Google APIs provide real-time data (routes, hours, locations).

**Two generation modes:**
- **FAST**: Single-pass AI planning + route optimization (~15-30s) - [generator.py](../backend/app/generators/day_plan/fast/generator.py)
- **JOURNEY (V6)**: Multi-city trip planning with Scout → Enrich → Review → Planner loop (~2-5min) - [journey_plan/v6/](../backend/app/generators/journey_plan/v6/)

**Service flow**: `routers/` → `generators/{day_plan,journey_plan,tips}/` → `services/{external,internal}/`

### Folder Structure

```
backend/app/
├── config/                   # Settings & tuning
│   ├── settings.py           # Environment config (Pydantic Settings)
│   ├── tuning.py             # Tunable params (frozen dataclasses)
│   ├── planning.py           # Pace configs, duration estimates
│   └── regional_transport.py # Transport intelligence by region
├── core/
│   ├── clients/              # HTTP & OpenAI client pools
│   │   ├── http.py           # Shared httpx.AsyncClient
│   │   └── openai.py         # OpenAIClient singleton
│   └── middleware/           # Request tracing, logging
├── prompts/                  # CENTRALIZED prompt templates (.md files)
│   ├── loader.py             # PromptLoader class, cached loading
│   ├── journey/              # Scout, reviewer, planner prompts
│   ├── day_plan/             # Planning, validation prompts
│   └── tips/                 # Tips generation prompts
├── generators/
│   ├── journey_plan/         # Multi-city trip planning
│   │   ├── request.py        # JourneyRequest model
│   │   └── v6/               # V6 LLM-first approach
│   │       ├── orchestrator.py, scout.py, enricher.py, reviewer.py, planner.py
│   │       ├── day_plan_generator.py
│   │       └── models.py
│   ├── day_plan/             # Single-city itinerary
│   │   ├── fast/             # Single-pass mode
│   │   │   ├── generator.py, ai_service.py
│   │   │   └── prompts/      # Delegates to app/prompts/
│   │   └── quality/          # Day-plan quality evaluation
│   │       ├── scorer.py
│   │       └── evaluators/   # 7 metric evaluators
│   └── tips/                 # Activity tips generation
│       ├── generator.py
│       └── prompts/          # Delegates to app/prompts/
├── models/                   # Shared data models
├── routers/                  # API endpoints
├── services/
│   ├── external/             # API wrappers
│   │   ├── azure_openai.py   # AzureOpenAIService (chat_completion, chat_completion_json)
│   │   ├── google_places.py  # GooglePlacesService
│   │   └── google_routes.py  # GoogleRoutesService
│   └── internal/             # Algorithms (optimizer, scheduler)
└── utils/                    # Shared utilities
backend/tests/                # All tests
```

### Journey Planning (V6 Multi-City)
LLM-first approach with iterative refinement:
1. **Scout**: LLM suggests cities based on region and interests
2. **Enricher**: Google APIs add real coordinates & travel times
3. **Reviewer**: LLM evaluates plan quality
4. **Planner**: LLM fixes issues identified by Reviewer
5. **V6DayPlanGenerator**: Uses FastItineraryGenerator for detailed day plans

Key files:
- Models: [v6/models.py](../backend/app/generators/journey_plan/v6/models.py)
- Orchestrator: [v6/orchestrator.py](../backend/app/generators/journey_plan/v6/orchestrator.py)
- Day Plans: [v6/day_plan_generator.py](../backend/app/generators/journey_plan/v6/day_plan_generator.py)
- API: [routers/journey.py](../backend/app/routers/journey.py)

## Code Style

### Python (Backend)
- **Types**: Use generic type hints (`list[str]`, `Optional[dict]`), `TYPE_CHECKING` for circular imports
- **Docstrings**: Google-style with Args/Returns sections
- **Async**: All LLM/API calls are `async`, use `httpx.AsyncClient`
- Exemplars: [v6/orchestrator.py](../backend/app/generators/journey_plan/v6/orchestrator.py), [itinerary.py](../backend/app/models/itinerary.py)

### TypeScript (Frontend)
- Functional components with hooks, props interfaces inline
- Union types for enums: `type Pace = 'relaxed' | 'moderate' | 'packed'`
- Exemplar: [JourneyInputForm.tsx](../frontend/src/components/JourneyInputForm.tsx)

## Build and Test

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest                    # Run tests
pytest --cov             # With coverage

# Frontend
cd frontend && npm install
npm run dev              # Vite dev server
npm run build && npm run lint
```

## Project Conventions

### Prompt Templates
All prompts are centralized in `app/prompts/` as .md files:
- **Journey**: `prompts/journey/` (scout_system.md, scout_user.md, reviewer_*.md, planner_*.md)
- **Day Plan**: `prompts/day_plan/` (planning_*.md, validation_*.md)
- **Tips**: `prompts/tips/` (tips_system.md, tips_user.md)

Load prompts using the PromptLoader:
```python
from app.prompts.loader import journey_prompts, day_plan_prompts, tips_prompts

system = journey_prompts.load("scout_system")
system, user = day_plan_prompts.load_pair("planning")  # loads planning_system.md, planning_user.md
```

### OpenAI Service
Use centralized `AzureOpenAIService` for all LLM calls:
```python
from app.services.external import AzureOpenAIService

service = AzureOpenAIService()

# For JSON responses
data = await service.chat_completion_json(system_prompt, user_prompt)

# For text responses
text = await service.chat_completion(system_prompt, user_prompt)
```

### Regional Transport Intelligence
Transport recommendations by region are in `config/regional_transport.py`:
```python
from app.config.regional_transport import get_transport_guidance, detect_region

guidance = get_transport_guidance("Mumbai", "India", user_prefs)
region = detect_region("Tokyo", "Japan")  # returns "japan"
```

### Quality Evaluators
Add new metrics by extending `BaseEvaluator` ([base.py](../backend/app/generators/day_plan/quality/evaluators/base.py)):
- Define `name`, `weight`, and `evaluate()` returning `MetricResult`
- Register in [scorer.py](../backend/app/generators/day_plan/quality/scorer.py)

### Configuration
- **Environment**: `config/settings.py` (Pydantic Settings)
- **Tunable params**: `config/tuning.py` (frozen dataclasses)
- **Planning constants**: `config/planning.py` (pace configs, duration estimates)
- **Regional transport**: `config/regional_transport.py` (transport profiles by region)

## Integration Points

| Service | Purpose | Config |
|---------|---------|--------|
| Azure OpenAI | LLM calls (GPT-4o) | `AZURE_OPENAI_*` env vars |
| Google Places API | Place discovery | `GOOGLE_PLACES_API_KEY` |
| Google Routes API | Travel times | `GOOGLE_ROUTES_API_KEY` |

API clients in `backend/app/core/clients/` use `httpx.AsyncClient` with retry/timeout patterns.

Frontend streams progress via **SSE**:
- Single city: `POST /api/itinerary/stream`
- Multi-city journey: `POST /api/journey/plan/stream`
- Journey day plans: `POST /api/journey/days/stream`

See [api.ts](../frontend/src/services/api.ts) for client implementation.
