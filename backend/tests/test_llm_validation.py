"""Tests for LLM service schema validation and retry logic."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from app.services.llm.azure_openai import AzureOpenAILLMService
from app.services.llm.anthropic import AnthropicLLMService
from app.services.llm.gemini import GeminiLLMService
from app.services.llm.exceptions import LLMValidationError


class SampleModel(BaseModel):
    name: str
    score: int = Field(..., ge=0, le=100)


# ═══════════════════════════════════════════════════════════════
# Azure OpenAI
# ═══════════════════════════════════════════════════════════════

class TestAzureOpenAIValidation:
    def _make_service(self) -> AzureOpenAILLMService:
        return AzureOpenAILLMService(
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            deployment="gpt-4-test",
            api_version="2024-02-15-preview",
        )

    def _mock_response(self, content: str) -> MagicMock:
        msg = MagicMock()
        msg.content = content
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    @pytest.mark.asyncio
    async def test_returns_validated_model(self):
        svc = self._make_service()
        svc.client = MagicMock()
        svc.client.chat.completions.create = AsyncMock(
            return_value=self._mock_response(json.dumps({"name": "test", "score": 85}))
        )
        result = await svc.generate_structured(
            system_prompt="test", user_prompt="test", schema=SampleModel,
        )
        assert isinstance(result, SampleModel)
        assert result.name == "test"
        assert result.score == 85

    @pytest.mark.asyncio
    async def test_retries_on_validation_error_then_succeeds(self):
        svc = self._make_service()
        bad_json = json.dumps({"name": "test"})  # missing score
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
        svc = self._make_service()
        bad_json = json.dumps({"name": "test"})  # always missing score
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
        assert exc_info.value.attempts == 3


# ═══════════════════════════════════════════════════════════════
# Anthropic
# ═══════════════════════════════════════════════════════════════

class TestAnthropicValidation:
    def _make_service(self) -> AnthropicLLMService:
        return AnthropicLLMService(api_key="test-key", model="claude-test")

    def _mock_response(self, tool_input: dict) -> MagicMock:
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

    @pytest.mark.asyncio
    async def test_no_tool_use_block_retries(self):
        svc = self._make_service()
        no_tool = MagicMock()
        no_tool.content = [MagicMock(type="text")]
        good = self._mock_response({"name": "ok", "score": 50})
        svc.client = MagicMock()
        svc.client.messages.create = AsyncMock(side_effect=[no_tool, good])
        result = await svc.generate_structured(
            system_prompt="test", user_prompt="test", schema=SampleModel, max_retries=1,
        )
        assert isinstance(result, SampleModel)


# ═══════════════════════════════════════════════════════════════
# Gemini
# ═══════════════════════════════════════════════════════════════

class TestGeminiValidation:
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
