"""
Medical Research Agent implementation.

This agent specializes in medical literature and research, providing
evidence-based responses with citations and clinical context using a
graph-based workflow.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging

from app.services.agents.base import BaseAgent, AgentError
from app.api.models.chat import ChatRequest, ChatResponse
from app.core.logging import get_logger
from app.services.agents.medical_research.graph import create_medical_agent_graph, MedicalChatState

logger = get_logger(__name__)

class MedicalResearchAgent(BaseAgent):
    """Medical Research Agent implementation using graph-based workflow."""
    
    def __init__(self, settings):
        logger.info("Initializing MedicalResearchAgent.")
        super().__init__(settings)
        self.graph = create_medical_agent_graph(settings)
        logger.info("MedicalResearchAgent initialized successfully.")
    
    @property
    def agent_id(self) -> str:
        return "medical_research"
    
    @property
    def agent_name(self) -> str:
        return "Medical Research Agent"
    
    @property
    def agent_description(self) -> str:
        return (
            "A specialized agent focused on medical research and literature. "
            "This agent provides evidence-based responses with citations from "
            "medical literature, clinical guidelines, and research papers. "
            "It uses a graph-based workflow to process medical queries, "
            "retrieve relevant literature, manage evidence levels, and "
            "generate clinically appropriate responses."
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
                "use_medical_literature": {
                    "type": "boolean",
                    "description": "Whether to use medical literature for context",
                    "default": True
                },
                "citation_style": {
                    "type": "string",
                    "description": "Citation style to use (e.g. AMA, APA)",
                    "default": "AMA",
                    "enum": ["AMA", "APA", "Vancouver"]
                },
                "max_citations": {
                    "type": "integer",
                    "description": "Maximum number of citations to include",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                },
                "evidence_level": {
                    "type": "string",
                    "description": "Minimum evidence level to include",
                    "default": "all",
                    "enum": ["all", "1", "2", "3", "4", "5"]
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
            "use_medical_literature": True,  # Always available
            "citation_style": getattr(self.settings, "medical_citation_style", "AMA"),
            "max_citations": getattr(self.settings, "medical_max_citations", 5),
            "evidence_level": getattr(self.settings, "medical_evidence_level", "all"),
            "max_context_length": getattr(self.settings, "max_context_length", 2000),
            "temperature": getattr(self.settings, "temperature", 0.7)
        }
        
        # Merge settings
        return {**base_settings, **agent_settings}
    
    async def process_chat_request(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message using the medical research agent implementation.
        
        This implementation uses a graph-based workflow to:
        - Process medical queries
        - Retrieve relevant literature
        - Manage evidence levels
        - Generate clinically appropriate responses with citations
        """
        # Initialize conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Get agent settings
        settings = await self.get_available_settings()
        
        # Get memory sources using base method
        memory_sources = self._get_memory_sources(settings)
        
        logger.info(
            f"Processing chat request using medical research agent",
            extra={
                "conversation_id": conversation_id,
                "provider": request.provider,
                "agent_id": self.agent_id,
                "message_length": len(request.message),
                "settings": settings  # Log all settings
            }
        )
        
        try:
            # Initialize graph state
            initial_state: MedicalChatState = {
                "request": request,
                "conversation_id": conversation_id,
                "medical_context": "",
                "evidence_sources": [],
                "citations": [],
                "memory_sources": memory_sources,
                "response": None,
                "error": None,
                "metadata": {
                    "settings": settings,
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_id": self.agent_id,
                    "agent_name": self.agent_name,
                    "citation_style": settings["citation_style"],
                    "max_citations": settings["max_citations"],
                    "evidence_level": settings["evidence_level"]
                },
                "metrics": {},
                "next_step": None
            }
            
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
                context=final_state["medical_context"],
                memory_sources=memory_sources,
                settings=settings,
                metrics=final_state["metrics"],
                additional_content={
                    "evidence_sources": final_state["evidence_sources"],
                    "citations": final_state["citations"]
                }
            )
            
            # Get provider from request or metrics
            provider = request.provider or final_state["metrics"].get("provider")
            if not provider:
                raise AgentError("Provider not set in request or metrics")

            # Create response using base method with medical-specific metadata
            return self._create_base_response(
                response=final_state["response"],
                conversation_id=conversation_id,
                provider=provider,
                memory_sources=memory_sources,
                settings=settings,
                metrics=final_state["metrics"],
                additional_metadata={
                    "medical_metadata": {
                        "evidence_sources": len(final_state["evidence_sources"]),
                        "citations": len(final_state["citations"]),
                        "evidence_level": final_state["metadata"]["evidence_level"],
                        "citation_style": final_state["metadata"]["citation_style"]
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error in medical research agent: {str(e)}")
            raise AgentError(f"Error processing request: {str(e)}") 