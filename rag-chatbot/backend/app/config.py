# filepath: backend/app/config.py
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


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


from typing import List

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
    
    # Logging settings
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_json: bool = Field(default=True, env="LOG_JSON")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # LLM API keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    
    # Default LLM provider
    default_llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI, env="DEFAULT_LLM_PROVIDER"
    )
    
    # Model names
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    groq_model: str = Field(default="llama-3.3-70b-versatile", env="GROQ_MODEL")
    
    # Embedding model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        env="EMBEDDING_MODEL"
    )
    
    # Database URIs and credentials
    # MongoDB (Episodic Memory)
    mongo_uri: str = Field(default="mongodb://mongo:27017/ragchatbot", env="MONGO_URI")
    mongo_db_name: str = Field(default="ragchatbot", env="MONGO_DB_NAME")
    
    # PostgreSQL (Relational Database)
    postgres_uri: str = Field(
        default="postgresql://postgres:postgres@postgres:5432/ragchatbot", 
        env="POSTGRES_URI"
    )
    
    # Redis (Short-term Memory)
    redis_host: str = Field(default="redis", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # ChromaDB (Semantic Memory)
    chroma_host: str = Field(default="chroma", env="CHROMA_HOST")
    chroma_port: int = Field(default=8000, env="CHROMA_PORT")
    
    # Neo4j (Procedural Memory)
    neo4j_uri: str = Field(default="neo4j://neo4j:7687", env="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(default="password", env="NEO4J_PASSWORD")
    
    # Text chunking settings
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # Memory settings
    memory_enabled: bool = Field(default=True, env="MEMORY_ENABLED")
    enable_short_term_memory: bool = Field(default=True, env="ENABLE_SHORT_TERM_MEMORY")
    enable_semantic_memory: bool = Field(default=True, env="ENABLE_SEMANTIC_MEMORY")
    enable_episodic_memory: bool = Field(default=True, env="ENABLE_EPISODIC_MEMORY")
    enable_procedural_memory: bool = Field(default=True, env="ENABLE_PROCEDURAL_MEMORY")
    short_term_ttl: int = Field(default=3600, env="SHORT_TERM_TTL")  # 1 hour
    memory_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "short_term": 1.0,
            "semantic": 1.0,
            "episodic": 0.5,
            "procedural": 0.8
        },
        env="MEMORY_WEIGHTS"
    )
    
    # Service retry and timeout settings
    retry_attempts: int = Field(default=3, env="RETRY_ATTEMPTS")
    retry_delay: float = Field(default=0.5, env="RETRY_DELAY")  # seconds
    request_timeout: float = Field(default=30.0, env="REQUEST_TIMEOUT")  # seconds
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string to list if necessary."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("memory_weights", mode="before")
    @classmethod
    def parse_memory_weights(cls, v):
        """Parse memory weights from string to dict if necessary."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Default weights
                return {
                    "short_term": 1.0,
                    "semantic": 1.0,
                    "episodic": 0.5,
                    "procedural": 0.8
                }
        return v
    
    @model_validator(mode="after")
    def validate_llm_provider(self):
        """Validate that the selected LLM provider has an API key."""
        if self.default_llm_provider == LLMProvider.OPENAI and not self.openai_api_key:
            self.default_llm_provider = next(
                (p for p in [LLMProvider.ANTHROPIC, LLMProvider.GROQ] 
                 if getattr(self, f"{p.value}_api_key")),
                LLMProvider.OPENAI
            )
        return self
    
    @model_validator(mode="after")
    def extract_db_names(self):
        """Extract database names from URIs."""
        # Extract MongoDB database name from URI if not explicitly set
        if "://" in self.mongo_uri and not self.mongo_db_name:
            db_name = self.mongo_uri.split("/")[-1]
            if db_name and "?" not in db_name:
                self.mongo_db_name = db_name
        return self
    
    def get_log_level(self) -> int:
        """Convert string log level to logging module constant."""
        return getattr(logging, self.log_level.upper())
    
    def get_enabled_memory_types(self) -> List[str]:
        """Get list of enabled memory types."""
        memory_types = []
        if self.enable_short_term_memory:
            memory_types.append("short_term")
        if self.enable_semantic_memory:
            memory_types.append("semantic")
        if self.enable_episodic_memory:
            memory_types.append("episodic")
        if self.enable_procedural_memory:
            memory_types.append("procedural")
        return memory_types


@lru_cache()
def get_settings() -> Settings:
    """
    Create and cache settings instance.
    
    Returns:
        Application settings from environment variables
    """
    return Settings()


# Pydantic models for API

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    conversation_id: Optional[str] = None
    provider: Optional[LLMProvider] = None
    use_rag: bool = True
    use_sql: bool = False
    use_mongo: bool = False
    use_memory: bool = True
    memory_types: Optional[List[str]] = None
    memory_weights: Optional[Dict[str, float]] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    message: str
    conversation_id: str
    provider: LLMProvider
    memory_sources: Dict[str, bool] = {}


class MemoryItem(BaseModel):
    """Model for a memory item."""
    key: str
    content: Any
    memory_type: str
    timestamp: str
    metadata: Dict[str, Any] = {}


class MultiMemoryQuery(BaseModel):
    """Request model for querying multiple memory systems."""
    query: str
    conversation_id: Optional[str] = None
    memory_types: Optional[List[str]] = None
    weights: Optional[Dict[str, float]] = None
    limit_per_type: int = 5


class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    document_id: str
    filename: str
    status: str
    message: str