"""
Standard graph-based chat agent implementation.

This agent uses langgraph to implement a more sophisticated conversation flow
with access to memory, RAG, and database querying.
"""
from typing import Dict, Any
from app.services.agents.base import BaseAgent, AgentError
from app.api.models.chat import ChatRequest, ChatResponse
from app.services.llm.factory import get_llm_service
from app.services.llm.base import LLMProviderError
from app.core.logging import get_logger
from app.services.agents.standard_graph.prompts import StandardGraphPromptTemplate
from .graph import create_agent_graph, ChatState
import uuid
from datetime import datetime

logger = get_logger(__name__)

class StandardGraphAgent(BaseAgent):
    """Standard graph-based chat agent implementation."""
    
    def __init__(self, settings):
        logger.info("Initializing StandardGraphAgent.")
        super().__init__(settings)
        self.graph = None  # Will be initialized on first use
        self.prompt_template = StandardGraphPromptTemplate()
        logger.info("StandardGraphAgent initialized successfully.")
    
    @property
    def agent_id(self) -> str:
        return "standard_graph"
    
    @property
    def agent_name(self) -> str:
        return "Graph-based Agent"
    
    @property
    def agent_description(self) -> str:
        return (
            "A sophisticated agent that uses langgraph to implement "
            "advanced conversation flows with memory, RAG, and database "
            "querying capabilities. This agent can handle complex "
            "multi-step reasoning and task decomposition."
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
                },
                "max_iterations": {
                    "type": "integer",
                    "description": "Maximum number of graph iterations",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                },
                "task_decomposition": {
                    "type": "boolean",
                    "description": "Enable task decomposition for complex queries",
                    "default": True
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
            "temperature": getattr(self.settings, "temperature", 0.7),
            "max_iterations": getattr(self.settings, "max_iterations", 5),
            "task_decomposition": getattr(self.settings, "task_decomposition", True)
        }
        
        # Merge settings
        return {**base_settings, **agent_settings}
    
    async def get_graph_data(self) -> Dict[str, Any]:
        """
        Get graph visualization data for the standard graph agent.
        
        Returns:
            Dictionary containing nodes and edges for visualization
        """
        return {
            "nodes": {
                "retrieve_context": {
                    "name": "Context Retrieval",
                    "description": "Retrieves context from memory, SQL, and MongoDB",
                    "style": "fill:#e6f3ff,stroke:#333,stroke-width:2px"
                },
                "generate_response": {
                    "name": "Response Generation",
                    "description": "Generates response using LLM",
                    "style": "fill:#e6ffe6,stroke:#333,stroke-width:2px"
                },
                "store_memory": {
                    "name": "Memory Storage",
                    "description": "Stores conversation in memory systems",
                    "style": "fill:#ffe6e6,stroke:#333,stroke-width:2px"
                },
                "error_handler": {
                    "name": "Error Handler",
                    "description": "Handles errors in the workflow",
                    "style": "fill:#ffe6cc,stroke:#333,stroke-width:2px"
                },
                "END": {
                    "name": "End",
                    "description": "End of conversation",
                    "style": "fill:#f2f2f2,stroke:#333,stroke-width:2px"
                }
            },
            "edges": [
                {
                    "from": "retrieve_context",
                    "to": "generate_response",
                    "label": "Context Ready"
                },
                {
                    "from": "retrieve_context",
                    "to": "error_handler",
                    "label": "Error"
                },
                {
                    "from": "generate_response",
                    "to": "store_memory",
                    "label": "Response Ready"
                },
                {
                    "from": "generate_response",
                    "to": "error_handler",
                    "label": "Error"
                },
                {
                    "from": "store_memory",
                    "to": "END",
                    "label": "Complete"
                },
                {
                    "from": "error_handler",
                    "to": "END",
                    "label": "Error Handled"
                }
            ]
        }
    
    async def process_chat_request(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message using the standard graph agent.
        
        This implementation provides a sophisticated conversation flow using langgraph,
        including:
        - Request validation
        - Context collection
        - Response generation
        - Memory management
        """
        # Initialize conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Get agent settings
        settings = await self.get_available_settings()
        
        # Get memory sources using base method
        memory_sources = self._get_memory_sources(settings)
        
        logger.info(
            f"Processing chat request using standard graph agent",
            extra={
                "conversation_id": conversation_id,
                "provider": request.provider,
                "agent_id": self.agent_id,
                "message_length": len(request.message),
                "settings": settings  # Log all settings
            }
        )

        # Initialize graph if not already done
        if self.graph is None:
            self.graph = create_agent_graph(self.settings)

        # Prepare the initial state for the graph
        initial_state: ChatState = {
            "request": request,
            "conversation_id": conversation_id,
            "context": "",
            "memory_sources": memory_sources,
            "response": None,
            "error": None,
            "metadata": {
                "prompt_template": self.prompt_template,
                "settings": settings,
                "max_iterations": settings["max_iterations"],
                "task_decomposition": settings["task_decomposition"]
            },
            "metrics": {},
            "next_step": None,
            "provider": request.provider.value if hasattr(request.provider, "value") else request.provider
        }
        
        try:
            # Execute graph workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            # Check for errors
            if final_state.get("error"):
                raise AgentError(final_state["error"])
            
            # Store conversation in memory using base method
            await self._store_conversation_memory(
                conversation_id=conversation_id,
                request=request,
                response=final_state["response"],
                context=final_state["context"],
                memory_sources=memory_sources,
                settings=settings,
                metrics=final_state["metrics"]
            )
            
            # Get provider from request or metrics
            provider = request.provider or final_state["metrics"].get("provider")
            if not provider:
                raise AgentError("Provider not set in request or metrics")

            # Create response using base method
            return self._create_base_response(
                response=final_state["response"],
                conversation_id=conversation_id,
                provider=provider,
                memory_sources=memory_sources,
                settings=settings,
                metrics=final_state["metrics"]
            )
            
        except Exception as e:
            logger.error(f"Error in standard graph agent: {str(e)}")
            raise AgentError(f"Error processing request: {str(e)}") 