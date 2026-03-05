# LLM Output Validation Design

## Problem

LLM responses are not validated after generation. `generate_structured()` returns raw `dict[str, Any]` — no schema validation, no completeness checks. Agents manually parse with `.get()` and silently accept incomplete data. Users can receive plans with 0 cities, empty days, or hallucinated destinations without any error.

## Decision: Fail Hard

When LLM output fails validation after retries, the pipeline raises an error. Users see "Planning failed — please try again" rather than receiving a degraded plan.

## Approach: Centralized Validation at LLM Service Layer

### 1. LLM Service Layer

**Return type changes from `dict[str, Any]` to `T` (validated Pydantic model).**

`base.py`:
```python
T = TypeVar("T", bound=BaseModel)

async def generate_structured(
    self,
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
    max_tokens: int = 8000,
    temperature: float = 0.7,
    max_retries: int = 2,
) -> T:  # returns validated model
```

Each provider (Azure OpenAI, Anthropic, Gemini):
1. Gets raw dict via JSON parse (existing logic)
2. Calls `schema.model_validate(raw_dict)`
3. On `ValidationError`, retries LLM call up to `max_retries` times
4. After exhausting retries, raises `LLMValidationError`

New exception in `app/services/llm/exceptions.py`:
```python
class LLMValidationError(Exception):
    """LLM response failed schema validation after retries."""
    def __init__(self, schema_name: str, errors: list[str], attempts: int): ...
```

### 2. Agent Simplification

Agents drop manual `_parse_plan()` dict-parsing methods. They receive validated Pydantic models directly and add only semantic validation.

**Scout Agent** — semantic checks after receiving `JourneyPlan`:
- `cities` non-empty
- Every city has a non-empty `name`
- `len(travel_legs) == len(cities) - 1` when cities > 1
- Raises `LLMValidationError` on failure

**Planner Agent** — no fallback to original plan on bad data:
- Receives validated `JourneyPlan` from LLM
- Same semantic checks as Scout
- On failure → `LLMValidationError` (not silent return of original)

**Day Planner Agent** — semantic checks after receiving `AIPlan`:
- `day_groups` non-empty
- Every day group has at least one `place_id`
- Orphan place IDs (not in candidates) are cleaned silently (not a hard error)
- Raises `LLMValidationError` on structural failures

**Reviewer Agent** — minimal change:
- Receives `ReviewResult` directly (no dict parsing)
- Score already bounded 0-100 by model validators

### 3. Error Propagation

**Journey Orchestrator**: `LLMValidationError` caught by existing top-level handler → yields `phase="error"` with user-friendly message.

**Day Plan Orchestrator**: per-city `try/except` block catches `LLMValidationError` → skips that city, continues with others. Partial results (3 of 4 cities) are still useful.

### 4. Test Coverage

**Agent tests** (`test_agents.py`):
- Scout: empty cities, missing city name, travel leg count mismatch, invalid enum
- Planner: no fallback on bad data (raises instead)
- Reviewer: missing score field
- Day Planner: empty day_groups, empty place_ids per day, orphan ID cleanup

**LLM service tests** (new `test_llm_validation.py`):
- `generate_structured` returns validated Pydantic model
- Retries on `ValidationError`, succeeds on 2nd attempt
- Raises `LLMValidationError` after exhausting retries

## Files Changed

| File | Change |
|------|--------|
| `app/services/llm/exceptions.py` | New — `LLMValidationError` |
| `app/services/llm/base.py` | Return type `dict → T`, add `max_retries` param |
| `app/services/llm/azure_openai.py` | Add `model_validate()` + retry loop |
| `app/services/llm/anthropic.py` | Add `model_validate()` + retry loop |
| `app/services/llm/gemini.py` | Add `model_validate()` + retry loop |
| `app/agents/scout.py` | Drop `_parse_plan()`, add `_validate_plan()` |
| `app/agents/planner.py` | Drop `_parse_plan()`, add `_validate_plan()`, remove fallback |
| `app/agents/reviewer.py` | Drop `_parse_result()`, use model directly |
| `app/agents/day_planner.py` | Simplify `_parse_plan()`, add `_validate_ai_plan()` |
| `app/services/chat.py` | Update calls to `generate_structured` (receives model) |
| `app/services/tips.py` | Update calls to `generate_structured` (receives model) |
| `tests/test_agents.py` | Add malformed-response tests |
| `tests/test_llm_validation.py` | New — LLM service validation tests |
| `tests/conftest.py` | Update `MockLLMService` to return models |
