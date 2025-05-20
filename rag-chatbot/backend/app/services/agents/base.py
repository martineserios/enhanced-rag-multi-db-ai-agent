"""
Base interfaces for all chat agents and prompt templates.

This module defines the common interfaces that all chat agents and prompt templates
must implement. Each agent can have its own implementation of the chat processing
logic and prompt management while maintaining consistent interfaces.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.api.models.chat import ChatRequest, ChatResponse
from app.config import Settings
from app.services.memory.manager import get_memory_manager
import logging
import uuid

logger = logging.getLogger(__name__)

class BasePromptTemplate(ABC):
    """Base class for all agent prompt templates."""
    
    @abstractmethod
    def get_system_prompt(
        self,
        context: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Get the system prompt for the agent.
        
        Args:
            context: Optional context information to include
            settings: Optional agent settings to customize the prompt
            **kwargs: Additional parameters for prompt customization
            
        Returns:
            The formatted system prompt
        """
        pass
    
    @abstractmethod
    def format_context(
        self,
        source: str,
        content: str,
        relevance: float = 1.0
    ) -> str:
        """
        Format context information for inclusion in the prompt.
        
        Args:
            source: The source of the context (e.g. "Memory", "SQL Database")
            content: The context content
            relevance: Relevance score for the context (0.0 to 1.0)
            
        Returns:
            Formatted context string
        """
        pass
    
    @abstractmethod
    def format_user_message(
        self,
        message: str,
        **kwargs
    ) -> str:
        """
        Format a user message for inclusion in the prompt.
        
        Args:
            message: The user's message
            **kwargs: Additional parameters for message formatting
            
        Returns:
            Formatted user message
        """
        pass

class BaseAgent(ABC):
    """Base interface for all chat agents"""
    
    def __init__(self, settings: Settings):
        """Initialize the agent with application settings"""
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
    
    def _validate_provider(self, request: ChatRequest) -> str:
        """
        Validate and get the provider from request or settings.
        This is a common implementation that can be used by all agents.
        
        Args:
            request: The chat request containing provider information
            
        Returns:
            The validated provider string
            
        Raises:
            AgentError: If provider is not available or not configured
        """
        # Get provider from request or settings
        if hasattr(request.provider, "value"):
            provider = request.provider.value
        elif request.provider:
            provider = request.provider
        elif hasattr(self.settings.default_llm_provider, "value"):
            provider = self.settings.default_llm_provider.value
        else:
            provider = self.settings.default_llm_provider

        # Check if provider API key is configured
        api_key_attr = f"{provider}_api_key"
        api_key_value = getattr(self.settings, api_key_attr, None)
        
        if not hasattr(self.settings, api_key_attr) or not api_key_value:
            raise AgentError(f"{provider.capitalize()} API key is not configured")
            
        return provider
    
    def _get_memory_sources(self, settings: Dict[str, Any]) -> Dict[str, bool]:
        """
        Get memory source settings in a consistent format.
        This is a common implementation that can be used by all agents.
        
        Args:
            settings: The agent settings dictionary
            
        Returns:
            Dictionary of memory source settings
        """
        return {
            "short_term": settings["short_term_memory"],
            "semantic": settings["semantic_memory"],
            "episodic": settings["episodic_memory"],
            "procedural": settings["procedural_memory"]
        }
    
    def _create_base_response(
        self,
        response: str,
        conversation_id: str,
        provider: str,
        memory_sources: Dict[str, bool],
        settings: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Create a ChatResponse with all required fields.
        This is a common implementation that can be used by all agents.
        
        Args:
            response: The agent's response message
            conversation_id: The conversation ID
            provider: The LLM provider
            memory_sources: Dictionary of memory source settings
            settings: The agent settings
            metrics: Optional metrics dictionary
            additional_metadata: Optional additional metadata
            
        Returns:
            ChatResponse with all required fields
        """
        metadata = {
            "settings": settings,
            "metrics": metrics or {}
        }
        
        if additional_metadata:
            metadata.update(additional_metadata)
            
        return ChatResponse(
            message=response,
            conversation_id=conversation_id,
            provider=provider,  # Required field
            agent_id=self.agent_id,  # Required field
            agent_name=self.agent_name,  # Required field
            memory_sources=memory_sources,
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata
        )
    
    async def _store_conversation_memory(
        self,
        conversation_id: str,
        request: ChatRequest,
        response: str,
        context: str,
        memory_sources: Dict[str, bool],
        settings: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None,
        additional_content: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store conversation in memory with consistent structure.
        This is a common implementation that can be used by all agents.
        
        Args:
            conversation_id: The conversation ID
            request: The original chat request
            response: The agent's response
            context: The context used for the response
            memory_sources: Dictionary of memory source settings
            settings: The agent settings
            metrics: Optional metrics dictionary
            additional_content: Optional additional content to store
        """
        if not any(memory_sources.values()):
            return
            
        content = {
            "user_message": request.message,
            "assistant_message": response,
            "context": context,
            "agent_id": self.agent_id
        }
        
        if additional_content:
            content.update(additional_content)
            
        metadata = {
            "provider": request.provider,
            "timestamp": datetime.utcnow().isoformat(),
            "settings": settings,
            "conversation_id": conversation_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "memory_sources": memory_sources
        }
        
        if metrics:
            metadata["metrics"] = metrics
            
        await self.store_conversation_memory(
            conversation_id=conversation_id,
            content=content,
            metadata=metadata
        )
    
    @property
    def base_memory_settings_schema(self) -> Dict[str, Any]:
        """
        Base schema for memory and data source settings that all agents inherit.
        These settings control the agent's access to different memory systems and data sources.
        """
        return {
            "type": "object",
            "properties": {
                # Memory Systems
                "short_term_memory": {
                    "type": "boolean",
                    "description": "Use short-term memory (Redis) for recent conversation context",
                    "default": True
                },
                "semantic_memory": {
                    "type": "boolean",
                    "description": "Use semantic memory (ChromaDB) for document knowledge",
                    "default": True
                },
                "episodic_memory": {
                    "type": "boolean",
                    "description": "Use episodic memory (MongoDB) for conversation history",
                    "default": True
                },
                "procedural_memory": {
                    "type": "boolean",
                    "description": "Use procedural memory (Neo4j) for action workflows",
                    "default": True
                },
                # Data Sources
                "use_rag": {
                    "type": "boolean",
                    "description": "Use RAG (ChromaDB) for semantic search",
                    "default": True
                },
                "use_sql": {
                    "type": "boolean",
                    "description": "Use SQL database (PostgreSQL) for structured data",
                    "default": True
                },
                "use_mongo": {
                    "type": "boolean",
                    "description": "Use MongoDB for document storage",
                    "default": True
                }
            }
        }
    
    @property
    @abstractmethod
    def agent_id(self) -> str:
        """
        Unique identifier for the agent.
        This should be a short, lowercase string without spaces.
        Example: 'standard', 'standard_graph', 'expert_agent'
        """
        pass
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """
        Human-readable name for the agent.
        This will be displayed in the UI.
        Example: 'Standard Agent', 'Graph-based Agent', 'Expert Agent'
        """
        pass
    
    @property
    @abstractmethod
    def agent_description(self) -> str:
        """
        Description of the agent's capabilities and characteristics.
        This will be shown in the UI to help users choose the right agent.
        """
        pass
    
    @property
    @abstractmethod
    def agent_settings_schema(self) -> Dict[str, Any]:
        """
        JSON schema for agent-specific settings.
        This defines what settings can be configured for this agent.
        The schema should be merged with base_memory_settings_schema.
        
        Example implementation in agent class:
        ```python
        @property
        def agent_settings_schema(self) -> Dict[str, Any]:
            # Get base schema
            base_schema = self.base_memory_settings_schema
            
            # Define agent-specific schema
            agent_schema = {
                "type": "object",
                "properties": {
                    # Agent-specific settings here
                }
            }
            
            # Merge schemas
            merged_schema = {
                "type": "object",
                "properties": {
                    **base_schema["properties"],
                    **agent_schema["properties"]
                }
            }
            
            return merged_schema
        ```
        """
        pass
    
    @abstractmethod
    async def process_chat_request(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message using this agent's implementation.
        
        Args:
            request: The chat request containing the message and context
            
        Returns:
            ChatResponse containing the agent's response
            
        Raises:
            AgentError: If there's an error processing the request
        """
        pass
    
    @abstractmethod
    async def get_available_settings(self) -> Dict[str, Any]:
        """
        Get available settings for this agent.
        This should return the current settings and their values.
        The implementation should include both base memory settings and agent-specific settings.
        
        Example implementation in agent class:
        ```python
        async def get_available_settings(self) -> Dict[str, Any]:
            # Get base settings
            base_settings = {
                "short_term_memory": self.settings.memory_enabled,
                "semantic_memory": self.settings.memory_enabled,
                "episodic_memory": self.settings.memory_enabled,
                "procedural_memory": self.settings.memory_enabled,
                "use_rag": True,  # Always available
                "use_sql": True,  # Always available
                "use_mongo": True  # Always available
            }
            
            # Get agent-specific settings
            agent_settings = {
                # Agent-specific settings here
            }
            
            # Merge settings
            return {**base_settings, **agent_settings}
        ```
        """
        pass
    
    async def get_conversations(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent conversations for this agent.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            Dictionary containing conversation information
        """
        if not self.settings.memory_enabled or not self.memory_manager:
            return {"conversations": []}
            
        try:
            # Get conversations from memory manager
            conversations = await self.memory_manager.get_conversations(
                agent_id=self.agent_id,
                limit=limit
            )
            
            # Format conversations for response
            formatted_conversations = []
            for conv in conversations:
                # Get the latest message from the conversation
                latest_message = conv.get("content", {}).get("assistant_message", "")
                if not latest_message:
                    latest_message = conv.get("content", {}).get("user_message", "")
                
                formatted_conversations.append({
                    "conversation_id": conv.get("conversation_id"),
                    "latest_message": latest_message,
                    "latest_time": conv.get("metadata", {}).get("timestamp"),
                    "message_count": conv.get("metadata", {}).get("message_count", 1),
                    "agent_id": self.agent_id,
                    "agent_name": self.agent_name
                })
            
            return {"conversations": formatted_conversations}
            
        except Exception as e:
            logger.error(f"Error retrieving conversations: {str(e)}")
            return {"conversations": []}
    
    async def store_conversation_memory(
        self,
        conversation_id: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store conversation in memory systems.
        This is a common implementation that can be used by all agents.
        
        Args:
            conversation_id: The ID of the conversation
            content: The conversation content to store
            metadata: Additional metadata about the conversation
        """
        if not metadata:
            metadata = {}
            
        # Add agent-specific metadata
        metadata.update({
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Store in memory systems using the semantically meaningful method
        await self.memory_manager.store_conversation(
            conversation_id=conversation_id,
            content=content,
            metadata=metadata
        )

class AgentError(Exception):
    """Base exception for agent-related errors"""
    pass

class AgentConfigurationError(AgentError):
    """Raised when there's an error in agent configuration"""
    pass

class AgentProcessingError(AgentError):
    """Raised when there's an error processing a chat request"""
    pass 