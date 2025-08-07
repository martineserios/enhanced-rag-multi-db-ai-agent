"""
Configuration management for GlabitAI Backend

Handles environment variables and application settings
with medical AI specific configuration.
"""

from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import field_validator, ConfigDict


class Settings(BaseSettings):
    """Application settings with medical AI configuration."""

    # Application settings
    APP_NAME: str = "GlabitAI Medical Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # API Keys for medical AI services
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # Medical AI model configuration
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 1500
    OPENAI_TEMPERATURE: float = 0.3  # Conservative for medical accuracy

    # Groq model configuration
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Medical conversation settings
    MAX_CONVERSATION_HISTORY: int = 10
    CONVERSATION_TIMEOUT_MINUTES: int = 30

    # Medical safety settings
    ENABLE_MEDICAL_VALIDATION: bool = True
    MEDICAL_DISCLAIMER: str = (
        "Esta información es solo para fines educativos y no reemplaza "
        "el consejo médico profesional. Consulte siempre con su médico."
    )

    # Language support
    DEFAULT_LANGUAGE: str = "es"  # Spanish primary
    SUPPORTED_LANGUAGES: str = "es,en"

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Database settings
    MONGO_URI: Optional[str] = None

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_api_key(cls, v):
        """Validate OpenAI API key format."""
        if v and not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")
        return v

    @field_validator("OPENAI_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v):
        """Ensure temperature is appropriate for medical use."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        if v > 0.5:
            # Log warning for high temperature in medical context
            import logging

            logging.getLogger(__name__).warning(
                f"High temperature ({v}) may reduce medical accuracy"
            )
        return v

    @field_validator("DEFAULT_LANGUAGE")
    @classmethod
    def validate_default_language(cls, v):
        """Ensure default language is supported."""
        supported = [
            "es",
            "en",
        ]  # Use static list since SUPPORTED_LANGUAGES not available in validator
        if v not in supported:
            raise ValueError(
                f"Default language '{v}' must be in supported languages: {supported}"
            )
        return v

    @property
    def supported_languages_list(self) -> list:
        """Get supported languages as a list."""
        return [lang.strip() for lang in self.SUPPORTED_LANGUAGES.split(",")]

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Uses lru_cache to ensure settings are loaded once and cached.
    """
    return Settings()
