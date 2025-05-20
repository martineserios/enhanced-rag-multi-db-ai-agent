# filepath: backend/services/memory/manager.py
"""
Memory Manager for coordinating different memory systems.

This module implements the Memory Manager, which orchestrates interactions
with different memory systems using the Facade pattern. It provides a unified
interface for storing and retrieving information across multiple memory types.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from app.config import Settings
from app.core.exceptions import (
    MemoryError,
    MemoryInitializationError,
    MemoryRetrievalError,
    MemoryStorageError,
)
from app.core.logging import get_logger, log_execution_time
from app.services.memory.base import MemoryItem, MemorySystem

# Type for specific memory system implementations
T = TypeVar('T', bound=MemorySystem)

from app.services.memory.episodic import EpisodicMemory
from app.services.memory.procedural import ProceduralMemory
from app.services.memory.semantic import SemanticMemory

# Import specific memory implementations
from app.services.memory.short_term import ShortTermMemory

logger = get_logger(__name__)

class MemoryManager:
    """
    Manages access to different memory systems.
    
    This class:
    1. Provides a unified interface to multiple memory systems
    2. Implements Multi-Context Processing to combine information from different sources
    3. Manages resources and connections for memory systems
    4. Implements fallback strategies when specific memory systems are unavailable
    
    It follows the Facade design pattern, simplifying the interface to the memory subsystems.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the memory manager with configuration settings.
        
        Args:
            settings: Application configuration settings
            
        Raises:
            MemoryInitializationError: If initialization fails
        """
        self.settings = settings
        self.logger = logger
        
        # Dictionary to store memory system instances
        self.memory_systems: Dict[str, MemorySystem] = {}
        
        # Flag to track initialization status
        self.initialized = False
    
    @log_execution_time(logger)
    async def initialize(self) -> None:
        """
        Initialize all memory systems.
        
        This method initializes each memory system and performs health checks.
        
        Raises:
            MemoryInitializationError: If initialization fails
        """
        try:
            self.logger.info("Initializing memory systems")
            
            # Initialize short-term memory (Redis)
            if self.settings.enable_short_term_memory:
                short_term = ShortTermMemory(
                    settings=self.settings,
                    ttl=self.settings.short_term_ttl
                )
                # Initialize the Redis connection asynchronously
                if not await short_term.initialize():
                    self.logger.warning("Short-term memory initialization completed but health check failed")
                self.memory_systems['short_term'] = short_term
                
            # Initialize semantic memory (ChromaDB)
            if self.settings.enable_semantic_memory:
                self.memory_systems['semantic'] = SemanticMemory(
                    settings=self.settings
                )
            
            # Initialize episodic memory (MongoDB)
            if self.settings.enable_episodic_memory:
                self.memory_systems['episodic'] = EpisodicMemory(
                    settings=self.settings
                )
            
            # Initialize procedural memory (Neo4j)
            if self.settings.enable_procedural_memory:
                self.memory_systems['procedural'] = ProceduralMemory(
                    settings=self.settings
                )
            
            # Perform health checks
            health_results = await self._check_memory_systems_health()
            
            # Log initialization results
            for memory_type, status in health_results.items():
                if status:
                    self.logger.info(f"Memory system '{memory_type}' initialized successfully")
                else:
                    self.logger.warning(f"Memory system '{memory_type}' is unhealthy or unavailable")
            
            self.initialized = True
            self.logger.info("Memory manager initialization complete")
            
        except Exception as e:
            self.logger.exception("Failed to initialize memory systems")
            raise MemoryInitializationError(f"Memory initialization failed: {str(e)}")
    
    async def _check_memory_systems_health(self) -> Dict[str, bool]:
        """
        Check the health of all initialized memory systems.
        
        Returns:
            A dictionary mapping memory system names to health status
        """
        health_results = {}
        
        for name, system in self.memory_systems.items():
            try:
                health_results[name] = await system.health_check()
            except Exception as e:
                self.logger.exception(f"Health check failed for memory system '{name}'")
                health_results[name] = False
        
        return health_results
    
    def _get_memory_system(self, memory_type: str) -> MemorySystem:
        """
        Get a specific memory system instance.
        
        Args:
            memory_type: The type of memory system to get
            
        Returns:
            The memory system instance
            
        Raises:
            MemoryError: If the memory system is not initialized
        """
        if not self.initialized:
            raise MemoryError("Memory manager is not initialized")
        
        memory_system = self.memory_systems.get(memory_type)
        if memory_system is None:
            raise MemoryError(f"Memory system '{memory_type}' is not available")
        
        return memory_system
    
    @log_execution_time(logger)
    async def store_memory(
        self,
        memory_type: str,
        content: Any,
        key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Store content in a specific memory system.
        
        Args:
            memory_type: The type of memory system to use
            content: The content to store
            key: A unique identifier for the content (generated if not provided)
            metadata: Additional metadata to store with the content
            **kwargs: Additional parameters for the specific memory system
            
        Returns:
            The key used to store the content
            
        Raises:
            MemoryStorageError: If storing the content fails
        """
        try:
            memory_system = self._get_memory_system(memory_type)
            
            # Generate a key if not provided
            if key is None:
                key = f"{memory_type}:{uuid.uuid4()}"
            
            # Add timestamp to metadata if not present
            if metadata is None:
                metadata = {}
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.utcnow().isoformat()
            
            # Store the content
            return await memory_system.store(key, content, metadata, **kwargs)
            
        except Exception as e:
            self.logger.exception(f"Failed to store in memory system '{memory_type}'")
            raise MemoryStorageError(f"Failed to store in {memory_type} memory: {str(e)}")
    
    @log_execution_time(logger)
    async def store_conversation(
        self,
        conversation_id: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Store a conversation in episodic memory.
        This is a higher-level method that provides a more semantically meaningful
        interface for storing conversations.
        
        Args:
            conversation_id: The ID of the conversation
            content: The conversation content (must contain user_message and/or assistant_message)
            metadata: Additional metadata about the conversation
            **kwargs: Additional parameters for the memory system
            
        Returns:
            The key used to store the conversation
            
        Raises:
            MemoryStorageError: If storing the conversation fails
            ValueError: If content is missing required fields
        """
        try:
            # Validate content
            if not isinstance(content, dict):
                raise ValueError("Content must be a dictionary")
            
            if not content.get("user_message") and not content.get("assistant_message"):
                raise ValueError("Content must contain either user_message or assistant_message")
            
            # Generate a unique key for the message
            key = f"conversation:{conversation_id}:message:{uuid.uuid4()}"
            
            # Add conversation-specific metadata
            if metadata is None:
                metadata = {}
            metadata.update({
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Store in episodic memory
            return await self.store_memory(
                memory_type="episodic",
                content=content,
                key=key,
                metadata=metadata,
                conversation_id=conversation_id,
                **kwargs
            )
            
        except Exception as e:
            self.logger.exception("Failed to store conversation")
            raise MemoryStorageError(f"Failed to store conversation: {str(e)}")
    
    @log_execution_time(logger)
    async def retrieve_memory(
        self,
        memory_type: str,
        key: str,
        **kwargs
    ) -> Optional[Any]:
        """
        Retrieve content from a specific memory system.
        
        Args:
            memory_type: The type of memory system to use
            key: The identifier for the content to retrieve
            **kwargs: Additional parameters for the specific memory system
            
        Returns:
            The retrieved content, or None if not found
            
        Raises:
            MemoryRetrievalError: If retrieving the content fails
        """
        try:
            memory_system = self._get_memory_system(memory_type)
            return await memory_system.retrieve(key, **kwargs)
            
        except Exception as e:
            self.logger.exception(f"Failed to retrieve from memory system '{memory_type}'")
            raise MemoryRetrievalError(f"Failed to retrieve from {memory_type} memory: {str(e)}")
    
    @log_execution_time(logger)
    async def search_memory(
        self,
        memory_type: str,
        query: str,
        limit: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for content in a specific memory system.
        
        Args:
            memory_type: The type of memory system to use
            query: The search query
            limit: Maximum number of results to return
            **kwargs: Additional parameters for the specific memory system
            
        Returns:
            A list of matching content items with metadata
            
        Raises:
            MemoryRetrievalError: If searching fails
        """
        try:
            memory_system = self._get_memory_system(memory_type)
            return await memory_system.search(query, limit, **kwargs)
            
        except Exception as e:
            self.logger.exception(f"Failed to search memory system '{memory_type}'")
            raise MemoryRetrievalError(f"Failed to search {memory_type} memory: {str(e)}")
    
    @log_execution_time(logger)
    async def multi_context_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        memory_types: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
        limit_per_type: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query multiple memory systems and combine the results.
        
        This method implements the Multi-Context Processing pattern by querying
        multiple memory systems in parallel and aggregating the results.
        
        Args:
            query: The search query
            conversation_id: Optional conversation ID for context
            memory_types: List of memory types to query (all available if None)
            weights: Relative importance weights for different memory types
            limit_per_type: Maximum results to return per memory type
            
        Returns:
            Dictionary mapping memory types to search results
            
        Raises:
            MemoryRetrievalError: If the multi-context query fails
        """
        if not self.initialized:
            raise MemoryError("Memory manager is not initialized")
        
        try:
            # Determine which memory systems to query
            if memory_types is None:
                memory_types = list(self.memory_systems.keys())
            
            # Filter to only available memory systems
            available_types = [
                memory_type for memory_type in memory_types
                if memory_type in self.memory_systems
            ]
            
            if not available_types:
                return {}
            
            # Default weights if not provided
            if weights is None:
                weights = {memory_type: 1.0 for memory_type in available_types}
            
            # Prepare arguments for each memory type
            search_tasks = {}
            
            for memory_type in available_types:
                memory_system = self.memory_systems[memory_type]
                
                # Add memory-specific parameters
                kwargs = {"limit": limit_per_type}
                
                if memory_type == "short_term" and conversation_id:
                    kwargs["conversation_id"] = conversation_id
                    
                if memory_type == "episodic" and conversation_id:
                    kwargs["conversation_id"] = conversation_id
                
                # Create the search task
                search_tasks[memory_type] = self.search_memory(
                    memory_type=memory_type,
                    query=query,
                    **kwargs
                )
            
            # Execute all searches in parallel
            results = {}
            
            # Wait for all searches to complete
            for memory_type, task in search_tasks.items():
                try:
                    results[memory_type] = await task
                except Exception as e:
                    self.logger.exception(f"Failed to search {memory_type} memory")
                    results[memory_type] = []
            
            return results
            
        except Exception as e:
            self.logger.exception("Multi-context query failed")
            raise MemoryRetrievalError(f"Multi-context query failed: {str(e)}")
    
    @log_execution_time(logger)
    async def create_unified_context(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        memory_types: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
        limit_per_type: int = 5
    ) -> str:
        """
        Create a unified context string from all memory types.
        
        This method queries multiple memory systems and formats the results
        into a single context string for an LLM.
        
        Args:
            query: The search query
            conversation_id: Optional conversation ID for context
            memory_types: List of memory types to query (all available if None)
            weights: Relative importance weights for different memory types
            limit_per_type: Maximum results to return per memory type
            
        Returns:
            A formatted context string
            
        Raises:
            MemoryRetrievalError: If creating the unified context fails
        """
        try:
            # Get results from all memory systems
            all_memory = await self.multi_context_query(
                query=query,
                conversation_id=conversation_id,
                memory_types=memory_types,
                weights=weights,
                limit_per_type=limit_per_type
            )
            
            context_parts = []
            
            # Format short-term memory results
            if "short_term" in all_memory and all_memory["short_term"]:
                context_parts.append("## Recent Conversation Context")
                for item in all_memory["short_term"]:
                    context_parts.append(f"User: {item.get('user_message', '')}")
                    context_parts.append(f"Assistant: {item.get('assistant_message', '')}")
                    context_parts.append("")
            
            # Format semantic memory results
            if "semantic" in all_memory and all_memory["semantic"]:
                context_parts.append("## Relevant Document Information")
                for i, doc in enumerate(all_memory["semantic"]):
                    context_parts.append(f"Document {i+1}: {doc.get('content', '')}")
                    context_parts.append("")
            
            # Format episodic memory results
            if "episodic" in all_memory and all_memory["episodic"]:
                context_parts.append("## Similar Past Conversations")
                for i, convo in enumerate(all_memory["episodic"][:2]):
                    context_parts.append(f"Past Conversation {i+1}:")
                    context_parts.append(f"User: {convo.get('user_message', '')}")
                    context_parts.append(f"Assistant: {convo.get('assistant_message', '')}")
                    context_parts.append("")
            
            # Format procedural memory results
            if "procedural" in all_memory and all_memory["procedural"]:
                context_parts.append("## Relevant Procedure")
                for i, step in enumerate(all_memory["procedural"]):
                    context_parts.append(f"Step {i+1}: {step.get('description', '')}")
                context_parts.append("")
            
            # If no context was generated, return empty string
            if not context_parts:
                return ""
            
            # Combine all context parts
            unified_context = "\n".join(context_parts)
            
            return unified_context
            
        except Exception as e:
            self.logger.exception("Failed to create unified context")
            raise MemoryRetrievalError(f"Failed to create unified context: {str(e)}")
    
    async def close(self) -> None:
        """
        Close all memory system connections.
        
        This method should be called when shutting down the application
        to release resources properly.
        """
        close_tasks = []
        
        for name, system in self.memory_systems.items():
            self.logger.info(f"Closing memory system: {name}")
            # Add each system's close method to tasks
            if hasattr(system, "close") and callable(getattr(system, "close")):
                close_tasks.append(system.close())
        
        # Wait for all close operations to complete
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.logger.info("All memory systems closed")


# Singleton instance of MemoryManager
_memory_manager = None

async def init_memory_manager(settings: Settings) -> MemoryManager:
    """
    Initialize the global memory manager.
    
    Args:
        settings: Application configuration settings
        
    Returns:
        The memory manager instance
        
    Raises:
        MemoryInitializationError: If initialization fails
    """
    global _memory_manager
    
    if _memory_manager is None:
        _memory_manager = MemoryManager(settings)
        await _memory_manager.initialize()
    
    return _memory_manager

def get_memory_manager() -> MemoryManager:
    """
    Get the global memory manager instance.
    
    Returns:
        The memory manager instance
        
    Raises:
        MemoryError: If the memory manager is not initialized
    """
    global _memory_manager
    
    if _memory_manager is None:
        raise MemoryError("Memory manager not initialized")
    
    return _memory_manager