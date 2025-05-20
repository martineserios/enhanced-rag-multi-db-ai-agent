"""
Standard chat agent implementation.

This is the default agent that provides balanced capabilities for general conversation,
with access to memory, RAG, and database querying. This version does not use langgraph.
"""
from typing import Dict, Any
from app.services.agents.base import BaseAgent, AgentError
from app.api.models.chat import ChatRequest, ChatResponse
from app.services.llm.factory import get_llm_service
from app.services.llm.base import LLMProviderError, LLMRequestError
from app.services.database import query_postgres, query_mongo
from app.core.logging import get_logger
from app.services.agents.standard.prompts import StandardPromptTemplate
import uuid
from datetime import datetime
from app.services.memory.manager import get_memory_manager

logger = get_logger(__name__)

class StandardAgent(BaseAgent):
    """Standard chat agent implementation with balanced capabilities."""
    
    def __init__(self, settings):
        logger.info("Initializing StandardAgent.")
        super().__init__(settings)
        self.prompt_template = StandardPromptTemplate()
        
        self.llm_service = get_llm_service(
            settings.default_llm_provider,
            settings
        )
        self.memory_manager = (
            get_memory_manager() if settings.memory_enabled else None
        )

        logger.info("StandardAgent initialized successfully.")
    
    @property
    def agent_id(self) -> str:
        return "standard"
    
    @property
    def agent_name(self) -> str:
        return "Standard Agent"
    
    @property
    def agent_description(self) -> str:
        return (
            "A balanced agent that provides general conversation capabilities "
            "with access to memory, RAG, and database querying. This agent "
            "uses a straightforward implementation without langgraph."
        )
    
    @property
    def agent_settings_schema(self) -> Dict[str, Any]:
        # Get base schema
        base_schema = self.base_memory_settings_schema
        
        # Define agent-specific schema
        agent_schema = {
            "type": "object",
            "properties": {
                "use_memory": {
                    "type": "boolean",
                    "description": "Whether to use memory for context (legacy setting, use specific memory types instead)",
                    "default": True
                },
                "max_context_length": {
                    "type": "integer",
                    "description": "Maximum number of tokens to include in context",
                    "default": 2000,
                    "minimum": 100,
                    "maximum": 8000
                },
                "temperature": {
                    "type": "number",
                    "description": "Response temperature (0.0 to 1.0)",
                    "default": 0.7,
                    "minimum": 0.0,
                    "maximum": 1.0
                }
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
    
    async def get_available_settings(self) -> Dict[str, Any]:
        """Get current agent settings"""
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
            "use_memory": self.settings.memory_enabled,  # Legacy setting
            "max_context_length": getattr(self.settings, "max_context_length", 2000),
            "temperature": getattr(self.settings, "temperature", 0.7)
        }
        
        # Merge settings
        return {**base_settings, **agent_settings}
    
    async def process_chat_request(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message using the standard agent implementation.
        
        This implementation provides a balanced approach with:
        - Memory-enhanced RAG
        - SQL and MongoDB querying
        - Standard conversation capabilities
        """
        # Validate provider using base method
        provider = self._validate_provider(request)
        
        # Initialize conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Get agent settings
        settings = await self.get_available_settings()
        
        logger.info(
            f"Processing chat request with {provider} using standard agent",
            extra={
                "conversation_id": conversation_id,
                "provider": provider,
                "agent_id": self.agent_id,
                "message_length": len(request.message),
                "settings": settings  # Log all settings
            }
        )
        
        # Get memory sources using base method
        memory_sources = self._get_memory_sources(settings)
        
        # Collect context from various sources based on settings
        context = ""
        
        # Get context from memory if enabled
        if any(memory_sources.values()):
            try:
                context = await self.memory_manager.create_unified_context(
                    conversation_id=conversation_id,
                    query=request.message,
                    memory_types=[k for k, v in memory_sources.items() if v]
                )
            except Exception as e:
                logger.error(f"Error getting memory context: {str(e)}")
                context = ""
        
        # Get context from RAG if enabled
        if settings["use_rag"]:
            try:
                rag_context = await self.memory_manager.search_memory(
                    query=request.message,
                    memory_type="semantic",
                    limit=3
                )
                if rag_context:
                    context += "\n\nRelevant documents:\n" + "\n".join(rag_context)
            except Exception as e:
                logger.error(f"Error getting RAG context: {str(e)}")
        
        # Get context from SQL if enabled
        if settings["use_sql"]:
            try:
                sql_context = await query_postgres(
                    question=request.message,
                    settings=self.settings
                )
                if sql_context:
                    context += "\n\nSQL Database Results:\n" + sql_context
            except Exception as e:
                logger.error(f"Error querying SQL database: {str(e)}")
        
        # Get context from MongoDB if enabled
        if settings["use_mongo"]:
            try:
                mongo_context = await query_mongo(
                    question=request.message,
                    settings=self.settings
                )
                if mongo_context:
                    context += "\n\nMongoDB Results:\n" + mongo_context
            except Exception as e:
                logger.error(f"Error querying MongoDB: {str(e)}")
        
        # Get system prompt with context
        system_prompt = self.prompt_template.get_system_prompt(
            context=context,
            settings=settings
        )
        
        try:
            # Generate response using LLM
            response = await self.llm_service.generate_response(
                query=request.message,
                context=context,
                temperature=settings["temperature"]
            )
            
            # Store conversation in memory using base method
            await self._store_conversation_memory(
                conversation_id=conversation_id,
                request=request,
                response=response,
                context=context,
                memory_sources=memory_sources,
                settings=settings
            )
            
            # Create response using base method
            return self._create_base_response(
                response=response,
                conversation_id=conversation_id,
                provider=provider,
                memory_sources=memory_sources,
                settings=settings
            )
            
        except LLMRequestError as e:
            logger.error(f"LLM request error: {str(e)}")
            raise AgentError(f"Error generating response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise AgentError(f"Unexpected error: {str(e)}") 