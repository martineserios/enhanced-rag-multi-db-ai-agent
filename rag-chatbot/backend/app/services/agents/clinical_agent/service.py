"""
Clinical Agent Service (Spanish-speaking).

This module implements the Spanish-speaking clinical agent service that provides
direct diagnosis and treatment recommendations.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from app.core.logging import get_logger
from app.config import Settings
from app.api.models.chat import ChatRequest, ChatResponse
from app.services.agents.base import BaseAgent
from app.services.agents.clinical_agent.graph import create_clinical_agent_graph, ClinicalChatState
from app.services.agents.clinical_agent.prompts import ClinicalPromptTemplate
from app.services.memory.manager import get_memory_manager

logger = get_logger(__name__)

class ClinicalAgent(BaseAgent):
    """Spanish-speaking clinical agent service."""
    
    def __init__(self, settings: Settings):
        """Initialize the clinical agent."""
        super().__init__(settings)
        self.graph = create_clinical_agent_graph(settings)
        self.prompt_template = ClinicalPromptTemplate()
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
    
    @property
    def agent_id(self) -> str:
        """Get the agent's unique identifier."""
        return "clinical_es"
    
    @property
    def agent_name(self) -> str:
        """Get the agent's human-readable name."""
        return "Asistente Clínico"
    
    @property
    def agent_description(self) -> str:
        """Get the agent's description."""
        return (
            "Asistente clínico en español que proporciona diagnósticos y recomendaciones de tratamiento "
            "basados en síntomas y historial médico. Este agente está diseñado para ayudar en la "
            "evaluación inicial de condiciones médicas y proporcionar orientación sobre próximos pasos."
        )
    
    @property
    def agent_settings_schema(self) -> Dict[str, Any]:
        """Get the agent's settings schema."""
        # Get base schema
        base_schema = self.base_memory_settings_schema
        
        # Define agent-specific schema
        agent_schema = {
            "type": "object",
            "properties": {
                "max_history_items": {
                    "type": "integer",
                    "description": "Número máximo de elementos del historial a considerar",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "urgency_threshold": {
                    "type": "string",
                    "description": "Umbral para determinar la urgencia de una condición",
                    "enum": ["bajo", "medio", "alto"],
                    "default": "medio"
                },
                "include_treatment_options": {
                    "type": "boolean",
                    "description": "Incluir opciones de tratamiento en las respuestas",
                    "default": True
                },
                "include_follow_up": {
                    "type": "boolean",
                    "description": "Incluir recomendaciones de seguimiento",
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
        """Get available settings for this agent."""
        # Get base settings
        base_settings = {
            "short_term_memory": self.settings.memory_enabled,
            "semantic_memory": self.settings.memory_enabled,
            "episodic_memory": self.settings.memory_enabled,
            "procedural_memory": self.settings.memory_enabled,
            "use_rag": True,
            "use_sql": True,
            "use_mongo": True
        }
        
        # Get agent-specific settings
        agent_settings = {
            "max_history_items": 5,
            "urgency_threshold": "medio",
            "include_treatment_options": True,
            "include_follow_up": True
        }
        
        # Merge settings
        return {**base_settings, **agent_settings}
    
    async def process_chat_request(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat request using the clinical agent.
        
        Args:
            request: The chat request to process
            
        Returns:
            ChatResponse containing the agent's response
        """
        # Initialize conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        provider = self._validate_provider(request)
        
        try:
            # Initialize state
            state: ClinicalChatState = {
                "request": request,
                "conversation_id": conversation_id,
                "medical_context": "",
                "detected_terms": {},
                "patient_history": {},
                "response": None,
                "error": None,
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_id": self.agent_id,
                    "agent_name": self.agent_name,
                    "settings": await self.get_available_settings()
                },
                "metrics": {
                    "provider": request.provider.value if hasattr(request.provider, "value") else request.provider
                },
                "next_step": None
            }
            
            # Run the graph
            final_state = await self.graph.ainvoke(state)
            
            # Create response
            response = ChatResponse(
                message=final_state["response"],
                conversation_id=conversation_id,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                metadata=final_state["metadata"],
                metrics=final_state["metrics"],
                provider=provider
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing clinical request: {str(e)}", exc_info=True)
            return ChatResponse(
                message=(
                    "Lo siento, pero encontré un error al procesar su solicitud. "
                    "Para emergencias médicas, por favor contacte a los servicios de emergencia "
                    "o a su proveedor de salud inmediatamente."
                ),
                conversation_id=conversation_id,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                error=str(e),
                provider=provider
            )
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the clinical agent."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "description": self.agent_description,
            "capabilities": [
                "Análisis de síntomas",
                "Diagnóstico clínico",
                "Evaluación de urgencia",
                "Recomendaciones de tratamiento",
                "Historial del paciente"
            ],
            "language": "es",
            "version": "1.0.0"
        } 