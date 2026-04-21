# Web Search Grounding Layer — Design Document

**Date:** 2026-03-18
**Status:** Approved
**Scope:** Provider-agnostic web search grounding across all LLM-powered agents

## Problem

LLM agents in the pipeline rely on parametric memory for factual claims — accommodation pricing, transport feasibility, activity status, seasonal conditions. This causes:

- **Hallucinated prices** (e.g., $170/night for hotels that cost $80 or $400)
- **Defunct/renamed attractions** suggested as must-sees
- **Impossible transport connections** (e.g., direct trains that don't exist)
- **Outdated seasonal info** (closures, renovations, events)

These errors are the primary driver of low quality scores, especially on multi-country trips (SE Asia: 62-70 vs Japan: ~75).

## Solution

Add web search grounding to all 9 LLM-powered agents via each provider's native search tool. The LLM can search the web mid-generation to verify and ground its claims in real-time data.

## Architecture

### New LLM Abstraction Methods

Two new methods on `LLMService` base class with default fallback (non-breaking):

```python
class SearchCitation(BaseModel):
    """Normalized citation from any provider's web search."""
    url: str
    title: str
    cited_text: str = ""

class LLMService(ABC):
    # ... existing methods ...

    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list[SearchCitation]]:
        """Generate text with web search grounding.
        Default: falls back to generate() with empty citations.
        """
        text = await self.generate(system_prompt, user_prompt, max_tokens, temperature)
        return (text, [])

    async def generate_structured_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> tuple[T, list[SearchCitation]]:
        """Generate structured output with web search grounding.
        Default: falls back to generate_structured() with empty citations.
        """
        result = await self.generate_structured(
            system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
        )
        return (result, [])
```

Default implementations ensure zero breakage — any provider that hasn't implemented search yet still works.

### Provider Implementations

#### Gemini (simplest)

Add `google_search` tool to existing `generateContent` call:

```python
config = types.GenerateContentConfig(
    tools=[types.Tool(google_search=types.GoogleSearch())],
    response_mime_type="application/json",
    response_json_schema=schema.model_json_schema(),
    # ... existing params
)
```

Extract citations from `response.candidates[0].grounding_metadata.grounding_chunks`:

```python
citations = [
    SearchCitation(url=chunk.web.uri, title=chunk.web.title)
    for chunk in grounding_metadata.grounding_chunks
]
```

Gemini supports `google_search` tool alongside `response_json_schema` — both in the same call.

#### Anthropic (straightforward)

Add `web_search` server tool alongside existing `submit` tool:

```python
tools = [
    {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 3,
    },
    {
        "name": "submit",
        "description": "Submit structured response",
        "input_schema": schema.model_json_schema(),
    },
]
```

`web_search` is a **server tool** — auto-executed by the API, independent of `tool_choice`. The existing `tool_choice={"type": "tool", "name": "submit"}` still forces Claude to output structured data via the submit tool. Server tools operate in a separate layer.

Extract citations from `text` content blocks with `citations` field:

```python
for block in response.content:
    if hasattr(block, 'citations') and block.citations:
        for citation in block.citations:
            citations.append(SearchCitation(
                url=citation.url,
                title=citation.title,
                cited_text=citation.cited_text or "",
            ))
```

#### Azure OpenAI (Responses API for search calls)

Search-grounded calls use the Responses API (`client.responses.create()`) instead of Chat Completions. Same Azure resource, same API key, different endpoint.

```python
response = await self.client.responses.create(
    model=self.deployment,
    tools=[{"type": "web_search"}],
    input=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    text={"format": {"type": "json_schema", "schema": schema.model_json_schema()}},
    max_output_tokens=max_tokens,
    temperature=temperature,
)
```

Extract citations from `url_citation` annotations:

```python
for annotation in message.content[0].annotations:
    if annotation.type == "url_citation":
        citations.append(SearchCitation(
            url=annotation.url_citation.url,
            title=annotation.url_citation.title,
        ))
```

Non-search calls stay on Chat Completions — no change to existing `generate()` / `generate_structured()`.

Reasoning model handling (o1/o3/gpt-5): same parameter adjustments apply on Responses API (omit temperature, use `max_output_tokens`).

## Integration Points (All 9 Agents)

| Agent/Service | Method | What Search Grounds |
|---|---|---|
| **Scout** | `generate_structured_with_search` | Hotel pricing, transport feasibility, visa/border info, seasonal conditions |
| **Must-See Icons** | `generate_structured_with_search` | Verify attractions exist and are currently accessible |
| **Reviewer** | `generate_structured_with_search` | Fact-check claims in the plan (hotel exists? route real?) |
| **Planner** | `generate_structured_with_search` | Fix reviewer issues with real data instead of re-hallucinating |
| **Day Scout** | `generate_structured_with_search` | Activity pricing, seasonal closures, event timing |
| **Day Reviewer** | `generate_structured_with_search` | Verify activity feasibility, duration accuracy |
| **Day Fixer** | `generate_structured_with_search` | Find real replacement activities |
| **Tips Service** | `generate_with_search` | Current ticket prices, opening hours, practical tips |
| **Chat Service** | `generate_structured_with_search` | Answer user questions with current data |

**Not grounded:** Enricher (already fully API-driven via Google Places/Routes/Directions).

## Configuration

New constant in `planning.py` (follows `ROUTE_COMPUTATION_MODE` pattern):

```python
# Web search grounding mode — controls which agents use search-grounded LLM calls
SEARCH_GROUNDING_MODE: str = "full"
# "full"       — all 9 agents get search grounding (~20-30 searches/trip)
# "selective"  — Scout + Day Scout + Tips + Chat only (~8-12 searches/trip)
# "none"       — disabled, identical behavior to today
```

Agent-side usage pattern:

```python
from app.config.planning import SEARCH_GROUNDING_MODE, should_use_search_grounding

# Helper function in planning.py:
def should_use_search_grounding(agent_tier: str = "full") -> bool:
    """Check if search grounding is enabled for the given agent tier.
    agent_tier: "full" (all agents) or "selective" (high-value agents only)
    """
    if SEARCH_GROUNDING_MODE == "none":
        return False
    if SEARCH_GROUNDING_MODE == "selective":
        return agent_tier == "selective"
    return True  # "full" mode

# In agent code:
if should_use_search_grounding("selective"):  # Scout, Day Scout, Tips, Chat
    plan, citations = await self.llm.generate_structured_with_search(...)
else:
    plan = await self.llm.generate_structured(...)
```

Selective tier agents: Scout, Day Scout, Tips, Chat (highest factual accuracy impact).
Full tier agents: Reviewer, Planner, Day Reviewer, Day Fixer, Must-See Icons.

## Fallback Behavior

If search fails at any point:
- Provider implementation catches the error and falls back to regular `generate()` / `generate_structured()`
- Logs a warning: `[LLM] Search grounding failed, falling back to standard generation: {error}`
- Returns empty citations list
- Pipeline continues normally — search grounding is an enhancement, never a blocker

## Cost Impact

Per-trip estimates (10-day, 3-city trip):

| Mode | Searches/Trip | Anthropic ($10/1K) | Azure ($14/1K) | Gemini 2.5 ($35/1K) |
|---|---|---|---|---|
| `full` | ~20-30 | +$0.20-0.30 | +$0.28-0.42 | +$0.70-1.05 |
| `selective` | ~8-12 | +$0.08-0.12 | +$0.11-0.17 | +$0.28-0.42 |
| `none` | 0 | $0 | $0 | $0 |

Current trip costs: Anthropic ~$3.30, Azure ~$6.70, Gemini ~$2.50. Full search grounding adds 4-28% depending on provider.

**Latency impact:** ~1-2s added per search-grounded call (search round-trip). For pipeline agents (Scout, Reviewer), this is absorbed into existing 5-15s generation time. For user-facing calls (Chat, Tips), it's noticeable but acceptable.

## Environment Variables

No new environment variables required. All 3 providers use search tools built into their existing APIs:
- Gemini: `google_search` tool via existing `GEMINI_API_KEY`
- Anthropic: `web_search` server tool via existing `ANTHROPIC_API_KEY`
- Azure: Responses API `web_search` via existing `AZURE_OPENAI_*` credentials

## Files Changed

### Core LLM Layer (4 files)
| File | Change |
|---|---|
| `app/services/llm/base.py` | Add `SearchCitation` model, 2 new methods with default fallback |
| `app/services/llm/gemini.py` | Implement `generate_with_search`, `generate_structured_with_search` using `google_search` tool |
| `app/services/llm/anthropic.py` | Implement both methods using `web_search_20250305` server tool |
| `app/services/llm/azure_openai.py` | Implement both methods using Responses API `web_search` tool |

### Configuration (1 file)
| File | Change |
|---|---|
| `app/config/planning.py` | Add `SEARCH_GROUNDING_MODE`, `should_use_search_grounding()` helper |

### Agents (7 files)
| File | Change |
|---|---|
| `app/agents/scout.py` | Use `generate_structured_with_search` (selective tier) |
| `app/agents/reviewer.py` | Use `generate_structured_with_search` (full tier) |
| `app/agents/planner.py` | Use `generate_structured_with_search` (full tier) |
| `app/agents/day_scout.py` | Use `generate_structured_with_search` (selective tier) |
| `app/agents/day_reviewer.py` | Use `generate_structured_with_search` (full tier) |
| `app/agents/day_fixer.py` | Use `generate_structured_with_search` (full tier) |
| `app/orchestrators/journey.py` | Use `generate_structured_with_search` for must-see call (full tier) |

### Services (2 files)
| File | Change |
|---|---|
| `app/services/tips.py` | Use `generate_with_search` (selective tier) |
| `app/services/chat.py` | Use `generate_structured_with_search` (selective tier) |

### Tests (2 files)
| File | Change |
|---|---|
| `tests/test_agents.py` | Tests for search-grounded agent calls, mock search results |
| `tests/test_services.py` | Tests for search-grounded Tips/Chat |

**Total: ~16 files, estimated effort ~4-5 days.**

## Implementation Order

1. **LLM base + config** — `SearchCitation` model, abstract methods with default fallbacks, `SEARCH_GROUNDING_MODE`
2. **Gemini provider** — simplest implementation, good for validating the pattern
3. **Anthropic provider** — server tool alongside existing submit tool
4. **Azure provider** — Responses API path for search calls
5. **Selective-tier agents** — Scout, Day Scout, Tips, Chat (highest impact)
6. **Full-tier agents** — Reviewer, Planner, Day Reviewer, Day Fixer, Must-See Icons
7. **Tests** — mock search results per provider, verify fallback behavior
8. **Integration test** — run a real trip with `SEARCH_GROUNDING_MODE=full`, compare scores

## Verification

1. `pytest -v` — all existing tests pass (default fallback means zero regression)
2. `SEARCH_GROUNDING_MODE=none` — identical behavior to today
3. `SEARCH_GROUNDING_MODE=selective` — Scout, Day Scout, Tips, Chat use search
4. `SEARCH_GROUNDING_MODE=full` — all 9 agents use search
5. Run Japan trip with `full` mode — verify citations in logs, compare score to baseline (~75)
6. Run SE Asia trip with `full` mode — verify score improvement over baseline (~62-70)
7. Test each provider individually to verify search integration works
