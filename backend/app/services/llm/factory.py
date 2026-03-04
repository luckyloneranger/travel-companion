from app.config.settings import Settings

from .anthropic import AnthropicLLMService
from .azure_openai import AzureOpenAILLMService
from .base import LLMService
from .gemini import GeminiLLMService


def create_llm_service(settings: Settings) -> LLMService:
    if settings.llm_provider == "anthropic":
        return AnthropicLLMService(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )
    elif settings.llm_provider == "gemini":
        return GeminiLLMService(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
    else:
        return AzureOpenAILLMService(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
        )
