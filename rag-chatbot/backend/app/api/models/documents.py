# filepath: backend/app/api/models/documents.py
"""
Pydantic models for document-related API endpoints.

This module defines the request and response models for document operations,
ensuring proper validation and serialization.
"""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class DocumentFormat(str, Enum):
    """Supported document formats."""
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    HTML = "html"
    MD = "md"
    PPT = "ppt"
    PPTX = "pptx"
    JSON = "json"


class DocumentMetadata(BaseModel):
    """Metadata for documents."""
    author: Optional[str] = None
    created_at: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    description: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """Representation of a document chunk."""
    chunk_id: str
    document_id: str
    content: str
    metadata: Optional[DocumentMetadata] = None
    chunk_index: int = 0
    total_chunks: int = 1
    embedding: Optional[List[float]] = None
    score: Optional[float] = None


class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    description: Optional[str] = None
    chunk_size: int = Field(1000, ge=100, le=10000)
    chunk_overlap: int = Field(200, ge=0, le=5000)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('tags', pre=True)
    def parse_tags(cls, v):
        """Parse tags from string if needed."""
        if isinstance(v, str):
            return [tag.strip() for tag in v.split(',') if tag.strip()]
        return v


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    document_id: str
    filename: str
    status: str
    message: str
    chunk_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Optional[DocumentMetadata] = None


class DocumentResponse(BaseModel):
    """Response model for document information."""
    document_id: str
    filename: str
    upload_date: str
    metadata: Optional[DocumentMetadata] = None
    chunk_count: int = 0
    file_type: Optional[str] = None
    file_size: Optional[int] = None


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    documents: List[DocumentResponse]
    total_count: int
    page: int = 1
    page_size: int = 100


class DocumentSearchRequest(BaseModel):
    """Request model for document search."""
    query: str
    limit: int = Field(10, ge=1, le=100)
    filter_tags: Optional[List[str]] = None
    filter_metadata: Optional[Dict[str, Any]] = None


class DocumentSearchResultItem(BaseModel):
    """An individual document search result."""
    document_id: str
    filename: str
    chunk_id: str
    content: str
    score: float
    metadata: Optional[DocumentMetadata] = None


class DocumentSearchResponse(BaseModel):
    """Response model for document search."""
    query: str
    results: List[DocumentSearchResultItem]
    total_results: int
    processing_time_ms: float


class DocumentChunkResponse(BaseModel):
    """Response model for document chunks."""
    document_id: str
    chunk_count: int
    chunks: List[DocumentChunk]


class DocumentDeleteResponse(BaseModel):
    """Response model for document deletion."""
    document_id: str
    status: str
    message: str
    file_deleted: bool = False