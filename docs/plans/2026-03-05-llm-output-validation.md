# LLM Output Validation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add schema validation and semantic completeness checks to all LLM responses, failing hard on invalid output after retries.

**Architecture:** Centralized Pydantic `model_validate()` at the LLM service layer with retry on `ValidationError`. Agents receive validated models (not dicts) and add domain-specific semantic checks. `LLMValidationError` propagates to orchestrators which yield `phase="error"`.

**Tech Stack:** Pydantic v2 (`model_validate`), pytest, pytest-asyncio, unittest.mock

---

### Task 1: Create LLMValidationError exception

**Files:**
- Create: `backend/app/services/llm/exceptions.py`

**Step 1: Create the exception class**

```python
# backend/app/services/llm/exceptions.py
"""Exceptions for LLM service layer."""


class LLMValidationError(Exception):
    """LLM response failed schema validation after retries."""

    def __init__(self, schema_name: str, errors: list[str], attempts: int) -> None:
        self.schema_name = schema_name
        self.errors = errors
        self.attempts = attempts
        detail = "; ".join(errors[:3])
        super().__init__(
            f"{schema_name} validation failed after {attempts} attempt(s): {detail}"
        )
```

**Step 2: Export from package**

Modify `backend/app/services/llm/__init__.py` — add `LLMValidationError` to imports and `__all__`:

```python
from .base import LLMService
from .exceptions import LLMValidationError
from .factory import create_llm_service
from .gemini import GeminiLLMService

__all__ = ["LLMService", "LLMValidationError", "create_llm_service", "GeminiLLMService"]
```

**Step 3: Commit**

```bash
git add backend/app/services/llm/exceptions.py backend/app/services/llm/__init__.py
git commit -m "feat: add LLMValidationError exception class"
```

---

### Task 2: Update LLMService base class signature

**Files:**
- Modify: `backend/app/services/llm/base.py`

**Step 1: Update generate_structured signature to return `T` instead of `dict`**

Replace the entire file content:

```python
# backend/app/services/llm/base.py
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


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
        """Generate structured response validated against schema.

        Args:
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt for the LLM.
            schema: Pydantic model class to validate against.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature.
            max_retries: Number of retry attempts on validation failure.

        Returns:
            Validated Pydantic model instance.

        Raises:
            LLMValidationError: If validation fails after all retries.
        """

    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
```

**Step 2: Commit**

```bash
git add backend/app/services/llm/base.py
git commit -m "feat: change generate_structured return type from dict to T (Pydantic model)"
```

---

### Task 3: Add validation + retry to AzureOpenAILLMService

**Files:**
- Modify: `backend/app/services/llm/azure_openai.py`
- Test: `backend/tests/test_llm_validation.py`

**Step 1: Write failing tests for Azure provider validation**

Create `backend/tests/test_llm_validation.py`:

```python
"""Tests for LLM service schema validation and retry logic."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from app.services.llm.azure_openai import AzureOpenAILLMService
from app.services.llm.exceptions import LLMValidationError


class SampleModel(BaseModel):
    name: str
    score: int = Field(..., ge=0, le=100)


class TestAzureOpenAIValidation:
    """Test schema validation in AzureOpenAILLMService.generate_structured."""

    def _make_service(self) -> AzureOpenAILLMService:
        return AzureOpenAILLMService(
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            deployment="gpt-4-test",
            api_version="2024-02-15-preview",
        )

    def _mock_response(self, content: str) -> MagicMock:
        """Build a mock OpenAI chat completion response."""
        msg = MagicMock()
        msg.content = content
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    @pytest.mark.asyncio
    async def test_returns_validated_model(self):
        """Valid JSON returns a validated Pydantic model instance."""
        svc = self._make_service()
        valid_json = json.dumps({"name": "test", "score": 85})
        svc.client = MagicMock()
        svc.client.chat.completions.create = AsyncMock(
            return_value=self._mock_response(valid_json)
        )

        result = await svc.generate_structured(
            system_prompt="test", user_prompt="test", schema=SampleModel,
        )

        assert isinstance(result, SampleModel)
        assert result.name == "test"
        assert result.score == 85

    @pytest.mark.asyncio
    async def test_retries_on_validation_error_then_succeeds(self):
        """Invalid first response triggers retry; valid second response succeeds."""
        svc = self._make_service()
        bad_json = json.dumps({"name": "test"})  # missing required 'score'
        good_json = json.dumps({"name": "test", "score": 75})
        svc.client = MagicMock()
        svc.client.chat.completions.create = AsyncMock(
            side_effect=[
                self._mock_response(bad_json),
                self._mock_response(good_json),
            ]
        )

        result = await svc.generate_structured(
            system_prompt="test", user_prompt="test", schema=SampleModel, max_retries=2,
        )

        assert isinstance(result, SampleModel)
        assert result.score == 75
        assert svc.client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Raises LLMValidationError after exhausting all retries."""
        svc = self._make_service()
        bad_json = json.dumps({"name": "test"})  # always missing 'score'
        svc.client = MagicMock()
        svc.client.chat.completions.create = AsyncMock(
            return_value=self._mock_response(bad_json)
        )

        with pytest.raises(LLMValidationError) as exc_info:
            await svc.generate_structured(
                system_prompt="test", user_prompt="test",
                schema=SampleModel, max_retries=2,
            )

        assert exc_info.value.schema_name == "SampleModel"
        assert exc_info.value.attempts == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_invalid_enum_raises_validation_error(self):
        """Invalid enum values cause validation failure."""
        from app.models.common import TransportMode
        from app.models.journey import TravelLeg

        class PlanWithLeg(BaseModel):
            legs: list[TravelLeg]

        svc = self._make_service()
        bad_json = json.dumps({
            "legs": [{"from_city": "A", "to_city": "B", "mode": "teleport", "duration_hours": 1}]
        })
        svc.client = MagicMock()
        svc.client.chat.completions.create = AsyncMock(
            return_value=self._mock_response(bad_json)
        )

        with pytest.raises(LLMValidationError):
            await svc.generate_structured(
                system_prompt="test", user_prompt="test",
                schema=PlanWithLeg, max_retries=0,
            )
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_llm_validation.py -v`
Expected: FAIL (generate_structured still returns dict, not model)

**Step 3: Implement validation + retry in Azure provider**

Replace `generate_structured` method in `backend/app/services/llm/azure_openai.py`:

```python
import json
import logging
from typing import Any, TypeVar

import openai
from pydantic import BaseModel, ValidationError

from .base import LLMService
from .exceptions import LLMValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Models that only support temperature=1 and max_completion_tokens (not max_tokens)
_REASONING_MODEL_PREFIXES = ("o1", "o3", "gpt-5")


class AzureOpenAILLMService(LLMService):
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str,
    ) -> None:
        self.deployment = deployment
        self.client = openai.AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self._is_reasoning = any(
            deployment.lower().startswith(p) for p in _REASONING_MODEL_PREFIXES
        )

    def _build_params(
        self, max_tokens: int, temperature: float, **extra: Any,
    ) -> dict[str, Any]:
        """Build model params, omitting temperature for reasoning models."""
        params: dict[str, Any] = {
            "max_completion_tokens": max_tokens,
            **extra,
        }
        if not self._is_reasoning:
            params["temperature"] = temperature
        return params

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""
        try:
            params = self._build_params(max_tokens, temperature)
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **params,
            )
            return response.choices[0].message.content or ""
        except openai.OpenAIError as e:
            logger.error("Azure OpenAI generate failed: %s", e)
            raise

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> T:
        """Generate structured JSON response validated against schema."""
        json_system_prompt = f"{system_prompt}\n\nYou must respond with valid JSON."
        last_validation_errors: list[str] = []

        for attempt in range(1 + max_retries):
            try:
                params = self._build_params(
                    max_tokens, temperature,
                    response_format={"type": "json_object"},
                )
                response = await self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": json_system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    **params,
                )
                content = response.choices[0].message.content or "{}"
                raw = json.loads(content)
                return schema.model_validate(raw)

            except ValidationError as e:
                last_validation_errors = [
                    err["msg"] for err in e.errors()
                ]
                logger.warning(
                    "Schema validation failed for %s (attempt %d/%d): %s",
                    schema.__name__, attempt + 1, 1 + max_retries,
                    last_validation_errors,
                )
                continue

            except json.JSONDecodeError as e:
                last_validation_errors = [f"Invalid JSON: {e}"]
                logger.warning(
                    "JSON parse failed for %s (attempt %d/%d): %s",
                    schema.__name__, attempt + 1, 1 + max_retries, e,
                )
                continue

            except openai.OpenAIError as e:
                logger.error("Azure OpenAI generate_structured failed: %s", e)
                raise

        raise LLMValidationError(
            schema_name=schema.__name__,
            errors=last_validation_errors,
            attempts=1 + max_retries,
        )

    async def close(self) -> None:
        """Cleanup resources."""
        await self.client.close()
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_llm_validation.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/llm/azure_openai.py backend/tests/test_llm_validation.py
git commit -m "feat: add schema validation + retry to AzureOpenAILLMService"
```

---

### Task 4: Add validation + retry to AnthropicLLMService

**Files:**
- Modify: `backend/app/services/llm/anthropic.py`
- Modify: `backend/tests/test_llm_validation.py`

**Step 1: Write failing tests for Anthropic provider**

Append to `backend/tests/test_llm_validation.py`:

```python
from app.services.llm.anthropic import AnthropicLLMService


class TestAnthropicValidation:
    """Test schema validation in AnthropicLLMService.generate_structured."""

    def _make_service(self) -> AnthropicLLMService:
        return AnthropicLLMService(api_key="test-key", model="claude-test")

    def _mock_response(self, tool_input: dict) -> MagicMock:
        """Build a mock Anthropic tool_use response."""
        block = MagicMock()
        block.type = "tool_use"
        block.input = tool_input
        resp = MagicMock()
        resp.content = [block]
        return resp

    @pytest.mark.asyncio
    async def test_returns_validated_model(self):
        svc = self._make_service()
        svc.client = MagicMock()
        svc.client.messages.create = AsyncMock(
            return_value=self._mock_response({"name": "test", "score": 90})
        )

        result = await svc.generate_structured(
            system_prompt="test", user_prompt="test", schema=SampleModel,
        )

        assert isinstance(result, SampleModel)
        assert result.score == 90

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        svc = self._make_service()
        svc.client = MagicMock()
        svc.client.messages.create = AsyncMock(
            return_value=self._mock_response({"name": "test"})  # missing score
        )

        with pytest.raises(LLMValidationError):
            await svc.generate_structured(
                system_prompt="test", user_prompt="test",
                schema=SampleModel, max_retries=1,
            )
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_llm_validation.py::TestAnthropicValidation -v`
Expected: FAIL

**Step 3: Implement validation + retry in Anthropic provider**

Replace `backend/app/services/llm/anthropic.py`:

```python
import logging
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from .base import LLMService
from .exceptions import LLMValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AnthropicLLMService(LLMService):
    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error("Anthropic generate failed: %s", e)
            raise

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
        tool_definition = {
            "name": "submit",
            "description": "Submit structured response",
            "input_schema": schema.model_json_schema(),
        }
        last_validation_errors: list[str] = []

        for attempt in range(1 + max_retries):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    tools=[tool_definition],
                    tool_choice={"type": "tool", "name": "submit"},
                )

                raw: dict[str, Any] = {}
                for block in response.content:
                    if block.type == "tool_use":
                        raw = block.input
                        break

                if not raw:
                    last_validation_errors = ["No tool_use block in response"]
                    logger.warning(
                        "No tool_use block from Anthropic (attempt %d/%d)",
                        attempt + 1, 1 + max_retries,
                    )
                    continue

                return schema.model_validate(raw)

            except ValidationError as e:
                last_validation_errors = [err["msg"] for err in e.errors()]
                logger.warning(
                    "Schema validation failed for %s (attempt %d/%d): %s",
                    schema.__name__, attempt + 1, 1 + max_retries,
                    last_validation_errors,
                )
                continue

            except anthropic.APIError as e:
                logger.error("Anthropic generate_structured failed: %s", e)
                raise

        raise LLMValidationError(
            schema_name=schema.__name__,
            errors=last_validation_errors,
            attempts=1 + max_retries,
        )

    async def close(self) -> None:
        """Cleanup resources."""
        await self.client.close()
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_llm_validation.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/llm/anthropic.py backend/tests/test_llm_validation.py
git commit -m "feat: add schema validation + retry to AnthropicLLMService"
```

---

### Task 5: Add validation + retry to GeminiLLMService

**Files:**
- Modify: `backend/app/services/llm/gemini.py`
- Modify: `backend/tests/test_llm_validation.py`

**Step 1: Write failing tests for Gemini provider**

Append to `backend/tests/test_llm_validation.py`:

```python
from app.services.llm.gemini import GeminiLLMService


class TestGeminiValidation:
    """Test schema validation in GeminiLLMService.generate_structured."""

    def _make_service(self) -> GeminiLLMService:
        return GeminiLLMService(api_key="test-key", model="gemini-test")

    def _mock_response(self, text: str) -> MagicMock:
        resp = MagicMock()
        resp.text = text
        return resp

    @pytest.mark.asyncio
    async def test_returns_validated_model(self):
        svc = self._make_service()
        svc.client = MagicMock()
        svc.client.aio.models.generate_content = AsyncMock(
            return_value=self._mock_response(json.dumps({"name": "test", "score": 80}))
        )

        result = await svc.generate_structured(
            system_prompt="test", user_prompt="test", schema=SampleModel,
        )

        assert isinstance(result, SampleModel)
        assert result.score == 80

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        svc = self._make_service()
        svc.client = MagicMock()
        svc.client.aio.models.generate_content = AsyncMock(
            return_value=self._mock_response(json.dumps({"name": "test"}))
        )

        with pytest.raises(LLMValidationError):
            await svc.generate_structured(
                system_prompt="test", user_prompt="test",
                schema=SampleModel, max_retries=1,
            )
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_llm_validation.py::TestGeminiValidation -v`
Expected: FAIL

**Step 3: Implement validation + retry in Gemini provider**

Replace `backend/app/services/llm/gemini.py`:

```python
import json
import logging
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from .base import LLMService
from .exceptions import LLMValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiLLMService(LLMService):
    """Google Gemini LLM service using the google-genai SDK."""

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = genai.Client(api_key=api_key)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )
            return response.text or ""
        except Exception as e:
            logger.error("Gemini generate failed: %s", e)
            raise

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
        last_validation_errors: list[str] = []

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
                    ),
                )
                content = response.text or "{}"
                raw = json.loads(content)
                return schema.model_validate(raw)

            except ValidationError as e:
                last_validation_errors = [err["msg"] for err in e.errors()]
                logger.warning(
                    "Schema validation failed for %s (attempt %d/%d): %s",
                    schema.__name__, attempt + 1, 1 + max_retries,
                    last_validation_errors,
                )
                continue

            except json.JSONDecodeError as e:
                last_validation_errors = [f"Invalid JSON: {e}"]
                logger.warning(
                    "JSON parse failed for %s (attempt %d/%d): %s",
                    schema.__name__, attempt + 1, 1 + max_retries, e,
                )
                continue

            except Exception as e:
                logger.error("Gemini generate_structured failed: %s", e)
                raise

        raise LLMValidationError(
            schema_name=schema.__name__,
            errors=last_validation_errors,
            attempts=1 + max_retries,
        )

    async def close(self) -> None:
        """Cleanup resources."""
        pass
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_llm_validation.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/llm/gemini.py backend/tests/test_llm_validation.py
git commit -m "feat: add schema validation + retry to GeminiLLMService"
```

---

### Task 6: Update MockLLMService and conftest

**Files:**
- Modify: `backend/tests/conftest.py`

**Step 1: Update MockLLMService to return validated Pydantic models**

In `backend/tests/conftest.py`, replace the `MockLLMService` class (lines 79-102):

```python
class MockLLMService(LLMService):
    """LLM service that returns canned responses for tests."""

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        return json.dumps({"message": "mock llm response"})

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        max_tokens: int = 8000,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> BaseModel:
        """Return a default instance of the requested schema."""
        # Build minimal valid data for common schemas
        return schema.model_validate({"message": "mock structured response"})

    async def close(self) -> None:
        pass
```

Note: The `MockLLMService.generate_structured` will now raise `ValidationError` for schemas without a `message` field. Tests that use `MockLLMService` via the `app` fixture AND call `generate_structured` will need their own mocks (which they already have — `test_agents.py` uses `MagicMock()`). The `conftest` MockLLMService is mainly used via the `app` fixture for API-level tests, which mock at a higher level.

**Step 2: Run existing tests to check nothing is broken**

Run: `cd backend && python -m pytest tests/ -v --timeout=60`
Expected: All 164 tests PASS (no behavior change yet — agents use their own mocks)

**Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "feat: update MockLLMService to match new generate_structured signature"
```

---

### Task 7: Simplify ScoutAgent — use validated model + add semantic checks

**Files:**
- Modify: `backend/app/agents/scout.py`
- Modify: `backend/tests/test_agents.py`

**Step 1: Write failing tests for Scout semantic validation**

Append to `backend/tests/test_agents.py`:

```python
from app.services.llm.exceptions import LLMValidationError


class TestScoutValidation:
    """Test Scout semantic validation of LLM responses."""

    @pytest.mark.asyncio
    async def test_empty_cities_raises(self):
        """Scout raises LLMValidationError when LLM returns no cities."""
        mock_llm = MagicMock()
        plan = _make_journey_plan(cities=[], travel_legs=[])
        mock_llm.generate_structured = AsyncMock(return_value=plan)

        agent = ScoutAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="No cities"):
            await agent.generate_plan(_make_request())

    @pytest.mark.asyncio
    async def test_city_missing_name_raises(self):
        """Scout raises LLMValidationError when a city has empty name."""
        mock_llm = MagicMock()
        plan = _make_journey_plan(
            cities=[CityStop(name="", country="Italy", days=3, why_visit="")],
            travel_legs=[],
        )
        mock_llm.generate_structured = AsyncMock(return_value=plan)

        agent = ScoutAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="empty name"):
            await agent.generate_plan(_make_request())

    @pytest.mark.asyncio
    async def test_travel_legs_mismatch_raises(self):
        """Scout raises LLMValidationError when travel legs != cities - 1."""
        mock_llm = MagicMock()
        plan = _make_journey_plan(travel_legs=[])  # 2 cities but 0 legs
        mock_llm.generate_structured = AsyncMock(return_value=plan)

        agent = ScoutAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="travel legs"):
            await agent.generate_plan(_make_request())
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_agents.py::TestScoutValidation -v`
Expected: FAIL

**Step 3: Rewrite ScoutAgent to use validated model + semantic checks**

Replace `backend/app/agents/scout.py`:

```python
"""Scout agent — generates an initial journey plan from a trip request via LLM."""

import logging

from app.config.regional_transport import get_transport_guidance
from app.models.journey import JourneyPlan
from app.models.trip import TripRequest
from app.prompts import journey_prompts
from app.services.llm.base import LLMService
from app.services.llm.exceptions import LLMValidationError

logger = logging.getLogger(__name__)


class ScoutAgent:
    """Generates initial journey plan using LLM intelligence."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def generate_plan(self, request: TripRequest) -> JourneyPlan:
        """Generate initial journey plan from user request."""
        transport_guidance = get_transport_guidance(
            origin=request.origin or "",
            region=request.destination,
        )

        system_prompt = journey_prompts.load("scout_system").format(
            region=request.destination,
            total_days=request.total_days,
            pace=request.pace.value,
            travel_dates=str(request.start_date),
        )

        user_prompt = journey_prompts.load("scout_user").format(
            region=request.destination,
            origin=request.origin or "not specified",
            total_days=request.total_days,
            travel_dates=str(request.start_date),
            interests=(
                ", ".join(request.interests) if request.interests else "general sightseeing"
            ),
            pace=request.pace.value,
            travelers_description=request.travelers.summary,
            must_include=(
                ", ".join(request.must_include) if request.must_include else "none"
            ),
            avoid=", ".join(request.avoid) if request.avoid else "none",
            transport_guidance=transport_guidance,
        )

        logger.info(
            "[Scout] Generating %d-day journey for %s",
            request.total_days,
            request.destination,
        )

        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_SCOUT_TEMPERATURE
        plan = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=JourneyPlan,
            max_tokens=LLM_DEFAULT_MAX_TOKENS,
            temperature=LLM_SCOUT_TEMPERATURE,
        )

        self._validate_plan(plan)

        # Build route string
        plan.route = (
            " → ".join([request.origin] + [c.name for c in plan.cities])
            if request.origin
            else " → ".join(c.name for c in plan.cities)
        )

        logger.info(
            "[Scout] Generated plan with %d cities: %s",
            len(plan.cities),
            plan.route or "no route",
        )

        return plan

    def _validate_plan(self, plan: JourneyPlan) -> None:
        """Validate semantic completeness of a journey plan.

        Raises:
            LLMValidationError: If the plan is semantically incomplete.
        """
        if not plan.cities:
            raise LLMValidationError("JourneyPlan", ["No cities in plan"], 1)

        for i, city in enumerate(plan.cities):
            if not city.name.strip():
                raise LLMValidationError(
                    "JourneyPlan",
                    [f"City at index {i} has empty name"],
                    1,
                )

        expected_legs = len(plan.cities) - 1
        if expected_legs > 0 and len(plan.travel_legs) != expected_legs:
            raise LLMValidationError(
                "JourneyPlan",
                [f"Expected {expected_legs} travel legs for {len(plan.cities)} cities, "
                 f"got {len(plan.travel_legs)}"],
                1,
            )
```

**Step 4: Update existing Scout tests to pass models instead of dicts**

In `backend/tests/test_agents.py`, update the existing `TestScoutAgent` tests. The mock `generate_structured` now returns a `JourneyPlan` model, not a dict:

Replace lines in `TestScoutAgent` — change all instances of:
```python
plan_data = _make_journey_plan().model_dump(mode="json")
mock_llm.generate_structured = AsyncMock(return_value=plan_data)
```
to:
```python
plan = _make_journey_plan()
mock_llm.generate_structured = AsyncMock(return_value=plan)
```

**Step 5: Run all agent tests**

Run: `cd backend && python -m pytest tests/test_agents.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add backend/app/agents/scout.py backend/tests/test_agents.py
git commit -m "feat: Scout uses validated model, adds semantic checks"
```

---

### Task 8: Simplify ReviewerAgent — use validated model directly

**Files:**
- Modify: `backend/app/agents/reviewer.py`
- Modify: `backend/tests/test_agents.py`

**Step 1: Update existing Reviewer tests to pass models instead of dicts**

In `TestReviewerAgent`, change all instances of:
```python
review_data = ReviewResult(...).model_dump(mode="json")
mock_llm.generate_structured = AsyncMock(return_value=review_data)
```
to:
```python
review = ReviewResult(...)
mock_llm.generate_structured = AsyncMock(return_value=review)
```

**Step 2: Rewrite ReviewerAgent to use validated model**

Replace `backend/app/agents/reviewer.py`:

```python
import logging

from app.models.journey import JourneyPlan, ReviewResult
from app.models.trip import TripRequest
from app.services.llm.base import LLMService
from app.prompts import journey_prompts

logger = logging.getLogger(__name__)


class ReviewerAgent:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def review(self, plan: JourneyPlan, request: TripRequest, iteration: int = 1) -> ReviewResult:
        """Review a journey plan for feasibility and quality."""
        system_prompt = journey_prompts.load("reviewer_system")

        cities_detail = self._format_cities(plan)
        travel_detail = self._format_travel(plan)

        user_prompt = journey_prompts.load("reviewer_user").format(
            total_days=plan.total_days,
            travel_dates=str(request.start_date),
            route=plan.route or "N/A",
            origin=request.origin or "not specified",
            region=request.destination,
            interests=", ".join(request.interests) if request.interests else "general sightseeing",
            pace=request.pace.value,
            cities_detail=cities_detail,
            travel_detail=travel_detail,
        )

        from app.config.planning import LLM_REVIEWER_MAX_TOKENS, LLM_REVIEWER_TEMPERATURE
        result = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ReviewResult,
            max_tokens=LLM_REVIEWER_MAX_TOKENS,
            temperature=LLM_REVIEWER_TEMPERATURE,
        )

        # Override iteration from the call parameter (not from LLM)
        result.iteration = iteration

        logger.info(
            "[Reviewer] Score: %d, acceptable: %s, issues: %d",
            result.score, result.is_acceptable, len(result.issues),
        )

        return result

    def _format_cities(self, plan: JourneyPlan) -> str:
        """Format city details for the prompt."""
        lines = []
        for i, city in enumerate(plan.cities):
            lines.append(f"{i+1}. {city.name}, {city.country} ({city.days} days)")
            if city.why_visit:
                lines.append(f"   Why: {city.why_visit}")
            if city.highlights:
                lines.append(f"   Highlights: {', '.join(h.name for h in city.highlights)}")
            if city.accommodation:
                lines.append(f"   Hotel: {city.accommodation.name}")
            if city.location:
                lines.append(f"   Location: ({city.location.lat}, {city.location.lng})")
        return "\n".join(lines) if lines else "No cities specified."

    def _format_travel(self, plan: JourneyPlan) -> str:
        """Format travel leg details for the prompt."""
        if not plan.travel_legs:
            return "No travel legs."
        lines = []
        for leg in plan.travel_legs:
            detail = f"{leg.from_city} → {leg.to_city}: {leg.mode.value}, {leg.duration_hours}h"
            if leg.distance_km:
                detail += f", {leg.distance_km}km"
            lines.append(detail)
            if leg.notes:
                lines.append(f"   Notes: {leg.notes}")
        return "\n".join(lines)
```

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add backend/app/agents/reviewer.py backend/tests/test_agents.py
git commit -m "feat: Reviewer uses validated model directly, drops manual parsing"
```

---

### Task 9: Simplify PlannerAgent — use validated model, remove fallback

**Files:**
- Modify: `backend/app/agents/planner.py`
- Modify: `backend/tests/test_agents.py`

**Step 1: Write failing test for Planner validation (no fallback)**

Append to `backend/tests/test_agents.py`:

```python
from app.agents.planner import PlannerAgent


class TestPlannerValidation:
    """Test Planner semantic validation — no silent fallback."""

    @pytest.mark.asyncio
    async def test_empty_cities_raises(self):
        """Planner raises LLMValidationError when fixed plan has no cities."""
        mock_llm = MagicMock()
        empty_plan = _make_journey_plan(cities=[], travel_legs=[])
        mock_llm.generate_structured = AsyncMock(return_value=empty_plan)

        agent = PlannerAgent(llm=mock_llm)
        original = _make_journey_plan()
        review = ReviewResult(is_acceptable=False, score=40, issues=[], summary="Bad", iteration=1)

        with pytest.raises(LLMValidationError, match="No cities"):
            await agent.fix_plan(original, review, _make_request())

    @pytest.mark.asyncio
    async def test_valid_fix_returns_plan(self):
        """Planner returns the fixed plan when valid."""
        mock_llm = MagicMock()
        fixed = _make_journey_plan(theme="Fixed Plan")
        mock_llm.generate_structured = AsyncMock(return_value=fixed)

        agent = PlannerAgent(llm=mock_llm)
        original = _make_journey_plan()
        review = ReviewResult(is_acceptable=False, score=40, issues=[], summary="Bad", iteration=1)

        result = await agent.fix_plan(original, review, _make_request())
        assert result.theme == "Fixed Plan"
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_agents.py::TestPlannerValidation -v`
Expected: FAIL

**Step 3: Rewrite PlannerAgent**

Replace `backend/app/agents/planner.py`:

```python
import logging

from app.models.journey import JourneyPlan, ReviewResult
from app.models.trip import TripRequest
from app.services.llm.base import LLMService
from app.services.llm.exceptions import LLMValidationError
from app.prompts import journey_prompts

logger = logging.getLogger(__name__)


class PlannerAgent:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def fix_plan(self, plan: JourneyPlan, review: ReviewResult, request: TripRequest) -> JourneyPlan:
        """Fix a journey plan based on reviewer feedback."""
        system_prompt = journey_prompts.load("planner_system")

        cities_detail = self._format_cities(plan)
        travel_detail = self._format_travel(plan)
        issues_text = self._format_issues(review)

        user_prompt = journey_prompts.load("planner_user").format(
            route=plan.route or "N/A",
            total_days=plan.total_days,
            issues=issues_text,
            origin=request.origin or "not specified",
            region=request.destination,
            interests=", ".join(request.interests) if request.interests else "general sightseeing",
            pace=request.pace.value,
            travel_dates=str(request.start_date),
            cities_detail=cities_detail,
            travel_detail=travel_detail,
        )

        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_DEFAULT_TEMPERATURE
        fixed = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=JourneyPlan,
            max_tokens=LLM_DEFAULT_MAX_TOKENS,
            temperature=LLM_DEFAULT_TEMPERATURE,
        )

        self._validate_plan(fixed)

        # Rebuild route string
        fixed.route = (
            " → ".join([request.origin] + [c.name for c in fixed.cities])
            if request.origin
            else " → ".join(c.name for c in fixed.cities)
        )

        return fixed

    def _validate_plan(self, plan: JourneyPlan) -> None:
        """Validate semantic completeness of a fixed journey plan."""
        if not plan.cities:
            raise LLMValidationError("JourneyPlan", ["No cities in fixed plan"], 1)

        for i, city in enumerate(plan.cities):
            if not city.name.strip():
                raise LLMValidationError(
                    "JourneyPlan",
                    [f"City at index {i} has empty name in fixed plan"],
                    1,
                )

        expected_legs = len(plan.cities) - 1
        if expected_legs > 0 and len(plan.travel_legs) != expected_legs:
            raise LLMValidationError(
                "JourneyPlan",
                [f"Expected {expected_legs} travel legs, got {len(plan.travel_legs)}"],
                1,
            )

    def _format_cities(self, plan: JourneyPlan) -> str:
        lines = []
        for i, city in enumerate(plan.cities):
            lines.append(f"{i+1}. {city.name}, {city.country} ({city.days} days)")
            if city.highlights:
                lines.append(f"   Highlights: {', '.join(h.name for h in city.highlights)}")
            if city.accommodation:
                lines.append(f"   Hotel: {city.accommodation.name}")
        return "\n".join(lines) if lines else "No cities specified."

    def _format_travel(self, plan: JourneyPlan) -> str:
        if not plan.travel_legs:
            return "No travel legs."
        lines = []
        for leg in plan.travel_legs:
            detail = f"{leg.from_city} → {leg.to_city}: {leg.mode.value}, {leg.duration_hours}h"
            if leg.distance_km:
                detail += f", {leg.distance_km}km"
            lines.append(detail)
        return "\n".join(lines)

    def _format_issues(self, review: ReviewResult) -> str:
        if not review.issues:
            return "No specific issues."
        lines = []
        for issue in review.issues:
            lines.append(f"- [{issue.severity.upper()}] {issue.description}")
            if issue.suggested_fix:
                lines.append(f"  Suggested fix: {issue.suggested_fix}")
        return "\n".join(lines)
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/agents/planner.py backend/tests/test_agents.py
git commit -m "feat: Planner uses validated model, fails hard instead of silent fallback"
```

---

### Task 10: Simplify DayPlannerAgent — add semantic validation

**Files:**
- Modify: `backend/app/agents/day_planner.py`
- Modify: `backend/tests/test_agents.py`

**Step 1: Write failing tests for DayPlanner validation**

Append to `backend/tests/test_agents.py`:

```python
from app.agents.day_planner import DayPlannerAgent
from app.models.internal import AIPlan, DayGroup, PlaceCandidate
from app.models.common import Location


def _make_candidates(n: int = 5) -> list[PlaceCandidate]:
    """Build sample PlaceCandidates."""
    return [
        PlaceCandidate(
            place_id=f"place_{i}",
            name=f"Place {i}",
            address=f"Address {i}",
            location=Location(lat=48.8 + i * 0.01, lng=2.3 + i * 0.01),
            types=["tourist_attraction"],
        )
        for i in range(n)
    ]


class TestDayPlannerValidation:
    """Test DayPlanner semantic validation."""

    @pytest.mark.asyncio
    async def test_empty_day_groups_raises(self):
        """DayPlanner raises LLMValidationError when no day groups returned."""
        mock_llm = MagicMock()
        empty_plan = AIPlan(selected_place_ids=[], day_groups=[], durations={})
        # Return empty twice (initial + retry)
        mock_llm.generate_structured = AsyncMock(return_value=empty_plan)

        agent = DayPlannerAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="No day groups"):
            await agent.plan_days(
                candidates=_make_candidates(),
                city_name="Paris",
                num_days=2,
                interests=["art"],
                pace="moderate",
            )

    @pytest.mark.asyncio
    async def test_day_with_no_places_raises(self):
        """DayPlanner raises LLMValidationError when a day group has no places."""
        mock_llm = MagicMock()
        plan = AIPlan(
            selected_place_ids=["place_0"],
            day_groups=[
                DayGroup(theme="Day 1", place_ids=["place_0"]),
                DayGroup(theme="Day 2", place_ids=[]),  # empty!
            ],
            durations={},
        )
        mock_llm.generate_structured = AsyncMock(return_value=plan)

        agent = DayPlannerAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="no places"):
            await agent.plan_days(
                candidates=_make_candidates(),
                city_name="Paris",
                num_days=2,
                interests=["art"],
                pace="moderate",
            )

    @pytest.mark.asyncio
    async def test_orphan_ids_cleaned(self):
        """Orphan place IDs are silently removed without raising."""
        mock_llm = MagicMock()
        candidates = _make_candidates(3)
        plan = AIPlan(
            selected_place_ids=["place_0", "place_1", "orphan_99"],
            day_groups=[
                DayGroup(theme="Day 1", place_ids=["place_0", "place_1", "orphan_99"]),
            ],
            durations={"place_0": 60, "orphan_99": 30},
            cost_estimates={"orphan_99": 10.0},
        )
        mock_llm.generate_structured = AsyncMock(return_value=plan)

        agent = DayPlannerAgent(llm=mock_llm)
        result = await agent.plan_days(
            candidates=candidates,
            city_name="Paris",
            num_days=1,
            interests=["art"],
            pace="moderate",
        )

        assert "orphan_99" not in result.selected_place_ids
        assert "orphan_99" not in result.day_groups[0].place_ids
        assert "orphan_99" not in result.durations
        assert "orphan_99" not in result.cost_estimates
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_agents.py::TestDayPlannerValidation -v`
Expected: FAIL

**Step 3: Rewrite DayPlannerAgent**

The key changes in `backend/app/agents/day_planner.py`:
- `plan_days()` receives `AIPlan` model directly from `generate_structured`
- Drop `_parse_plan()` method entirely
- Add `_validate_ai_plan()` for semantic checks
- Keep `_deduplicate_plan()` and `_build_user_prompt()` unchanged
- Keep orphan cleanup (not a hard error)

Replace `_parse_plan` and surrounding logic. The `plan_days` method should be updated as follows — replace from `data = await self.llm.generate_structured(...)` through the end of the method:

```python
    async def plan_days(
        self,
        candidates: list[PlaceCandidate],
        city_name: str,
        num_days: int,
        interests: list[str],
        pace: str,
        budget: str = "moderate",
        daily_budget_usd: float | None = None,
        must_include: list[str] | None = None,
        time_constraints: list[dict] | None = None,
        travelers_description: str = "1 adult",
    ) -> AIPlan:
        """Given discovered place candidates, select and group into themed days."""
        system_prompt = day_plan_prompts.load("planning_system")
        user_prompt = self._build_user_prompt(
            candidates, city_name, num_days, interests, pace,
            budget=budget, daily_budget_usd=daily_budget_usd,
            must_include=must_include, time_constraints=time_constraints,
            travelers_description=travelers_description,
        )

        logger.info(
            "[DayPlanner] Planning %d day(s) in %s (%d candidates, pace=%s)",
            num_days, city_name, len(candidates), pace,
        )

        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_DEFAULT_TEMPERATURE
        plan = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=AIPlan,
            max_tokens=LLM_DEFAULT_MAX_TOKENS,
            temperature=LLM_DEFAULT_TEMPERATURE,
        )

        # Derive selected_place_ids from day_groups if empty
        if not plan.selected_place_ids and plan.day_groups:
            seen: set[str] = set()
            ids: list[str] = []
            for group in plan.day_groups:
                for pid in group.place_ids:
                    if pid not in seen:
                        seen.add(pid)
                        ids.append(pid)
            plan.selected_place_ids = ids

        # Semantic validation
        valid_ids = {c.place_id for c in candidates}
        self._validate_ai_plan(plan, valid_ids)

        # Deduplicate
        plan = self._deduplicate_plan(plan, candidates)

        # Clean orphan IDs (soft — not a hard error)
        orphan_ids = [pid for pid in plan.selected_place_ids if pid not in valid_ids]
        if orphan_ids:
            logger.warning(
                "[DayPlanner] %d orphan place_ids not in candidates: %s",
                len(orphan_ids), orphan_ids[:5],
            )
            plan.selected_place_ids = [pid for pid in plan.selected_place_ids if pid in valid_ids]
            for group in plan.day_groups:
                group.place_ids = [pid for pid in group.place_ids if pid in valid_ids]
            for oid in orphan_ids:
                plan.cost_estimates.pop(oid, None)
                plan.durations.pop(oid, None)

        # Validate dining presence per day
        dining_ids = {c.place_id for c in candidates if _is_dining(c)}
        for i, group in enumerate(plan.day_groups):
            day_dining = [pid for pid in group.place_ids if pid in dining_ids]
            if len(day_dining) == 0:
                logger.warning(
                    "[DayPlanner] Day %d (%s) has NO dining places",
                    i + 1, group.theme,
                )

        logger.info(
            "[DayPlanner] LLM selected %d places across %d day groups",
            len(plan.selected_place_ids), len(plan.day_groups),
        )

        return plan

    def _validate_ai_plan(self, plan: AIPlan, valid_ids: set[str]) -> None:
        """Validate semantic completeness of an AI plan.

        Raises:
            LLMValidationError: If the plan is structurally incomplete.
        """
        if not plan.day_groups:
            raise LLMValidationError("AIPlan", ["No day groups returned"], 1)

        for i, group in enumerate(plan.day_groups):
            # Filter to only valid IDs before checking emptiness
            valid_place_ids = [pid for pid in group.place_ids if pid in valid_ids]
            if not valid_place_ids:
                raise LLMValidationError(
                    "AIPlan",
                    [f"Day {i + 1} ({group.theme}) has no places after orphan removal"],
                    1,
                )
```

Also remove the old `_parse_plan` method entirely. Keep `_deduplicate_plan` and `_build_user_prompt` unchanged.

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/agents/day_planner.py backend/tests/test_agents.py
git commit -m "feat: DayPlanner uses validated model, adds semantic validation"
```

---

### Task 11: Update ChatService for new generate_structured return type

**Files:**
- Modify: `backend/app/services/chat.py`

**Step 1: Update ChatService to handle model return type**

The chat service calls `generate_structured` with `schema=ChatEditResponse`, which returns a `ChatEditResponse` model with fields like `updated_journey` (already a `JourneyPlan | None`). The current code manually parses a dict — we can now use the model directly.

In `backend/app/services/chat.py`, update `edit_journey` method — replace from `raw = await self.llm.generate_structured(...)` to end of method:

```python
        result = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ChatEditResponse,
            max_tokens=8000,
            temperature=0.7,
        )

        return result
```

Update `edit_day_plans` method similarly — replace from `raw = await self.llm.generate_structured(...)` to end of method:

```python
        result = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ChatEditResponse,
            max_tokens=12000,
            temperature=0.7,
        )

        return result
```

Note: `ChatEditResponse` has `reply: str` as required. If the LLM uses `assistant_message` or `understood_request` instead, it will now fail validation. Check the chat prompt templates to confirm the LLM is instructed to use the `reply` field name. If the prompts use different field names, add `model_validator` or field aliases to `ChatEditResponse`.

**Step 2: Run existing chat tests**

Run: `cd backend && python -m pytest tests/test_services.py -v -k "chat"`
Expected: PASS (or adjust if needed)

**Step 3: Commit**

```bash
git add backend/app/services/chat.py
git commit -m "feat: ChatService uses validated model from generate_structured"
```

---

### Task 12: Update DayPlanOrchestrator retry logic

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py`

**Step 1: Update the orchestrator**

The day plan orchestrator currently retries when `ai_plan.day_groups` is empty (lines 207-225). With the new DayPlannerAgent validation, empty day groups now raise `LLMValidationError`. Update the retry logic:

In `backend/app/orchestrators/day_plan.py`, replace the AI planning try/except block (lines 193-239):

```python
                from app.services.llm.exceptions import LLMValidationError
                try:
                    ai_plan = await self.day_planner.plan_days(
                        candidates=candidates,
                        city_name=city_name,
                        num_days=city.days,
                        interests=request.interests,
                        pace=request.pace.value,
                        budget=request.budget.value if hasattr(request, 'budget') else "moderate",
                        daily_budget_usd=(request.budget_usd / request.total_days) if request.budget_usd else None,
                        must_include=request.must_include if request.must_include else None,
                        time_constraints=time_constraints if time_constraints else None,
                        travelers_description=request.travelers.summary,
                    )
                except LLMValidationError:
                    # Retry once on validation failure
                    logger.warning(
                        "[DayPlanOrchestrator] Validation failed for %s, retrying...",
                        city_name,
                    )
                    try:
                        ai_plan = await self.day_planner.plan_days(
                            candidates=candidates,
                            city_name=city_name,
                            num_days=city.days,
                            interests=request.interests,
                            pace=request.pace.value,
                            budget=request.budget.value if hasattr(request, 'budget') else "moderate",
                            daily_budget_usd=(request.budget_usd / request.total_days) if request.budget_usd else None,
                            must_include=request.must_include if request.must_include else None,
                            time_constraints=time_constraints if time_constraints else None,
                            travelers_description=request.travelers.summary,
                        )
                    except (LLMValidationError, Exception) as exc:
                        logger.error(
                            "[DayPlanOrchestrator] AI planning failed for %s after retry: %s",
                            city_name, exc,
                        )
                        day_offset += city.days
                        yield ProgressEvent(
                            phase="city_complete",
                            message=f"{city_name}: AI planning failed",
                            progress=pct_end,
                            data={"city": city_name, "day_plans": []},
                        )
                        continue
                except Exception as exc:
                    logger.error(
                        "[DayPlanOrchestrator] AI planning failed for %s: %s",
                        city_name, exc,
                    )
                    day_offset += city.days
                    yield ProgressEvent(
                        phase="city_complete",
                        message=f"{city_name}: AI planning failed",
                        progress=pct_end,
                        data={"city": city_name, "day_plans": []},
                    )
                    continue
```

**Step 2: Run tests**

Run: `cd backend && python -m pytest tests/ -v --timeout=60`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add backend/app/orchestrators/day_plan.py
git commit -m "feat: DayPlanOrchestrator retries on LLMValidationError"
```

---

### Task 13: Run full test suite and fix any breakage

**Step 1: Run all 164 tests**

Run: `cd backend && python -m pytest tests/ -v --timeout=120`
Expected: All 164 tests PASS

If any test fails, the most likely cause is:
- A test that mocked `generate_structured` to return a `dict` but now the agent expects a Pydantic model — fix by returning the model instead
- A test using `MockLLMService` from conftest that hits a schema it can't construct — add specific mock overrides

**Step 2: Fix any failing tests**

Address each failure by updating the mock return value from `dict` to the appropriate Pydantic model.

**Step 3: Commit**

```bash
git add -u
git commit -m "fix: update remaining tests for validated model return type"
```

---

### Task 14: Final verification and cleanup

**Step 1: Run full test suite once more**

Run: `cd backend && python -m pytest tests/ -v --timeout=120`
Expected: All tests PASS

**Step 2: Run linting**

Run: `cd frontend && npm run build && npm run lint`
Expected: PASS (no frontend changes, but verify nothing broke)

**Step 3: Verify no regressions in imports**

Run: `cd backend && python -c "from app.services.llm import LLMService, LLMValidationError, create_llm_service; print('OK')"`
Expected: `OK`

**Step 4: Commit any final fixes**

```bash
git add -u
git commit -m "chore: final cleanup for LLM output validation"
```
