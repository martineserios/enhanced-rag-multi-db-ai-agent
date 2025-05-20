"""
Application configuration settings.

This module defines the configuration schema for the application using Pydantic
for type validation and environment variable loading.
"""
import os
from functools import lru_cache
from typing import Dict, List, Any, Optional, Literal
from enum import Enum
import logging
import json

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Valid logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application configuration settings.
    
    This class uses Pydantic to load and validate configuration from environment
    variables, with sensible defaults.
    """
    # Application settings
    app_name: str = Field(default="Memory-Enhanced RAG Chatbot", env="APP_NAME")
    llm_providers: List[str] = Field(
        default_factory=lambda: [provider.value for provider in LLMProvider],
        env="LLM_PROVIDERS"
    )
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    default_agent_id: str = Field(default="standard", env="DEFAULT_AGENT_ID")
    
    # Logging settings 