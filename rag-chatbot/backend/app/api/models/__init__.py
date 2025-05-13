# filepath: backend/app/api/models/__init__.py
"""
API models package.

This package contains Pydantic models for API requests and responses,
ensuring proper validation and serialization.
"""
from app.api.models.chat import (
    ChatRequest, ChatResponse, StreamChatResponse,
    ConversationMessage, ConversationSummary,
    ConversationListResponse, ConversationHistoryResponse,
    ConversationDeleteResponse, LLMProvider, ChatMessage
)

from app.api.models.documents import (
    DocumentUploadRequest, DocumentUploadResponse,
    DocumentResponse, DocumentListResponse,
    DocumentSearchRequest, DocumentSearchResponse,
    DocumentChunkResponse, DocumentDeleteResponse,
    DocumentMetadata, DocumentChunk, DocumentFormat,
    DocumentSearchResultItem
)

from app.api.models.memory import (
    MemoryType, MemorySystemInfo, MemoryTypesResponse,
    MemoryHealthResponse, MemoryItem, MemoryQueryRequest,
    MemoryQueryResponse, UnifiedContextResponse,
    ShortTermMemoryResponse, EpisodicMemoryResponse,
    ProceduralMemoryResponse, ProceduralMemoryCreateRequest,
    ProceduralMemoryCreateResponse, ShortTermMemoryItem,
    EpisodicMemoryItem, ProceduralMemoryItem, ProceduralStep,
    SemanticMemoryItem
)

__all__ = [
    # Chat models
    'ChatRequest', 'ChatResponse', 'StreamChatResponse',
    'ConversationMessage', 'ConversationSummary',
    'ConversationListResponse', 'ConversationHistoryResponse',
    'ConversationDeleteResponse', 'LLMProvider', 'ChatMessage',
    
    # Document models
    'DocumentUploadRequest', 'DocumentUploadResponse',
    'DocumentResponse', 'DocumentListResponse',
    'DocumentSearchRequest', 'DocumentSearchResponse',
    'DocumentChunkResponse', 'DocumentDeleteResponse',
    'DocumentMetadata', 'DocumentChunk', 'DocumentFormat',
    'DocumentSearchResultItem',
    
    # Memory models
    'MemoryType', 'MemorySystemInfo', 'MemoryTypesResponse',
    'MemoryHealthResponse', 'MemoryItem', 'MemoryQueryRequest',
    'MemoryQueryResponse', 'UnifiedContextResponse',
    'ShortTermMemoryResponse', 'EpisodicMemoryResponse',
    'ProceduralMemoryResponse', 'ProceduralMemoryCreateRequest',
    'ProceduralMemoryCreateResponse', 'ShortTermMemoryItem',
    'EpisodicMemoryItem', 'ProceduralMemoryItem', 'ProceduralStep',
    'SemanticMemoryItem'
]