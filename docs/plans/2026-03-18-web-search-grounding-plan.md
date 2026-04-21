# Web Search Grounding Layer — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add provider-agnostic web search grounding to all 9 LLM-powered agents, reducing hallucinations and improving plan quality scores.

**Architecture:** Two new methods on `LLMService` base class (`generate_with_search`, `generate_structured_with_search`) with default fallbacks. Each provider (Gemini, Anthropic, Azure) implements using native search tools. A `SEARCH_GROUNDING_MODE` config controls which agents use grounding. Agents check this config and call `_with_search` variants when enabled.

**Tech Stack:** google-genai SDK (Gemini `google_search` tool), anthropic SDK (`web_search_20250305` server tool), openai SDK (Responses API `web_search` tool), Pydantic v2 for `SearchCitation` model.

**Design doc:** `docs/plans/2026-03-18-web-search-grounding-design.md`

---

### Task 1: SearchCitation Model + Base Class Methods

**Files:**
- Modify: `backend/app/services/llm/base.py:1-50`
- Test: `backend/tests/test_agents.py` (add `TestSearchGrounding` class)

**Step 1: Write the failing test**

In `backend/tests/test_agents.py`, add at the bottom:

```python
class TestSearchGrounding:
    """Tests for web search grounding base class defaults."""

    @pytest.mark.asyncio
    async def test_generate_with_search_default_fallback(self):
        """Default implementation falls back to generate() with empty citations."""
        from tests.conftest import MockLLMService
        llm = MockLLMService()
        text, citations = await llm.generate_with_search(
            system_prompt="test", user_prompt="test"
        )
        assert isinstance(text, str)
        assert citations == []

    @pytest.mark.asyncio
    async def test_generate_structured_with_search_default_fallback(self):
        """Default implementation falls back to generate_structured() with empty citations."""
        from pydantic import BaseModel
        from tests.conftest import MockLLMService

        class SimpleSchema(BaseModel):
            message: str = "default"

        llm = MockLLMService()
        result, citations = await llm.generate_structured_with_search(
            system_prompt="test", user_prompt="test", schema=SimpleSchema
        )
        assert isinstance(result, SimpleSchema)
        assert citations == []

    def test_search_citation_model(self):
        """SearchCitation model validates correctly."""
        from app.services.llm.base import SearchCitation
        citation = SearchCitation(url="https://example.com", title="Example", cited_text="some text")
        assert citation.url == "https://example.com"
        assert citation.title == "Example"
        assert citation.cited_text == "some text"

    def test_search_citation_minimal(self):
        """SearchCitation works with just url and title."""
        from app.services.llm.base import SearchCitation
        citation = SearchCitation(url="https://example.com", title="Example")
        assert citation.cited_text == ""
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_agents.py::TestSearchGrounding -v
```
Expected: FAIL — `SearchCitation` doesn't exist, `generate_with_search` doesn't exist.

**Step 3: Write the implementation**

Replace `backend/app/services/llm/base.py` entirely:

```python
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class SearchCitation(BaseModel):
    """Normalized citation from any provider's web search."""
    url: str
    title: str
    cited_text: str = ""


class LLMService(ABC):
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> T:
        """Generate structured response validated against schema."""

    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list[SearchCitation]]:
        """Generate text with web search grounding.

        Default: falls back to generate() with empty citations.
        Providers override this to use native search tools.
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
        Providers override this to use native search tools.
        """
        result = await self.generate_structured(
            system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
        )
        return (result, [])

    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
```

**Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_agents.py::TestSearchGrounding -v
```
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
cd backend && git add app/services/llm/base.py tests/test_agents.py
git commit -m "feat(llm): add SearchCitation model and search grounding base methods"
```

---

### Task 2: SEARCH_GROUNDING_MODE Config

**Files:**
- Modify: `backend/app/config/planning.py:26` (after `ROUTE_COMPUTATION_MODE`)
- Test: `backend/tests/test_agents.py` (add to `TestSearchGrounding`)

**Step 1: Write the failing test**

Add to `TestSearchGrounding` in `tests/test_agents.py`:

```python
    def test_should_use_search_grounding_full(self):
        """Full mode enables all tiers."""
        from app.config.planning import should_use_search_grounding
        # Temporarily set mode (tests restore after)
        import app.config.planning as planning
        original = planning.SEARCH_GROUNDING_MODE
        try:
            planning.SEARCH_GROUNDING_MODE = "full"
            assert should_use_search_grounding("selective") is True
            assert should_use_search_grounding("full") is True
        finally:
            planning.SEARCH_GROUNDING_MODE = original

    def test_should_use_search_grounding_selective(self):
        """Selective mode only enables selective tier."""
        from app.config.planning import should_use_search_grounding
        import app.config.planning as planning
        original = planning.SEARCH_GROUNDING_MODE
        try:
            planning.SEARCH_GROUNDING_MODE = "selective"
            assert should_use_search_grounding("selective") is True
            assert should_use_search_grounding("full") is False
        finally:
            planning.SEARCH_GROUNDING_MODE = original

    def test_should_use_search_grounding_none(self):
        """None mode disables all tiers."""
        from app.config.planning import should_use_search_grounding
        import app.config.planning as planning
        original = planning.SEARCH_GROUNDING_MODE
        try:
            planning.SEARCH_GROUNDING_MODE = "none"
            assert should_use_search_grounding("selective") is False
            assert should_use_search_grounding("full") is False
        finally:
            planning.SEARCH_GROUNDING_MODE = original
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_agents.py::TestSearchGrounding::test_should_use_search_grounding_full -v
```
Expected: FAIL — `should_use_search_grounding` doesn't exist.

**Step 3: Write the implementation**

In `backend/app/config/planning.py`, add after line 25 (`ROUTE_COMPUTATION_MODE`):

```python
# Web search grounding: "full" (all agents), "selective" (Scout/DayScout/Tips/Chat), "none" (disabled)
SEARCH_GROUNDING_MODE: str = "none"


def should_use_search_grounding(agent_tier: str = "full") -> bool:
    """Check if search grounding is enabled for the given agent tier.

    Args:
        agent_tier: "selective" for high-value agents (Scout, DayScout, Tips, Chat)
                    or "full" for all agents (Reviewer, Planner, etc.)
    """
    if SEARCH_GROUNDING_MODE == "none":
        return False
    if SEARCH_GROUNDING_MODE == "selective":
        return agent_tier == "selective"
    return True  # "full" mode
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_agents.py::TestSearchGrounding -v
```
Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
cd backend && git add app/config/planning.py tests/test_agents.py
git commit -m "feat(config): add SEARCH_GROUNDING_MODE with selective/full/none tiers"
```

---

### Task 3: Gemini Search Grounding Implementation

**Files:**
- Modify: `backend/app/services/llm/gemini.py:1-105`
- Test: `backend/tests/test_agents.py` (add `TestGeminiSearchGrounding`)

**Step 1: Write the failing test**

Add to `tests/test_agents.py`:

```python
class TestGeminiSearchGrounding:
    """Tests for Gemini web search grounding implementation."""

    @pytest.mark.asyncio
    async def test_generate_with_search_extracts_citations(self):
        """Gemini search grounding extracts citations from grounding metadata."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.llm.gemini import GeminiLLMService
        from app.services.llm.base import SearchCitation

        service = GeminiLLMService.__new__(GeminiLLMService)
        service.model = "gemini-2.5-flash"
        service.client = MagicMock()

        # Mock response with grounding metadata
        mock_chunk = MagicMock()
        mock_chunk.web.uri = "https://example.com/hotels"
        mock_chunk.web.title = "Tokyo Hotels Guide"

        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata.grounding_chunks = [mock_chunk]

        mock_response = MagicMock()
        mock_response.text = "Hotel recommendations..."
        mock_response.candidates = [mock_candidate]

        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        text, citations = await service.generate_with_search(
            system_prompt="You are a travel expert.",
            user_prompt="Best hotels in Tokyo?",
        )

        assert text == "Hotel recommendations..."
        assert len(citations) == 1
        assert citations[0].url == "https://example.com/hotels"
        assert citations[0].title == "Tokyo Hotels Guide"

    @pytest.mark.asyncio
    async def test_generate_with_search_no_grounding_metadata(self):
        """Returns empty citations when no grounding metadata present."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.llm.gemini import GeminiLLMService

        service = GeminiLLMService.__new__(GeminiLLMService)
        service.model = "gemini-2.5-flash"
        service.client = MagicMock()

        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = None

        mock_response = MagicMock()
        mock_response.text = "Some response"
        mock_response.candidates = [mock_candidate]

        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        text, citations = await service.generate_with_search(
            system_prompt="test", user_prompt="test",
        )

        assert text == "Some response"
        assert citations == []

    @pytest.mark.asyncio
    async def test_generate_with_search_fallback_on_error(self):
        """Falls back to regular generate on search error."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.services.llm.gemini import GeminiLLMService

        service = GeminiLLMService.__new__(GeminiLLMService)
        service.model = "gemini-2.5-flash"
        service.client = MagicMock()

        # First call (with search) fails, generate() called as fallback
        call_count = 0
        async def mock_generate_content(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Search tool not available")
            mock_resp = MagicMock()
            mock_resp.text = "Fallback response"
            return mock_resp

        service.client.aio.models.generate_content = mock_generate_content

        text, citations = await service.generate_with_search(
            system_prompt="test", user_prompt="test",
        )

        assert text == "Fallback response"
        assert citations == []
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_agents.py::TestGeminiSearchGrounding -v
```
Expected: FAIL — `generate_with_search` not overridden in Gemini service.

**Step 3: Write the implementation**

Add these two methods to `GeminiLLMService` in `backend/app/services/llm/gemini.py`, after the `generate_structured` method (before `close`):

```python
    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list["SearchCitation"]]:
        """Generate text with Google Search grounding."""
        from .base import SearchCitation
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
            text = (response.text or "").replace("\x00", "")
            citations = self._extract_citations(response)
            return (text, citations)
        except Exception as e:
            logger.warning("Gemini search grounding failed, falling back: %s", e)
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
    ) -> tuple[T, list["SearchCitation"]]:
        """Generate structured JSON with Google Search grounding."""
        from .base import SearchCitation
        last_errors: list[str] = []
        all_citations: list[SearchCitation] = []

        for attempt in range(1 + max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_json_schema=schema.model_json_schema(),
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                )
                content = (response.text or "{}").replace("\x00", "")
                all_citations = self._extract_citations(response)
                raw = json.loads(content)
                return (schema.model_validate(raw), all_citations)
            except ValidationError as e:
                last_errors = [str(err) for err in e.errors()]
                logger.warning(
                    "Schema validation failed (attempt %d/%d): %s",
                    attempt + 1, 1 + max_retries, e,
                )
                continue
            except json.JSONDecodeError as e:
                last_errors = [str(e)]
                logger.warning(
                    "JSON parse failed (attempt %d/%d): %s",
                    attempt + 1, 1 + max_retries, e,
                )
                continue
            except Exception as e:
                logger.warning("Gemini search+structured failed, falling back: %s", e)
                result = await self.generate_structured(
                    system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
                )
                return (result, [])

        raise LLMValidationError(schema.__name__, last_errors, 1 + max_retries)

    @staticmethod
    def _extract_citations(response) -> list["SearchCitation"]:
        """Extract SearchCitation list from Gemini grounding metadata."""
        from .base import SearchCitation
        citations: list[SearchCitation] = []
        try:
            candidates = getattr(response, "candidates", None)
            if not candidates:
                return []
            metadata = getattr(candidates[0], "grounding_metadata", None)
            if not metadata:
                return []
            chunks = getattr(metadata, "grounding_chunks", None) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if web:
                    citations.append(SearchCitation(
                        url=getattr(web, "uri", ""),
                        title=getattr(web, "title", ""),
                    ))
        except Exception:
            pass
        return citations
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_agents.py::TestGeminiSearchGrounding -v
```
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
cd backend && git add app/services/llm/gemini.py tests/test_agents.py
git commit -m "feat(gemini): implement web search grounding via google_search tool"
```

---

### Task 4: Anthropic Search Grounding Implementation

**Files:**
- Modify: `backend/app/services/llm/anthropic.py:1-109`
- Test: `backend/tests/test_agents.py` (add `TestAnthropicSearchGrounding`)

**Step 1: Write the failing test**

Add to `tests/test_agents.py`:

```python
class TestAnthropicSearchGrounding:
    """Tests for Anthropic web search grounding implementation."""

    @pytest.mark.asyncio
    async def test_generate_with_search_extracts_citations(self):
        """Anthropic search grounding extracts citations from text blocks."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.llm.anthropic import AnthropicLLMService

        service = AnthropicLLMService.__new__(AnthropicLLMService)
        service.model = "claude-sonnet-4-5-20250929"
        service.client = MagicMock()

        # Mock response with web search results and citations
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "The best hotels in Tokyo include..."
        citation = MagicMock()
        citation.type = "web_search_result_location"
        citation.url = "https://example.com/tokyo-hotels"
        citation.title = "Tokyo Hotel Guide"
        citation.cited_text = "Top rated hotels in Tokyo"
        text_block.citations = [citation]

        mock_response = MagicMock()
        mock_response.content = [text_block]

        service.client.messages.create = AsyncMock(return_value=mock_response)

        text, citations = await service.generate_with_search(
            system_prompt="test", user_prompt="Best hotels in Tokyo?",
        )

        assert "best hotels" in text.lower()
        assert len(citations) == 1
        assert citations[0].url == "https://example.com/tokyo-hotels"

    @pytest.mark.asyncio
    async def test_generate_structured_with_search_combines_tools(self):
        """Anthropic combines web_search server tool with submit tool."""
        from unittest.mock import AsyncMock, MagicMock
        from pydantic import BaseModel
        from app.services.llm.anthropic import AnthropicLLMService

        class SimpleResult(BaseModel):
            answer: str = "test"

        service = AnthropicLLMService.__new__(AnthropicLLMService)
        service.model = "claude-sonnet-4-5-20250929"
        service.client = MagicMock()

        # Mock response: search result + tool_use (submit)
        search_block = MagicMock()
        search_block.type = "server_tool_use"

        text_block_with_citation = MagicMock()
        text_block_with_citation.type = "text"
        text_block_with_citation.text = "Based on search..."
        cit = MagicMock()
        cit.url = "https://example.com"
        cit.title = "Source"
        cit.cited_text = "relevant text"
        text_block_with_citation.citations = [cit]

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.input = {"answer": "grounded answer"}

        mock_response = MagicMock()
        mock_response.content = [search_block, text_block_with_citation, tool_block]

        service.client.messages.create = AsyncMock(return_value=mock_response)

        result, citations = await service.generate_structured_with_search(
            system_prompt="test", user_prompt="test", schema=SimpleResult,
        )

        assert result.answer == "grounded answer"
        assert len(citations) == 1
        assert citations[0].url == "https://example.com"
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_agents.py::TestAnthropicSearchGrounding -v
```
Expected: FAIL — methods not overridden.

**Step 3: Write the implementation**

Add these methods to `AnthropicLLMService` in `backend/app/services/llm/anthropic.py`, before `close`:

```python
    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list["SearchCitation"]]:
        """Generate text with Anthropic web search grounding."""
        from .base import SearchCitation
        try:
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 3,
                }],
            )
            text_parts = []
            citations = []
            for block in response.content:
                if getattr(block, "type", "") == "text":
                    text_parts.append(getattr(block, "text", ""))
                    for cit in getattr(block, "citations", []) or []:
                        citations.append(SearchCitation(
                            url=getattr(cit, "url", ""),
                            title=getattr(cit, "title", ""),
                            cited_text=getattr(cit, "cited_text", ""),
                        ))
            text = "".join(text_parts).replace("\x00", "")
            return (text, citations)
        except Exception as e:
            logger.warning("Anthropic search grounding failed, falling back: %s", e)
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
    ) -> tuple[T, list["SearchCitation"]]:
        """Generate structured JSON with Anthropic web search grounding.

        Combines web_search server tool with submit tool. Server tools
        are auto-executed by the API, independent of tool_choice.
        """
        from .base import SearchCitation
        tool_definition = {
            "name": "submit",
            "description": "Submit structured response",
            "input_schema": schema.model_json_schema(),
        }
        web_search_tool = {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 3,
        }
        last_errors: list[str] = []

        for attempt in range(1 + max_retries):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    tools=[web_search_tool, tool_definition],
                    tool_choice={"type": "tool", "name": "submit"},
                )

                # Extract citations from text blocks
                citations = []
                for block in response.content:
                    if getattr(block, "type", "") == "text":
                        for cit in getattr(block, "citations", []) or []:
                            citations.append(SearchCitation(
                                url=getattr(cit, "url", ""),
                                title=getattr(cit, "title", ""),
                                cited_text=getattr(cit, "cited_text", ""),
                            ))

                # Extract structured data from tool_use block
                raw = None
                for block in response.content:
                    if block.type == "tool_use":
                        raw = block.input
                        break

                if raw is None:
                    last_errors = ["No tool_use block found in response"]
                    logger.warning(
                        "No tool_use block (attempt %d/%d)",
                        attempt + 1, 1 + max_retries,
                    )
                    continue

                return (schema.model_validate(raw), citations)
            except ValidationError as e:
                last_errors = [str(err) for err in e.errors()]
                logger.warning(
                    "Schema validation failed (attempt %d/%d): %s",
                    attempt + 1, 1 + max_retries, e,
                )
                continue
            except anthropic.APIError as e:
                logger.warning("Anthropic search+structured failed, falling back: %s", e)
                result = await self.generate_structured(
                    system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
                )
                return (result, [])

        raise LLMValidationError(schema.__name__, last_errors, 1 + max_retries)
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_agents.py::TestAnthropicSearchGrounding -v
```
Expected: All 2 tests PASS.

**Step 5: Commit**

```bash
cd backend && git add app/services/llm/anthropic.py tests/test_agents.py
git commit -m "feat(anthropic): implement web search grounding via web_search server tool"
```

---

### Task 5: Azure OpenAI Search Grounding Implementation

**Files:**
- Modify: `backend/app/services/llm/azure_openai.py:1-184`
- Test: `backend/tests/test_agents.py` (add `TestAzureSearchGrounding`)

**Step 1: Write the failing test**

Add to `tests/test_agents.py`:

```python
class TestAzureSearchGrounding:
    """Tests for Azure OpenAI web search grounding via Responses API."""

    @pytest.mark.asyncio
    async def test_generate_with_search_extracts_citations(self):
        """Azure search grounding extracts url_citation annotations."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.llm.azure_openai import AzureOpenAILLMService

        service = AzureOpenAILLMService.__new__(AzureOpenAILLMService)
        service.deployment = "gpt-4-test"
        service.client = MagicMock()
        service._is_reasoning = False

        # Mock Responses API output
        annotation = MagicMock()
        annotation.type = "url_citation"
        annotation.url = "https://example.com/guide"
        annotation.title = "Travel Guide"

        output_text_block = MagicMock()
        output_text_block.type = "output_text"
        output_text_block.text = "Here are the top hotels..."
        output_text_block.annotations = [annotation]

        output_message = MagicMock()
        output_message.type = "message"
        output_message.content = [output_text_block]

        mock_response = MagicMock()
        mock_response.output = [output_message]
        mock_response.output_text = "Here are the top hotels..."

        service.client.responses.create = AsyncMock(return_value=mock_response)

        text, citations = await service.generate_with_search(
            system_prompt="test", user_prompt="Best hotels?",
        )

        assert "top hotels" in text.lower()
        assert len(citations) == 1
        assert citations[0].url == "https://example.com/guide"

    @pytest.mark.asyncio
    async def test_generate_with_search_fallback_on_error(self):
        """Falls back to regular generate when Responses API fails."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.llm.azure_openai import AzureOpenAILLMService

        service = AzureOpenAILLMService.__new__(AzureOpenAILLMService)
        service.deployment = "gpt-4-test"
        service.client = MagicMock()
        service._is_reasoning = False

        # Responses API fails
        service.client.responses.create = AsyncMock(side_effect=Exception("Responses API unavailable"))

        # Regular generate works
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = "Fallback response"
        service.client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        text, citations = await service.generate_with_search(
            system_prompt="test", user_prompt="test",
        )

        assert text == "Fallback response"
        assert citations == []
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_agents.py::TestAzureSearchGrounding -v
```
Expected: FAIL — methods not overridden.

**Step 3: Write the implementation**

Add these methods to `AzureOpenAILLMService` in `backend/app/services/llm/azure_openai.py`, before `close`:

```python
    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list["SearchCitation"]]:
        """Generate text with web search grounding via Responses API."""
        from .base import SearchCitation
        try:
            params: dict[str, Any] = {
                "model": self.deployment,
                "tools": [{"type": "web_search"}],
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_output_tokens": max_tokens,
            }
            if not self._is_reasoning:
                params["temperature"] = temperature

            response = await self.client.responses.create(**params)
            text = _sanitize_content(response.output_text or "")
            citations = self._extract_response_citations(response)
            return (text, citations)
        except Exception as e:
            logger.warning("Azure search grounding failed, falling back: %s", e)
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
    ) -> tuple[T, list["SearchCitation"]]:
        """Generate structured JSON with web search via Responses API."""
        from .base import SearchCitation
        json_system_prompt = f"{system_prompt}\n\nYou must respond with valid JSON."
        last_errors: list[str] = []

        for attempt in range(1 + max_retries):
            try:
                params: dict[str, Any] = {
                    "model": self.deployment,
                    "tools": [{"type": "web_search"}],
                    "input": [
                        {"role": "system", "content": json_system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "schema": schema.model_json_schema(),
                            "name": schema.__name__,
                            "strict": False,
                        }
                    },
                    "max_output_tokens": max_tokens,
                }
                if not self._is_reasoning:
                    params["temperature"] = temperature

                response = await self.client.responses.create(**params)
                content = _sanitize_content(response.output_text or "{}")
                citations = self._extract_response_citations(response)
                raw = json.loads(content)
                return (schema.model_validate(raw), citations)
            except ValidationError as e:
                last_errors = [str(err) for err in e.errors()]
                logger.warning(
                    "Schema validation failed (attempt %d/%d): %s",
                    attempt + 1, 1 + max_retries, e,
                )
                continue
            except json.JSONDecodeError as e:
                last_errors = [str(e)]
                logger.warning(
                    "JSON parse failed (attempt %d/%d): %s",
                    attempt + 1, 1 + max_retries, e,
                )
                continue
            except Exception as e:
                if isinstance(e, openai.OpenAIError) and _is_content_filter_error(e):
                    raise LLMContentFilterError(e) from e
                logger.warning("Azure search+structured failed, falling back: %s", e)
                result = await self.generate_structured(
                    system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
                )
                return (result, [])

        raise LLMValidationError(schema.__name__, last_errors, 1 + max_retries)

    @staticmethod
    def _extract_response_citations(response) -> list["SearchCitation"]:
        """Extract citations from Responses API url_citation annotations."""
        from .base import SearchCitation
        citations: list[SearchCitation] = []
        try:
            for item in getattr(response, "output", []):
                if getattr(item, "type", "") != "message":
                    continue
                for block in getattr(item, "content", []):
                    for annotation in getattr(block, "annotations", []) or []:
                        if getattr(annotation, "type", "") == "url_citation":
                            citations.append(SearchCitation(
                                url=getattr(annotation, "url", ""),
                                title=getattr(annotation, "title", ""),
                            ))
        except Exception:
            pass
        return citations
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_agents.py::TestAzureSearchGrounding -v
```
Expected: All 2 tests PASS.

**Step 5: Commit**

```bash
cd backend && git add app/services/llm/azure_openai.py tests/test_agents.py
git commit -m "feat(azure): implement web search grounding via Responses API"
```

---

### Task 6: Update MockLLMService for Tests

**Files:**
- Modify: `backend/tests/conftest.py:78-114`

**Step 1: Add search grounding methods to MockLLMService**

The `MockLLMService` inherits from `LLMService` which already has default `generate_with_search` / `generate_structured_with_search` that fall back to `generate` / `generate_structured`. So existing tests won't break.

However, explicitly adding them makes the mock more transparent and allows tests to verify search-grounded calls:

In `backend/tests/conftest.py`, add after the `close` method in `MockLLMService`:

```python
    async def generate_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> tuple[str, list]:
        text = await self.generate(system_prompt, user_prompt, max_tokens, temperature)
        return (text, [])

    async def generate_structured_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> tuple[BaseModel, list]:
        result = await self.generate_structured(
            system_prompt, user_prompt, schema, max_tokens, temperature, max_retries
        )
        return (result, [])
```

**Step 2: Run full test suite to verify no regressions**

```bash
cd backend && python -m pytest -v
```
Expected: All 245+ tests PASS.

**Step 3: Commit**

```bash
cd backend && git add tests/conftest.py
git commit -m "test: add search grounding methods to MockLLMService"
```

---

### Task 7: Wire Search Grounding into Selective-Tier Agents (Scout, Day Scout, Tips, Chat)

**Files:**
- Modify: `backend/app/agents/scout.py:86-93` (LLM call)
- Modify: `backend/app/agents/day_scout.py:68-71` (LLM call)
- Modify: `backend/app/services/tips.py:95-100` (LLM call)
- Modify: `backend/app/services/chat.py:108-114,170-176` (two LLM calls)

**Step 1: Update Scout agent**

In `backend/app/agents/scout.py`, change lines 86-93:

FROM:
```python
        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_SCOUT_TEMPERATURE
        plan = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=JourneyPlan,
            max_tokens=LLM_DEFAULT_MAX_TOKENS,
            temperature=LLM_SCOUT_TEMPERATURE,
        )
```

TO:
```python
        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_SCOUT_TEMPERATURE, should_use_search_grounding
        if should_use_search_grounding("selective"):
            plan, _citations = await self.llm.generate_structured_with_search(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=JourneyPlan,
                max_tokens=LLM_DEFAULT_MAX_TOKENS,
                temperature=LLM_SCOUT_TEMPERATURE,
            )
        else:
            plan = await self.llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=JourneyPlan,
                max_tokens=LLM_DEFAULT_MAX_TOKENS,
                temperature=LLM_SCOUT_TEMPERATURE,
            )
```

**Step 2: Update Day Scout agent**

In `backend/app/agents/day_scout.py`, change lines 68-71:

FROM:
```python
        plan = await self.llm.generate_structured(
            system_prompt, user_prompt, schema=AIPlan
        )
        return plan
```

TO:
```python
        from app.config.planning import should_use_search_grounding
        if should_use_search_grounding("selective"):
            plan, _citations = await self.llm.generate_structured_with_search(
                system_prompt, user_prompt, schema=AIPlan
            )
        else:
            plan = await self.llm.generate_structured(
                system_prompt, user_prompt, schema=AIPlan
            )
        return plan
```

**Step 3: Update Tips service**

In `backend/app/services/tips.py`, change lines 95-100:

FROM:
```python
        raw_text = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4000,
            temperature=0.7,
        )
```

TO:
```python
        from app.config.planning import should_use_search_grounding
        if should_use_search_grounding("selective"):
            raw_text, _citations = await self.llm.generate_with_search(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4000,
                temperature=0.7,
            )
        else:
            raw_text = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4000,
                temperature=0.7,
            )
```

**Step 4: Update Chat service (both methods)**

In `backend/app/services/chat.py`, change `edit_journey` lines 108-114:

FROM:
```python
        result = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ChatEditResponse,
            max_tokens=8000,
            temperature=0.7,
        )
```

TO:
```python
        from app.config.planning import should_use_search_grounding
        if should_use_search_grounding("selective"):
            result, _citations = await self.llm.generate_structured_with_search(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=ChatEditResponse,
                max_tokens=8000,
                temperature=0.7,
            )
        else:
            result = await self.llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=ChatEditResponse,
                max_tokens=8000,
                temperature=0.7,
            )
```

And `edit_day_plans` lines 170-176:

FROM:
```python
        result = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ChatEditResponse,
            max_tokens=12000,
            temperature=0.7,
        )
```

TO:
```python
        from app.config.planning import should_use_search_grounding
        if should_use_search_grounding("selective"):
            result, _citations = await self.llm.generate_structured_with_search(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=ChatEditResponse,
                max_tokens=12000,
                temperature=0.7,
            )
        else:
            result = await self.llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=ChatEditResponse,
                max_tokens=12000,
                temperature=0.7,
            )
```

**Step 5: Run tests**

```bash
cd backend && python -m pytest -v
```
Expected: All tests PASS (SEARCH_GROUNDING_MODE defaults to "none", so all agents use regular methods).

**Step 6: Commit**

```bash
cd backend && git add app/agents/scout.py app/agents/day_scout.py app/services/tips.py app/services/chat.py
git commit -m "feat(agents): wire search grounding into selective-tier agents (Scout, DayScout, Tips, Chat)"
```

---

### Task 8: Wire Search Grounding into Full-Tier Agents (Reviewer, Planner, DayReviewer, DayFixer, Must-See)

**Files:**
- Modify: `backend/app/agents/reviewer.py:42-48`
- Modify: `backend/app/agents/planner.py:45-51`
- Modify: `backend/app/agents/day_reviewer.py:34-36`
- Modify: `backend/app/agents/day_fixer.py:62-64`
- Modify: `backend/app/orchestrators/journey.py:268-274`

**Step 1: Update Reviewer agent**

In `backend/app/agents/reviewer.py`, change lines 42-48:

FROM:
```python
        from app.config.planning import LLM_REVIEWER_MAX_TOKENS, LLM_REVIEWER_TEMPERATURE
        result = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ReviewResult,
            max_tokens=LLM_REVIEWER_MAX_TOKENS,
            temperature=LLM_REVIEWER_TEMPERATURE,
        )
```

TO:
```python
        from app.config.planning import LLM_REVIEWER_MAX_TOKENS, LLM_REVIEWER_TEMPERATURE, should_use_search_grounding
        if should_use_search_grounding("full"):
            result, _citations = await self.llm.generate_structured_with_search(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=ReviewResult,
                max_tokens=LLM_REVIEWER_MAX_TOKENS,
                temperature=LLM_REVIEWER_TEMPERATURE,
            )
        else:
            result = await self.llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=ReviewResult,
                max_tokens=LLM_REVIEWER_MAX_TOKENS,
                temperature=LLM_REVIEWER_TEMPERATURE,
            )
```

**Step 2: Update Planner agent**

In `backend/app/agents/planner.py`, change lines 44-51:

FROM:
```python
        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_DEFAULT_TEMPERATURE
        fixed = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=JourneyPlan,
            max_tokens=LLM_DEFAULT_MAX_TOKENS,
            temperature=LLM_DEFAULT_TEMPERATURE,
        )
```

TO:
```python
        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_DEFAULT_TEMPERATURE, should_use_search_grounding
        if should_use_search_grounding("full"):
            fixed, _citations = await self.llm.generate_structured_with_search(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=JourneyPlan,
                max_tokens=LLM_DEFAULT_MAX_TOKENS,
                temperature=LLM_DEFAULT_TEMPERATURE,
            )
        else:
            fixed = await self.llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=JourneyPlan,
                max_tokens=LLM_DEFAULT_MAX_TOKENS,
                temperature=LLM_DEFAULT_TEMPERATURE,
            )
```

**Step 3: Update Day Reviewer agent**

In `backend/app/agents/day_reviewer.py`, change lines 34-36:

FROM:
```python
        result = await self.llm.generate_structured(
            system_prompt, user_prompt, schema=DayReviewResult
        )
```

TO:
```python
        from app.config.planning import should_use_search_grounding
        if should_use_search_grounding("full"):
            result, _citations = await self.llm.generate_structured_with_search(
                system_prompt, user_prompt, schema=DayReviewResult
            )
        else:
            result = await self.llm.generate_structured(
                system_prompt, user_prompt, schema=DayReviewResult
            )
```

**Step 4: Update Day Fixer agent**

In `backend/app/agents/day_fixer.py`, change lines 62-64:

FROM:
```python
        return await self.llm.generate_structured(
            system_prompt, user_prompt, schema=AIPlan
        )
```

TO:
```python
        from app.config.planning import should_use_search_grounding
        if should_use_search_grounding("full"):
            result, _citations = await self.llm.generate_structured_with_search(
                system_prompt, user_prompt, schema=AIPlan
            )
            return result
        return await self.llm.generate_structured(
            system_prompt, user_prompt, schema=AIPlan
        )
```

**Step 5: Update Must-See Icons call in orchestrator**

In `backend/app/orchestrators/journey.py`, change lines 268-274:

FROM:
```python
            result = await self.llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=MustSeeAttractions,
                max_tokens=LLM_MUST_SEE_MAX_TOKENS,
                temperature=LLM_MUST_SEE_TEMPERATURE,
            )
```

TO:
```python
            from app.config.planning import should_use_search_grounding
            if should_use_search_grounding("full"):
                result, _citations = await self.llm.generate_structured_with_search(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=MustSeeAttractions,
                    max_tokens=LLM_MUST_SEE_MAX_TOKENS,
                    temperature=LLM_MUST_SEE_TEMPERATURE,
                )
            else:
                result = await self.llm.generate_structured(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=MustSeeAttractions,
                    max_tokens=LLM_MUST_SEE_MAX_TOKENS,
                    temperature=LLM_MUST_SEE_TEMPERATURE,
                )
```

**Step 6: Run tests**

```bash
cd backend && python -m pytest -v
```
Expected: All tests PASS.

**Step 7: Commit**

```bash
cd backend && git add app/agents/reviewer.py app/agents/planner.py app/agents/day_reviewer.py app/agents/day_fixer.py app/orchestrators/journey.py
git commit -m "feat(agents): wire search grounding into full-tier agents (Reviewer, Planner, DayReviewer, DayFixer, Must-See)"
```

---

### Task 9: Run Full Test Suite + Final Verification

**Step 1: Run all tests**

```bash
cd backend && python -m pytest -v
```
Expected: All 245+ tests PASS.

**Step 2: Verify default mode is safe**

```bash
cd backend && python -c "from app.config.planning import SEARCH_GROUNDING_MODE, should_use_search_grounding; print(f'Mode: {SEARCH_GROUNDING_MODE}'); print(f'Selective: {should_use_search_grounding(\"selective\")}'); print(f'Full: {should_use_search_grounding(\"full\")}')"
```
Expected output:
```
Mode: none
Selective: False
Full: False
```

This confirms that with the default `"none"` mode, all agents use their existing non-search methods. Search grounding is opt-in by changing `SEARCH_GROUNDING_MODE` in `planning.py`.

**Step 3: Commit the plan**

```bash
git add docs/plans/2026-03-18-web-search-grounding-plan.md
git commit -m "docs: add web search grounding implementation plan"
```

---

## Activation

To enable search grounding after implementation:

1. Change `SEARCH_GROUNDING_MODE` in `backend/app/config/planning.py` from `"none"` to `"selective"` or `"full"`
2. Restart the server
3. Run a trip and check logs for `"search grounding"` entries and citation counts

Start with `"selective"` to test Scout + Day Scout + Tips + Chat before enabling all agents.
