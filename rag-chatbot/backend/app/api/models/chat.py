# filepath: backend/app/api/models/chat.py
"""
Pydantic models for chat-related API endpoints.

This module defines the request and response models for chat operations,
ensuring proper validation and serialization.
"""
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class ChatMessage(BaseModel):
    """Model for a chat message."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[str] = None


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
    stream: bool = False
    system_prompt: Optional[str] = None
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    message: str
    conversation_id: str
    provider: LLMProvider
    memory_sources: Dict[str, bool] = Field(default_factory=dict)
    timestamp: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    processing_time_ms: Optional[float] = None


class StreamChatResponse(BaseModel):
    """Response model for streaming chat."""
    message_chunk: str
    conversation_id: str
    provider: LLMProvider
    is_complete: bool = False


class ConversationMessage(BaseModel):
    """Model for a message in a conversation."""
    message_id: str
    conversation_id: str
    user_message: str
    assistant_message: str
    timestamp: str
    memory_sources: Optional[Dict[str, bool]] = None
    provider: Optional[LLMProvider] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSummary(BaseModel):
    """Summary of a conversation."""
    conversation_id: str
    latest_message: str
    latest_response: str
    latest_time: str
    message_count: int
    title: Optional[str] = None


class ConversationListResponse(BaseModel):
    """Response model for listing conversations."""
    conversations: List[ConversationSummary]
    total_count: Optional[int] = None


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""
    conversation_id: str
    message_count: int
    messages: List[ConversationMessage]
    title: Optional[str] = None


class ConversationDeleteResponse(BaseModel):
    """Response model for conversation deletion."""
    conversation_id: str
    status: str
    message: str