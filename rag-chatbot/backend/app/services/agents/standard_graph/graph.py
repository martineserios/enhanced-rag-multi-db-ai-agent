"""
Graph implementation for the standard graph-based agent.

This module implements the LangGraph workflow for the standard graph-based agent,
providing a sophisticated conversation flow with memory, RAG, and database querying.
"""
from typing import Dict, List, Any, Optional, TypedDict, Annotated, Literal
from datetime import datetime
import uuid
import logging
import time

from langgraph.graph import Graph, StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.config import Settings
from app.api.models.chat import ChatRequest, ChatResponse
from app.services.llm.factory import get_llm_service
from app.services.memory.manager import get_memory_manager
from app.services.database import query_postgres, query_mongo
from app.core.exceptions import ValidationError

logger = get_logger(__name__)

# Define the state type for our graph
class ChatState(TypedDict):
    """State type for the chat graph."""
    request: ChatRequest
    conversation_id: str
    context: str
    memory_sources: Dict[str, bool]
    response: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    metrics: Dict[str, Any]
    next_step: Optional[Literal["llm_response", "error", "end"]]
    provider: str

class ValidationNode:
    """Node responsible for validating the chat request."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    async def __call__(self, state: ChatState) -> ChatState:
        """Validate the chat request."""
        request = state["request"]
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Validate provider
            provider = request.provider.value if hasattr(request.provider, "value") else request.provider
            if not provider:
                provider = self.settings.default_llm_provider.value if hasattr(self.settings.default_llm_provider, "value") else self.settings.default_llm_provider
            
            # Check if provider API key is configured
            api_key_attr = f"{provider}_api_key"
            api_key_value = getattr(self.settings, api_key_attr, None)
            
            if not hasattr(self.settings, api_key_attr) or not api_key_value:
                raise ValidationError(f"{provider.capitalize()} API key is not configured")
            
            # Update metrics
            metrics["validation_time"] = time.time() - start_time
            metrics["provider"] = provider
            
            return {**state, "metrics": metrics, "next_step": "context_retrieval"}
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}

class ContextRetrievalNode:
    """Node responsible for retrieving context from various sources."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
    
    async def __call__(self, state: ChatState) -> ChatState:
        """Retrieve context from memory, SQL, and MongoDB."""
        request = state["request"]
        context = ""
        memory_sources = state["memory_sources"]
        metrics = state.get("metrics", {})
        prompt_template = state["metadata"]["prompt_template"]
        start_time = time.time()
        
        try:
            # Get context from memory if enabled
            if self.settings.memory_enabled and request.use_memory:
                try:
                    memory_types = request.memory_types or self.settings.get_enabled_memory_types()
                    memory_context = await self.memory_manager.create_unified_context(
                        query=request.message,
                        conversation_id=state["conversation_id"],
                        memory_types=memory_types,
                        weights=request.memory_weights
                    )
                    
                    if memory_context:
                        for memory_type in memory_types:
                            memory_sources[memory_type] = True
                        context += prompt_template.format_context(
                            source="Memory",
                            content=memory_context,
                            relevance=1.0
                        )
                        
                except Exception as e:
                    logger.error(f"Error retrieving context from memory: {str(e)}")
            
            # Get SQL context if requested
            if request.use_sql:
                try:
                    sql_results = await query_postgres(
                        question=request.message,
                        settings=self.settings
                    )
                    if sql_results:
                        context += prompt_template.format_context(
                            source="SQL Database",
                            content=sql_results,
                            relevance=0.8
                        )
                except Exception as e:
                    logger.error(f"Error querying SQL database: {str(e)}")
            
            # Get MongoDB context if requested
            if request.use_mongo:
                try:
                    mongo_results = await query_mongo(
                        question=request.message,
                        settings=self.settings
                    )
                    if mongo_results:
                        context += prompt_template.format_context(
                            source="MongoDB",
                            content=mongo_results,
                            relevance=0.8
                        )
                except Exception as e:
                    logger.error(f"Error querying MongoDB: {str(e)}")
            
            metrics["context_retrieval_time"] = time.time() - start_time
            metrics["context_length"] = len(context)
            
            # Set next_step to llm_response if context retrieval was successful
            return {
                **state,
                "context": context,
                "memory_sources": memory_sources,
                "metrics": metrics,
                "next_step": "llm_response"
            }
            
        except Exception as e:
            logger.error(f"Error in context retrieval: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}

class LLMResponseNode:
    """Node responsible for generating responses using the LLM."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    async def __call__(self, state: ChatState) -> ChatState:
        """Generate a response using the LLM."""
        request = state["request"]
        metrics = state.get("metrics", {})
        prompt_template = state["metadata"]["prompt_template"]
        settings = state["metadata"]["settings"]
        start_time = time.time()
        
        try:
            # Get provider directly from state
            provider = state["provider"]
            if not provider:
                raise ValueError("Provider not set in state")
            
            llm_service = get_llm_service(provider, self.settings)
            
            response = await llm_service.generate_response(
                query=request.message,
                context=state["context"]
            )
            
            metrics["llm_response_time"] = time.time() - start_time
            metrics["response_length"] = len(response)
            
            return {**state, "response": response, "metrics": metrics, "next_step": "memory_storage"}
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}

class MemoryStorageNode:
    """Node responsible for storing conversation in memory."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
    
    async def __call__(self, state: ChatState) -> ChatState:
        """Store the conversation in memory if enabled."""
        if not self.settings.memory_enabled or not state["request"].use_memory:
            return {**state, "next_step": "end"}
        
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            content = {
                "user_message": state["request"].message,
                "assistant_message": state["response"],
                "agent_id": "standard_graph"  # Add agent ID to content
            }
            
            metadata = {
                # Get provider directly from state
                "provider": state.get("provider"),
                "timestamp": datetime.utcnow().isoformat(),
                "memory_types_used": [
                    memory_type for memory_type, used in state["memory_sources"].items() if used
                ],
                "metrics": metrics,
                "agent_id": "standard_graph",  # Add agent ID to metadata
                "agent_name": "Graph-based Agent"  # Add agent name to metadata
            }
            
            message_key = f"conversation:{state['conversation_id']}:message:{uuid.uuid4()}"
            
            memory_types = state["request"].memory_types or self.settings.get_enabled_memory_types()
            for memory_type in memory_types:
                if memory_type in ["short_term", "episodic"]:
                    await self.memory_manager.store_memory(
                        memory_type=memory_type,
                        content=content,
                        key=message_key,
                        metadata=metadata,
                        conversation_id=state["conversation_id"]
                    )
            
            metrics["memory_storage_time"] = time.time() - start_time
            return {**state, "metrics": metrics, "next_step": "end"}
            
        except Exception as e:
            logger.error(f"Error storing conversation in memory: {str(e)}")
            # Don't fail the request if memory storage fails
            return {**state, "next_step": "end"}

class StandardErrorHandlerNode:
    """Node responsible for handling errors."""

    async def __call__(self, state: ChatState) -> ChatState:
        """Return the state with the error message."""
        logger.error(f"Error encountered in graph: {state.get('error')}")
        # Return state with error, will be handled by calling service
        return state

def router(state: ChatState) -> str:
    """Route to the next node based on the state."""
    return state["next_step"] or "end"

def create_agent_graph(settings: Settings) -> Graph:
    """Create the chat processing graph."""

    # Define the nodes
    settings_instance = settings # Use the settings instance passed to the function
    context_retrieval_node = ContextRetrievalNode(settings=settings_instance)
    llm_response_node = LLMResponseNode(settings=settings_instance)
    memory_storage_node = MemoryStorageNode(settings=settings_instance)
    error_handler_node = StandardErrorHandlerNode()

    # Build the graph
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("retrieve_context", context_retrieval_node)
    workflow.add_node("generate_response", llm_response_node)
    workflow.add_node("store_memory", memory_storage_node)
    workflow.add_node("error_handler", error_handler_node)

    # Set the entry point
    workflow.set_entry_point("retrieve_context")

    # Add edges based on the router function
    workflow.add_conditional_edges(
        "retrieve_context",
        router,
        {
            "llm_response": "generate_response",
            "error": "error_handler",
        },
    )
    workflow.add_conditional_edges(
        "generate_response",
        router,
        {
            "memory_storage": "store_memory",
            "error": "error_handler",
        },
    )
    workflow.add_conditional_edges(
        "store_memory",
        router,
        {
            "end": END,
        },
    )

    # Add edge from error handler to END
    workflow.add_edge("error_handler", END)

    # Compile the graph
    app = workflow.compile()

    return app 