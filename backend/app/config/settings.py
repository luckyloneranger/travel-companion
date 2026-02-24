"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Azure OpenAI Configuration
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4"
    azure_openai_api_version: str = "2024-02-15-preview"

    # Google APIs Configuration
    google_places_api_key: str = ""
    google_routes_api_key: str = ""

    # Application Configuration
    app_env: str = "development"
    debug: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    log_level: str = "INFO"

    @field_validator('azure_openai_endpoint')
    @classmethod
    def validate_azure_endpoint(cls, v: str) -> str:
        """Validate Azure OpenAI endpoint is provided."""
        if not v:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT is required. "
                "Set it in your .env file or environment variables."
            )
        return v

    @field_validator('azure_openai_api_key')
    @classmethod
    def validate_azure_api_key(cls, v: str) -> str:
        """Validate Azure OpenAI API key is provided."""
        if not v:
            raise ValueError(
                "AZURE_OPENAI_API_KEY is required. "
                "Set it in your .env file or environment variables."
            )
        return v

    @field_validator('google_places_api_key')
    @classmethod
    def validate_places_api_key(cls, v: str) -> str:
        """Validate Google Places API key is provided."""
        if not v:
            raise ValueError(
                "GOOGLE_PLACES_API_KEY is required. "
                "Set it in your .env file or environment variables."
            )
        return v

    @field_validator('google_routes_api_key')
    @classmethod
    def validate_routes_api_key(cls, v: str) -> str:
        """Validate Google Routes API key is provided."""
        if not v:
            raise ValueError(
                "GOOGLE_ROUTES_API_KEY is required. "
                "Set it in your .env file or environment variables."
            )
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
