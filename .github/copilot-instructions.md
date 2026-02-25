# Travel Companion - AI Agent Guidelines

## Architecture

Hybrid AI + deterministic approach: LLMs (Azure OpenAI) handle creative decisions, Google APIs provide real-time data.

**Two generation modes:**
- **FAST**: Single-pass AI + route optimization (~15-30s) - [fast/generator.py](../backend/app/generators/day_plan/fast/generator.py)
- **JOURNEY (V6)**: Multi-city with Scout → Enrich → Review → Planner loop (~2-5min) - [v6/orchestrator.py](../backend/app/generators/journey_plan/v6/orchestrator.py)

**Service flow**: `routers/` → `generators/` → `services/{external,internal}/`

**Key directories:**
- `config/` - Settings (`settings.py`), tunable params (`tuning.py`), planning constants (`planning.py`)
- `prompts/` - Centralized .md templates loaded via `PromptLoader`
- `core/` - Singleton clients (`clients/`), request tracing middleware
- `services/external/` - API wrappers (Azure OpenAI, Google Places/Routes/Directions)

## Code Style

### Python
- **Types**: Generic hints (`list[str]`), `Optional[T]`, `TYPE_CHECKING` for circular imports
- **Docstrings**: Google-style with Args/Returns
- **Async**: All LLM/API calls `async` with `httpx.AsyncClient`
- **Enums**: `class Pace(str, Enum)` for JSON serialization

### Pydantic Models ([models/itinerary.py](../backend/app/models/itinerary.py))
```python
class Request(BaseModel):
    field: str = Field(..., min_length=2, max_length=200)
    optional_field: Optional[str] = None
    id: str = Field(default_factory=lambda: str(uuid4()))

    @field_validator("end_date")
    @classmethod
    def validate(cls, v, info):
        if invalid: raise ValueError("message")
        return v
```

### TypeScript
- Functional components with hooks, inline props interfaces
- Union types: `type Pace = 'relaxed' | 'moderate' | 'packed'`

## Build and Test

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest                    # Run all tests
pytest --cov             # With coverage

# Frontend
cd frontend && npm install
npm run dev              # Vite dev server (port 5173)
npm run build && npm run lint
```

### Testing Patterns ([tests/conftest.py](../backend/tests/conftest.py))
```python
@pytest.fixture
def client():
    return TestClient(app)

# Validation tests
with pytest.raises(ValueError, match="end_date must be after"):
    ItineraryRequest(...)
```

## Project Conventions

### Service Registry ([core/registry.py](../backend/app/core/registry.py))
```python
from app.core import services

places = services.get_places()   # Lazy singleton
routes = services.get_routes()
await services.close_all()       # Cleanup
```

### Prompt Templates ([prompts/loader.py](../backend/app/prompts/loader.py))
```python
from app.prompts.loader import journey_prompts, day_plan_prompts

system = journey_prompts.load("scout_system")
user = day_plan_prompts.load("planning_user")
```

### LLM Calls ([services/external/azure_openai.py](../backend/app/services/external/azure_openai.py))
```python
from app.services.external import AzureOpenAIService

service = AzureOpenAIService()
data = await service.chat_completion_json(system, user)  # JSON response
```

### Error Handling
```python
# Routers: HTTPException with logging
try:
    result = await generator.generate(request)
except Exception as e:
    logger.error(f"Failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Generation failed")

# Services: Plain exceptions
if response.status_code != 200:
    raise Exception(f"API failed: {response.status_code}")
```

### SSE Streaming ([routers/itinerary.py](../backend/app/routers/itinerary.py))
Events: `progress` (phase/message/progress), `complete` (result), `error` (message)
```python
yield f"data: {json.dumps({'type': 'progress', 'phase': 'planning', 'progress': 50})}\n\n"
yield f"data: {json.dumps({'type': 'complete', 'result': result.model_dump(mode='json')})}\n\n"
```

### Configuration
```python
from app.config import get_settings
from app.config.tuning import FAST_MODE

settings = get_settings()  # lru_cached singleton
temperature = FAST_MODE.planning_temperature
```

## Environment Variables

Required in `.env`:
```
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4
GOOGLE_PLACES_API_KEY=...
GOOGLE_ROUTES_API_KEY=...
```

Frontend: `VITE_API_BASE_URL` (defaults to `http://localhost:8000`)

## Integration Points

| Service | Purpose | Client |
|---------|---------|--------|
| Azure OpenAI | LLM (GPT-4o) | [azure_openai.py](../backend/app/services/external/azure_openai.py) |
| Google Places | Place discovery | [google_places.py](../backend/app/services/external/google_places.py) |
| Google Routes | Driving/walking times | [google_routes.py](../backend/app/services/external/google_routes.py) |
| Google Directions | Transit & ferry routes | [google_directions.py](../backend/app/services/external/google_directions.py) |

**SSE Endpoints:**
- `POST /api/itinerary/stream` - Single city
- `POST /api/journey/v6/plan/stream` - Multi-city journey
- `POST /api/journey/v6/days/stream` - Journey day plans

Frontend SSE consumption: [api.ts](../frontend/src/services/api.ts) (AsyncGenerator pattern with AbortController)
