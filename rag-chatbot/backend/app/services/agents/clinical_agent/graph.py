"""
Clinical Agent implementation (Spanish-speaking).

This module implements a LangGraph workflow for a Spanish-speaking clinical agent that provides
direct diagnosis and treatment recommendations based on symptoms and medical history.
"""
from typing import Dict, List, Any, Optional, TypedDict, Annotated, Literal
from datetime import datetime
import uuid
import logging
import time
import re

from langgraph.graph import Graph, StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.config import Settings
from app.api.models.chat import ChatRequest, ChatResponse
from app.services.llm.factory import get_llm_service
from app.services.memory.manager import get_memory_manager
from app.services.database import query_postgres, query_mongo

logger = get_logger(__name__)

# Spanish medical terminology patterns for symptom and condition detection
MEDICAL_TERMS = {
    "sintomas": r"\b(dolor|fiebre|tos|dolor de cabeza|nausea|vomito|fatiga|mareo|erupcion|hinchazon)\b",
    "condiciones": r"\b(diabetes|hipertension|asma|artritis|infeccion|inflamacion|enfermedad|sindrome)\b",
    "severidad": r"\b(severo|leve|moderado|agudo|cronico|emergencia|urgente)\b",
    "duracion": r"\b(dias|semanas|meses|anos|repentino|gradual|persistente|intermitente)\b"
}

class ClinicalChatState(TypedDict):
    """State type for the clinical chat graph."""
    request: ChatRequest
    conversation_id: str
    medical_context: str
    detected_terms: Dict[str, List[str]]  # Detected symptoms and conditions
    patient_history: Dict[str, Any]  # Relevant patient history
    response: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    metrics: Dict[str, Any]
    next_step: Optional[Literal["analyze", "diagnose", "treat", "store_memory", "error", "end"]]

class ClinicalAnalysisNode:
    """Node responsible for analyzing symptoms and medical history in Spanish."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
        self.llm_service = None
    
    async def __call__(self, state: ClinicalChatState) -> ClinicalChatState:
        """Analyze symptoms and medical history in Spanish."""
        request = state["request"]
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Initialize LLM service if needed
            if not self.llm_service:
                provider = request.provider.value if hasattr(request.provider, "value") else request.provider
                if not provider:
                    provider = self.settings.default_llm_provider.value
                self.llm_service = get_llm_service(provider, self.settings)
            
            # Detect medical terms in Spanish
            detected_terms = self._detect_medical_terms(request.message)
            
            # Get patient history if available
            patient_history = {}
            if self.settings.memory_enabled and request.use_memory:
                try:
                    history_context = await self.memory_manager.create_unified_context(
                        query=request.message,
                        conversation_id=state["conversation_id"],
                        memory_types=["episodic"],
                        weights={"episodic": 1.0}
                    )
                    if history_context:
                        patient_history = history_context
                except Exception as e:
                    logger.error(f"Error retrieving patient history: {str(e)}")
            
            metrics["analysis_time"] = time.time() - start_time
            metrics["terms_detected"] = sum(len(terms) for terms in detected_terms.values())
            
            return {
                **state,
                "detected_terms": detected_terms,
                "patient_history": patient_history,
                "metrics": metrics,
                "next_step": "diagnose"
            }
            
        except Exception as e:
            logger.error(f"Error in clinical analysis: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}
    
    def _detect_medical_terms(self, message: str) -> Dict[str, List[str]]:
        """Detect medical terms in Spanish message."""
        detected_terms = {}
        message_lower = message.lower()
        
        for category, pattern in MEDICAL_TERMS.items():
            matches = list(re.finditer(pattern, message_lower))
            if matches:
                detected_terms[category] = [m.group() for m in matches]
        
        return detected_terms

class ClinicalDiagnosisNode:
    """Node responsible for generating clinical diagnosis in Spanish."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_service = None
    
    async def __call__(self, state: ClinicalChatState) -> ClinicalChatState:
        """Generate clinical diagnosis based on symptoms and history in Spanish."""
        request = state["request"]
        detected_terms = state["detected_terms"]
        patient_history = state["patient_history"]
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Initialize LLM service if needed
            if not self.llm_service:
                provider = metrics.get("provider")
                self.llm_service = get_llm_service(provider, self.settings)
            
            # Prepare context for diagnosis in Spanish
            context = "Información del Paciente:\n"
            if detected_terms.get("sintomas"):
                context += f"Síntomas: {', '.join(detected_terms['sintomas'])}\n"
            if detected_terms.get("condiciones"):
                context += f"Condiciones Conocidas: {', '.join(detected_terms['condiciones'])}\n"
            if detected_terms.get("severidad"):
                context += f"Severidad: {', '.join(detected_terms['severidad'])}\n"
            if detected_terms.get("duracion"):
                context += f"Duración: {', '.join(detected_terms['duracion'])}\n"
            if patient_history:
                context += f"\nHistorial del Paciente:\n{patient_history}\n"
            
            # Generate diagnosis in Spanish
            system_prompt = (
                "Eres un asistente clínico enfocado en proporcionar diagnósticos claros y recomendaciones. "
                "Basándote en los síntomas y el historial del paciente, proporciona:\n"
                "1. Un diagnóstico claro o posibles diagnósticos\n"
                "2. Nivel de urgencia (emergencia, urgente, rutina)\n"
            )

            # Get settings from state metadata
            settings = state["metadata"]["settings"]

            # Conditionally add follow-up steps and treatment recommendations based on settings
            if settings.get("include_follow_up", False):
                system_prompt += "3. Pasos recomendados a seguir\n"
            
            if settings.get("include_treatment_options", False):
                 # Adjust the numbering if follow-up was not included
                treatment_step_number = 4 if settings.get("include_follow_up", False) else 3
                system_prompt += f"{treatment_step_number}. Recomendaciones de tratamiento\n\n"

            system_prompt += "Sé directo y claro en tu evaluación. Responde siempre en español."
            
            diagnosis = await self.llm_service.generate_response(
                query=request.message,
                context=context,
                system_prompt=system_prompt
            )
            
            metrics["diagnosis_time"] = time.time() - start_time
            metrics["diagnosis_length"] = len(diagnosis)
            
            return {
                **state,
                "response": diagnosis,
                "metrics": metrics,
                "next_step": "store_memory"
            }
            
        except Exception as e:
            logger.error(f"Error generating diagnosis: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}

class ClinicalMemoryStorageNode:
    """Node responsible for storing clinical conversation in memory."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
    
    async def __call__(self, state: ClinicalChatState) -> ClinicalChatState:
        """Store the clinical conversation in memory if enabled."""
        if not self.settings.memory_enabled or not state["request"].use_memory:
            return {**state, "next_step": "end"}
        
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            content = {
                "user_message": state["request"].message,
                "assistant_message": state["response"],
                "agent_id": "clinical_es",
                "detected_terms": state["detected_terms"],
                "patient_history": state["patient_history"]
            }
            
            metadata = {
                "provider": metrics.get("provider"),
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": "clinical_es",
                "agent_name": "Asistente Clínico"
            }
            
            message_key = f"conversation:{state['conversation_id']}:message:{uuid.uuid4()}"
            
            await self.memory_manager.store_memory(
                memory_type="episodic",
                content=content,
                key=message_key,
                metadata=metadata,
                conversation_id=state["conversation_id"]
            )
            
            metrics["memory_storage_time"] = time.time() - start_time
            return {**state, "metrics": metrics, "next_step": "end"}
            
        except Exception as e:
            logger.error(f"Error storing clinical conversation: {str(e)}")
            return {**state, "next_step": "end"}

class ClinicalErrorHandlerNode:
    """Node responsible for handling clinical errors in Spanish."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    async def __call__(self, state: ClinicalChatState) -> ClinicalChatState:
        """Handle errors in clinical processing."""
        error_message = state.get("error", "Ocurrió un error durante la evaluación clínica.")
        logger.error(f"Clinical error: {error_message}")
        
        return {
            **state,
            "response": (
                "Lo siento, pero encontré un error al procesar su solicitud. "
                "Para emergencias médicas, por favor contacte a los servicios de emergencia o a su proveedor de salud inmediatamente. "
                f"Detalles del error: {error_message}"
            ),
            "next_step": "end"
        }

def router(state: ClinicalChatState) -> str:
    """Route to the next node based on state."""
    if state.get("error"):
        return "error_handler"
    return state.get("next_step", "end")

def create_clinical_agent_graph(settings: Settings) -> Graph:
    """Create the Spanish-speaking clinical agent graph."""
    workflow = StateGraph(ClinicalChatState)
    
    # Add nodes
    workflow.add_node("analyze", ClinicalAnalysisNode(settings))
    workflow.add_node("diagnose", ClinicalDiagnosisNode(settings))
    workflow.add_node("store_memory", ClinicalMemoryStorageNode(settings))
    workflow.add_node("error_handler", ClinicalErrorHandlerNode(settings))
    
    # Define edges
    workflow.add_edge("analyze", "diagnose")
    workflow.add_conditional_edges(
        "diagnose",
        router,
        {
            "store_memory": "store_memory",
            "error_handler": "error_handler",
            "end": END
        }
    )
    workflow.add_edge("store_memory", END)
    workflow.add_edge("error_handler", END)
    
    # Set entry point
    workflow.set_entry_point("analyze")
    
    return workflow.compile() 