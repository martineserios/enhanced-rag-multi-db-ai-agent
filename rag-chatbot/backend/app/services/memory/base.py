# filepath: backend/services/memory/base.py
"""
Base classes for memory system components.

This module defines the interface for all memory systems using the Strategy pattern,
allowing different memory implementations to be used interchangeably.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, TypeVar, Generic
from datetime import datetime
import logging

from app.core.logging import get_logger
from app.core.exceptions import MemoryError, MemoryStorageError, MemoryRetrievalError

# Generic type for memory content
T = TypeVar('T')

logger = get_logger(__name__)

class MemorySystem(ABC, Generic[T]):
    """
    Abstract base class for all memory systems.
    
    This class defines the interface that all memory systems must implement,
    regardless of their specific implementation details.
    """
    
    def __init__(self, name: str):
        """
        Initialize the memory system.
        
        Args:
            name: A name for this memory system (used for logging)
        """
        self.name = name
        self.logger = get_logger(f"memory.{name}")
    
    @abstractmethod
    async def store(self, key: str, content: T, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """
        Store content in the memory system.
        
        Args:
            key: A unique identifier for the content
            content: The content to store
            metadata: Additional metadata to store with the content
            **kwargs: Additional implementation-specific parameters
            
        Returns:
            A unique identifier for the stored content
            
        Raises:
            MemoryStorageError: If storing the content fails
        """
        pass
    
    @abstractmethod
    async def retrieve(self, key: str, **kwargs) -> Optional[T]:
        """
        Retrieve content from the memory system.
        
        Args:
            key: The identifier for the content to retrieve
            **kwargs: Additional implementation-specific parameters
            
        Returns:
            The retrieved content, or None if not found
            
        Raises:
            MemoryRetrievalError: If retrieving the content fails
        """
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for content in the memory system.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            **kwargs: Additional implementation-specific parameters
            
        Returns:
            A list of matching content items with metadata
            
        Raises:
            MemoryRetrievalError: If searching fails
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str, **kwargs) -> bool:
        """
        Delete content from the memory system.
        
        Args:
            key: The identifier for the content to delete
            **kwargs: Additional implementation-specific parameters
            
        Returns:
            True if content was deleted, False otherwise
            
        Raises:
            MemoryError: If deleting the content fails
        """
        pass
    
    @abstractmethod
    async def clear(self, **kwargs) -> None:
        """
        Clear all content from the memory system.
        
        Args:
            **kwargs: Additional implementation-specific parameters
            
        Raises:
            MemoryError: If clearing the memory fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the memory system is healthy and available.
        
        Returns:
            True if the memory system is healthy, False otherwise
        """
        pass
    
    async def __aenter__(self):
        """Support for async context manager protocol."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support for async context manager protocol."""
        # Implement any cleanup here if needed
        pass


class MemoryItem(Generic[T]):
    """
    A generic container for an item stored in memory.
    
    This class provides a consistent structure for all memory items,
    regardless of the memory system they come from.
    """
    
    def __init__(
        self,
        key: str,
        content: T,
        memory_type: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a memory item.
        
        Args:
            key: A unique identifier for the content
            content: The content stored in memory
            memory_type: The type of memory system the item came from
            timestamp: When the item was created or updated
            metadata: Additional metadata about the item
        """
        self.key = key
        self.content = content
        self.memory_type = memory_type
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the memory item to a dictionary.
        
        Returns:
            A dictionary representation of the memory item
        """
        return {
            "key": self.key,
            "content": self.content,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }