"""
Test configuration for Redis tests.

This module provides test-specific configuration for Redis-related tests.
"""
import os
from pathlib import Path
from typing import Any, Dict

from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict

from app.config import Settings as BaseSettings


class TestSettings(BaseSettings):
    """Test settings that override the base settings for testing."""
    
    # Override debug to ensure it's a boolean
    debug: bool = True
    
    # Redis settings for testing
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_db: int = 1  # Use a different DB for tests
    
    # Memory settings for testing
    memory_enabled: bool = True
    enable_short_term_memory: bool = True
    enable_semantic_memory: bool = False
    enable_episodic_memory: bool = False
    enable_procedural_memory: bool = False
    
    # Disable other services for faster tests
    enable_sql: bool = False
    enable_mongo: bool = False
    enable_neo4j: bool = False
    enable_chroma: bool = False
    
    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="TEST_"  # Use TEST_ prefix for test-specific env vars
    )
    
    @field_validator('debug', mode='before')
    def parse_debug(cls, v: Any) -> bool:
        """Ensure debug is always a boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 't', 'y', 'yes')
        return bool(v)


def get_test_settings() -> TestSettings:
    """
    Get test settings with environment variables overrides.
    
    This ensures that environment variables are properly loaded and
    the debug setting is always a boolean.
    """
    # Create a temporary environment with DEBUG set to a boolean
    env = os.environ.copy()
    if 'DEBUG' in env:
        env['DEBUG'] = 'true' if env['DEBUG'].lower() in ('true', '1', 't', 'y', 'yes') else 'false'
    
    # Create settings with the modified environment
    return TestSettings(_env_file='.env.test', _env_file_encoding='utf-8')
