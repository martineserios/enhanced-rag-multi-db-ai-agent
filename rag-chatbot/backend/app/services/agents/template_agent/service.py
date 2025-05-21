"""
Template chat agent implementation.

This agent serves as a template for creating new specialized agents using langgraph.
"""
from typing import Dict, Any
from app.services.agents.base import BaseAgent, AgentError
from app.api.models.chat import ChatRequest, ChatResponse
from app.core.logging import get_logger
from app.config import Settings
from .graph import create_template_agent_graph, TemplateChatState
import uuid
from datetime import datetime

logger = get_logger(__name__)

class TemplateAgent(BaseAgent):
    """Template chat agent implementation using langgraph."""

    def __init__(self, settings: Settings):
        logger.info("Initializing TemplateAgent.")
        super().__init__(settings)
        self.graph = None  # Graph will be initialized on first use
        logger.info("TemplateAgent initialized successfully.")

    @property
    def agent_id(self) -> str:
        return "template_agent"

    @property
    def agent_name(self) -> str:
        return "Template Agent"

    @property
    def agent_description(self) -> str:
        return (
            "This is a template agent based on langgraph, "
            "designed to be customized for specific domains or tasks. "
            "It includes basic validation, processing, analysis, "
            "response generation, and memory storage steps."
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
                "processing_level": {
                    "type": "string",
                    "description": "Level of detail for processing (e.g., 'basic', 'advanced')",
                    "default": "basic",
                    "enum": ["basic", "advanced", "expert"]
                },
                "max_references": {
                    "type": "integer",
                    "description": "Maximum number of references to include",
                    "default": 3,
                    "minimum": 0,
                    "maximum": 10
                },
                "reference_style": {
                    "type": "string",
                    "description": "Citation style for references (e.g., 'apa', 'mla')",
                    "default": "apa",
                    "enum": ["apa", "mla", "chicago", "ieee"]
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
            "processing_level": getattr(self.settings, "processing_level", "basic"),
            "max_references": getattr(self.settings, "max_references", 3),
            "reference_style": getattr(self.settings, "reference_style", "inline"),
            "max_context_length": getattr(self.settings, "max_context_length", 2000),
            "temperature": getattr(self.settings, "temperature", 0.7)
        }
        
        # Merge settings
        return {**base_settings, **agent_settings}

    async def get_graph_data(self) -> Dict[str, Any]:
        """
        Get graph visualization data for the template agent.
        
        Returns:
            Dictionary containing nodes and edges for visualization
        """
        return {
            "nodes": {
                "process": {
                    "name": "Process Input",
                    "description": "Processes domain-specific information",
                    "style": "fill:#e6f3ff,stroke:#333,stroke-width:2px"
                },
                "analyze": {
                    "name": "Analyze",
                    "description": "Analyzes processed information",
                    "style": "fill:#e6ffe6,stroke:#333,stroke-width:2px"
                },
                "generate": {
                    "name": "Generate Response",
                    "description": "Generates response with references",
                    "style": "fill:#ffe6e6,stroke:#333,stroke-width:2px"
                },
                "store_memory": {
                    "name": "Store Memory",
                    "description": "Stores conversation in memory",
                    "style": "fill:#fff2e6,stroke:#333,stroke-width:2px"
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
                    "from": "process",
                    "to": "analyze",
                    "label": "Processed"
                },
                {
                    "from": "analyze",
                    "to": "generate",
                    "label": "Analyzed"
                },
                {
                    "from": "generate",
                    "to": "store_memory",
                    "label": "Response Ready"
                },
                {
                    "from": "generate",
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
        Process a chat message using the template agent graph.
        
        This implementation provides a template workflow that can be customized
        for specific domains or tasks, including:
        - Request validation
        - Domain-specific processing
        - Reference management
        - Response generation
        """
        # Initialize conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Get agent settings
        settings = await self.get_available_settings()
        
        # Get memory sources using base method
        memory_sources = self._get_memory_sources(settings)
        
        logger.info(
            f"Processing chat request using template agent",
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
            self.graph = create_template_agent_graph(self.settings)

        # Prepare the initial state for the graph
        initial_state: TemplateChatState = {
            "request": request,
            "conversation_id": conversation_id,
            "context": "",
            "sources": [],
            "references": [],
            "memory_sources": memory_sources,
            "detected_terms": {},
            "specialized_data": [],
            "response": None,
            "error": None,
            "metadata": {
                "settings": settings,
                "processing_level": settings["processing_level"],
                "max_references": settings["max_references"],
                "reference_style": settings["reference_style"]
            },
            "metrics": {},
            "next_step": None
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
                metrics=final_state["metrics"],
                additional_content={
                    "sources": final_state["sources"],
                    "references": final_state["references"]
                }
            )
            
            # Get provider from request or metrics
            provider = request.provider or final_state["metrics"].get("provider")
            if not provider:
                raise AgentError("Provider not set in request or metrics")

            # Create response using base method with template-specific metadata
            return self._create_base_response(
                response=final_state["response"],
                conversation_id=conversation_id,
                provider=provider,
                memory_sources=memory_sources,
                settings=settings,
                metrics=final_state["metrics"],
                additional_metadata={
                    "template_metadata": {
                        "processing_level": final_state["metadata"]["processing_level"],
                        "sources_count": len(final_state["sources"]),
                        "references_count": len(final_state["references"]),
                        "reference_style": final_state["metadata"]["reference_style"]
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error in template agent: {str(e)}")
            raise AgentError(f"Error processing request: {str(e)}") 