# filepath: backend/core/exceptions.py
"""
Custom exception hierarchy for the application.

This module defines a set of custom exceptions to represent different
error conditions in a structured and consistent way.
"""
from typing import Dict, Any, Optional, List, Union
from http import HTTPStatus


class BaseAppException(Exception):
    """
    Base exception for all application-specific exceptions.
    
    All custom exceptions in the application should inherit from this class
    to ensure consistent handling and formatting.
    """
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred"
    
    def __init__(
        self, 
        detail: Optional[str] = None, 
        status_code: Optional[int] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize the exception with custom details.
        
        Args:
            detail: A human-readable explanation of the error
            status_code: HTTP status code to return to the client
            errors: Additional error details as a list of dictionaries
        """
        self.detail = detail or self.detail
        self.status_code = status_code or self.status_code
        self.errors = errors or []
        super().__init__(self.detail)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the exception to a dictionary for API responses.
        
        Returns:
            A dictionary representation of the exception
        """
        result = {
            "status_code": self.status_code,
            "detail": self.detail
        }
        
        if self.errors:
            result["errors"] = self.errors
            
        return result


# Service-specific exceptions

class ServiceConnectionError(BaseAppException):
    """Exception raised when a service connection fails."""
    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    detail = "Failed to connect to a required service"


class ServiceTimeoutError(BaseAppException):
    """Exception raised when a service request times out."""
    status_code = HTTPStatus.GATEWAY_TIMEOUT
    detail = "Service request timed out"


# Memory-related exceptions

class MemoryError(BaseAppException):
    """Base exception for memory-related errors."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "Memory operation failed"


class MemoryInitializationError(MemoryError):
    """Exception raised when memory system initialization fails."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "Failed to initialize memory system"


class MemoryStorageError(MemoryError):
    """Exception raised when storing in memory fails."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "Failed to store data in memory"


class MemoryRetrievalError(MemoryError):
    """Exception raised when retrieving from memory fails."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "Failed to retrieve data from memory"


class MemoryNotFoundError(MemoryError):
    """Exception raised when requested memory is not found."""
    status_code = HTTPStatus.NOT_FOUND
    detail = "Requested memory not found"


# LLM-related exceptions

class LLMError(BaseAppException):
    """Base exception for LLM-related errors."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "LLM operation failed"


class LLMProviderError(LLMError):
    """Exception raised when an LLM provider is unavailable."""
    status_code = HTTPStatus.BAD_REQUEST
    detail = "LLM provider not available or not configured"


class LLMRequestError(LLMError):
    """Exception raised when an LLM request fails."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "LLM request failed"


class LLMRateLimitError(LLMError):
    """Exception raised when an LLM rate limit is reached."""
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    detail = "LLM rate limit exceeded"


# Document-related exceptions

class DocumentError(BaseAppException):
    """Base exception for document-related errors."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "Document operation failed"


class DocumentProcessingError(DocumentError):
    """Exception raised when document processing fails."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "Failed to process document"


class DocumentNotFoundError(DocumentError):
    """Exception raised when requested document is not found."""
    status_code = HTTPStatus.NOT_FOUND
    detail = "Document not found"


class UnsupportedDocumentTypeError(DocumentError):
    """Exception raised when document type is not supported."""
    status_code = HTTPStatus.BAD_REQUEST
    detail = "Unsupported document type"


# Validation exceptions

class ValidationError(BaseAppException):
    """Exception raised when input validation fails."""
    status_code = HTTPStatus.BAD_REQUEST
    detail = "Validation error"


# Database exceptions

class DatabaseError(BaseAppException):
    """Base exception for database-related errors."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "Database operation failed"


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    detail = "Failed to connect to database"


class DatabaseQueryError(DatabaseError):
    """Exception raised when a database query fails."""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    detail = "Database query failed"