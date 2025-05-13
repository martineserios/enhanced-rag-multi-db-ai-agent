# filepath: backend/app/api/models/memory.py
"""
Pydantic models for memory-related API endpoints.

This module defines the request and response models for memory operations,
ensuring proper validation and serialization.
"""
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator


class MemoryType(str, Enum):
    """Supported memory types."""
    SHORT_TERM = "short_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class MemorySystemInfo(BaseModel):
    """Information about a memory system."""
    name: str
    description: str
    enabled: bool
    parameters: Dict[str, Any] = Field(default_factory=dict)


class MemoryTypesResponse(BaseModel):
    """Response model for memory types endpoint."""
    enabled: bool
    types: Dict[str, MemorySystemInfo]
    weights: Dict[str, float] = Field(default_factory=dict)


class MemoryHealthResponse(BaseModel):
    """Response model for memory health check endpoint."""
    status: Dict[str, bool]


class MemoryItem(BaseModel):
    """Model for a memory item."""
    key: str
    content: Any
    memory_type: MemoryType
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ShortTermMemoryItem(BaseModel):
    """Model for a short-term memory item."""
    key: str
    user_message: str
    assistant_message: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EpisodicMemoryItem(BaseModel):
    """Model for an episodic memory item."""
    key: str
    conversation_id: str
    user_message: str
    assistant_message: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProceduralStep(BaseModel):
    """Model for a step in a procedure."""
    description: str
    action: Optional[str] = None
    order: int
    id: Optional[str] = None


class ProceduralMemoryItem(BaseModel):
    """Model for a procedural memory item."""
    name: str
    steps: List[ProceduralStep]
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticMemoryItem(BaseModel):
    """Model for a semantic memory item."""
    key: str
    content: str
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    relevance_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryQueryRequest(BaseModel):
    """Request model for multi-context memory queries."""
    query: str
    conversation_id: Optional[str] = None
    memory_types: Optional[List[MemoryType]] = None
    weights: Optional[Dict[str, float]] = None
    limit_per_type: int = Field(5, ge=1, le=20)


class MemoryQueryResponse(BaseModel):
    """Response model for memory query endpoint."""
    query: str
    conversation_id: Optional[str] = None
    results: Dict[str, List[Any]]


class UnifiedContextResponse(BaseModel):
    """Response model for unified context endpoint."""
    query: str
    conversation_id: Optional[str] = None
    context: str
    context_length: int


class ShortTermMemoryResponse(BaseModel):
    """Response model for short-term memory endpoint."""
    conversation_id: str
    memory_type: Literal["short_term"]
    items: List[ShortTermMemoryItem]


class EpisodicMemoryResponse(BaseModel):
    """Response model for episodic memory endpoint."""
    conversation_id: Optional[str]
    keyword: Optional[str]
    memory_type: Literal["episodic"]
    items: List[EpisodicMemoryItem]


class ProceduralMemoryResponse(BaseModel):
    """Response model for procedural memory endpoint."""
    name: str
    memory_type: Literal["procedural"]
    procedure: ProceduralMemoryItem


class ProceduralMemoryCreateRequest(BaseModel):
    """Request model for creating a procedure."""
    name: str
    steps: List[ProceduralStep]
    metadata: Optional[Dict[str, Any]] = None


class ProceduralMemoryCreateResponse(BaseModel):
    """Response model for procedure creation endpoint."""
    status: str
    message: str
    procedure_id: str
    step_count: int